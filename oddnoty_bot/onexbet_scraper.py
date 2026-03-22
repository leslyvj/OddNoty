import asyncio
import logging
import httpx
import random
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def normalize_line(val: Any) -> str:
    """Normalizes a line value to string, removing .0 if it's an integer."""
    try:
        f = float(val)
        if f == int(f):
            return str(int(f))
        return str(f)
    except:
        return str(val)

class OneXBetScraper:
    def __init__(self):
        self.mirrors = [
            "https://indi-1xbet.com",
            "https://1xbet-sport.in",
            "https://1xbetindia.info",
            "https://1x-india.in",
        ]
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "X-Requested-With": "XMLHttpRequest",
            "x-svc-source": "__BETTING_APP__",
            "Connection": "keep-alive"
        }
        self.live_matches_cache = {}
        self.prematch_matches_cache = {}

    def _get_random_mirror(self):
        return random.choice(self.mirrors)

    async def get_live_matches(self) -> List[Dict[str, Any]]:
        for mirror in self.mirrors:
            url = f"{mirror}/service-api/LiveFeed/Get1x2_VZip"
            params = {"sports": 1, "count": 100, "lng": "en", "mode": 4}
            try:
                async with httpx.AsyncClient(headers=self.headers, timeout=15.0) as client:
                    response = await client.get(url, params=params)
                    if response.status_code == 200:
                        data = response.json().get("Value", [])
                        parsed = []
                        for item in data:
                            match_id = str(item.get("I"))
                            fs = item.get("SC", {}).get("FS", {})
                            parsed.append({
                                "match_id": match_id,
                                "home_team": item.get("O1"),
                                "away_team": item.get("O2"),
                                "league": item.get("LE"),
                                "score": f"{fs.get('S1', 0)}-{fs.get('S2', 0)}",
                                "minute": item.get("SC", {}).get("TS", 0) // 60,
                                "is_live": True
                            })
                            self.live_matches_cache[match_id] = parsed[-1]
                        return parsed
            except Exception as e:
                logger.error(f"Live matches fetch failed for mirror {mirror}: {e}")
        return list(self.live_matches_cache.values())

    async def get_prematch_matches(self) -> List[Dict[str, Any]]:
        """Fetches top upcoming matches (Line) from 1xBet."""
        for mirror in self.mirrors:
            url = f"{mirror}/service-api/LineFeed/Get1x2_VZip"
            params = {"sports": 1, "count": 100, "lng": "en", "mode": 4, "partner": 71}
            try:
                async with httpx.AsyncClient(headers=self.headers, timeout=15.0) as client:
                    response = await client.get(url, params=params)
                    if response.status_code == 200:
                        data = response.json().get("Value", [])
                        parsed = []
                        for item in data:
                            match_id = str(item.get("I"))
                            parsed.append({
                                "match_id": match_id,
                                "home_team": item.get("O1"),
                                "away_team": item.get("O2"),
                                "league": item.get("LE"),
                                "score": "pre-match",
                                "minute": "Not started",
                                "is_live": False
                            })
                            self.prematch_matches_cache[match_id] = parsed[-1]
                        return parsed
            except Exception as e:
                logger.error(f"Pre-match matches fetch failed for mirror {mirror}: {e}")
        return list(self.prematch_matches_cache.values())

    async def get_match_odds(self, match_id: str) -> Dict[str, Any]:
        # Determine if it's a live or pre-match game
        is_live = match_id in self.live_matches_cache
        base_endpoint = "LiveFeed" if is_live else "LineFeed"

        for mirror in self.mirrors:
            url = f"{mirror}/service-api/{base_endpoint}/GetGameZip"
            params = {"id": match_id, "lng": "en", "isSubGames": "true", "GroupEvents": "true", "countevents": 500}
            
            # If LineFeed, we might need a backup check if LiveFeed fails
            # (sometimes games move from Line to Live)
            
            odds_data = {
                "match_id": match_id,
                "markets": {},
                "is_live": is_live
            }
            
            try:
                async with httpx.AsyncClient(headers=self.headers, timeout=15.0) as client:
                    response = await client.get(url, params=params)
                    if response.status_code == 200:
                        data = response.json().get("Value", {})
                        if not data:
                            # Try other endpoint if this one gave nothing
                            alt_endpoint = "LineFeed" if is_live else "LiveFeed"
                            url_alt = f"{mirror}/service-api/{alt_endpoint}/GetGameZip"
                            response = await client.get(url_alt, params=params)
                            data = response.json().get("Value", {}) if response.status_code == 200 else {}
                            if data: odds_data["is_live"] = not is_live

                        # Loop through Group Events where the granular odds are nested
                        for group in data.get("GE", []):
                            for event_list in group.get("E", []):
                                for event in event_list:
                                    t = event.get("T")
                                    p = event.get("P")
                                    c = event.get("C")
                                    
                                    # Very simplified mapping logic for MVP
                                    # T: 9 (Over), T: 10 (Under) - for generic market, P serves as line
                                    line_str = normalize_line(p) if p is not None else ""
                                    
                                    if t == 9 and p is not None:
                                        market = f"Over/Under {line_str}"
                                        if market not in odds_data["markets"]: odds_data["markets"][market] = {}
                                        odds_data["markets"][market]["Over"] = c
                                    elif t == 10 and p is not None:
                                        market = f"Over/Under {line_str}"
                                        if market not in odds_data["markets"]: odds_data["markets"][market] = {}
                                        odds_data["markets"][market]["Under"] = c
                                    elif t == 11 and p is not None:
                                        market = f"Team 1 Total {line_str}"
                                        if market not in odds_data["markets"]: odds_data["markets"][market] = {}
                                        odds_data["markets"][market]["Over"] = c
                                    elif t == 12 and p is not None:
                                        market = f"Team 1 Total {line_str}"
                                        if market not in odds_data["markets"]: odds_data["markets"][market] = {}
                                        odds_data["markets"][market]["Under"] = c
                                    elif t == 13 and p is not None:
                                        market = f"Team 2 Total {line_str}"
                                        if market not in odds_data["markets"]: odds_data["markets"][market] = {}
                                        odds_data["markets"][market]["Over"] = c
                                    elif t == 14 and p is not None:
                                        market = f"Team 2 Total {line_str}"
                                        if market not in odds_data["markets"]: odds_data["markets"][market] = {}
                                        odds_data["markets"][market]["Under"] = c
                        
                        if odds_data["markets"]:
                            return odds_data 
            except Exception as e:
                logger.error(f"Game odds fetch failed for mirror {mirror}: {e}")
                
        return odds_data
