"""
OddNoty — Lanus vs Boca Juniors Live Tracker
═══════════════════════════════════════════════
Match: Lanus vs Boca Juniors
League: Argentina Primera Division
Kickoff: 2026-03-05 00:00 UTC (5:30 AM IST)

Tracks Over 0.5 Goals odds throughout the match.
Sends Telegram alerts on:
  - Match kickoff
  - Goal scored
  - Odds movement > 5%
  - Half-time / Full-time

API Budget (conservative):
  - TheOddsAPI: poll odds every 5 min = ~18 calls per match
  - Football-Data: poll scores every 90s = ~60 calls per match
  Total: ~78 calls — leaves plenty of quota

Usage:
  python scripts/lanus_boca_tracker.py
"""

import asyncio
import aiohttp
import logging
import sys
import os
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "worker")))
from config import WorkerSettings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("tracker")

# ── Config ─────────────────────────────────────────────────────────────────
MATCH_KICKOFF_UTC = "2026-03-05T00:00:00Z"
HOME_TEAM = "Lanus"
AWAY_TEAM = "Boca Juniors"
LEAGUE_KEY = "soccer_argentina_primera_division"

ODDS_API_KEY = "6b8e652ff8ab692f77d80461dca82bbc"
FD_API_KEY = "cb0cec00437c4431b2b17e3065c9714f"
FD_API_KEY_2 = "57e0df313b0c4b589e24c3985ea7bfee"

SCORE_POLL_INTERVAL = 90       # seconds — score updates
ODDS_POLL_INTERVAL = 300       # 5 min — odds updates (conserves quota)
MOVEMENT_THRESHOLD = 5.0       # alert if odds change > 5%
TARGET_LINES = ["0.5", "1.5", "2.5"]  # track multiple O/U lines


# ── Telegram ───────────────────────────────────────────────────────────────

async def tg(bot_token, chat_id, msg):
    """Send Telegram message."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    async with aiohttp.ClientSession() as s:
        async with s.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}) as r:
            if r.status == 200:
                logger.info("📨 Telegram sent")
            else:
                logger.error(f"Telegram error: {r.status}")


# ── Score Fetcher (Football-Data.org) ──────────────────────────────────────

async def fetch_score(api_key):
    """Fetch live scores, return match dict if found."""
    url = "https://api.football-data.org/v4/matches"
    headers = {"X-Auth-Token": api_key}
    params = {"status": "LIVE"}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, headers=headers, params=params,
                             timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status == 429:
                    logger.warning("Football-Data rate limited, switching key...")
                    return None
                if r.status != 200:
                    return None
                data = await r.json()
                for m in data.get("matches", []):
                    home = m.get("homeTeam", {}).get("name", "")
                    away = m.get("awayTeam", {}).get("name", "")
                    if "lanus" in home.lower() or "lanus" in away.lower() or \
                       "boca" in home.lower() or "boca" in away.lower():
                        sc = m.get("score", {})
                        ft = sc.get("fullTime", {})
                        ht = sc.get("halfTime", {})
                        return {
                            "home": m.get("homeTeam", {}).get("shortName", home),
                            "away": m.get("awayTeam", {}).get("shortName", away),
                            "home_score": ft.get("home") or ht.get("home") or 0,
                            "away_score": ft.get("away") or ht.get("away") or 0,
                            "minute": m.get("minute", 0) or 0,
                            "status": m.get("status", "UNKNOWN"),
                        }
                return None
    except Exception as e:
        logger.error(f"Score fetch error: {e}")
        return None


# ── Odds Fetcher (TheOddsAPI) ──────────────────────────────────────────────

async def fetch_ou_odds():
    """Fetch O/U odds for the target match. Returns dict of lines."""
    url = f"https://api.the-odds-api.com/v4/sports/{LEAGUE_KEY}/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "markets": "totals",
        "regions": "uk,eu",
        "oddsFormat": "decimal",
    }
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, params=params,
                             timeout=aiohttp.ClientTimeout(total=10)) as r:
                remaining = r.headers.get("x-requests-remaining", "?")
                logger.info(f"   OddsAPI quota remaining: {remaining}")

                if r.status != 200:
                    logger.error(f"OddsAPI error: {r.status}")
                    return None, remaining

                data = await r.json()
                for ev in data:
                    h = ev.get("home_team", "").lower()
                    a = ev.get("away_team", "").lower()
                    if "lanus" in h or "lanus" in a or "boca" in h or "boca" in a:
                        ou_lines = {}
                        for bm in ev.get("bookmakers", [])[:1]:
                            for mkt in bm.get("markets", []):
                                if mkt.get("key") == "totals":
                                    for o in mkt.get("outcomes", []):
                                        point = str(o.get("point", ""))
                                        side = "over" if o.get("name") == "Over" else "under"
                                        ou_lines.setdefault(point, {})[side] = o.get("price")
                        return ou_lines, remaining
                return None, remaining
    except Exception as e:
        logger.error(f"Odds fetch error: {e}")
        return None, "?"


# ── Movement Detection ─────────────────────────────────────────────────────

def check_movement(old, new, threshold):
    """Compare old and new odds. Return list of movement alerts."""
    alerts = []
    for line in new:
        if line not in old:
            continue
        for side in ["over", "under"]:
            o = old[line].get(side)
            n = new[line].get(side)
            if o and n and o > 0:
                pct = ((n - o) / o) * 100
                if abs(pct) >= threshold:
                    direction = "📈 UP" if pct > 0 else "📉 DOWN"
                    alerts.append({
                        "line": line, "side": side.title(),
                        "old": o, "new": n, "pct": pct, "dir": direction,
                    })
    return alerts


# ── Main Loop ──────────────────────────────────────────────────────────────

async def main():
    settings = WorkerSettings()
    bot_token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID

    kickoff = datetime.fromisoformat(MATCH_KICKOFF_UTC.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)

    print()
    print("=" * 60)
    print(f"  ⚽ OddNoty — {HOME_TEAM} vs {AWAY_TEAM}")
    print(f"  🏆 Argentina Primera Division")
    print(f"  ⏰ Kickoff: {MATCH_KICKOFF_UTC} ({kickoff.strftime('%I:%M %p UTC')})")
    print("=" * 60)
    print()

    # ── Phase 0: Announce tracker ─────────────────────────────────
    await tg(bot_token, chat_id,
        f"🟡 <b>OddNoty Tracker Armed</b>\n\n"
        f"⚽ <b>{HOME_TEAM} vs {AWAY_TEAM}</b>\n"
        f"🏆 Argentina Primera Division\n"
        f"⏰ Kickoff: {kickoff.strftime('%b %d, %I:%M %p UTC')}\n\n"
        f"📌 Tracking: Over/Under 0.5, 1.5, 2.5 Goals\n"
        f"🔔 Alert threshold: {MOVEMENT_THRESHOLD}% movement\n\n"
        f"I'll notify you when the match starts and on every odds shift!"
    )

    # ── Phase 1: Fetch pre-match odds (baseline) ─────────────────
    logger.info("📊 Fetching pre-match baseline odds...")
    prev_odds, remaining = await fetch_ou_odds()
    api_calls = 1

    if prev_odds:
        lines_msg = ""
        for line in sorted(prev_odds.keys()):
            o = prev_odds[line].get("over", "?")
            u = prev_odds[line].get("under", "?")
            lines_msg += f"   O/U {line}: Over <b>{o}</b> | Under <b>{u}</b>\n"
            logger.info(f"   O/U {line}: Over {o} | Under {u}")

        await tg(bot_token, chat_id,
            f"📊 <b>Pre-Match Odds (Baseline)</b>\n\n"
            f"⚽ {HOME_TEAM} vs {AWAY_TEAM}\n\n"
            f"{lines_msg}\n"
            f"📉 Tracking for movements > {MOVEMENT_THRESHOLD}%"
        )
    else:
        logger.warning("No pre-match odds found yet")

    # ── Phase 2: Wait for kickoff ─────────────────────────────────
    wait_seconds = (kickoff - datetime.now(timezone.utc)).total_seconds()
    if wait_seconds > 0:
        logger.info(f"⏳ Waiting {wait_seconds/3600:.1f} hours until kickoff...")
        logger.info(f"   Kickoff: {kickoff.strftime('%Y-%m-%d %H:%M UTC')}")
        logger.info(f"   You can leave this running — it will auto-start tracking!")

        # Check odds every 30 min while waiting (pre-match movement)
        while True:
            remaining_wait = (kickoff - datetime.now(timezone.utc)).total_seconds()
            if remaining_wait <= 0:
                break

            if remaining_wait > 1800:  # More than 30 min to go
                hrs = remaining_wait / 3600
                logger.info(f"   ⏳ {hrs:.1f}h until kickoff... (next odds check in 30 min)")
                await asyncio.sleep(1800)

                # Pre-match odds check
                new_odds, remaining = await fetch_ou_odds()
                api_calls += 1
                if new_odds and prev_odds:
                    movements = check_movement(prev_odds, new_odds, MOVEMENT_THRESHOLD)
                    if movements:
                        for mv in movements:
                            logger.info(f"   ⚡ Pre-match movement: {mv['side']} {mv['line']} "
                                       f"{mv['old']} → {mv['new']} ({mv['pct']:+.1f}%)")
                            await tg(bot_token, chat_id,
                                f"⚡ <b>Pre-Match Odds Movement</b>\n\n"
                                f"⚽ {HOME_TEAM} vs {AWAY_TEAM}\n"
                                f"{mv['dir']}: {mv['side']} {mv['line']}\n"
                                f"Was: <b>{mv['old']}</b> → Now: <b>{mv['new']}</b>\n"
                                f"Change: <b>{mv['pct']:+.1f}%</b>"
                            )
                    prev_odds = new_odds
            else:
                logger.info(f"   ⏳ {remaining_wait:.0f}s to kickoff!")
                await asyncio.sleep(remaining_wait)
                break

    # ── Phase 3: MATCH IS LIVE ────────────────────────────────────
    logger.info("🟢 KICKOFF TIME! Starting live tracking...")
    await tg(bot_token, chat_id,
        f"🟢 <b>KICKOFF!</b>\n\n"
        f"⚽ <b>{HOME_TEAM} vs {AWAY_TEAM}</b>\n"
        f"🏆 Argentina Primera Division\n\n"
        f"Live tracking started!\n"
        f"📊 Score updates every {SCORE_POLL_INTERVAL}s\n"
        f"📈 Odds updates every {ODDS_POLL_INTERVAL // 60} min"
    )

    last_score = "0-0"
    last_odds_time = 0
    fd_key_index = 0
    fd_keys = [FD_API_KEY, FD_API_KEY_2]
    cycle = 0
    match_ended = False

    try:
        while not match_ended:
            cycle += 1
            now_ts = time.time()

            # ── Score check ───────────────────────────────────────
            match_data = await fetch_score(fd_keys[fd_key_index])
            api_calls += 1

            if match_data is None:
                # Try other key
                fd_key_index = (fd_key_index + 1) % len(fd_keys)
                match_data = await fetch_score(fd_keys[fd_key_index])
                api_calls += 1

            if match_data:
                current_score = f"{match_data['home_score']}-{match_data['away_score']}"
                minute = match_data.get("minute", "?")
                status = match_data.get("status", "?")

                logger.info(f"[Cycle {cycle}] ⚽ {HOME_TEAM} vs {AWAY_TEAM} | "
                           f"{current_score} | Min {minute} | Status: {status}")

                # Goal alert
                if current_score != last_score and last_score != "0-0" or \
                   (current_score != "0-0" and last_score == "0-0"):
                    if current_score != last_score:
                        await tg(bot_token, chat_id,
                            f"⚽🎉 <b>GOAL!</b>\n\n"
                            f"⚽ <b>{HOME_TEAM} vs {AWAY_TEAM}</b>\n"
                            f"📊 Score: <b>{current_score}</b> (was {last_score})\n"
                            f"⏱ Minute: {minute}"
                        )
                        last_score = current_score

                # Check for match end
                if status in ("FINISHED", "FULL_TIME", "FT"):
                    match_ended = True
                    await tg(bot_token, chat_id,
                        f"🏁 <b>FULL TIME</b>\n\n"
                        f"⚽ <b>{HOME_TEAM} vs {AWAY_TEAM}</b>\n"
                        f"📊 Final Score: <b>{current_score}</b>\n\n"
                        f"📊 Total API calls: {api_calls}\n"
                        f"📉 OddsAPI remaining: {remaining}"
                    )
                    break

                # Half-time notification
                if status in ("HALF_TIME", "HT", "PAUSED"):
                    logger.info("   ⏸ Half-time")
            else:
                logger.info(f"[Cycle {cycle}] Match not in live feed yet...")

            # ── Odds check (every ODDS_POLL_INTERVAL) ─────────────
            if now_ts - last_odds_time >= ODDS_POLL_INTERVAL:
                last_odds_time = now_ts
                logger.info("   📈 Checking odds...")
                new_odds, remaining = await fetch_ou_odds()
                api_calls += 1

                if new_odds and prev_odds:
                    movements = check_movement(prev_odds, new_odds, MOVEMENT_THRESHOLD)
                    if movements:
                        for mv in movements:
                            score_str = current_score if match_data else "?"
                            min_str = minute if match_data else "?"
                            await tg(bot_token, chat_id,
                                f"🔔 <b>ODDS MOVEMENT</b>\n\n"
                                f"⚽ {HOME_TEAM} vs {AWAY_TEAM}\n"
                                f"📊 {score_str} | ⏱ Min {min_str}\n\n"
                                f"{mv['dir']}: <b>{mv['side']} {mv['line']}</b>\n"
                                f"Was: <b>{mv['old']:.2f}</b>\n"
                                f"Now: <b>{mv['new']:.2f}</b>\n"
                                f"Change: <b>{mv['pct']:+.1f}%</b>"
                            )
                            logger.info(f"   🔔 ALERT: {mv['side']} {mv['line']} "
                                       f"{mv['old']} → {mv['new']} ({mv['pct']:+.1f}%)")
                    else:
                        logger.info("   No significant movement")

                    # Log current odds
                    for line in sorted(new_odds.keys()):
                        o = new_odds[line].get("over", "?")
                        u = new_odds[line].get("under", "?")
                        logger.info(f"   O/U {line}: Over {o} | Under {u}")

                    prev_odds = new_odds
                elif new_odds:
                    prev_odds = new_odds
                    logger.info("   Baseline odds set")

            logger.info(f"   📊 API calls: {api_calls} | Next check: {SCORE_POLL_INTERVAL}s")
            await asyncio.sleep(SCORE_POLL_INTERVAL)

    except KeyboardInterrupt:
        logger.info("🛑 Stopped by user")
        await tg(bot_token, chat_id,
            f"🛑 <b>Tracker Stopped</b>\n\n"
            f"⚽ {HOME_TEAM} vs {AWAY_TEAM}\n"
            f"📊 Last Score: {last_score}\n"
            f"📊 Total API calls: {api_calls}"
        )

    logger.info(f"\n{'='*60}")
    logger.info(f"Session complete. Total API calls: {api_calls}")
    logger.info(f"OddsAPI remaining: {remaining}")


# ── FastAPI Health Check (for Render Free Tier) ──────────────────────────

from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
async def health_check():
    return {
        "status": "OddNoty Tracker is running live!",
        "match": f"{HOME_TEAM} vs {AWAY_TEAM}",
        "time_utc": datetime.now(timezone.utc).isoformat()
    }

async def run_server():
    """Start the health check server on the port provided by Render."""
    port = int(os.environ.get("PORT", 10000))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="error")
    server = uvicorn.Server(config)
    await server.serve()

# ── Main Entry Point ──────────────────────────────────────────────────────

async def start():
    """Run both the health server and the tracker simultaneously."""
    # Start the tracker and the server in parallel
    await asyncio.gather(
        run_server(),
        main()
    )

if __name__ == "__main__":
    try:
        asyncio.run(start())
    except KeyboardInterrupt:
        pass
