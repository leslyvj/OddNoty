"""API-Football fetcher (via RapidAPI / api-sports.io).

Score pillar provider — fetches live matches and Over/Under odds.
Free tier: 100 requests/day.
API docs: https://www.api-football.com/documentation-v3
"""

import aiohttp
import logging

logger = logging.getLogger("oddnoty.fetcher.api_football")

# O/U goals bet IDs in API-Football
# Bet ID 5 = Over/Under (Goals) in API-Football v3
OU_BET_ID = 5


class APIFootballFetcher:
    """Fetch live matches and O/U odds from API-Football (v3)."""

    def __init__(self, api_key: str, base_url: str = "https://v3.football.api-sports.io"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {"x-apisports-key": api_key}

    async def fetch_live_matches(self) -> list[dict]:
        """Fetch currently live football fixtures.

        Endpoint: GET /fixtures?live=all
        """
        url = f"{self.base_url}/fixtures"
        params = {"live": "all"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    logger.error(f"API-Football fixtures error: {resp.status}")
                    return []
                data = await resp.json()
                fixtures = data.get("response", [])
                return self._normalize_matches(fixtures)

    async def fetch_live_matches_raw(self) -> tuple[list[dict], int, dict]:
        """Fetch with raw response for key pool handling."""
        url = f"{self.base_url}/fixtures"
        params = {"live": "all"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                status = resp.status
                headers = dict(resp.headers)
                if status != 200:
                    return [], status, headers
                data = await resp.json()
                fixtures = data.get("response", [])
                return self._normalize_matches(fixtures), status, headers

    async def fetch_odds(self, match_id: str) -> list[dict]:
        """Fetch Over/Under goals odds for a specific fixture.

        Endpoint: GET /odds?fixture={id}&bet={OU_BET_ID}
        Filters to bet_id=5 (Over/Under Goals) only.
        """
        url = f"{self.base_url}/odds"
        params = {"fixture": match_id, "bet": OU_BET_ID}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    logger.error(f"API-Football odds error: {resp.status}")
                    return []
                data = await resp.json()
                return self._normalize_odds(data.get("response", []))

    async def fetch_odds_raw(self, match_id: str) -> tuple[list[dict], int, dict]:
        """Fetch odds with raw response for key pool handling."""
        url = f"{self.base_url}/odds"
        params = {"fixture": match_id, "bet": OU_BET_ID}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                status = resp.status
                headers = dict(resp.headers)
                if status != 200:
                    return [], status, headers
                data = await resp.json()
                return self._normalize_odds(data.get("response", [])), status, headers

    def _normalize_matches(self, raw: list) -> list[dict]:
        """Normalize API-Football fixture data to internal format."""
        normalized = []
        for f in raw:
            fixture = f.get("fixture", {})
            league = f.get("league", {})
            teams = f.get("teams", {})
            goals = f.get("goals", {})

            # Elapsed time (match minute)
            elapsed = fixture.get("status", {}).get("elapsed", 0)

            normalized.append({
                "match_id": str(fixture.get("id", "")),
                "league": league.get("name", "Unknown"),
                "home_team": teams.get("home", {}).get("name", "Unknown"),
                "away_team": teams.get("away", {}).get("name", "Unknown"),
                "home_score": goals.get("home", 0) or 0,
                "away_score": goals.get("away", 0) or 0,
                "match_minute": elapsed or 0,
                "status": "live",
                "source": "api-football",
            })
        return normalized

    def _normalize_odds(self, raw: list) -> list[dict]:
        """Normalize API-Football odds to O/U goals format.

        Returns list of dicts with keys: market, line, over, under, bookmaker
        """
        results = []
        supported_lines = {"0.5", "1.5", "2.5", "3.5"}

        for entry in raw:
            for bookmaker in entry.get("bookmakers", [])[:1]:  # first bookmaker
                bk_name = bookmaker.get("name", "Unknown")
                for bet in bookmaker.get("bets", []):
                    if bet.get("id") != OU_BET_ID:
                        continue
                    for value in bet.get("values", []):
                        val_str = str(value.get("value", ""))
                        # val_str looks like "Over 2.5" or "Under 1.5"
                        parts = val_str.split(" ")
                        if len(parts) != 2:
                            continue
                        side, line = parts[0].lower(), parts[1]
                        if line not in supported_lines:
                            continue
                        odds_val = value.get("odd")
                        if odds_val:
                            results.append({
                                "market": side,
                                "line": float(line),
                                "odds": float(odds_val),
                                "bookmaker": bk_name,
                            })
        return results
