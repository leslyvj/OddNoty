"""TheOddsAPI fetcher.

Odds pillar provider — fetches Over/Under goals odds.
Free tier: 500 requests/month per key.

CRITICAL: Always pass markets=totals to restrict to O/U goals only.
Omitting this param returns h2h + spreads + totals and burns quota 3-4x faster.
"""

import aiohttp
import logging
from key_pool import OU_LABEL_MAP, THEODDSAPI_OU_PARAMS

logger = logging.getLogger("oddnoty.fetcher.theoddsapi")

BASE_URL = "https://api.the-odds-api.com/v4"


class TheOddsAPIFetcher:
    """Fetch live matches and Over/Under odds from TheOddsAPI.

    Always requests markets=totals to stay within O/U goals scope.
    """

    def __init__(self, api_key: str, base_url: str = BASE_URL,
                 sport_key: str = "soccer_epl"):
        self.api_key = api_key
        self.base_url = base_url
        self.sport_key = sport_key

    async def fetch_live_matches(self) -> list[dict]:
        """Fetch currently live football matches with O/U odds included."""
        url = f"{self.base_url}/sports/{self.sport_key}/odds"
        params = {
            "apiKey": self.api_key,
            **THEODDSAPI_OU_PARAMS,  # markets=totals enforced here
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    logger.error(f"TheOddsAPI error: {resp.status}")
                    return []
                data = await resp.json()
                return self._normalize_matches(data)

    async def fetch_live_matches_raw(self) -> tuple[list[dict], int, dict]:
        """Fetch with raw response info for key pool handling."""
        url = f"{self.base_url}/sports/{self.sport_key}/odds"
        params = {
            "apiKey": self.api_key,
            **THEODDSAPI_OU_PARAMS,
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                status = resp.status
                headers = dict(resp.headers)
                if status != 200:
                    return [], status, headers
                data = await resp.json()
                return self._normalize_matches(data), status, headers

    async def fetch_odds(self, match_id: str) -> list[dict]:
        """TheOddsAPI returns odds with matches, so this is usually a no-op.

        If you need per-match odds, use fetch_ou_odds() instead.
        """
        return []

    async def fetch_ou_odds(self) -> dict:
        """Fetch Over/Under goals odds for all events.

        ALWAYS passes markets=totals — this is critical for quota efficiency.
        Returns dict keyed by "HomeTeam vs AwayTeam" → ou_lines.

        Example return:
        {
            "Chelsea vs Arsenal": {
                "ou_05": {"over": 1.08, "under": 8.0},
                "ou_15": {"over": 1.35, "under": 3.4},
                "ou_25": {"over": 1.90, "under": 1.95},
                "ou_35": {"over": 3.20, "under": 1.35},
            },
            ...
        }
        """
        url = f"{self.base_url}/sports/{self.sport_key}/odds"
        params = {
            "apiKey": self.api_key,
            **THEODDSAPI_OU_PARAMS,
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    logger.error(f"TheOddsAPI odds error: {resp.status}")
                    return {}
                data = await resp.json()
                return self._extract_ou_odds(data)

    async def fetch_ou_odds_raw(self) -> tuple[dict, int, dict]:
        """Fetch O/U odds with raw response for key pool handling."""
        url = f"{self.base_url}/sports/{self.sport_key}/odds"
        params = {
            "apiKey": self.api_key,
            **THEODDSAPI_OU_PARAMS,
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                status = resp.status
                headers = dict(resp.headers)
                if status != 200:
                    return {}, status, headers
                data = await resp.json()
                return self._extract_ou_odds(data), status, headers

    def _normalize_matches(self, raw: list) -> list[dict]:
        """Normalize TheOddsAPI match data to internal format."""
        return [
            {
                "match_id": str(m.get("id", "")),
                "league": m.get("sport_title", "Unknown"),
                "home_team": m.get("home_team", "Unknown"),
                "away_team": m.get("away_team", "Unknown"),
                "home_score": 0,
                "away_score": 0,
                "match_minute": 0,
                "status": "live",
                "source": "theoddsapi",
            }
            for m in raw
        ]

    def _extract_ou_odds(self, raw: list) -> dict:
        """Extract Over/Under goals odds from TheOddsAPI response.

        Filters to totals market only and maps point values (0.5–3.5)
        to our standard labels (ou_05–ou_35).
        """
        ou_by_match = {}
        for event in raw:
            match_key = f"{event.get('home_team', '?')} vs {event.get('away_team', '?')}"
            ou_lines = {}

            for bookmaker in event.get("bookmakers", [])[:1]:  # first bookmaker
                for market in bookmaker.get("markets", []):
                    if market.get("key") != "totals":
                        continue  # belt-and-suspenders: skip non-totals

                    for outcome in market.get("outcomes", []):
                        point = str(outcome.get("point", ""))
                        label = OU_LABEL_MAP.get(point)
                        if not label:
                            continue  # skip unsupported lines
                        side = "over" if outcome.get("name") == "Over" else "under"
                        ou_lines.setdefault(label, {})[side] = outcome.get("price")

            if ou_lines:
                ou_by_match[match_key] = ou_lines

        return ou_by_match
