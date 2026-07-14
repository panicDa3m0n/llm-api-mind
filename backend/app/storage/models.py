from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import Column, JSON, UniqueConstraint
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class ChatSession(SQLModel, table=True):
    __tablename__ = "sessions"

    id: str = Field(default_factory=lambda: new_id("ses"), primary_key=True)
    title: str | None = None
    created_at: datetime = Field(default_factory=utc_now, index=True)
    updated_at: datetime = Field(default_factory=utc_now, index=True)
    provider_history_json: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    metadata_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )


class SessionSummary(SQLModel, table=True):
    __tablename__ = "session_summaries"
    __table_args__ = (
        UniqueConstraint("session_id", name="uq_session_summaries_session_id"),
    )

    id: str = Field(default_factory=lambda: new_id("ses_sum"), primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", index=True)
    summary: str
    topics_json: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    decisions_json: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    open_questions_json: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    memory_ids_json: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    message_count: int = Field(default=0)
    source_turn_count: int = Field(default=0)
    last_message_id: str | None = Field(
        default=None,
        foreign_key="messages.id",
        index=True,
    )
    status: str = Field(default="active", index=True)
    summary_version: str = Field(default="episodic-v1", index=True)
    created_at: datetime = Field(default_factory=utc_now, index=True)
    updated_at: datetime = Field(default_factory=utc_now, index=True)
    metadata_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )


class Turn(SQLModel, table=True):
    __tablename__ = "turns"

    id: str = Field(default_factory=lambda: new_id("turn"), primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", index=True)
    status: str = Field(default="started", index=True)
    model: str | None = None
    started_at: datetime = Field(default_factory=utc_now, index=True)
    completed_at: datetime | None = None
    latency_ms: int | None = None
    error_json: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: str = Field(default_factory=lambda: new_id("msg"), primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", index=True)
    turn_id: str | None = Field(default=None, foreign_key="turns.id", index=True)
    role: str = Field(index=True)
    content: str
    provider_message_id: str | None = None
    raw_content_json: dict[str, Any] | list[Any] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    created_at: datetime = Field(default_factory=utc_now, index=True)
    metadata_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )


class Trace(SQLModel, table=True):
    __tablename__ = "traces"

    id: str = Field(default_factory=lambda: new_id("trace"), primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", index=True)
    turn_id: str | None = Field(default=None, foreign_key="turns.id", index=True)
    kind: str = Field(index=True)
    payload_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    created_at: datetime = Field(default_factory=utc_now, index=True)


class CognitiveEvent(SQLModel, table=True):
    __tablename__ = "events"

    id: str = Field(default_factory=lambda: new_id("evt"), primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", index=True)
    turn_id: str | None = Field(default=None, foreign_key="turns.id", index=True)
    seq: int = Field(default=0, index=True)
    type: str = Field(index=True)
    source: str = Field(default="runtime", index=True)
    actor: str = Field(default="backend", index=True)
    visibility: str = Field(default="debug", index=True)
    status: str = Field(default="completed", index=True)
    parent_event_id: str | None = Field(
        default=None,
        foreign_key="events.id",
        index=True,
    )
    trace_id: str | None = Field(default=None, foreign_key="traces.id", index=True)
    tool_call_id: str | None = Field(
        default=None,
        foreign_key="tool_calls.id",
        index=True,
    )
    message_id: str | None = Field(default=None, foreign_key="messages.id", index=True)
    payload_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    created_at: datetime = Field(default_factory=utc_now, index=True)


class AppSetting(SQLModel, table=True):
    __tablename__ = "app_settings"

    key: str = Field(primary_key=True)
    value_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    updated_at: datetime = Field(default_factory=utc_now, index=True)


class MaintenanceJob(SQLModel, table=True):
    __tablename__ = "maintenance_jobs"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_maintenance_jobs_idempotency_key"),
    )

    id: str = Field(default_factory=lambda: new_id("mnt"), primary_key=True)
    kind: str = Field(index=True)
    status: str = Field(default="pending", index=True)
    session_id: str = Field(foreign_key="sessions.id", index=True)
    trigger_turn_id: str | None = Field(
        default=None,
        foreign_key="turns.id",
        index=True,
    )
    trigger_event_id: str | None = Field(
        default=None,
        foreign_key="events.id",
        index=True,
    )
    due_at: datetime = Field(default_factory=utc_now, index=True)
    started_at: datetime | None = Field(default=None, index=True)
    completed_at: datetime | None = Field(default=None, index=True)
    superseded_by_job_id: str | None = Field(
        default=None,
        foreign_key="maintenance_jobs.id",
        index=True,
    )
    idempotency_key: str = Field(index=True)
    input_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    result_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    error_json: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    created_at: datetime = Field(default_factory=utc_now, index=True)
    updated_at: datetime = Field(default_factory=utc_now, index=True)


class ToolCall(SQLModel, table=True):
    __tablename__ = "tool_calls"

    id: str = Field(default_factory=lambda: new_id("tool"), primary_key=True)
    session_id: str | None = Field(default=None, foreign_key="sessions.id", index=True)
    turn_id: str | None = Field(default=None, foreign_key="turns.id", index=True)
    tool_name: str = Field(index=True)
    arguments_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    result_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    status: str = Field(index=True)
    latency_ms: int | None = None
    created_at: datetime = Field(default_factory=utc_now, index=True)


class FocusRecord(SQLModel, table=True):
    __tablename__ = "focus_records"

    id: str = Field(default_factory=lambda: new_id("focus"), primary_key=True)
    owner_profile_id: str = Field(default="local-user", index=True)
    status: str = Field(default="active", index=True)
    focus_object: str = Field(index=True)
    focus_type: str = Field(default="general", index=True)
    intensity: float = Field(default=0.5, ge=0.0, le=1.0)
    duration_policy: str | None = Field(default=None, index=True)
    reason: str
    resolution: str | None = None
    impossible_reason: str | None = None
    created_by: str = Field(default="scarlet", index=True)
    source_session_id: str | None = Field(
        default=None,
        foreign_key="sessions.id",
        index=True,
    )
    source_turn_id: str | None = Field(
        default=None,
        foreign_key="turns.id",
        index=True,
    )
    source_message_id: str | None = Field(
        default=None,
        foreign_key="messages.id",
        index=True,
    )
    created_at: datetime = Field(default_factory=utc_now, index=True)
    updated_at: datetime = Field(default_factory=utc_now, index=True)
    closed_at: datetime | None = Field(default=None, index=True)
    metadata_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )


class FocusTransition(SQLModel, table=True):
    __tablename__ = "focus_transitions"

    id: str = Field(default_factory=lambda: new_id("focus_edge"), primary_key=True)
    owner_profile_id: str = Field(default="local-user", index=True)
    from_focus_id: str | None = Field(
        default=None,
        foreign_key="focus_records.id",
        index=True,
    )
    to_focus_id: str | None = Field(
        default=None,
        foreign_key="focus_records.id",
        index=True,
    )
    relation: str = Field(index=True)
    reason: str | None = None
    source_session_id: str | None = Field(
        default=None,
        foreign_key="sessions.id",
        index=True,
    )
    source_turn_id: str | None = Field(
        default=None,
        foreign_key="turns.id",
        index=True,
    )
    source_message_id: str | None = Field(
        default=None,
        foreign_key="messages.id",
        index=True,
    )
    created_at: datetime = Field(default_factory=utc_now, index=True)
    metadata_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )


class IntentionRecord(SQLModel, table=True):
    __tablename__ = "intention_records"

    id: str = Field(default_factory=lambda: new_id("intent"), primary_key=True)
    owner_profile_id: str = Field(default="local-user", index=True)
    status: str = Field(default="active", index=True)
    desire: str = Field(index=True)
    origin: str = Field(default="scarlet", index=True)
    horizon: str | None = Field(default=None, index=True)
    intensity: float = Field(default=0.5, ge=0.0, le=1.0)
    autonomy_level: str = Field(default="self_generated", index=True)
    reason: str
    next_possible_reflection: str | None = None
    last_reviewed_at: datetime | None = Field(default=None, index=True)
    next_review_at: datetime | None = Field(default=None, index=True)
    review_interval_seconds: int | None = Field(default=None, index=True)
    review_count: int = Field(default=0)
    resolution: str | None = None
    impossible_reason: str | None = None
    created_by: str = Field(default="scarlet", index=True)
    source_session_id: str | None = Field(
        default=None,
        foreign_key="sessions.id",
        index=True,
    )
    source_turn_id: str | None = Field(
        default=None,
        foreign_key="turns.id",
        index=True,
    )
    source_message_id: str | None = Field(
        default=None,
        foreign_key="messages.id",
        index=True,
    )
    source_focus_id: str | None = Field(
        default=None,
        foreign_key="focus_records.id",
        index=True,
    )
    created_at: datetime = Field(default_factory=utc_now, index=True)
    updated_at: datetime = Field(default_factory=utc_now, index=True)
    closed_at: datetime | None = Field(default=None, index=True)
    metadata_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )


class IntentionLink(SQLModel, table=True):
    __tablename__ = "intention_links"

    id: str = Field(default_factory=lambda: new_id("intent_link"), primary_key=True)
    intention_id: str = Field(foreign_key="intention_records.id", index=True)
    target_type: str = Field(index=True)
    target_id: str = Field(index=True)
    relation: str = Field(default="related_to", index=True)
    created_at: datetime = Field(default_factory=utc_now, index=True)
    metadata_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )


class AffectState(SQLModel, table=True):
    __tablename__ = "affect_states"

    id: str = Field(default_factory=lambda: new_id("affect"), primary_key=True)
    owner_profile_id: str = Field(default="local-user", index=True)
    session_id: str | None = Field(default=None, foreign_key="sessions.id", index=True)
    turn_id: str | None = Field(default=None, foreign_key="turns.id", index=True)
    status: str = Field(default="active", index=True)
    mode: str = Field(default="shadow", index=True)
    emotion: str = Field(index=True)
    intensity: float = Field(default=0.0, ge=0.0, le=1.0)
    intensity_label: str = Field(default="low", index=True)
    valence: float = Field(default=0.0, ge=-1.0, le=1.0)
    activation: float = Field(default=0.0, ge=0.0, le=1.0)
    prototype_version: str = Field(index=True)
    variables_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    causes_json: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    tendencies_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    pack_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    created_at: datetime = Field(default_factory=utc_now, index=True)
    updated_at: datetime = Field(default_factory=utc_now, index=True)
    decays_at: datetime | None = Field(default=None, index=True)
    metadata_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )


class MemoryRecord(SQLModel, table=True):
    __tablename__ = "memories"

    id: str = Field(default_factory=lambda: new_id("mem"), primary_key=True)
    memory_type: str = Field(index=True)
    scope: str = Field(default="project", index=True)
    status: str = Field(default="active", index=True)
    content: str
    reason_for_storage: str
    expected_future_use: str | None = None
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    salience: float = Field(default=0.7, ge=0.0, le=1.0)
    created_by: str = Field(default="scarlet", index=True)
    source_session_id: str | None = Field(
        default=None,
        foreign_key="sessions.id",
        index=True,
    )
    source_turn_id: str | None = Field(
        default=None,
        foreign_key="turns.id",
        index=True,
    )
    source_message_id: str | None = Field(
        default=None,
        foreign_key="messages.id",
        index=True,
    )
    tags_json: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    metadata_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    usage_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=utc_now, index=True)
    updated_at: datetime = Field(default_factory=utc_now, index=True)
    last_used_at: datetime | None = Field(default=None, index=True)


class MemoryActivity(SQLModel, table=True):
    """Append-only evidence that a memory took part in cognitive work."""

    __tablename__ = "memory_activities"

    id: str = Field(default_factory=lambda: new_id("mem_act"), primary_key=True)
    memory_id: str = Field(foreign_key="memories.id", index=True)
    activity_kind: str = Field(index=True)
    occurred_at: datetime = Field(default_factory=utc_now, index=True)
    profile_id: str | None = Field(default=None, index=True)
    actor: str = Field(default="scarlet", index=True)
    source: str = Field(index=True)
    session_id: str | None = Field(default=None, foreign_key="sessions.id", index=True)
    turn_id: str | None = Field(default=None, foreign_key="turns.id", index=True)
    message_id: str | None = Field(default=None, foreign_key="messages.id", index=True)
    trace_id: str | None = Field(default=None, foreign_key="traces.id", index=True)
    eligible_for_recent: bool = Field(default=True, index=True)
    metadata_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )


class MemoryFact(SQLModel, table=True):
    __tablename__ = "memory_facts"

    id: str = Field(default_factory=lambda: new_id("fact"), primary_key=True)
    memory_id: str = Field(foreign_key="memories.id", index=True)
    entity: str = Field(index=True)
    predicate: str = Field(index=True)
    value_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    valid_from: datetime | None = Field(default=None, index=True)
    valid_to: datetime | None = Field(default=None, index=True)
    recorded_at: datetime = Field(default_factory=utc_now, index=True)
    source_trace_id: str | None = Field(default=None, index=True)
    source_session_id: str | None = Field(
        default=None,
        foreign_key="sessions.id",
        index=True,
    )
    source_turn_id: str | None = Field(
        default=None,
        foreign_key="turns.id",
        index=True,
    )
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    salience: float = Field(default=0.7, ge=0.0, le=1.0)
    status: str = Field(default="active", index=True)
    supersedes_fact_id: str | None = Field(default=None, index=True)
    superseded_by_fact_id: str | None = Field(default=None, index=True)
    metadata_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )


class MemoryProposal(SQLModel, table=True):
    __tablename__ = "memory_proposals"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_memory_proposals_idempotency_key"),
    )

    id: str = Field(default_factory=lambda: new_id("prop"), primary_key=True)
    status: str = Field(default="pending", index=True)
    source: str = Field(default="maintenance.memory_review", index=True)
    proposed_action: str = Field(default="create_new", index=True)
    action_confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    risk: str = Field(default="medium", index=True)
    candidate_type: str = Field(index=True)
    candidate_scope: str = Field(default="project", index=True)
    content: str
    reason_for_storage: str
    expected_future_use: str | None = None
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    salience: float = Field(default=0.7, ge=0.0, le=1.0)
    evidence: str | None = None
    source_session_id: str | None = Field(
        default=None,
        foreign_key="sessions.id",
        index=True,
    )
    source_turn_id: str | None = Field(
        default=None,
        foreign_key="turns.id",
        index=True,
    )
    source_trace_id: str | None = Field(
        default=None,
        foreign_key="traces.id",
        index=True,
    )
    maintenance_job_id: str | None = Field(
        default=None,
        foreign_key="maintenance_jobs.id",
        index=True,
    )
    source_message_ids_json: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    tags_json: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    similar_memory_ids_json: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    related_fact_ids_json: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    candidate_facts_json: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    decision_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    result_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    metadata_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    idempotency_key: str = Field(index=True)
    created_at: datetime = Field(default_factory=utc_now, index=True)
    updated_at: datetime = Field(default_factory=utc_now, index=True)
    applied_at: datetime | None = Field(default=None, index=True)


class MemorySurface(SQLModel, table=True):
    __tablename__ = "memory_surfaces"
    __table_args__ = (
        UniqueConstraint("surface_key", name="uq_memory_surfaces_surface_key"),
    )

    id: str = Field(default_factory=lambda: new_id("surf"), primary_key=True)
    surface_key: str = Field(index=True)
    target_type: str = Field(index=True)
    target_id: str = Field(index=True)
    surface_kind: str = Field(index=True)
    content: str
    content_hash: str = Field(index=True)
    scope: str | None = Field(default=None, index=True)
    status: str = Field(default="active", index=True)
    source_session_id: str | None = Field(
        default=None,
        foreign_key="sessions.id",
        index=True,
    )
    source_turn_id: str | None = Field(
        default=None,
        foreign_key="turns.id",
        index=True,
    )
    source_message_id: str | None = Field(
        default=None,
        foreign_key="messages.id",
        index=True,
    )
    source_trace_id: str | None = Field(
        default=None,
        foreign_key="traces.id",
        index=True,
    )
    embedding_status: str = Field(default="pending", index=True)
    embedding_model: str | None = Field(default=None, index=True)
    embedding_vector_id: str | None = Field(default=None, index=True)
    metadata_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    created_at: datetime = Field(default_factory=utc_now, index=True)
    updated_at: datetime = Field(default_factory=utc_now, index=True)


class EmbeddingVector(SQLModel, table=True):
    __tablename__ = "embedding_vectors"
    __table_args__ = (
        UniqueConstraint("object_key", name="uq_embedding_vectors_object_key"),
    )

    id: str = Field(default_factory=lambda: new_id("emb"), primary_key=True)
    object_key: str = Field(index=True)
    provider: str = Field(index=True)
    model: str = Field(index=True)
    input_hash: str = Field(index=True)
    input_kind: str = Field(default="memory_surface", index=True)
    vector_dim: int = Field(index=True)
    vector_json: list[float] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    source_surface_id: str | None = Field(
        default=None,
        foreign_key="memory_surfaces.id",
        index=True,
    )
    target_type: str | None = Field(default=None, index=True)
    target_id: str | None = Field(default=None, index=True)
    surface_kind: str | None = Field(default=None, index=True)
    status: str = Field(default="active", index=True)
    metadata_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    created_at: datetime = Field(default_factory=utc_now, index=True)
    updated_at: datetime = Field(default_factory=utc_now, index=True)


class MemoryGraphNode(SQLModel, table=True):
    __tablename__ = "memory_graph_nodes"
    __table_args__ = (
        UniqueConstraint("node_key", name="uq_memory_graph_nodes_node_key"),
    )

    id: str = Field(default_factory=lambda: new_id("node"), primary_key=True)
    node_key: str = Field(index=True)
    node_type: str = Field(index=True)
    label: str
    scope: str | None = Field(default=None, index=True)
    status: str = Field(default="active", index=True)
    aliases_json: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    source_memory_id: str | None = Field(
        default=None,
        foreign_key="memories.id",
        index=True,
    )
    source_fact_id: str | None = Field(
        default=None,
        foreign_key="memory_facts.id",
        index=True,
    )
    source_session_id: str | None = Field(
        default=None,
        foreign_key="sessions.id",
        index=True,
    )
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    salience: float = Field(default=0.7, ge=0.0, le=1.0)
    metadata_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    created_at: datetime = Field(default_factory=utc_now, index=True)
    updated_at: datetime = Field(default_factory=utc_now, index=True)


class MemoryGraphEdge(SQLModel, table=True):
    __tablename__ = "memory_graph_edges"
    __table_args__ = (
        UniqueConstraint("edge_key", name="uq_memory_graph_edges_edge_key"),
    )

    id: str = Field(default_factory=lambda: new_id("edge"), primary_key=True)
    edge_key: str = Field(index=True)
    source_node_id: str = Field(foreign_key="memory_graph_nodes.id", index=True)
    target_node_id: str = Field(foreign_key="memory_graph_nodes.id", index=True)
    relation: str = Field(index=True)
    status: str = Field(default="active", index=True)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    salience: float = Field(default=0.7, ge=0.0, le=1.0)
    source_memory_id: str | None = Field(
        default=None,
        foreign_key="memories.id",
        index=True,
    )
    source_fact_id: str | None = Field(
        default=None,
        foreign_key="memory_facts.id",
        index=True,
    )
    source_session_id: str | None = Field(
        default=None,
        foreign_key="sessions.id",
        index=True,
    )
    metadata_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    created_at: datetime = Field(default_factory=utc_now, index=True)
    updated_at: datetime = Field(default_factory=utc_now, index=True)
