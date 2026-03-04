"""
OddNoty Live Match Tracker — End-to-End Demo

Finds a live match, tracks Over 0.5 goals odds throughout the game,
and sends Telegram notifications when odds change significantly.

API Call Budget (conservative):
  - Football-Data.org: poll scores every 60s (~90 calls per match)
  - API-Football: poll odds every 120s (~45 calls per match)
  Total: ~135 calls — well within free tier limits.

Usage:
    python scripts/live_tracker.py
"""

import asyncio
import aiohttp
import logging
import sys
import os
import time
from datetime import datetime

# Add worker to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "worker")))

from config import WorkerSettings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("live_tracker")

# ── Configuration ──────────────────────────────────────────────────────────

SCORE_POLL_INTERVAL = 60      # seconds between score checks
ODDS_POLL_INTERVAL = 120      # seconds between odds checks
MOVEMENT_THRESHOLD = 5.0      # % change to trigger alert (lower for demo)
TARGET_LINE = "0.5"           # Track Over/Under 0.5 goals

# Keys from goaledge_keys.yaml
FD_API_KEY = "cb0cec00437c4431b2b17e3065c9714f"
APIF_API_KEY = "773042c66cmsh9619e0c0ace271bp1bfffejsn582e31534b17"


# ── Telegram Helper ────────────────────────────────────────────────────────

async def send_telegram(bot_token: str, chat_id: str, message: str):
    """Send a message via Telegram Bot API."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            if resp.status == 200:
                logger.info("📨 Telegram notification sent!")
            else:
                logger.error(f"Telegram failed: {resp.status}")


# ── Score Fetcher (Football-Data.org) ──────────────────────────────────────

async def fetch_live_scores() -> list[dict]:
    """Fetch live matches from Football-Data.org."""
    url = "https://api.football-data.org/v4/matches"
    headers = {"X-Auth-Token": FD_API_KEY}
    params = {"status": "LIVE"}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params,
                               timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                logger.error(f"Football-Data error: {resp.status}")
                return []
            data = await resp.json()
            matches = data.get("matches", [])
            result = []
            for m in matches:
                score = m.get("score", {})
                ft = score.get("fullTime", {})
                ht = score.get("halfTime", {})
                home_score = ft.get("home") or ht.get("home") or 0
                away_score = ft.get("away") or ht.get("away") or 0
                result.append({
                    "match_id": str(m.get("id", "")),
                    "league": m.get("competition", {}).get("name", "?"),
                    "home_team": m.get("homeTeam", {}).get("shortName",
                                  m.get("homeTeam", {}).get("name", "?")),
                    "away_team": m.get("awayTeam", {}).get("shortName",
                                  m.get("awayTeam", {}).get("name", "?")),
                    "home_score": home_score if home_score is not None else 0,
                    "away_score": away_score if away_score is not None else 0,
                    "minute": m.get("minute", 0) or 0,
                })
            return result


# ── Odds Fetcher (API-Football via RapidAPI) ───────────────────────────────

async def fetch_odds_apif(fixture_id: str) -> dict:
    """Fetch Over/Under odds for a fixture from API-Football.

    Uses bet=5 (Over/Under) to filter to O/U markets only.
    Returns dict like: {"0.5": {"over": 1.08, "under": 8.0}, ...}
    """
    url = "https://v3.football.api-sports.io/odds"
    headers = {"x-apisports-key": APIF_API_KEY}
    params = {"fixture": fixture_id, "bet": "5"}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params,
                               timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                logger.error(f"API-Football odds error: {resp.status}")
                return {}
            data = await resp.json()
            return _parse_apif_odds(data)


async def fetch_live_fixtures_apif() -> list[dict]:
    """Fetch live fixtures from API-Football to get fixture IDs."""
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {"x-apisports-key": APIF_API_KEY}
    params = {"live": "all"}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params,
                               timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                logger.error(f"API-Football fixtures error: {resp.status}")
                return []
            data = await resp.json()
            fixtures = data.get("response", [])
            result = []
            for f in fixtures:
                teams = f.get("teams", {})
                goals = f.get("goals", {})
                fixture = f.get("fixture", {})
                status = fixture.get("status", {})
                result.append({
                    "fixture_id": str(fixture.get("id", "")),
                    "home_team": teams.get("home", {}).get("name", "?"),
                    "away_team": teams.get("away", {}).get("name", "?"),
                    "home_score": goals.get("home", 0) or 0,
                    "away_score": goals.get("away", 0) or 0,
                    "minute": status.get("elapsed", 0) or 0,
                    "league": f.get("league", {}).get("name", "?"),
                })
            return result


def _parse_apif_odds(data: dict) -> dict:
    """Parse API-Football odds response into structured O/U data."""
    ou_lines = {}
    response = data.get("response", [])
    if not response:
        return ou_lines

    for entry in response:
        for bookmaker in entry.get("bookmakers", [])[:1]:  # First bookmaker
            for bet in bookmaker.get("bets", []):
                if "over" not in bet.get("name", "").lower() and \
                   "under" not in bet.get("name", "").lower():
                    continue
                for val in bet.get("values", []):
                    value_str = str(val.get("value", ""))
                    odd = val.get("odd")
                    if odd is None:
                        continue
                    try:
                        odd = float(odd)
                    except (ValueError, TypeError):
                        continue

                    if "Over" in value_str:
                        line = value_str.replace("Over ", "")
                        ou_lines.setdefault(line, {})["over"] = odd
                    elif "Under" in value_str:
                        line = value_str.replace("Under ", "")
                        ou_lines.setdefault(line, {})["under"] = odd

    return ou_lines


# ── Movement Detection ─────────────────────────────────────────────────────

def detect_movement(old_odds: float, new_odds: float, threshold: float) -> dict | None:
    """Detect if odds movement exceeds threshold.

    Returns movement info dict or None.
    """
    if old_odds == 0 or old_odds is None or new_odds is None:
        return None

    pct_change = ((new_odds - old_odds) / old_odds) * 100

    if abs(pct_change) >= threshold:
        direction = "📈 INCREASED" if pct_change > 0 else "📉 DECREASED"
        return {
            "direction": direction,
            "old": old_odds,
            "new": new_odds,
            "pct_change": pct_change,
        }
    return None


# ── Main Tracker Loop ──────────────────────────────────────────────────────

async def run_tracker():
    """Main tracking loop."""
    settings = WorkerSettings()
    bot_token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID

    if not bot_token or bot_token == "your_telegram_bot_token_here":
        logger.error("❌ TELEGRAM_BOT_TOKEN not set in .env")
        return
    if not chat_id or chat_id == "your_telegram_chat_id_here":
        logger.error("❌ TELEGRAM_CHAT_ID not set in .env")
        return

    # ── Phase 1: Find a live match ────────────────────────────────
    logger.info("🔍 Looking for live matches...")

    # Try Football-Data first
    matches = await fetch_live_scores()
    apif_fixtures = await fetch_live_fixtures_apif()

    if not matches and not apif_fixtures:
        logger.warning("⚠️  No live matches found right now.")
        logger.info("Try running this script when matches are being played.")

        # Send a Telegram message about no live matches
        await send_telegram(bot_token, chat_id,
            "⚠️ <b>OddNoty Tracker</b>\n\n"
            "No live matches found right now.\n"
            "The tracker will keep checking every 60 seconds..."
        )

        # Keep checking until a match starts
        while not matches and not apif_fixtures:
            logger.info("⏳ Waiting 60s before checking again...")
            await asyncio.sleep(60)
            matches = await fetch_live_scores()
            apif_fixtures = await fetch_live_fixtures_apif()

    # Pick the first live match
    target_match = None
    target_fixture_id = None

    if apif_fixtures:
        target = apif_fixtures[0]
        target_match = target
        target_fixture_id = target["fixture_id"]
        logger.info(f"🎯 Tracking: {target['home_team']} vs {target['away_team']} "
                     f"({target['league']}) — Minute {target['minute']}")
    elif matches:
        target = matches[0]
        target_match = target
        # Try to find matching fixture in API-Football for odds
        for f in apif_fixtures:
            if (target["home_team"].lower() in f["home_team"].lower() or
                f["home_team"].lower() in target["home_team"].lower()):
                target_fixture_id = f["fixture_id"]
                break
        logger.info(f"🎯 Tracking: {target['home_team']} vs {target['away_team']} "
                     f"({target['league']}) — Minute {target.get('minute', 0)}")

    match_label = f"{target_match['home_team']} vs {target_match['away_team']}"

    # ── Phase 2: Send start notification ──────────────────────────
    start_msg = (
        f"🟢 <b>OddNoty — Live Tracker Started</b>\n\n"
        f"⚽ <b>{match_label}</b>\n"
        f"🏆 {target_match.get('league', '?')}\n"
        f"⏱ Minute: {target_match.get('minute', 0)}\n"
        f"📊 Score: {target_match.get('home_score', 0)}-{target_match.get('away_score', 0)}\n\n"
        f"📌 Tracking: <b>Over {TARGET_LINE} Goals</b> odds\n"
        f"🔔 Alert on: >{MOVEMENT_THRESHOLD}% change\n"
        f"⏰ Score poll: every {SCORE_POLL_INTERVAL}s\n"
        f"📉 Odds poll: every {ODDS_POLL_INTERVAL}s"
    )
    await send_telegram(bot_token, chat_id, start_msg)

    # ── Phase 3: Tracking loop ────────────────────────────────────
    previous_over_odds = None
    previous_under_odds = None
    cycle = 0
    last_odds_check = 0
    last_score = f"{target_match.get('home_score', 0)}-{target_match.get('away_score', 0)}"
    total_api_calls = 2  # Already used 2 for initial discovery

    logger.info(f"🏁 Tracking loop started. Press Ctrl+C to stop.")
    logger.info(f"   Score polling: every {SCORE_POLL_INTERVAL}s (Football-Data)")
    logger.info(f"   Odds polling : every {ODDS_POLL_INTERVAL}s (API-Football)")

    try:
        while True:
            cycle += 1
            now = time.time()

            # ── Fetch Score Update ────────────────────────────────
            logger.info(f"── Cycle {cycle} ──")

            score_matches = await fetch_live_scores()
            total_api_calls += 1

            current_match = None
            for m in score_matches:
                if (target_match["home_team"].lower() in m["home_team"].lower() or
                    m["home_team"].lower() in target_match["home_team"].lower()):
                    current_match = m
                    break

            if current_match is None:
                # Match might have ended or half-time
                if not score_matches:
                    logger.warning("⚠️  No live matches found — match may have ended.")
                    await send_telegram(bot_token, chat_id,
                        f"🏁 <b>Match Ended or Half-Time</b>\n\n"
                        f"⚽ {match_label}\n"
                        f"📊 Final Score: {last_score}\n"
                        f"📊 Total API calls used: {total_api_calls}"
                    )
                    break
                else:
                    logger.info(f"Match not found in live list. Other matches still live.")
                    # Check if it's in API-Football
                    apif_check = await fetch_live_fixtures_apif()
                    total_api_calls += 1
                    found = False
                    for f in apif_check:
                        if (target_match["home_team"].lower() in f["home_team"].lower() or
                            f["home_team"].lower() in target_match["home_team"].lower()):
                            found = True
                            current_score = f"{f['home_score']}-{f['away_score']}"
                            logger.info(f"📊 Score: {current_score} | Minute: {f['minute']}")
                            break
                    if not found:
                        logger.warning("Match ended (not in API-Football either).")
                        await send_telegram(bot_token, chat_id,
                            f"🏁 <b>Match Ended</b>\n\n"
                            f"⚽ {match_label}\n"
                            f"📊 Last Score: {last_score}\n"
                            f"📊 Total API calls: {total_api_calls}"
                        )
                        break
                    await asyncio.sleep(SCORE_POLL_INTERVAL)
                    continue

            current_score = f"{current_match['home_score']}-{current_match['away_score']}"
            minute = current_match.get("minute", 0)
            logger.info(f"📊 {match_label} | {current_score} | Min {minute}")

            # Goal scored alert
            if current_score != last_score:
                goal_msg = (
                    f"⚽🎉 <b>GOAL!</b>\n\n"
                    f"⚽ <b>{match_label}</b>\n"
                    f"📊 Score: <b>{current_score}</b> (was {last_score})\n"
                    f"⏱ Minute: {minute}"
                )
                await send_telegram(bot_token, chat_id, goal_msg)
                last_score = current_score

            # ── Fetch Odds Update (less frequently) ───────────────
            if target_fixture_id and (now - last_odds_check >= ODDS_POLL_INTERVAL):
                last_odds_check = now
                logger.info(f"📈 Fetching O/U odds for fixture {target_fixture_id}...")

                ou_odds = await fetch_odds_apif(target_fixture_id)
                total_api_calls += 1

                if ou_odds:
                    # Look for O/U 0.5 specifically
                    line_data = ou_odds.get(TARGET_LINE, {})
                    over_odds = line_data.get("over")
                    under_odds = line_data.get("under")

                    if over_odds:
                        logger.info(f"   Over {TARGET_LINE}: {over_odds} | Under {TARGET_LINE}: {under_odds}")

                        # Check for movement
                        if previous_over_odds is not None:
                            movement = detect_movement(previous_over_odds, over_odds, MOVEMENT_THRESHOLD)
                            if movement:
                                alert_msg = (
                                    f"🔔 <b>ODDS MOVEMENT ALERT</b>\n\n"
                                    f"⚽ <b>{match_label}</b>\n"
                                    f"📊 Score: {current_score} | ⏱ Min: {minute}\n\n"
                                    f"{movement['direction']}\n"
                                    f"📌 Over {TARGET_LINE} Goals:\n"
                                    f"   Was: <b>{movement['old']:.2f}</b>\n"
                                    f"   Now: <b>{movement['new']:.2f}</b>\n"
                                    f"   Change: <b>{movement['pct_change']:+.1f}%</b>"
                                )
                                await send_telegram(bot_token, chat_id, alert_msg)
                                logger.info(f"🔔 ALERT SENT: Over {TARGET_LINE} "
                                           f"{movement['old']} → {movement['new']} "
                                           f"({movement['pct_change']:+.1f}%)")
                            else:
                                logger.info(f"   No significant movement (threshold: {MOVEMENT_THRESHOLD}%)")
                        else:
                            logger.info(f"   First odds reading — baseline set.")
                            # Send initial odds notification
                            await send_telegram(bot_token, chat_id,
                                f"📊 <b>Initial Odds Set</b>\n\n"
                                f"⚽ {match_label} | {current_score} | Min {minute}\n\n"
                                f"📌 Over {TARGET_LINE}: <b>{over_odds}</b>\n"
                                f"📌 Under {TARGET_LINE}: <b>{under_odds}</b>\n\n"
                                f"Tracking for movements >{MOVEMENT_THRESHOLD}%..."
                            )

                        previous_over_odds = over_odds
                        previous_under_odds = under_odds
                    else:
                        logger.info(f"   O/U {TARGET_LINE} line not found. Available: {list(ou_odds.keys())}")
                        # If 0.5 not available, show what IS available
                        if ou_odds and previous_over_odds is None:
                            available = ", ".join(ou_odds.keys())
                            logger.info(f"   Available lines: {available}")
                            await send_telegram(bot_token, chat_id,
                                f"ℹ️ <b>Available O/U Lines</b>\n\n"
                                f"⚽ {match_label}\n"
                                f"Lines: {available}\n\n"
                                f"O/U 0.5 not yet available — will keep checking."
                            )
                else:
                    logger.info(f"   No odds data returned.")

            logger.info(f"   API calls used so far: {total_api_calls}")
            logger.info(f"   Next check in {SCORE_POLL_INTERVAL}s...")
            await asyncio.sleep(SCORE_POLL_INTERVAL)

    except KeyboardInterrupt:
        logger.info("🛑 Tracker stopped by user.")
        await send_telegram(bot_token, chat_id,
            f"🛑 <b>Tracker Stopped</b>\n\n"
            f"⚽ {match_label}\n"
            f"📊 Last Score: {last_score}\n"
            f"📊 Total API calls: {total_api_calls}"
        )


if __name__ == "__main__":
    print()
    print("=" * 60)
    print("  OddNoty Live Match Tracker")
    print("  Tracking Over 0.5 Goals odds with Telegram alerts")
    print("=" * 60)
    print()
    asyncio.run(run_tracker())
