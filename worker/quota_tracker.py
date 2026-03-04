"""Quota Tracker — dual-mode (in-memory / Redis).

Tracks API key usage counters and rate-limit state.
Uses in-memory dict by default; optionally backed by Redis
for multi-process setups.
"""

import time
import logging
import datetime
from typing import Optional

logger = logging.getLogger("oddnoty.quota_tracker")


def _next_midnight_ts() -> int:
    """Unix timestamp of the next midnight (local time)."""
    now = datetime.datetime.now()
    midnight = (now + datetime.timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return int(midnight.timestamp())


# ── In-Memory Tracker ──────────────────────────────────────────────────────

class InMemoryQuotaTracker:
    """Simple in-memory quota tracker. Resets on process restart.

    Good for single-process setups and development. For multi-process
    or multi-machine deployments, use RedisQuotaTracker instead.
    """

    def __init__(self):
        self._usage: dict[str, int] = {}
        self._rate_limits: dict[str, float] = {}  # key_id → expires_at

    def increment_usage(self, key_id: str, limit: int) -> dict:
        """Increment usage counter for a key. Returns status dict."""
        self._usage[key_id] = self._usage.get(key_id, 0) + 1
        used = self._usage[key_id]
        return {
            "key_id": key_id,
            "used": used,
            "limit": limit,
            "remaining": max(0, limit - used),
            "exhausted": used >= limit,
        }

    def get_usage(self, key_id: str) -> int:
        """Get current usage count for a key."""
        return self._usage.get(key_id, 0)

    def mark_rate_limited(self, key_id: str, retry_after_seconds: int = 3600):
        """Mark a key as rate-limited until expiry."""
        self._rate_limits[key_id] = time.time() + retry_after_seconds

    def is_rate_limited(self, key_id: str) -> bool:
        """Check if a key is currently rate-limited."""
        expires = self._rate_limits.get(key_id, 0)
        if time.time() >= expires:
            self._rate_limits.pop(key_id, None)
            return False
        return True

    def reset(self, key_id: Optional[str] = None):
        """Reset usage counters. If key_id is None, resets all."""
        if key_id:
            self._usage.pop(key_id, None)
            self._rate_limits.pop(key_id, None)
        else:
            self._usage.clear()
            self._rate_limits.clear()

    def get_all_usage(self) -> dict[str, int]:
        """Get usage dict for all tracked keys."""
        return dict(self._usage)


# ── Redis Tracker ──────────────────────────────────────────────────────────

class RedisQuotaTracker:
    """Redis-backed quota tracker for multi-process deployments.

    Usage counters auto-expire at midnight (local time).
    Rate-limit flags auto-expire after the retry-after window.

    Requires: redis>=5.0.0
    """

    PREFIX = "oddnoty:quota"

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        try:
            import redis
            self._redis = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self._redis.ping()
            logger.info(f"Redis quota tracker connected: {redis_url}")
        except Exception as e:
            logger.error(f"Redis connection failed: {e} — falling back to in-memory")
            raise

    def increment_usage(self, key_id: str, limit: int) -> dict:
        """Atomically increment usage counter in Redis."""
        counter_key = f"{self.PREFIX}:{key_id}:used"
        pipe = self._redis.pipeline()
        pipe.incr(counter_key)
        pipe.expireat(counter_key, _next_midnight_ts())
        results = pipe.execute()
        used = results[0]
        return {
            "key_id": key_id,
            "used": used,
            "limit": limit,
            "remaining": max(0, limit - used),
            "exhausted": used >= limit,
        }

    def get_usage(self, key_id: str) -> int:
        """Get current usage count from Redis."""
        val = self._redis.get(f"{self.PREFIX}:{key_id}:used")
        return int(val) if val else 0

    def mark_rate_limited(self, key_id: str, retry_after_seconds: int = 3600):
        """Set rate-limit flag in Redis with auto-expiry."""
        self._redis.setex(
            f"{self.PREFIX}:ratelimit:{key_id}",
            retry_after_seconds,
            "1",
        )

    def is_rate_limited(self, key_id: str) -> bool:
        """Check if rate-limit flag exists in Redis."""
        return self._redis.exists(f"{self.PREFIX}:ratelimit:{key_id}") == 1

    def reset(self, key_id: Optional[str] = None):
        """Delete usage counters. If key_id is None, deletes all."""
        if key_id:
            self._redis.delete(
                f"{self.PREFIX}:{key_id}:used",
                f"{self.PREFIX}:ratelimit:{key_id}",
            )
        else:
            for k in self._redis.scan_iter(f"{self.PREFIX}:*"):
                self._redis.delete(k)

    def get_all_usage(self) -> dict[str, int]:
        """Get usage for all tracked keys via scan."""
        result = {}
        for k in self._redis.scan_iter(f"{self.PREFIX}:*:used"):
            key_id = k.split(":")[2]
            val = self._redis.get(k)
            result[key_id] = int(val) if val else 0
        return result


# ── Factory ────────────────────────────────────────────────────────────────

def create_quota_tracker(
    redis_url: Optional[str] = None,
) -> InMemoryQuotaTracker | RedisQuotaTracker:
    """Create a quota tracker. Tries Redis first; falls back to in-memory.

    Args:
        redis_url: If provided, attempts Redis connection. If None or
                   connection fails, returns InMemoryQuotaTracker.
    """
    if redis_url:
        try:
            return RedisQuotaTracker(redis_url)
        except Exception:
            logger.warning("Redis unavailable — using in-memory quota tracker")
    return InMemoryQuotaTracker()
