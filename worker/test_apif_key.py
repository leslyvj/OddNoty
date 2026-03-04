import asyncio
import aiohttp
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from fetcher.api_football import APIFootballFetcher

async def test_apif_key(name, key):
    print(f"--- Testing {name} (RapidAPI) ---")
    fetcher = APIFootballFetcher(api_key=key)
    try:
        # Test fetching live matches
        matches, status, headers = await fetcher.fetch_live_matches_raw()
        if status == 200:
            print(f"✅ Success! Fetched {len(matches)} live matches.")
            if matches:
                print(f"Sample match: {matches[0]['home_team']} vs {matches[0]['away_team']}")
        else:
            print(f"❌ Status {status}: {headers.get('x-rapidapi-message', 'No message')}")
    except Exception as e:
        print(f"❌ Failed: {e}")

async def main():
    # Key from user's curl command
    rapidapi_key = "773042c66cmsh9619e0c0ace271bp1bfffejsn582e31534b17"
    await test_apif_key("apif_key_1", rapidapi_key)

if __name__ == "__main__":
    asyncio.run(main())
