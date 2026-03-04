
import asyncio
import aiohttp
import json

# Keys from goaledge_keys.yaml
APIF_KEY = "773042c66cmsh9619e0c0ace271bp1bfffejsn582e31534b17"
FD_KEY = "cb0cec00437c4431b2b17e3065c9714f"
THEODDS_KEY = "6b8e652ff8ab692f77d80461dca82bbc"

async def check_api_football():
    print("\n--- Checking API-Football ---")
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {"x-apisports-key": APIF_KEY}
    
    # Try March 3 and March 4
    for date in ["2026-03-03", "2026-03-04"]:
        params = {"date": date}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    fixtures = data.get("response", [])
                    print(f"Checking {date}, total fixtures: {len(fixtures)}")
                    for f in fixtures:
                        home = f["teams"]["home"]["name"]
                        away = f["teams"]["away"]["name"]
                        if "Torque" in home or "Torque" in away or "Defensor" in home or "Defensor" in away:
                            print(f"Found on {date}: {home} vs {away} (League: {f['league']['name']}, ID: {f['fixture']['id']}, Status: {f['fixture']['status']['long']})")

    # Also try searching for the team to find their recent/upcoming matches
    print("Searching for team 'Montevideo City Torque'...")
    team_url = "https://v3.football.api-sports.io/teams"
    async with aiohttp.ClientSession() as session:
        async with session.get(team_url, headers=headers, params={"search": "Torque"}) as resp:
            if resp.status == 200:
                data = await resp.json()
                teams = data.get("response", [])
                for t in teams:
                    team_id = t["team"]["id"]
                    print(f"Found Team: {t['team']['name']} (ID: {team_id})")
                    # Check fixtures for this team
                    fixture_url = "https://v3.football.api-sports.io/fixtures"
                    f_params = {"team": team_id, "last": 5}
                    async with session.get(fixture_url, headers=headers, params=f_params) as f_resp:
                        if f_resp.status == 200:
                            f_data = await f_resp.json()
                            for f in f_data.get("response", []):
                                print(f"  Last match: {f['teams']['home']['name']} {f['goals']['home']}-{f['goals']['away']} {f['teams']['away']['name']} (Date: {f['fixture']['date']})")

async def check_the_odds_api():
    print("\n--- Checking The Odds API ---")
    sports_url = "https://api.the-odds-api.com/v4/sports"
    params = {"apiKey": THEODDS_KEY}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(sports_url, params=params) as resp:
            if resp.status == 200:
                sports = await resp.json()
                relevant_sports = [s["key"] for s in sports if "uruguay" in s["key"].lower() or "conmebol" in s["key"].lower() or "sudamericana" in s["key"].lower()]
                print(f"Checking sports: {relevant_sports}")
                
                for sport in relevant_sports:
                    odds_url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"
                    params = {"apiKey": THEODDS_KEY, "regions": "us,uk,au,eu", "markets": "h2h"}
                    async with session.get(odds_url, params=params) as oresp:
                        if oresp.status == 200:
                            odata = await oresp.json()
                            print(f"Sport {sport} has {len(odata)} matches")
                            for m in odata:
                                home = m["home_team"]
                                away = m["away_team"]
                                print(f"  Match: {home} vs {away}")
                                if "Torque" in home or "Torque" in away or "Defensor" in home or "Defensor" in away:
                                    print(f"  !!! FOUND MATCH: {home} vs {away} !!!")

async def main():
    await check_api_football()
    await check_the_odds_api()

if __name__ == "__main__":
    asyncio.run(main())
