"""Sportmonks Football API fetcher."""

import aiohttp
import logging

logger = logging.getLogger("oddnoty.fetcher.sportmonks")

BASE_URL = "https://api.sportmonks.com/v3/football"


class SportmonksFetcher:
    """Fetch live matches and odds from Sportmonks API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"Authorization": api_key}

    async def fetch_live_matches(self) -> list[dict]:
        """Fetch currently live football matches."""
        url = f"{BASE_URL}/livescores/inplay"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as resp:
                if resp.status != 200:
                    logger.error(f"Sportmonks livescores error: {resp.status}")
                    return []
                data = await resp.json()
                matches = data.get("data", [])
                return self._normalize_matches(matches)

    async def fetch_odds(self, match_id: str) -> list[dict]:
        """Fetch Over/Under odds for a specific match."""
        url = f"{BASE_URL}/odds/pre-match/fixtures/{match_id}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as resp:
                if resp.status != 200:
                    logger.error(f"Sportmonks odds error: {resp.status}")
                    return []
                data = await resp.json()
                return self._normalize_odds(data.get("data", []))

    def _normalize_matches(self, raw: list) -> list[dict]:
        """Normalize Sportmonks match data to internal format."""
        # TODO: map Sportmonks fields to our schema
        return [
            {
                "match_id": str(m.get("id", "")),
                "league": m.get("league", {}).get("name", "Unknown"),
                "home_team": m.get("localTeam", {}).get("name", "Unknown"),
                "away_team": m.get("visitorTeam", {}).get("name", "Unknown"),
                "home_score": m.get("scores", {}).get("localteam_score", 0),
                "away_score": m.get("scores", {}).get("visitorteam_score", 0),
                "match_minute": m.get("time", {}).get("minute", 0),
                "status": "live",
            }
            for m in raw
        ]

    def _normalize_odds(self, raw: list) -> list[dict]:
        """Normalize Sportmonks odds data to internal format."""
        # TODO: extract over/under odds from Sportmonks response
        return raw
