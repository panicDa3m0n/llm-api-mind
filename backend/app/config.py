from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    app_name: str = "LLM API Mind"
    environment: str = "local"
    log_level: str = "INFO"

    llm_provider: str = "minimax"

    minimax_api_key: str | None = Field(default=None, repr=False)
    minimax_base_url: str = "https://api.minimax.io/anthropic"
    minimax_model: str = "MiniMax-M3"
    minimax_max_tokens: int = Field(default=131072, ge=1)
    auxiliary_minimax_model: str = "MiniMax-M2.7"
    auxiliary_minimax_max_tokens: int = Field(default=131072, ge=1)

    qwen_api_key: str | None = Field(default=None, repr=False)
    qwen_base_url: str = "https://dashscope-intl.aliyuncs.com/apps/anthropic"
    qwen_model: str = "qwen3.7-max"
    qwen_max_tokens: int = Field(default=4096, ge=1)

    provider_stream_max_attempts: int = Field(default=5, ge=1, le=5)
    provider_stream_retry_backoff_seconds: float = Field(
        default=0.5,
        ge=0.0,
        le=10.0,
    )
    provider_max_token_continuations: int = Field(default=8, ge=1, le=16)
    agent_system_prompt: str | None = Field(default=None, repr=False)
    agent_system_prompt_path: str | None = None

    database_url: str = "sqlite:///./data/app.db"
    database_role: str = "auto"
    codex_test: bool = False
    codex_test_database_url: str = "sqlite:///./data/codex_test.db"
    codex_test_seed_database_url: str | None = None

    maintenance_enabled: bool = True
    maintenance_idle_seconds: int = Field(default=900, ge=0)
    maintenance_worker_interval_seconds: float = Field(default=5.0, gt=0)
    maintenance_job_batch_size: int = Field(default=5, ge=1, le=50)
    summary_reconcile_enabled: bool = True
    summary_reconcile_batch_size: int = Field(default=2, ge=1, le=20)
    summary_reconcile_max_attempts: int = Field(default=3, ge=1, le=10)
    summary_reconcile_retry_backoff_seconds: int = Field(default=60, ge=1)

    autonomous_activation_enabled: bool = True
    # The legacy periodic interval is retained for non-active workspace modes.
    # Active cognition is governed by the shared min-gap/max-silence scheduler.
    autonomous_activation_interval_seconds: int = Field(default=600, ge=30)
    autonomous_activation_min_gap_seconds: int = Field(default=900, ge=60)
    autonomous_activation_max_silence_seconds: int = Field(default=10800, ge=900)
    autonomous_activation_worker_interval_seconds: float = Field(
        default=5.0,
        gt=0,
    )
    autonomous_activation_lease_seconds: int = Field(default=900, ge=60)
    autonomous_activation_defer_seconds: int = Field(default=60, ge=10)
    autonomous_activation_human_turn_freshness_seconds: int = Field(
        default=21600,
        ge=60,
    )
    autonomous_activation_batch_size: int = Field(default=1, ge=1, le=5)
    autonomous_activation_perception_channel_limit: int = Field(
        default=20,
        ge=1,
        le=100,
    )
    cognitive_workspace_mode: Literal["off", "shadow", "advisory", "active"] = (
        "active"
    )
    cognitive_workspace_signal_batch_size: int = Field(default=100, ge=1, le=1000)
    cognitive_workspace_appraisal_batch_size: int = Field(default=20, ge=1, le=100)
    cognitive_workspace_candidate_pool_limit: int = Field(default=20, ge=1, le=100)
    cognitive_workspace_parked_candidate_context_limit: int = Field(
        default=12,
        ge=0,
        le=50,
    )
    cognitive_workspace_appraisal_max_tokens: int = Field(
        default=8192,
        ge=512,
        le=32768,
    )
    cognitive_workspace_arbitration_max_tokens: int = Field(
        default=8192,
        ge=512,
        le=32768,
    )
    cognitive_workspace_max_deferrals: int = Field(default=3, ge=1, le=20)
    endogenous_cognition_enabled: bool = True
    endogenous_cognition_min_interval_seconds: int = Field(
        default=900,
        ge=300,
    )
    endogenous_cognition_base_interval_seconds: int = Field(
        default=3600,
        ge=300,
    )
    endogenous_cognition_max_interval_seconds: int = Field(
        default=10800,
        ge=900,
    )
    endogenous_cognition_productive_followup_seconds: int = Field(
        default=1800,
        ge=300,
    )
    endogenous_cognition_max_seeds: int = Field(default=4, ge=1, le=8)
    endogenous_cognition_max_tokens: int = Field(
        default=8192,
        ge=512,
        le=32768,
    )
    device_perception_admission_mode: Literal["off", "shadow", "active"] = "active"

    # Research Lab is an opt-in shell capability. Its Python execution lives
    # in a separate, network-disabled runner; the backend never executes
    # model-supplied code in-process.
    research_lab_enabled: bool = False
    research_lab_runner_uds: str | None = None
    research_lab_runner_timeout_seconds: float = Field(default=20.0, gt=0, le=60)
    research_lab_code_max_chars: int = Field(default=12_000, ge=256, le=12_000)
    research_lab_source_max_chars: int = Field(default=30_000, ge=1_000, le=30_000)
    research_lab_model_source_max_chars: int = Field(
        default=12_000,
        ge=1_000,
        le=30_000,
    )
    research_lab_web_timeout_seconds: float = Field(default=12.0, gt=0, le=60)
    research_lab_web_max_bytes: int = Field(default=512_000, ge=8_192, le=5_000_000)
    research_lab_artifact_max_bytes: int = Field(
        default=1_000_000,
        ge=8_192,
        le=1_000_000,
    )

    model_context_profile: Literal["legacy", "v2_shadow", "v2"] = "v2"
    model_context_previous_sessions_limit: int = Field(default=2, ge=0, le=10)
    model_context_relevant_memories_limit: int = Field(default=5, ge=0, le=20)
    model_context_recent_user_memories_limit: int = Field(default=5, ge=0, le=20)
    model_context_recent_general_memories_limit: int = Field(default=5, ge=0, le=20)

    context_window_tokens: int = Field(default=1_000_000, ge=1)
    context_operational_input_limit_tokens: int = Field(default=500_000, ge=1)
    context_compaction_trigger_tokens: int = Field(default=400_000, ge=1)
    history_compaction_target_tokens: int = Field(default=100_000, ge=1)
    history_compaction_verbatim_tokens: int = Field(default=100_000, ge=1)
    history_compaction_safety_tokens: int = Field(default=25_000, ge=0)
    # Retained for environment compatibility; selection is token-based in V1.36.
    history_compaction_recent_turns: int = Field(default=8, ge=1, le=100)
    history_compaction_mode: Literal["off", "shadow", "active"] = "shadow"
    context_estimated_chars_per_token: float = Field(default=3.5, ge=1.0, le=12.0)

    retrieval_shadow_enabled: bool = False
    retrieval_shadow_backend: str = "none"
    retrieval_shadow_top_k: int = Field(default=10, ge=1, le=50)
    retrieval_shadow_vector_dim: int = Field(default=2048, ge=8, le=4096)
    retrieval_shadow_embedding_model: str = "local_hash_embedding_v1"
    retrieval_shadow_cloud_surface_limit: int = Field(default=50, ge=1, le=500)
    retrieval_shadow_http_timeout_seconds: float = Field(default=30.0, gt=0)
    retrieval_shadow_rerank_enabled: bool = False
    retrieval_shadow_rerank_model: str = "nvidia/llama-nemotron-rerank-vl-1b-v2:free"
    retrieval_shadow_rerank_candidate_limit: int = Field(default=20, ge=1, le=100)
    retrieval_shadow_rerank_top_n: int = Field(default=10, ge=1, le=50)
    retrieval_hybrid_mode: str = "off"
    retrieval_hybrid_min_dense_score: float = Field(default=0.38, ge=-1.0, le=1.0)
    retrieval_hybrid_min_rerank_score: float = Field(default=0.004, ge=0.0, le=1.0)
    retrieval_hybrid_relative_rerank_floor: float = Field(
        default=0.01,
        ge=0.0,
        le=1.0,
    )
    # Retained for environment compatibility only. V1.31 active retrieval does
    # not fuse hand-authored weights; the final memory-level reranker decides.
    retrieval_hybrid_base_weight: float = Field(default=0.35, ge=0.0, le=1.0)
    retrieval_hybrid_sparse_weight: float = Field(default=0.15, ge=0.0, le=1.0)
    retrieval_hybrid_dense_weight: float = Field(default=0.35, ge=0.0, le=1.0)
    retrieval_hybrid_rerank_weight: float = Field(default=0.20, ge=0.0, le=1.0)
    retrieval_hybrid_support_weight: float = Field(default=0.05, ge=0.0, le=1.0)
    retrieval_hybrid_salience_weight: float = Field(default=0.0, ge=0.0, le=1.0)
    retrieval_hybrid_confidence_weight: float = Field(default=0.0, ge=0.0, le=1.0)
    milvus_lite_uri: str = "./data/milvus_lite_shadow.db"
    milvus_collection: str = "memory_surfaces_shadow"

    openrouter_api_key: str | None = Field(default=None, repr=False)
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    metacognitive_context_mode: str = "shadow"
    metacognitive_context_max_lessons: int = Field(default=3, ge=1, le=5)

    organ_focus_mode: str = "off"
    organ_volition_mode: str = "off"
    organ_affect_mode: str = "off"
    organ_temporal_experience_mode: str = "off"
    organ_dream_mode: str = "off"

    agent_mode_default: Literal["idle", "interactive", "scouting"] = "idle"
    agent_mode_routing: Literal["off", "shadow", "active"] = "active"

    runtime_timezone: str = "Europe/Rome"
    runtime_language: str = "it"
    runtime_language_label: str = "Italiano"
    runtime_country_code: str = "IT"
    runtime_country_label: str = "Italia"
    user_profile_id: str = "local-user"
    user_display_name: str = "Utente locale"
    user_privacy_scope: str = "local_single_user"

    gpt_bridge_api_key: str | None = Field(default=None, repr=False)

    @model_validator(mode="after")
    def validate_context_budget_order(self) -> "Settings":
        if self.context_operational_input_limit_tokens > self.context_window_tokens:
            raise ValueError(
                "context_operational_input_limit_tokens must not exceed "
                "context_window_tokens"
            )
        if (
            self.context_compaction_trigger_tokens
            > self.context_operational_input_limit_tokens
        ):
            raise ValueError(
                "context_compaction_trigger_tokens must not exceed "
                "context_operational_input_limit_tokens"
            )
        if (
            self.history_compaction_target_tokens
            >= self.context_operational_input_limit_tokens
        ):
            raise ValueError(
                "history_compaction_target_tokens must stay below "
                "context_operational_input_limit_tokens"
            )
        reserved_history = (
            self.history_compaction_target_tokens
            + self.history_compaction_verbatim_tokens
            + self.history_compaction_safety_tokens
        )
        if reserved_history >= self.context_operational_input_limit_tokens:
            raise ValueError(
                "history summary, verbatim chronology, and safety reservations "
                "must leave active growth space below the operational input limit"
            )
        if self.history_compaction_mode == "active" and not self.maintenance_enabled:
            raise ValueError(
                "active history compaction requires the maintenance worker"
            )
        if not (
            self.endogenous_cognition_min_interval_seconds
            <= self.endogenous_cognition_productive_followup_seconds
            <= self.endogenous_cognition_max_interval_seconds
        ):
            raise ValueError(
                "endogenous productive follow-up must stay between the minimum "
                "and maximum cognitive-window intervals"
            )
        if not (
            self.endogenous_cognition_min_interval_seconds
            <= self.endogenous_cognition_base_interval_seconds
            <= self.endogenous_cognition_max_interval_seconds
        ):
            raise ValueError(
                "endogenous base interval must stay between the minimum and "
                "maximum cognitive-window intervals"
            )
        if (
            self.autonomous_activation_max_silence_seconds
            < self.autonomous_activation_min_gap_seconds
        ):
            raise ValueError(
                "autonomous activation max silence must not be shorter than the "
                "minimum M3 activation gap"
            )
        if self.research_lab_model_source_max_chars > self.research_lab_source_max_chars:
            raise ValueError(
                "research_lab_model_source_max_chars must not exceed "
                "research_lab_source_max_chars"
            )
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
