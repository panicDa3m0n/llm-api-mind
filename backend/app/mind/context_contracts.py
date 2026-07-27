"""Typed contract for the compact model-facing context document."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class CompactMemoryHint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    content: str
    created_at: str
    updated_at: str
    source_session_id: str
    source_session_kind: str | None
    source_turn_id: str
    source_turn_trigger: str | None
    source_turn_actor: str | None
    source_message_id: str
    source_message_role: str | None
    source_provenance_status: str
    source_origin: str


class PreviousSessionHint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    last_message_at: str
    turn_count: int
    summary: str


class AutonomousSessionHint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    kind: str
    last_activity_at: str | None
    turn_count: int
    latest_checkpoint: str | None


class ModelContextV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "scarlet-model-context-v2"
    turn_origin: dict[str, Any]
    session: dict[str, Any]
    memories: dict[str, list[CompactMemoryHint]]
    preserved_context: list[dict[str, Any]]
