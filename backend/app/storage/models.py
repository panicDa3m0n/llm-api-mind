from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import Column, JSON
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

