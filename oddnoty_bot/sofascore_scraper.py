import cloudscraper
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class SofaScoreScraper:
    BASE_URL = "https://api.sofascore.com/api/v1"
    
    def __init__(self):
        self.scraper = cloudscraper.create_scraper()
        self.headers = {
            "Referer": "https://www.sofascore.com/",
            "x-requested-with": "c7e9c5"
        }

    async def search_match(self, home_team: str, away_team: str) -> str | None:
        """Finds the SofaScore event ID for a given match."""
        import asyncio
        query = f"{home_team} {away_team}"
        url = f"{self.BASE_URL}/search/all?q={query}"
        
        def _fetch():
            return self.scraper.get(url, headers=self.headers, timeout=10.0)

        try:
            resp = await asyncio.to_thread(_fetch)
            print(f"Debug: URL {url} Status {resp.status_code}")
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                print(f"Debug: Found {len(results)} results")
                for res in results:
                    rtype = res.get("type")
                    rname = res.get("entity", {}).get("name")
                    print(f"  Result: {rtype} - {rname}")
                    if rtype == "event":
                        entity = res.get("entity", {})
                        # Sport ID might be missing or None in some historical/search results
                        # but if it's an event, we usually want it.
                        sid = entity.get("sport", {}).get("id")
                        if sid is None or sid == 1:
                            return str(entity.get("id"))
            
            # Fallback to home team search if no event found
            if home_team and away_team:
                 return await self.search_match(home_team, "")

        except Exception as e:
            logger.error(f"SofaScore search error: {e}")
        return None

    async def get_match_details(self, event_id: str) -> Dict[str, Any]:
        """Fetches detailed match info, lineups, and statistics."""
        import asyncio
        data = {}

        def _fetch(endpoint):
            return self.scraper.get(f"{self.BASE_URL}/event/{event_id}{endpoint}", headers=self.headers, timeout=15.0)

        try:
            # 1. Basic event info
            resp = await asyncio.to_thread(_fetch, "")
            if resp.status_code == 200:
                data["event"] = resp.json().get("event", {})

            # 2. Statistics
            resp = await asyncio.to_thread(_fetch, "/statistics")
            if resp.status_code == 200:
                data["statistics"] = resp.json().get("statistics", [])

            # 3. Lineups
            resp = await asyncio.to_thread(_fetch, "/lineups")
            if resp.status_code == 200:
                data["lineups"] = resp.json()

            # 4. H2H
            resp = await asyncio.to_thread(_fetch, "/h2h")
            if resp.status_code == 200:
                data["h2h"] = resp.json()
        except Exception as e:
            logger.error(f"SofaScore details error: {e}")

        return data

async def test_sofa():
    scraper = SofaScoreScraper()
    print("Searching for match (specific)...")
    eid = await scraper.search_match("Arsenal", "Manchester City")
    if not eid:
        print("Specific match not found, searching for 'Arsenal'...")
        eid = await scraper.search_match("Arsenal", "")
    
    if eid:
        print(f"Found Event ID: {eid}")
        details = await scraper.get_match_details(eid)
        print(f"Data keys fetched: {list(details.keys())}")
        if "event" in details:
            print(f"Match: {details['event'].get('name')}")
    else:
        print("Match not found.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_sofa())
