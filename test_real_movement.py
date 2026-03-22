import asyncio
import time
from oddnoty_bot.onexbet_scraper import OneXBetScraper
from oddnoty_bot.odds_store import OddsStore
from oddnoty_bot.llm_analyst import LLMAnalyst

async def test_real_motion():
    print("🚀 Initializing Real Odds Fetcher (120s Test)...")
    scraper = OneXBetScraper()
    store = OddsStore()
    analyst = LLMAnalyst()
    
    # 1. Fetch matches and pick one
    matches = await scraper.get_live_matches()
    
    if not matches:
        print("❌ No matches live.")
        return
        
    match = matches[0]
    m_id = str(match['match_id'])
    print(f"🎯 Target Match: {match['home_team']} vs {match['away_team']} (ID: {m_id}, Min: {match['minute']}')")
    
    # 2. First fetch
    odds_data_1 = await scraper.get_match_odds(m_id)
    if not odds_data_1.get("markets"):
        print("❌ No odds found for this match.")
        return
        
    print(f"✅ T=0s: First odds fetch completed. Snapshotting...")
    store.snapshot(m_id, odds_data_1)
    
    # Check baseline
    baseline = store.get_movement(m_id)
    print(f"Sample T=0s (Over 1.5): {baseline.get('markets', {}).get('Over/Under 1.5', {}).get('Over', 'N/A')}")
    
    # 3. Wait 120 seconds
    print("⏳ Waiting 120 seconds for real market movement...")
    for i in range(12, 0, -1):
        print(f"   {i*10}s remaining...")
        await asyncio.sleep(10)
        
    # 4. Second fetch
    print("✅ T=120s: Doing second odds fetch...")
    odds_data_2 = await scraper.get_match_odds(m_id)
    store.snapshot(m_id, odds_data_2)
    
    # 5. Output movement
    movement = store.get_movement(m_id)
    
    print("\n--- MOVEMENT ANALYSIS ---")
    moved = False
    for market, outcomes in movement.get("markets", {}).items():
        for outcome, data in outcomes.items():
            if data['diff'] != 0.0:
                print(f"  {market} {outcome}: {data['odd']} ({data['implied_prob']} implied) | diff: {data['diff']} {data['movement_icon']} -> [{data['velocity_label']}]")
                moved = True
                
    if not moved:
        print("⚠️ No odds shifted in the 120 second window for this match.")
        
    print("\n--- LLM ANALYSIS ---")
    res = await analyst.analyze(match, movement)
    print(res)
    
if __name__ == "__main__":
    asyncio.run(test_real_motion())
