from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    app_name: str = "LLM API Mind"
    environment: str = "local"
    log_level: str = "INFO"

    minimax_api_key: str | None = Field(default=None, repr=False)
    minimax_base_url: str = "https://api.minimax.io/anthropic"
    minimax_model: str = "MiniMax-M2.7"
    minimax_max_tokens: int = Field(default=4096, ge=1)

    database_url: str = "sqlite:///./data/app.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
