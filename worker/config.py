"""Worker configuration."""

from pydantic_settings import BaseSettings


class WorkerSettings(BaseSettings):
    """Worker settings loaded from .env or environment."""

    # Data source (legacy single-key mode — used if KEY_POOL_CONFIG absent)
    DATA_SOURCE: str = "sportmonks"
    SPORTMONKS_API_KEY: str = ""
    THEODDSAPI_KEY: str = ""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://oddnoty:changeme@localhost:5432/oddnoty"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # Worker
    WORKER_INTERVAL_SECONDS: int = 10
    ODDS_MOVEMENT_THRESHOLD_PERCENT: float = 15.0

    # ── Key Pool Configuration ─────────────────────────────────────
    # Path to YAML config with multi-provider key pool definitions.
    # If this file exists, multi-key rotation is enabled automatically.
    KEY_POOL_CONFIG_PATH: str = "goaledge_keys.yaml"

    # Rotation strategy: "reactive", "proactive", "roundrobin", "weighted"
    ROTATION_STRATEGY: str = "proactive"

    # Safety threshold for proactive rotation (0.0–1.0).
    # Keys are rotated when usage reaches this fraction of the daily limit.
    SAFETY_THRESHOLD: float = 0.85

    # Print key health dashboard every N pipeline cycles (0 = disabled)
    HEALTH_DASHBOARD_INTERVAL: int = 30

    # Use Redis for quota tracking (multi-process support).
    # If false, uses in-memory tracking (resets on restart).
    USE_REDIS_QUOTA: bool = False

    # Score polling interval (seconds) — score pillar
    SCORE_POLL_INTERVAL: int = 15

    # Odds polling interval (seconds) — odds pillar
    ODDS_POLL_INTERVAL: int = 30

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }
