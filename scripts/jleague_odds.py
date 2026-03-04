"""Quick J-League odds check — find Hiroshima."""
import asyncio, aiohttp

KEY = "6b8e652ff8ab692f77d80461dca82bbc"

async def main():
    url = "https://api.the-odds-api.com/v4/sports/soccer_japan_j_league/odds"
    params = {"apiKey": KEY, "markets": "totals", "regions": "uk,eu", "oddsFormat": "decimal"}
    async with aiohttp.ClientSession() as s:
        async with s.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status == 200:
                data = await r.json()
                print(f"Found {len(data)} J-League events\n")
                for ev in data:
                    h = ev.get("home_team", "?")
                    a = ev.get("away_team", "?")
                    t = ev.get("commence_time", "?")
                    is_target = "hiroshima" in (h + a).lower()
                    mark = "🎯" if is_target else "  "
                    print(f"{mark} {h} vs {a} | {t}")
                    if is_target:
                        for bm in ev.get("bookmakers", [])[:2]:
                            print(f"   📚 {bm.get('title')}")
                            for mkt in bm.get("markets", []):
                                if mkt.get("key") == "totals":
                                    for o in mkt.get("outcomes", []):
                                        name = o.get("name")
                                        point = o.get("point")
                                        price = o.get("price")
                                        print(f"      {name} {point}: {price}")
                print(f"\nRemaining API requests: {r.headers.get('x-requests-remaining', '?')}")
            else:
                text = await r.text()
                print(f"Error {r.status}: {text[:300]}")

asyncio.run(main())
