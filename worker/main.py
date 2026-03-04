"""OddNoty Worker — Main entry point.

Runs a continuous data pipeline with multi-provider key rotation:

Score Pillar (every SCORE_POLL_INTERVAL seconds):
  1. Select key from score_providers pool
  2. Fetch live matches via provider-specific fetcher
  3. Handle 429/errors → auto-rotate to next key
  4. Cache results

Odds Pillar (every ODDS_POLL_INTERVAL seconds):
  1. Select key from odds_providers pool
  2. Fetch O/U goals odds (0.5, 1.5, 2.5, 3.5 only)
  3. Store odds snapshot → compare with previous → detect movement

Alert Pipeline:
  1. Evaluate alert rules against current match + odds data
  2. Trigger Telegram notifications for matched rules

Key Pool Health:
  - Dashboard printed every HEALTH_DASHBOARD_INTERVAL cycles
  - Graceful degradation: serves cached data when all keys exhausted
"""

import asyncio
import time
import logging
from pathlib import Path

from config import WorkerSettings
from key_pool import KeyPoolManager, KeyStatus
from quota_tracker import create_quota_tracker
from cli_dashboard import print_key_health, format_key_health_compact
from engine.rule_engine import RuleEngine
from notifier.telegram import TelegramNotifier

# Fetchers — imported dynamically based on provider
from fetcher.football_data import FootballDataFetcher
from fetcher.api_football import APIFootballFetcher
from fetcher.theoddsapi import TheOddsAPIFetcher
from fetcher.betfair import BetfairFetcher
from fetcher.sportmonks import SportmonksFetcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("oddnoty.worker")

# ── Cache for graceful degradation ─────────────────────────────────────────
_cached_matches: list[dict] = []
_cached_odds: dict = {}
_cache_timestamp: float = 0.0

# ── Provider → Fetcher mapping ─────────────────────────────────────────────
SCORE_FETCHER_MAP = {
    "football-data": lambda key: FootballDataFetcher(api_key=key.api_key, base_url=key.base_url),
    "api-football": lambda key: APIFootballFetcher(api_key=key.api_key, base_url=key.base_url),
    "sportmonks": lambda key: SportmonksFetcher(api_key=key.api_key),
    "openligadb": lambda key: None,  # TODO: implement OpenLigaDB fetcher
}

ODDS_FETCHER_MAP = {
    "betfair": lambda key: BetfairFetcher(
        app_key=key.api_key,
        username=key.extra.get("username", ""),
        password=key.extra.get("password", ""),
    ),
    "theoddsapi": lambda key: TheOddsAPIFetcher(
        api_key=key.api_key,
        base_url=key.base_url,
        sport_key=key.extra.get("ou_query_params", {}).get("sport", "soccer_epl"),
    ),
}


def _create_score_fetcher(key):
    """Create the appropriate score fetcher for a key's provider."""
    factory = SCORE_FETCHER_MAP.get(key.provider)
    if factory:
        return factory(key)
    logger.warning(f"Unknown score provider: {key.provider}")
    return None


def _create_odds_fetcher(key):
    """Create the appropriate odds fetcher for a key's provider."""
    factory = ODDS_FETCHER_MAP.get(key.provider)
    if factory:
        return factory(key)
    logger.warning(f"Unknown odds provider: {key.provider}")
    return None


# ── Score Pillar ───────────────────────────────────────────────────────────

async def fetch_scores_with_rotation(pool: KeyPoolManager) -> list[dict]:
    """Fetch live matches using the score provider key pool.

    Tries each available key in order. On 429/error, marks the key
    and retries with the next one. Falls back to cached data if all
    keys are exhausted.
    """
    global _cached_matches, _cache_timestamp
    max_retries = 5

    for attempt in range(max_retries):
        key = pool.get_key("score_providers")
        if not key:
            logger.warning("Score pillar: all keys exhausted — serving cached data")
            return _cached_matches

        fetcher = _create_score_fetcher(key)
        if not fetcher:
            continue

        try:
            # Use raw fetch if available for key pool handling
            if hasattr(fetcher, "fetch_live_matches_raw"):
                matches, status_code, headers = await fetcher.fetch_live_matches_raw()
                success = pool.handle_response(key, status_code, headers)
                if success:
                    _cached_matches = matches
                    _cache_timestamp = time.time()
                    return matches
                else:
                    logger.info(f"Score attempt {attempt + 1}: key {key.key_id} returned {status_code}, rotating...")
                    continue
            else:
                # Fallback for fetchers without raw method
                matches = await fetcher.fetch_live_matches()
                pool.record_success(key)
                _cached_matches = matches
                _cache_timestamp = time.time()
                return matches

        except Exception as e:
            logger.error(f"Score fetch error with {key.key_id}: {e}")
            key.error_count += 1
            if key.error_count >= 5:
                key.status = KeyStatus.DEAD
            continue

    logger.error("Score pillar: all retry attempts failed — serving cached data")
    return _cached_matches


# ── Odds Pillar ────────────────────────────────────────────────────────────

async def fetch_odds_with_rotation(pool: KeyPoolManager) -> dict:
    """Fetch O/U goals odds using the odds provider key pool.

    Tries each available key in order. Falls back to cached odds if all
    keys are exhausted. Stale odds are marked with last_updated timestamp.
    """
    global _cached_odds, _cache_timestamp
    max_retries = 5

    for attempt in range(max_retries):
        key = pool.get_key("odds_providers")
        if not key:
            logger.warning("Odds pillar: all keys exhausted — serving stale odds")
            return _cached_odds

        fetcher = _create_odds_fetcher(key)
        if not fetcher:
            continue

        try:
            if key.provider == "betfair":
                # Betfair: fetch all live O/U odds
                odds_data = await fetcher.fetch_all_live_ou_odds()
                if odds_data:
                    pool.record_success(key)
                    _cached_odds = odds_data
                    _cache_timestamp = time.time()
                    return odds_data
                else:
                    logger.info(f"Odds attempt {attempt + 1}: Betfair returned empty, rotating...")
                    continue

            elif key.provider == "theoddsapi":
                # TheOddsAPI: use raw fetch for key pool handling
                if hasattr(fetcher, "fetch_ou_odds_raw"):
                    odds_data, status_code, headers = await fetcher.fetch_ou_odds_raw()
                    success = pool.handle_response(key, status_code, headers)
                    if success:
                        _cached_odds = odds_data
                        _cache_timestamp = time.time()
                        return odds_data
                    else:
                        logger.info(f"Odds attempt {attempt + 1}: TheOddsAPI returned {status_code}, rotating...")
                        continue
                else:
                    odds_data = await fetcher.fetch_ou_odds()
                    pool.record_success(key)
                    _cached_odds = odds_data
                    _cache_timestamp = time.time()
                    return odds_data

        except Exception as e:
            logger.error(f"Odds fetch error with {key.key_id}: {e}")
            key.error_count += 1
            if key.error_count >= 5:
                key.status = KeyStatus.DEAD
            continue

    logger.error("Odds pillar: all retry attempts failed — serving stale odds")
    return _cached_odds


# ── Legacy Single-Key Mode ─────────────────────────────────────────────────

async def run_legacy_pipeline(settings: WorkerSettings) -> None:
    """Original single-key pipeline (fallback when no YAML config exists)."""
    if settings.DATA_SOURCE == "sportmonks":
        fetcher = SportmonksFetcher(api_key=settings.SPORTMONKS_API_KEY)
    else:
        fetcher = TheOddsAPIFetcher(api_key=settings.THEODDSAPI_KEY)

    matches = await fetcher.fetch_live_matches()
    logger.info(f"[Legacy] Fetched {len(matches)} live matches")

    for match in matches:
        odds = await fetcher.fetch_odds(match["match_id"])
        logger.debug(f"Fetched odds for {match.get('home_team')} vs {match.get('away_team')}")

    engine = RuleEngine()
    triggered = await engine.evaluate_all(matches)
    logger.info(f"[Legacy] Triggered {len(triggered)} alerts")

    if triggered:
        notifier = TelegramNotifier(
            bot_token=settings.TELEGRAM_BOT_TOKEN,
            chat_id=settings.TELEGRAM_CHAT_ID,
        )
        for alert in triggered:
            await notifier.send(alert)


# ── Multi-Key Pipeline ─────────────────────────────────────────────────────

async def run_pipeline(settings: WorkerSettings, pool: KeyPoolManager,
                       cycle: int) -> None:
    """Execute one cycle of the multi-key data pipeline."""

    # ── 1. Fetch live matches (Score Pillar) ──────────────────────
    matches = await fetch_scores_with_rotation(pool)
    logger.info(f"Fetched {len(matches)} live matches (score pillar)")

    # ── 2. Fetch O/U odds (Odds Pillar) ───────────────────────────
    odds_data = await fetch_odds_with_rotation(pool)
    logger.info(f"Fetched odds for {len(odds_data)} matches (odds pillar)")

    # TODO: Store odds snapshot to DB
    # TODO: Compare with previous odds (detect movement > threshold)

    # ── 3. Evaluate alert rules ───────────────────────────────────
    engine = RuleEngine()
    triggered = await engine.evaluate_all(matches)
    logger.info(f"Triggered {len(triggered)} alerts")

    # ── 4. Send notifications ─────────────────────────────────────
    if triggered:
        notifier = TelegramNotifier(
            bot_token=settings.TELEGRAM_BOT_TOKEN,
            chat_id=settings.TELEGRAM_CHAT_ID,
        )
        for alert in triggered:
            await notifier.send(alert)

    # ── 5. Health dashboard ───────────────────────────────────────
    if settings.HEALTH_DASHBOARD_INTERVAL > 0 and cycle % settings.HEALTH_DASHBOARD_INTERVAL == 0:
        print_key_health(pool)
    else:
        logger.info(format_key_health_compact(pool))


# ── Entry Point ────────────────────────────────────────────────────────────

async def main() -> None:
    """Main worker loop with multi-key rotation."""
    settings = WorkerSettings()
    config_path = Path(settings.KEY_POOL_CONFIG_PATH)

    # Check if multi-key mode is available
    if config_path.exists():
        logger.info(f"Multi-key mode: loading pool from {config_path}")
        pool = KeyPoolManager(
            config_path=str(config_path),
            strategy=settings.ROTATION_STRATEGY,
            safety_threshold=settings.SAFETY_THRESHOLD,
        )
        logger.info(
            f"Starting OddNoty worker — multi-key mode "
            f"(strategy={settings.ROTATION_STRATEGY}, "
            f"interval={settings.WORKER_INTERVAL_SECONDS}s)"
        )

        cycle = 0
        while True:
            cycle += 1
            try:
                await run_pipeline(settings, pool, cycle)
            except Exception as e:
                logger.error(f"Pipeline error (cycle {cycle}): {e}", exc_info=True)
            await asyncio.sleep(settings.WORKER_INTERVAL_SECONDS)
    else:
        logger.warning(
            f"Key pool config not found at {config_path} — "
            f"falling back to legacy single-key mode"
        )
        logger.info(
            f"Starting OddNoty worker — legacy mode "
            f"(source={settings.DATA_SOURCE}, "
            f"interval={settings.WORKER_INTERVAL_SECONDS}s)"
        )
        while True:
            try:
                await run_legacy_pipeline(settings)
            except Exception as e:
                logger.error(f"Pipeline error: {e}", exc_info=True)
            await asyncio.sleep(settings.WORKER_INTERVAL_SECONDS)


# ── FastAPI Health Check (for Render Free Tier) ──────────────────────────

from fastapi import FastAPI
import uvicorn
import os

app = FastAPI()

@app.get("/")
async def health_check():
    return {
        "status": "OddNoty Worker is running!",
        "time_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    }

async def run_server():
    """Start the health check server on the port provided by Render."""
    port = int(os.environ.get("PORT", 10000))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="error")
    server = uvicorn.Server(config)
    await server.serve()

# ── Main Entry Point ──────────────────────────────────────────────────────

async def start():
    """Run both the health server and the worker simultaneously."""
    # Start the worker and the server in parallel
    await asyncio.gather(
        run_server(),
        main()
    )

if __name__ == "__main__":
    try:
        asyncio.run(start())
    except KeyboardInterrupt:
        pass
