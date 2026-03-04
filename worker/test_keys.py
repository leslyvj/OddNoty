import asyncio
import aiohttp
import sys
import os

# Add current directory to path to import fetcher
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from fetcher.football_data import FootballDataFetcher

async def test_key(name, key):
    print(f"--- Testing {name} ---")
    fetcher = FootballDataFetcher(api_key=key)
    try:
        matches = await fetcher.fetch_live_matches()
        print(f"✅ Success! Fetched {len(matches)} live matches.")
        if matches:
            print(f"Sample match: {matches[0]['home_team']} vs {matches[0]['away_team']}")
    except Exception as e:
        print(f"❌ Failed: {e}")

async def main():
    # Keys from goaledge_keys.yaml
    keys = {
        "fd_key_1": "cb0cec00437c4431b2b17e3065c9714f",
        "fd_key_2": "57e0df313b0c4b589e24c3985ea7bfee"
    }
    
    for name, key in keys.items():
        await test_key(name, key)

if __name__ == "__main__":
    asyncio.run(main())
