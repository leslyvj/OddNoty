import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class TrackerManager:
    def __init__(self):
        # A mock store for user trackers. {user_id: [trackers_dict]}
        self.trackers: Dict[int, List[Dict[str, Any]]] = {}

    def add_tracker(self, user_id: int, match_id: str, market: str, outcome: Optional[str] = None, target_odd: float = 0.0):
        if user_id not in self.trackers:
            self.trackers[user_id] = []
            
        self.trackers[user_id].append({
            "match_id": match_id,
            "market": market,
            "outcome": outcome,
            "target_odd": target_odd,
            "last_notified_odd": None,
            "active": True
        })
        logger.info(f"Tracker added for User {user_id}: {market} {outcome} @ {target_odd}")

    def get_trackers(self, user_id: int):
        return self.trackers.get(user_id, [])

    def get_all_trackers(self):
        return self.trackers

    def remove_tracker(self, user_id: int, match_id: str, market: Optional[str] = None, outcome: Optional[str] = None):
        if user_id in self.trackers:
            if market is None:
                self.trackers[user_id] = [t for t in self.trackers[user_id] if t["match_id"] != match_id]
            else:
                self.trackers[user_id] = [t for t in self.trackers[user_id] if not (t["match_id"] == match_id and t["market"] == market and t["outcome"] == outcome)]

    def clear_all(self, user_id: int):
        if user_id in self.trackers:
            self.trackers[user_id] = []
