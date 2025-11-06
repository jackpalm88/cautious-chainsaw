from functools import lru_cache

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Application configuration loaded from environment variables."""

    api_prefix: str = Field(default="/api")
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173", "*"]
    )
    socket_ping_interval: float = 20.0
    socket_ping_timeout: float = 30.0
    fusion_default_symbol: str = "EURUSD"
    decision_history_limit: int = 20


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
