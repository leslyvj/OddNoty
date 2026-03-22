import json

with open("match_data_debug.json", "r") as f:
    data = json.load(f)

print("Looking for Over/Under events...")
for g in data.get("GE", []):
    for event_list in g.get("E", []):
        for e in event_list:
            t = e.get("T")
            p = e.get("P")
            c = e.get("C")
            
            # Print if it's over/under or BTTS...
            # 9 usually Over, 10 usually Under. Or maybe it's 1X2 (1, 2, 3)?
            if t in [1, 2, 3, 9, 10]:
                print(f"Goal event: T={t}, P={p}, C={c}")
