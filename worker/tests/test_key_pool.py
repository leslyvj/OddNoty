"""Tests for the KeyPoolManager."""

import time
import pytest
import tempfile
import os

from key_pool import KeyPoolManager, KeyStats, KeyStatus


# ── Helpers ────────────────────────────────────────────────────────────────

def _create_temp_config(content: str) -> str:
    """Write YAML content to a temp file and return the path."""
    fd, path = tempfile.mkstemp(suffix=".yaml")
    with os.fdopen(fd, "w") as f:
        f.write(content)
    return path


SAMPLE_CONFIG = """
score_providers:
  - id: key_a
    provider: football-data
    key: "test_key_a"
    base_url: "https://api.football-data.org/v4"
    daily_limit: 100
    priority: 1

  - id: key_b
    provider: football-data
    key: "test_key_b"
    base_url: "https://api.football-data.org/v4"
    daily_limit: 100
    priority: 2

  - id: key_c
    provider: api-football
    key: "test_key_c"
    base_url: "https://v3.football.api-sports.io"
    daily_limit: 50
    priority: 3

odds_providers:
  - id: odds_a
    provider: theoddsapi
    key: "test_odds_a"
    base_url: "https://api.the-odds-api.com/v4"
    daily_limit: 16
    priority: 1

  - id: odds_b
    provider: theoddsapi
    key: "test_odds_b"
    base_url: "https://api.the-odds-api.com/v4"
    daily_limit: 16
    priority: 2
"""


# ── Test: Config Loading ──────────────────────────────────────────────────

class TestConfigLoading:
    def test_loads_yaml_config(self):
        path = _create_temp_config(SAMPLE_CONFIG)
        try:
            pool = KeyPoolManager(config_path=path, strategy="proactive")
            status = pool.get_pool_status()
            assert "score_providers" in status
            assert "odds_providers" in status
            assert len(status["score_providers"]) == 3
            assert len(status["odds_providers"]) == 2
        finally:
            os.unlink(path)

    def test_missing_config_creates_empty_pool(self):
        pool = KeyPoolManager(config_path="/nonexistent/path.yaml")
        assert pool.get_pool_status() == {}

    def test_empty_config_creates_empty_pool(self):
        path = _create_temp_config("")
        try:
            pool = KeyPoolManager(config_path=path)
            assert pool.get_pool_status() == {}
        finally:
            os.unlink(path)


# ── Test: Key Selection ────────────────────────────────────────────────────

class TestKeySelection:
    def _make_pool(self, strategy="proactive") -> KeyPoolManager:
        path = _create_temp_config(SAMPLE_CONFIG)
        pool = KeyPoolManager(config_path=path, strategy=strategy)
        os.unlink(path)
        return pool

    def test_priority_selection(self):
        """Proactive strategy selects highest-priority (lowest number) key."""
        pool = self._make_pool("proactive")
        key = pool.get_key("score_providers")
        assert key is not None
        assert key.key_id == "key_a"
        assert key.priority == 1

    def test_roundrobin_cycles(self):
        """Round-robin selects keys in order and wraps around."""
        pool = self._make_pool("roundrobin")
        ids = [pool.get_key("score_providers").key_id for _ in range(6)]
        assert ids == ["key_a", "key_b", "key_c", "key_a", "key_b", "key_c"]

    def test_weighted_returns_valid_key(self):
        """Weighted always returns a key from the available pool."""
        pool = self._make_pool("weighted")
        for _ in range(20):
            key = pool.get_key("odds_providers")
            assert key is not None
            assert key.key_id in ("odds_a", "odds_b")

    def test_returns_none_when_all_exhausted(self):
        """Returns None when no keys are available."""
        pool = self._make_pool()
        for k in pool._pools["odds_providers"]:
            k.status = KeyStatus.DEAD
        assert pool.get_key("odds_providers") is None

    def test_returns_none_for_unknown_group(self):
        pool = self._make_pool()
        assert pool.get_key("nonexistent_group") is None


# ── Test: Response Handling ────────────────────────────────────────────────

class TestResponseHandling:
    def _make_pool(self) -> KeyPoolManager:
        path = _create_temp_config(SAMPLE_CONFIG)
        pool = KeyPoolManager(config_path=path, strategy="proactive")
        os.unlink(path)
        return pool

    def test_200_records_success(self):
        pool = self._make_pool()
        key = pool.get_key("score_providers")
        assert pool.handle_response(key, 200) is True
        assert key.used == 1
        assert key.status == KeyStatus.ACTIVE

    def test_429_marks_limited(self):
        pool = self._make_pool()
        key = pool.get_key("score_providers")
        result = pool.handle_response(key, 429, {"Retry-After": "60"})
        assert result is False
        assert key.status == KeyStatus.LIMITED
        assert key.reset_at > time.time()

    def test_401_marks_dead(self):
        pool = self._make_pool()
        key = pool.get_key("score_providers")
        result = pool.handle_response(key, 401)
        assert result is False
        assert key.status == KeyStatus.DEAD

    def test_403_marks_dead(self):
        pool = self._make_pool()
        key = pool.get_key("score_providers")
        result = pool.handle_response(key, 403)
        assert result is False
        assert key.status == KeyStatus.DEAD

    def test_402_marks_exhausted(self):
        pool = self._make_pool()
        key = pool.get_key("score_providers")
        result = pool.handle_response(key, 402)
        assert result is False
        assert key.status == KeyStatus.EXHAUSTED

    def test_5_errors_marks_dead(self):
        pool = self._make_pool()
        key = pool.get_key("score_providers")
        for _ in range(5):
            pool.handle_response(key, 500)
        assert key.status == KeyStatus.DEAD


# ── Test: Proactive Threshold ──────────────────────────────────────────────

class TestProactiveThreshold:
    def test_skips_key_at_threshold(self):
        """Key is skipped when usage hits the safety threshold."""
        path = _create_temp_config(SAMPLE_CONFIG)
        pool = KeyPoolManager(config_path=path, strategy="proactive", safety_threshold=0.85)
        os.unlink(path)

        key_a = pool._pools["score_providers"][0]
        key_a.used = 86  # 86/100 = 86% > 85% threshold

        selected = pool.get_key("score_providers")
        assert selected is not None
        assert selected.key_id != "key_a"  # should skip key_a
        assert selected.key_id == "key_b"  # next priority

    def test_uses_key_below_threshold(self):
        path = _create_temp_config(SAMPLE_CONFIG)
        pool = KeyPoolManager(config_path=path, strategy="proactive", safety_threshold=0.85)
        os.unlink(path)

        key_a = pool._pools["score_providers"][0]
        key_a.used = 50  # 50/100 = 50% < 85%

        selected = pool.get_key("score_providers")
        assert selected.key_id == "key_a"


# ── Test: Key Reactivation ─────────────────────────────────────────────────

class TestKeyReactivation:
    def test_reactivates_after_reset_window(self):
        """LIMITED key is reactivated once reset_at passes."""
        path = _create_temp_config(SAMPLE_CONFIG)
        pool = KeyPoolManager(config_path=path, strategy="reactive")
        os.unlink(path)

        # Mark all keys in odds_providers as limited with past reset time
        for k in pool._pools["odds_providers"]:
            k.status = KeyStatus.LIMITED
            k.reset_at = time.time() - 10  # expired 10 seconds ago

        key = pool.get_key("odds_providers")
        assert key is not None
        assert key.status == KeyStatus.ACTIVE

    def test_does_not_reactivate_before_reset(self):
        """LIMITED key stays limited before reset_at."""
        path = _create_temp_config(SAMPLE_CONFIG)
        pool = KeyPoolManager(config_path=path, strategy="reactive")
        os.unlink(path)

        for k in pool._pools["odds_providers"]:
            k.status = KeyStatus.LIMITED
            k.reset_at = time.time() + 3600  # 1 hour from now

        key = pool.get_key("odds_providers")
        assert key is None


# ── Test: Pool Status ──────────────────────────────────────────────────────

class TestPoolStatus:
    def test_total_remaining(self):
        path = _create_temp_config(SAMPLE_CONFIG)
        pool = KeyPoolManager(config_path=path)
        os.unlink(path)

        assert pool.total_remaining("score_providers") == 250  # 100+100+50

        pool._pools["score_providers"][0].used = 30
        assert pool.total_remaining("score_providers") == 220  # 70+100+50

    def test_add_key_dynamically(self):
        path = _create_temp_config(SAMPLE_CONFIG)
        pool = KeyPoolManager(config_path=path)
        os.unlink(path)

        new_key = KeyStats(
            key_id="dynamic_1",
            provider="football-data",
            api_key="dynamic_test",
            base_url="https://api.football-data.org/v4",
            daily_limit=200,
            priority=0,  # highest priority
        )
        pool.add_key("score_providers", new_key)

        selected = pool.get_key("score_providers")
        assert selected.key_id == "dynamic_1"

    def test_reset_all(self):
        path = _create_temp_config(SAMPLE_CONFIG)
        pool = KeyPoolManager(config_path=path)
        os.unlink(path)

        # Use some keys and mark one as limited
        pool._pools["score_providers"][0].used = 80
        pool._pools["score_providers"][1].status = KeyStatus.LIMITED
        pool._pools["score_providers"][2].status = KeyStatus.DEAD

        pool.reset_all()
        # Active and limited should reset; dead stays dead
        assert pool._pools["score_providers"][0].used == 0
        assert pool._pools["score_providers"][1].status == KeyStatus.ACTIVE
        assert pool._pools["score_providers"][2].status == KeyStatus.DEAD
