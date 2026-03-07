import asyncio
from oddnoty_bot.onexbet_scraper import OneXBetScraper
from oddnoty_bot.odds_store import OddsStore
from oddnoty_bot.llm_analyst import LLMAnalyst

async def test_bot_flow():
    print("🚀 Initializing 1xBet Live Testing Flow...")
    scraper = OneXBetScraper()
    store = OddsStore()
    analyst = LLMAnalyst()
    
    print("\n1. Fetching Live Matches...")
    matches = await scraper.get_live_matches()
    
    if not matches:
        print("❌ No matches currently live.")
        return
        
    match = matches[0]
    m_id = str(match['match_id'])
    print(f"✅ Found match: {match['home_team']} vs {match['away_team']} (ID: {m_id})")
    
    print("\n2. Fetching Odds for match...")
    odds_data = await scraper.get_match_odds(m_id)
    
    if not odds_data.get('markets'):
        print(f"⚠️ No Over/Under odds found for this match.")
    else:
        print(f"✅ Extracted odds specific to match.")
        
    print("\n3. Testing Store Snippet & Movement Engine...")
    import time
    
    # First Snapshot
    store.snapshot(m_id, odds_data)
    
    # Simulate time passing and a sharp drop in one odd
    time.sleep(1)
    
    # Artificially alter the data to simulate sharp movement
    import copy
    odds_data_2 = copy.deepcopy(odds_data)
    first_market = list(odds_data_2.get("markets", {}).keys())[0] if odds_data_2.get("markets") else None
    
    if first_market and "Over" in odds_data_2["markets"][first_market]:
        odds_data_2["markets"][first_market]["Over"] -= 0.15 # Sharp shorten
    if first_market and "Under" in odds_data_2["markets"][first_market]:
        odds_data_2["markets"][first_market]["Under"] += 0.20 # Sharp drift
        
    # Second Snapshot
    store.snapshot(m_id, odds_data_2)
    
    movement = store.get_movement(m_id)
    
    for market, outcomes in movement.get("markets", {}).items():
        print(f"  {market}:")
        for outcome, data in outcomes.items():
            print(f"    - {outcome}: {data['odd']} (Implied: {data['implied_prob']}) | diff: {data['diff']} {data['movement_icon']} -> [{data['velocity_label']}]")
            
    print("\n4. Testing LLM Analyst Logic...")
    analysis = await analyst.analyze(match, movement, store)
    print("----- PROMPT SIMULATION / OUTPUT ----")
    print(analysis)
    print("-------------------------------------")

    print("\n✅ Internal Systems passed flow execution.")

if __name__ == "__main__":
    asyncio.run(test_bot_flow())
