
import asyncio
import aiohttp
import json

APIF_KEY = "773042c66cmsh9619e0c0ace271bp1bfffejsn582e31534b17"

async def search_team(name):
    url = "https://v3.football.api-sports.io/teams"
    headers = {"x-apisports-key": APIF_KEY}
    params = {"search": name}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as resp:
            data = await resp.json()
            return data.get("response", [])

async def get_fixtures_for_team(team_id):
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {"x-apisports-key": APIF_KEY}
    params = {"team": team_id, "last": 5}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as resp:
            data = await resp.json()
            return data.get("response", [])

async def main():
    print("--- Searching for Montevideo City Torque in API-Football ---")
    teams = await search_team("Torque")
    for t in teams:
        tid = t["team"]["id"]
        tname = t["team"]["name"]
        print(f"Found Team: {tname} (ID: {tid})")
        fixtures = await get_fixtures_for_team(tid)
        for f in fixtures:
            home = f["teams"]["home"]["name"]
            away = f["teams"]["away"]["name"]
            date = f["fixture"]["date"]
            status = f["fixture"]["status"]["long"]
            score = f["goals"]
            print(f"  Match: {home} {score['home']}-{score['away']} {away} | Date: {date} | Status: {status}")

    print("\n--- Searching for Defensor Sporting in API-Football ---")
    teams = await search_team("Defensor")
    for t in teams:
        tid = t["team"]["id"]
        tname = t["team"]["name"]
        print(f"Found Team: {tname} (ID: {tid})")
        fixtures = await get_fixtures_for_team(tid)
        for f in fixtures:
            home = f["teams"]["home"]["name"]
            away = f["teams"]["away"]["name"]
            date = f["fixture"]["date"]
            status = f["fixture"]["status"]["long"]
            score = f["goals"]
            print(f"  Match: {home} {score['home']}-{score['away']} {away} | Date: {date} | Status: {status}")

if __name__ == "__main__":
    asyncio.run(main())
