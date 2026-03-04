"""GoalEdge Key Pool Manager.

Multi-provider API key rotation with fallback support.
Manages a pool of API keys across multiple providers and routes requests
to whichever key/provider has budget remaining.

ODDS SCOPE: Only Over/Under Goals markets (O/U 0.5, 1.5, 2.5, 3.5).
No other betting markets are requested or stored.
"""

import time
import random
import logging
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
from pathlib import Path

import yaml

logger = logging.getLogger("oddnoty.key_pool")


# ── O/U Goals Market Constants ─────────────────────────────────────────────

# Betfair market type strings — Soccer eventTypeId=1
BETFAIR_OU_MARKETS = [
    "OVER_UNDER_05",  # Over/Under 0.5 goals
    "OVER_UNDER_15",  # Over/Under 1.5 goals
    "OVER_UNDER_25",  # Over/Under 2.5 goals
    "OVER_UNDER_35",  # Over/Under 3.5 goals
]

# TheOddsAPI query params — always pass markets=totals to avoid
# pulling h2h, spreads, or any non-goals market
THEODDSAPI_OU_PARAMS = {
    "regions": "uk",
    "markets": "totals",  # totals = Over/Under goals ONLY
    "oddsFormat": "decimal",
}

# Human-readable label map for the output model
OU_LABEL_MAP = {
    # Betfair market type strings
    "OVER_UNDER_05": "ou_05",
    "OVER_UNDER_15": "ou_15",
    "OVER_UNDER_25": "ou_25",
    "OVER_UNDER_35": "ou_35",
    # TheOddsAPI point values
    "0.5": "ou_05",
    "1.5": "ou_15",
    "2.5": "ou_25",
    "3.5": "ou_35",
}

# Supported O/U lines
SUPPORTED_LINES = [0.5, 1.5, 2.5, 3.5]


class KeyStatus(Enum):
    """Status of an API key in the pool."""
    ACTIVE = "active"
    LIMITED = "limited"       # 429 received — wait for reset
    EXHAUSTED = "exhausted"   # daily/monthly quota used up
    DEAD = "dead"             # invalid key / account banned


@dataclass
class KeyStats:
    """Tracks state and usage for a single API key."""
    key_id: str
    provider: str
    api_key: Optional[str]
    base_url: Optional[str]
    daily_limit: int
    priority: int
    rate_limit_window: str = "day"
    used: int = 0
    status: KeyStatus = KeyStatus.ACTIVE
    reset_at: float = 0.0
    last_used: float = 0.0
    error_count: int = 0
    extra: dict = field(default_factory=dict)  # provider-specific config


class KeyPoolManager:
    """Manages a pool of API keys across multiple providers.

    Supports:
    - 429-triggered rotation (reactive)
    - Proactive threshold rotation (counter-based)
    - Round-robin (even distribution)
    - Priority-weighted random selection

    Odds requests are hardcoded to Over/Under Goals markets only.
    """

    SAFETY_THRESHOLD = 0.85  # rotate at 85% of daily limit

    def __init__(
        self,
        config_path: str = "goaledge_keys.yaml",
        strategy: str = "proactive",
        safety_threshold: float = 0.85,
    ):
        """Initialize key pool manager.

        Args:
            config_path: Path to YAML config file with key definitions
            strategy: Rotation strategy — "reactive", "proactive", "roundrobin", "weighted"
            safety_threshold: Fraction of daily limit before proactive rotation (0.0–1.0)
        """
        self.strategy = strategy
        self.SAFETY_THRESHOLD = safety_threshold
        self._pools: dict[str, list[KeyStats]] = {}
        self._rr_index: dict[str, int] = {}
        self._load_config(config_path)

    def _load_config(self, path: str):
        """Load key pool configuration from YAML file."""
        config_path = Path(path)
        
        # Prefer .local.yaml version if it exists (allows git-ignoring real keys)
        local_path = config_path.parent / (config_path.stem + ".local" + config_path.suffix)
        if local_path.exists():
            logger.info(f"Using local key config: {local_path}")
            config_path = local_path
        elif not config_path.exists():
            logger.warning(f"Key pool config not found at {path} — starting with empty pools")
            return

        with open(config_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        if not cfg:
            logger.warning("Key pool config is empty")
            return

        for group_name, keys in cfg.items():
            if not isinstance(keys, list):
                continue
            self._pools[group_name] = []
            self._rr_index[group_name] = 0
            for k in keys:
                self._pools[group_name].append(KeyStats(
                    key_id=k["id"],
                    provider=k["provider"],
                    api_key=k.get("key"),
                    base_url=k.get("base_url"),
                    daily_limit=k.get("daily_limit", k.get("monthly_limit", 100)),
                    priority=k.get("priority", 99),
                    rate_limit_window=k.get("rate_limit_window", "day"),
                    extra={
                        kk: vv for kk, vv in k.items()
                        if kk not in ("id", "provider", "key", "base_url",
                                      "daily_limit", "monthly_limit",
                                      "priority", "rate_limit_window")
                    },
                ))
        logger.info(f"Loaded key pools: {{{', '.join(f'{g}: {len(v)} keys' for g, v in self._pools.items())}}}")

    # ── Key Selection ──────────────────────────────────────────────

    def get_key(self, group: str) -> Optional[KeyStats]:
        """Select the best available key from the given group.

        Returns None if all keys are exhausted.
        """
        available = self._get_available(group)
        if not available:
            logger.error(f"[{group}] ALL KEYS EXHAUSTED — no available key")
            return None

        if self.strategy == "roundrobin":
            return self._round_robin(group, available)
        elif self.strategy == "weighted":
            return self._weighted(available)
        else:
            # reactive and proactive both use priority ordering
            return sorted(available, key=lambda k: k.priority)[0]

    def _get_available(self, group: str) -> list[KeyStats]:
        """Get list of currently usable keys in a group."""
        now = time.time()
        available = []

        for k in self._pools.get(group, []):
            # Reactivate keys whose reset window has passed
            if k.status == KeyStatus.LIMITED and now >= k.reset_at:
                logger.info(f"[{k.key_id}] Reset window passed — reactivating")
                k.status = KeyStatus.ACTIVE
                k.used = 0

            if k.status != KeyStatus.ACTIVE:
                continue

            # Proactive threshold check
            if self.strategy == "proactive":
                if k.daily_limit > 0 and k.used >= k.daily_limit * self.SAFETY_THRESHOLD:
                    logger.warning(
                        f"[{k.key_id}] Proactive threshold hit "
                        f"({k.used}/{k.daily_limit}) — skipping"
                    )
                    continue

            available.append(k)
        return available

    def _round_robin(self, group: str, available: list[KeyStats]) -> KeyStats:
        """Select keys in round-robin order."""
        idx = self._rr_index.get(group, 0) % len(available)
        self._rr_index[group] = (idx + 1) % len(available)
        return available[idx]

    def _weighted(self, available: list[KeyStats]) -> KeyStats:
        """Select keys with priority-weighted random distribution."""
        max_p = max(k.priority for k in available)
        weights = [(max_p - k.priority + 1) for k in available]
        return random.choices(available, weights=weights, k=1)[0]

    # ── Response Handling ──────────────────────────────────────────

    def record_success(self, key: KeyStats):
        """Record a successful API call for usage tracking."""
        key.used += 1
        key.last_used = time.time()
        key.error_count = max(0, key.error_count - 1)

    def handle_response(self, key: KeyStats, status_code: int,
                        headers: Optional[dict] = None) -> bool:
        """Handle an API response — returns True if successful.

        On failure, marks the key with appropriate status and returns False
        so the caller can retry with the next available key.
        """
        headers = headers or {}

        if status_code == 200:
            self.record_success(key)
            return True

        elif status_code == 429:
            retry_after = int(headers.get("Retry-After", 3600))
            key.status = KeyStatus.LIMITED
            key.reset_at = time.time() + retry_after
            logger.warning(
                f"[{key.key_id}] 429 Rate Limited — rotating. "
                f"Retry after {retry_after}s"
            )
            return False

        elif status_code in (401, 403):
            key.status = KeyStatus.DEAD
            logger.error(f"[{key.key_id}] {status_code} — key marked DEAD")
            return False

        elif status_code == 402:
            key.status = KeyStatus.EXHAUSTED
            key.reset_at = self._next_midnight()
            logger.warning(
                f"[{key.key_id}] 402 Quota Exhausted — resets at midnight"
            )
            return False

        else:
            key.error_count += 1
            if key.error_count >= 5:
                key.status = KeyStatus.DEAD
                logger.error(f"[{key.key_id}] {key.error_count} consecutive errors — marking DEAD")
            return False

    # ── Pool Status ────────────────────────────────────────────────

    def get_pool_status(self) -> dict:
        """Get usage and health status for all key pools."""
        status = {}
        for group, keys in self._pools.items():
            status[group] = [
                {
                    "id": k.key_id,
                    "provider": k.provider,
                    "used": k.used,
                    "limit": k.daily_limit,
                    "pct": round(k.used / max(k.daily_limit, 1) * 100, 1),
                    "status": k.status.value,
                }
                for k in keys
            ]
        return status

    def total_remaining(self, group: str) -> int:
        """Total remaining request budget across all active keys in a group."""
        return sum(
            max(0, k.daily_limit - k.used)
            for k in self._pools.get(group, [])
            if k.status == KeyStatus.ACTIVE
        )

    def get_all_groups(self) -> list[str]:
        """Return list of all configured pool group names."""
        return list(self._pools.keys())

    def has_available_key(self, group: str) -> bool:
        """Check if at least one key is available in the group."""
        return len(self._get_available(group)) > 0

    # ── Utilities ──────────────────────────────────────────────────

    @staticmethod
    def _next_midnight() -> float:
        """Timestamp of the next midnight (local time)."""
        import datetime
        now = datetime.datetime.now()
        midnight = (now + datetime.timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return midnight.timestamp()

    def add_key(self, group: str, key_stats: KeyStats):
        """Dynamically add a key to a pool group at runtime."""
        if group not in self._pools:
            self._pools[group] = []
            self._rr_index[group] = 0
        self._pools[group].append(key_stats)
        logger.info(f"Added key {key_stats.key_id} to [{group}]")

    def reset_all(self):
        """Reset all keys to ACTIVE with zero usage (for testing or daily reset)."""
        for group, keys in self._pools.items():
            for k in keys:
                if k.status != KeyStatus.DEAD:
                    k.status = KeyStatus.ACTIVE
                    k.used = 0
                    k.error_count = 0
        logger.info("All key pools reset")
