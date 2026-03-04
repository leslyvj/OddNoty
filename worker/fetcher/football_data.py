"""Football-Data.org fetcher.

Score pillar provider — fetches live match scores and minutes.
API docs: https://www.football-data.org/documentation/api
Free tier: 10 requests/minute (~600/hour).
"""

import aiohttp
import logging

logger = logging.getLogger("oddnoty.fetcher.football_data")


class FootballDataFetcher:
    """Fetch live matches from Football-Data.org (v4 API)."""

    def __init__(self, api_key: str, base_url: str = "https://api.football-data.org/v4"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {"X-Auth-Token": api_key}

    async def fetch_live_matches(self) -> list[dict]:
        """Fetch currently live football matches.

        Endpoint: GET /v4/matches?status=LIVE
        """
        url = f"{self.base_url}/matches"
        params = {"status": "LIVE"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    logger.error(f"Football-Data.org error: {resp.status}")
                    return []
                data = await resp.json()
                matches = data.get("matches", [])
                return self._normalize_matches(matches)

    async def fetch_live_matches_raw(self) -> tuple[list[dict], int, dict]:
        """Fetch with raw response info for key pool handling.

        Returns (matches, status_code, headers).
        """
        url = f"{self.base_url}/matches"
        params = {"status": "LIVE"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                status = resp.status
                headers = dict(resp.headers)
                if status != 200:
                    return [], status, headers
                data = await resp.json()
                matches = data.get("matches", [])
                return self._normalize_matches(matches), status, headers

    def _normalize_matches(self, raw: list) -> list[dict]:
        """Normalize Football-Data.org match data to internal format."""
        normalized = []
        for m in raw:
            score = m.get("score", {})
            full_time = score.get("fullTime", {})
            half_time = score.get("halfTime", {})

            # Use fullTime score if available, else halfTime
            home_score = full_time.get("home") or half_time.get("home") or 0
            away_score = full_time.get("away") or half_time.get("away") or 0

            # Extract match minute from the status field
            minute = m.get("minute", 0) or 0

            normalized.append({
                "match_id": str(m.get("id", "")),
                "league": m.get("competition", {}).get("name", "Unknown"),
                "home_team": m.get("homeTeam", {}).get("shortName", m.get("homeTeam", {}).get("name", "Unknown")),
                "away_team": m.get("awayTeam", {}).get("shortName", m.get("awayTeam", {}).get("name", "Unknown")),
                "home_score": home_score if home_score is not None else 0,
                "away_score": away_score if away_score is not None else 0,
                "match_minute": minute,
                "status": "live",
                "source": "football-data",
            })
        return normalized
