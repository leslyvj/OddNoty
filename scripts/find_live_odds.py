"""Find ANY currently live soccer match with O/U odds on TheOddsAPI."""
import asyncio, aiohttp

KEY = "6b8e652ff8ab692f77d80461dca82bbc"
BASE = "https://api.the-odds-api.com/v4"

async def main():
    async with aiohttp.ClientSession() as s:
        # Step 1: Get all active soccer sports
        print("🔍 Checking all active soccer competitions for live events...\n")
        async with s.get(f"{BASE}/sports", params={"apiKey": KEY}, timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status != 200:
                print(f"Error: {r.status}")
                return
            sports = await r.json()
            active = [sp for sp in sports if "soccer" in sp.get("key", "") and sp.get("active")]
            print(f"Found {len(active)} active soccer competitions\n")

        # Step 2: Check each for events with live odds
        found_any = False
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)

        for sp in active:
            key = sp["key"]
            title = sp.get("title", "?")
            url = f"{BASE}/sports/{key}/odds"
            params = {"apiKey": KEY, "markets": "totals", "regions": "uk,eu", "oddsFormat": "decimal"}
            
            async with s.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status != 200:
                    continue
                events = await r.json()
                
                # Check for events that have started (commence_time in the past)
                for ev in events:
                    commence = ev.get("commence_time", "")
                    try:
                        ct = datetime.fromisoformat(commence.replace("Z", "+00:00"))
                        if ct <= now:
                            # This match has started — it's live or recently finished
                            home = ev.get("home_team", "?")
                            away = ev.get("away_team", "?")
                            print(f"🟢 LIVE: {home} vs {away}")
                            print(f"   League: {title} ({key})")
                            print(f"   Started: {commence}")
                            
                            # Show O/U odds
                            for bm in ev.get("bookmakers", [])[:2]:
                                print(f"   📚 {bm.get('title')}")
                                for mkt in bm.get("markets", []):
                                    if mkt.get("key") == "totals":
                                        for o in mkt.get("outcomes", []):
                                            print(f"      {o.get('name')} {o.get('point')}: {o.get('price')}")
                            print()
                            found_any = True
                    except (ValueError, TypeError):
                        continue
                
                remaining = r.headers.get("x-requests-remaining", "?")
        
        if not found_any:
            print("❌ No currently live soccer matches found with O/U odds.")
            print("   This is common during off-peak hours (no matches in play).")
            print("\n   Next upcoming matches with odds available:")
            # Show nearest upcoming
            nearest = []
            for sp in active[:5]:
                url = f"{BASE}/sports/{sp['key']}/odds"
                params = {"apiKey": KEY, "markets": "totals", "regions": "uk,eu", "oddsFormat": "decimal"}
                async with s.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
                    if r.status == 200:
                        events = await r.json()
                        for ev in events:
                            ct = ev.get("commence_time", "")
                            nearest.append((ct, ev.get("home_team","?"), ev.get("away_team","?"), sp.get("title","?")))
            nearest.sort()
            for ct, h, a, lg in nearest[:8]:
                print(f"   ⏰ {ct} | {h} vs {a} ({lg})")
        
        # Show quota
        async with s.get(f"{BASE}/sports", params={"apiKey": KEY}) as r:
            print(f"\n📊 API Requests remaining: {r.headers.get('x-requests-remaining', '?')}")
            print(f"   Requests used: {r.headers.get('x-requests-used', '?')}")

asyncio.run(main())
