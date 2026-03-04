"""Test which RapidAPI service this key actually works with."""
import asyncio, aiohttp, json

RAPIDAPI_KEY = "773042c66cmsh9619e0c0ace271bp1bfffejsn582e31534b17"

async def test_api_football_rapidapi():
    """Test via RapidAPI's proxy (the correct way for RapidAPI keys)."""
    print("═══ API-Football via RapidAPI proxy ═══")
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
    headers = {
        "x-rapidapi-host": "api-football-v1.p.rapidapi.com",
        "x-rapidapi-key": RAPIDAPI_KEY,
    }
    params = {"live": "all"}
    async with aiohttp.ClientSession() as s:
        async with s.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
            print(f"  Status: {r.status}")
            if r.status == 200:
                data = await r.json()
                fixtures = data.get("response", [])
                print(f"  ✅ Found {len(fixtures)} live fixtures")
                for f in fixtures[:15]:
                    t = f.get("teams", {})
                    g = f.get("goals", {})
                    fix = f.get("fixture", {})
                    st = fix.get("status", {})
                    league = f.get("league", {}).get("name", "?")
                    print(f"    {t.get('home',{}).get('name','?')} vs {t.get('away',{}).get('name','?')} "
                          f"| {g.get('home',0)}-{g.get('away',0)} | Min {st.get('elapsed','?')} "
                          f"| {league} | ID: {fix.get('id')}")
                    if "hiroshima" in json.dumps(f).lower():
                        print(f"    ^^^ 🎯 HIROSHIMA FOUND! Fixture ID: {fix.get('id')}")
            else:
                data = await r.text()
                print(f"  ❌ Failed: {data[:200]}")

async def test_sports_open_data():
    """Test the Sports Open Data API (what the curl command was for)."""
    print("\n═══ Sports Open Data ═══")
    url = "https://sportsop-soccer-sports-open-data-v1.p.rapidapi.com/v1/leagues"
    headers = {
        "x-rapidapi-host": "sportsop-soccer-sports-open-data-v1.p.rapidapi.com",
        "x-rapidapi-key": RAPIDAPI_KEY,
    }
    async with aiohttp.ClientSession() as s:
        async with s.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as r:
            print(f"  Status: {r.status}")
            if r.status == 200:
                data = await r.json()
                leagues = data.get("data", {}).get("leagues", [])
                print(f"  ✅ {len(leagues)} leagues available")
            else:
                data = await r.text()
                print(f"  ❌ Failed: {data[:200]}")

async def main():
    print("🔍 Testing RapidAPI key against different services...\n")
    await test_api_football_rapidapi()
    await test_sports_open_data()

asyncio.run(main())
