"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """App settings loaded from .env or environment."""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://oddnoty:changeme@localhost:5432/oddnoty"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Data source
    DATA_SOURCE: str = "sportmonks"  # or "theoddsapi"
    SPORTMONKS_API_KEY: str = ""
    THEODDSAPI_KEY: str = ""

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # Worker
    WORKER_INTERVAL_SECONDS: int = 10
    ODDS_MOVEMENT_THRESHOLD_PERCENT: float = 15.0

    # App
    SECRET_KEY: str = "change-this-to-a-random-secret"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
