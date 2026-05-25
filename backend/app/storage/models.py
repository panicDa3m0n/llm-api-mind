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
