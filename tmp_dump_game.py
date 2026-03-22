import asyncio
from scrapers.bookmakers.onexbet import OneXBetScraper

async def dump_game():
    scraper = OneXBetScraper()
    matches = await scraper.fetch_live_odds()
    if not matches:
        print("No matches")
        return
    
    match_id = matches[0]["match_id"]
    print(f"Match ID: {match_id}")
    details = await scraper.fetch_game_details(match_id)
    
    import json
    with open("match_data_debug.json", "w") as f:
        json.dump(details, f)
    print("Dumped to match_data_debug.json")

if __name__ == "__main__":
    asyncio.run(dump_game())
