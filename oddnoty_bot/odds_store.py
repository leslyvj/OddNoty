import time
from typing import Dict, List, Any, Tuple

class OddsSnapshot:
    def __init__(self, match_id: str, odds: Dict[str, Any]):
        self.timestamp = time.time()
        self.match_id = match_id
        self.odds = odds

class OddsStore:
    def __init__(self):
        self.store: Dict[str, List[OddsSnapshot]] = {}
        self.max_snapshots = 30

    def snapshot(self, match_id: str, odds_data: Dict[str, Any]):
        if match_id not in self.store:
            self.store[match_id] = []
            
        snap = OddsSnapshot(match_id, odds_data)
        self.store[match_id].append(snap)
        
        # Keep only the latest `max_snapshots` snapshots
        if len(self.store[match_id]) > self.max_snapshots:
            self.store[match_id] = self.store[match_id][-self.max_snapshots:]

    def get_movement(self, match_id: str) -> Dict[str, Any]:
        """Returns the latest odds with movement arrows, velocity, and implied probabilities."""
        if match_id not in self.store or not self.store[match_id]:
            return {}

        snaps = self.store[match_id]
        current_snap = snaps[-1]
        
        movement_data: Dict[str, Any] = {
            "match_id": match_id,
            "markets": {}
        }
        
        # Structure current first
        for market, outcomes in current_snap.odds.get("markets", {}).items():
            movement_data["markets"][market] = {}
            for outcome, current_odd in outcomes.items():
                implied_prob = round((1 / current_odd) * 100, 1) if current_odd > 0 else 0
                movement_data["markets"][market][outcome] = {
                    "odd": current_odd,
                    "implied_prob": f"{implied_prob}%",
                    "movement_icon": "─",
                    "velocity_label": "STABLE",
                    "diff": 0.0
                }
                
        # Compare with previous if available
        if len(snaps) > 1:
            prev_snap = snaps[-2]
            time_diff_mins = max((current_snap.timestamp - prev_snap.timestamp) / 60.0, 1.0)
            
            for market, outcomes in current_snap.odds.get("markets", {}).items():
                for outcome, current_odd in outcomes.items():
                    prev_odd = prev_snap.odds.get("markets", {}).get(market, {}).get(outcome)
                    if prev_odd is not None and prev_odd > 0:
                        diff = round(current_odd - prev_odd, 3)
                        movement_data["markets"][market][outcome]["diff"] = diff
                        
                        if diff > 0:
                            movement_data["markets"][market][outcome]["movement_icon"] = "📈"
                        elif diff < 0:
                            movement_data["markets"][market][outcome]["movement_icon"] = "📉"
                            
                        # Velocity
                        velocity = abs(diff) / time_diff_mins
                        if velocity > 0.05:
                            movement_data["markets"][market][outcome]["velocity_label"] = "🚨 FAST MOVE"
                        elif velocity > 0.02:
                            movement_data["markets"][market][outcome]["velocity_label"] = "⚠️ MOVING"
                            
        return movement_data

    def get_trajectory(self, match_id: str, market: str, outcome: str, n: int = 6) -> List[Dict[str, Any]]:
        """Returns the last N snapshots for a specific market/outcome as a trajectory list.
        
        Each entry: {"mins_ago": float, "odd": float, "implied": str}
        """
        if match_id not in self.store or not self.store[match_id]:
            return []
            
        snaps = self.store[match_id]
        now = snaps[-1].timestamp
        
        trajectory = []
        # Walk backwards from latest, take up to n snapshots that have this market
        relevant_snaps = []
        for snap in reversed(snaps):
            odd_val = snap.odds.get("markets", {}).get(market, {}).get(outcome)
            if odd_val is not None and odd_val > 0:
                relevant_snaps.append((snap.timestamp, odd_val))
            if len(relevant_snaps) >= n:
                break
                
        # Reverse so oldest is first
        relevant_snaps.reverse()
        
        for ts, odd_val in relevant_snaps:
            mins_ago = round((now - ts) / 60.0, 1)
            implied = round((1 / odd_val) * 100, 1) if odd_val > 0 else 0
            trajectory.append({
                "mins_ago": mins_ago,
                "odd": odd_val,
                "implied": f"{implied}%"
            })
            
        return trajectory
