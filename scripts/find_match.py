"""Find Sanfrecce Hiroshima across all APIs."""
import asyncio, aiohttp, json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "worker"))

FD_KEY_1 = "cb0cec00437c4431b2b17e3065c9714f"
FD_KEY_2 = "57e0df313b0c4b589e24c3985ea7bfee"
APIF_KEY = "773042c66cmsh9619e0c0ace271bp1bfffejsn582e31534b17"

async def check_football_data():
    print("\n═══ Football-Data.org ═══")
    url = "https://api.football-data.org/v4/matches"
    # Try LIVE, IN_PLAY, SCHEDULED, etc.
    for status_filter in ["LIVE", "IN_PLAY", "SCHEDULED", "TIMED"]:
        headers = {"X-Auth-Token": FD_KEY_1}
        params = {"status": status_filter}
        async with aiohttp.ClientSession() as s:
            async with s.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status == 200:
                    data = await r.json()
                    matches = data.get("matches", [])
                    hiroshima = [m for m in matches if "hiroshima" in json.dumps(m).lower()]
                    if hiroshima:
                        print(f"  ✅ Found in status={status_filter}!")
                        for m in hiroshima:
                            home = m.get("homeTeam",{}).get("name","?")
                            away = m.get("awayTeam",{}).get("name","?")
                            st = m.get("status","?")
                            minute = m.get("minute", "?")
                            sc = m.get("score",{})
                            print(f"  {home} vs {away} | Status: {st} | Min: {minute}")
                            print(f"  Score: {sc}")
                            print(f"  Match ID: {m.get('id')}")
                    else:
                        print(f"  ❌ Not found in status={status_filter} ({len(matches)} matches)")
                else:
                    print(f"  Error {r.status} for {status_filter}")

async def check_api_football():
    print("\n═══ API-Football (RapidAPI) ═══")
    headers = {"x-apisports-key": APIF_KEY}
    
    # Check live
    url = "https://v3.football.api-sports.io/fixtures"
    params = {"live": "all"}
    async with aiohttp.ClientSession() as s:
        async with s.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status == 200:
                data = await r.json()
                fixtures = data.get("response", [])
                hiroshima = [f for f in fixtures if "hiroshima" in json.dumps(f).lower()]
                if hiroshima:
                    print(f"  ✅ Found LIVE!")
                    for f in hiroshima:
                        teams = f.get("teams",{})
                        goals = f.get("goals",{})
                        fix = f.get("fixture",{})
                        status = fix.get("status",{})
                        print(f"  {teams.get('home',{}).get('name','?')} vs {teams.get('away',{}).get('name','?')}")
                        print(f"  Fixture ID: {fix.get('id')}")
                        print(f"  Status: {status.get('long','?')} | Elapsed: {status.get('elapsed','?')}")
                        print(f"  Score: {goals.get('home',0)}-{goals.get('away',0)}")
                        print(f"  League: {f.get('league',{}).get('name','?')}")
                else:
                    print(f"  ❌ Not found in LIVE ({len(fixtures)} fixtures)")
                    # Show all live fixtures for reference
                    if fixtures:
                        print(f"  Live matches available:")
                        for f in fixtures[:10]:
                            t = f.get("teams",{})
                            print(f"    - {t.get('home',{}).get('name','?')} vs {t.get('away',{}).get('name','?')}")
            else:
                print(f"  Error: {r.status}")
    
    # Also check today's fixtures
    from datetime import datetime
    today = datetime.utcnow().strftime("%Y-%m-%d")
    params2 = {"date": today, "search": "hiroshima"}
    async with aiohttp.ClientSession() as s:
        async with s.get(url, headers=headers, params=params2, timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status == 200:
                data = await r.json()
                fixtures = data.get("response", [])
                if fixtures:
                    print(f"\n  📅 Today's Hiroshima fixtures:")
                    for f in fixtures:
                        teams = f.get("teams",{})
                        fix = f.get("fixture",{})
                        status = fix.get("status",{})
                        print(f"  {teams.get('home',{}).get('name','?')} vs {teams.get('away',{}).get('name','?')}")
                        print(f"  Fixture ID: {fix.get('id')}")
                        print(f"  Status: {status.get('long','?')} | Elapsed: {status.get('elapsed','?')}")

async def main():
    print("🔍 Searching for Sanfrecce Hiroshima across all APIs...")
    await check_football_data()
    await check_api_football()

asyncio.run(main())
