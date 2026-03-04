
import asyncio
import aiohttp
import json

APIF_KEY = "773042c66cmsh9619e0c0ace271bp1bfffejsn582e31534b17"

async def check_api():
    url = "https://v3.football.api-sports.io/status"
    headers = {"x-apisports-key": APIF_KEY}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            data = await resp.json()
            print(f"Status: {json.dumps(data, indent=2)}")

async def get_leagues_uruguay():
    url = "https://v3.football.api-sports.io/leagues"
    headers = {"x-apisports-key": APIF_KEY}
    params = {"country": "Uruguay"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as resp:
            data = await resp.json()
            leagues = data.get("response", [])
            for l in leagues:
                print(f"League: {l['league']['name']} (ID: {l['league']['id']})")
                
async def get_cup_matches():
    # Sudamericana is a continental cup (CONMEBOL)
    url = "https://v3.football.api-sports.io/leagues"
    headers = {"x-apisports-key": APIF_KEY}
    params = {"search": "Sudamericana"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as resp:
            data = await resp.json()
            for l in data.get("response", []):
                print(f"Cup: {l['league']['name']} (ID: {l['league']['id']})")
                
async def main():
    await check_api()
    print("\n--- Uruguay Leagues ---")
    await get_leagues_uruguay()
    print("\n--- Sudamericana Cup ---")
    await get_cup_matches()

if __name__ == "__main__":
    asyncio.run(main())
