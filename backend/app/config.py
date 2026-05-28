from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    app_name: str = "LLM API Mind"
    environment: str = "local"
    log_level: str = "INFO"

    llm_provider: str = "minimax"

    minimax_api_key: str | None = Field(default=None, repr=False)
    minimax_base_url: str = "https://api.minimax.io/anthropic"
    minimax_model: str = "MiniMax-M2.7"
    minimax_max_tokens: int = Field(default=131072, ge=1)

    qwen_api_key: str | None = Field(default=None, repr=False)
    qwen_base_url: str = "https://dashscope-intl.aliyuncs.com/apps/anthropic"
    qwen_model: str = "qwen3.7-max"
    qwen_max_tokens: int = Field(default=4096, ge=1)

    agent_system_prompt: str | None = Field(default=None, repr=False)
    agent_system_prompt_path: str | None = None

    database_url: str = "sqlite:///./data/app.db"

    maintenance_enabled: bool = True
    maintenance_idle_seconds: int = Field(default=900, ge=0)
    maintenance_worker_interval_seconds: float = Field(default=5.0, gt=0)
    maintenance_job_batch_size: int = Field(default=5, ge=1, le=50)

    retrieval_shadow_enabled: bool = False
    retrieval_shadow_backend: str = "none"
    retrieval_shadow_top_k: int = Field(default=10, ge=1, le=50)
    retrieval_shadow_vector_dim: int = Field(default=128, ge=8, le=4096)
    retrieval_shadow_embedding_model: str = "local_hash_embedding_v1"
    milvus_lite_uri: str = "./data/milvus_lite_shadow.db"
    milvus_collection: str = "memory_surfaces_shadow"

    runtime_timezone: str = "Europe/Rome"
    runtime_language: str = "it"
    runtime_language_label: str = "Italiano"
    runtime_country_code: str = "IT"
    runtime_country_label: str = "Italia"
    user_profile_id: str = "local-user"
    user_display_name: str = "Utente locale"
    user_privacy_scope: str = "local_single_user"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
