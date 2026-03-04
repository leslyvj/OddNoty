"""Test TheOddsAPI — find Sanfrecce Hiroshima and all live soccer events."""
import asyncio, aiohttp, json

ODDS_API_KEY = "6b8e652ff8ab692f77d80461dca82bbc"
BASE_URL = "https://api.the-odds-api.com/v4"

async def list_soccer_sports():
    """List all available soccer sport keys."""
    print("═══ Available Soccer Sports ═══")
    url = f"{BASE_URL}/sports"
    params = {"apiKey": ODDS_API_KEY}
    async with aiohttp.ClientSession() as s:
        async with s.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status == 200:
                data = await r.json()
                soccer = [s for s in data if "soccer" in s.get("key", "")]
                print(f"  Found {len(soccer)} soccer sports:")
                for sport in soccer:
                    active = "🟢" if sport.get("active") else "⚪"
                    print(f"  {active} {sport['key']} — {sport.get('title','?')}")
                    if "japan" in sport['key'].lower() or "j_league" in sport['key'].lower():
                        print(f"      ^^^ 🎯 J-LEAGUE FOUND!")
                
                # Show remaining quota from headers
                print(f"\n  Remaining requests: {r.headers.get('x-requests-remaining', '?')}")
                print(f"  Used requests: {r.headers.get('x-requests-used', '?')}")
            else:
                print(f"  ❌ Error: {r.status}")
                data = await r.text()
                print(f"  {data[:300]}")

async def fetch_j_league_odds():
    """Fetch J-League odds (Over/Under only)."""
    print("\n═══ J-League Over/Under Odds ═══")
    # Try common J-League sport keys
    sport_keys = ["soccer_japan_j_league", "soccer_japan_j1_league", "soccer_japan"]
    
    for sport_key in sport_keys:
        url = f"{BASE_URL}/sports/{sport_key}/odds"
        params = {
            "apiKey": ODDS_API_KEY,
            "markets": "totals",
            "regions": "uk,eu",
            "oddsFormat": "decimal",
        }
        async with aiohttp.ClientSession() as s:
            async with s.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status == 200:
                    data = await r.json()
                    print(f"\n  ✅ {sport_key}: {len(data)} events")
                    for event in data[:10]:
                        home = event.get("home_team", "?")
                        away = event.get("away_team", "?")
                        commence = event.get("commence_time", "?")
                        print(f"    ⚽ {home} vs {away} | Start: {commence}")
                        
                        if "hiroshima" in json.dumps(event).lower():
                            print(f"    ^^^ 🎯 HIROSHIMA FOUND!")
                            # Print odds detail
                            for bm in event.get("bookmakers", [])[:2]:
                                print(f"      📚 {bm.get('title')}")
                                for market in bm.get("markets", []):
                                    if market.get("key") == "totals":
                                        for outcome in market.get("outcomes", []):
                                            print(f"        {outcome.get('name')} {outcome.get('point')}: {outcome.get('price')}")
                    
                    print(f"\n  Remaining: {r.headers.get('x-requests-remaining', '?')}")
                elif r.status == 404:
                    print(f"  ❌ {sport_key}: not found (404)")
                elif r.status == 422:
                    print(f"  ❌ {sport_key}: not available (422)")
                else:
                    text = await r.text()
                    print(f"  ❌ {sport_key}: {r.status} — {text[:200]}")

async def fetch_all_live_soccer():
    """Try fetching ALL in-season soccer events to find Hiroshima."""
    print("\n═══ All In-Season Soccer Events (searching for Hiroshima) ═══")
    url = f"{BASE_URL}/sports"
    params = {"apiKey": ODDS_API_KEY}
    async with aiohttp.ClientSession() as s:
        async with s.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status != 200:
                print(f"  ❌ Sports list error: {r.status}")
                return
            sports = await r.json()
            active_soccer = [sp for sp in sports if "soccer" in sp.get("key","") and sp.get("active")]
            print(f"  {len(active_soccer)} active soccer competitions")
            
            # Search each active league for Hiroshima
            for sp in active_soccer:
                key = sp["key"]
                odds_url = f"{BASE_URL}/sports/{key}/odds"
                odds_params = {"apiKey": ODDS_API_KEY, "markets": "totals", "regions": "uk,eu", "oddsFormat": "decimal"}
                async with s.get(odds_url, params=odds_params, timeout=aiohttp.ClientTimeout(total=10)) as odds_r:
                    if odds_r.status == 200:
                        events = await odds_r.json()
                        for ev in events:
                            if "hiroshima" in json.dumps(ev).lower():
                                print(f"\n  🎯 FOUND in {key}!")
                                print(f"  {ev.get('home_team')} vs {ev.get('away_team')}")
                                print(f"  Commence: {ev.get('commence_time')}")
                                for bm in ev.get("bookmakers", [])[:1]:
                                    for mkt in bm.get("markets", []):
                                        if mkt.get("key") == "totals":
                                            for o in mkt.get("outcomes", []):
                                                print(f"    {o.get('name')} {o.get('point')}: {o.get('price')}")
                                return  # Found it, stop
            print("  ❌ Hiroshima not found in any active soccer league")

async def main():
    print("🔍 Testing TheOddsAPI for Sanfrecce Hiroshima...\n")
    await list_soccer_sports()
    await fetch_j_league_odds()

asyncio.run(main())
