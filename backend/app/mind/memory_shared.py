"""Shared semantic-memory contracts used by read and mutation handlers."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from sqlmodel import Session

from app.mind.contracts import MindAPIContext, MemoryOperationResult
from app.mind.facts import fact_payload
from app.storage import repositories
from app.storage.models import MemoryFact, MemoryRecord

MemoryType = str


MemoryScope = str


MEMORY_TYPE_VALUES = {
    "project_fact",
    "user_preference",
    "decision",
    "correction",
    "task_context",
    "behavioral_pattern",
    "episodic",
}


MEMORY_SCOPE_VALUES = {"project", "user", "session"}


DEFAULT_MEMORY_SCOPE = "general"


TYPE_ALIASES = {
    "pref": "user_preference",
    "preference": "user_preference",
    "preferenza": "user_preference",
    "operational-preference": "user_preference",
    "operational_preference": "user_preference",
    "standard-preference": "user_preference",
    "standard_preference": "user_preference",
    "user_pref": "user_preference",
    "nota-operativa": "task_context",
    "nota_operativa": "task_context",
    "operational-note": "task_context",
    "operational_note": "task_context",
    "fact": "project_fact",
    "project": "project_fact",
    "decisione": "decision",
    "correzione": "correction",
    "context": "task_context",
}


def _context_required(operation: str) -> MemoryOperationResult:
    return MemoryOperationResult(
        ok=False,
        error_code="memory.context_required",
        error_message=(
            f"Memory {operation} requires a session context so the operation "
            "can be traced."
        ),
        suggested_next_actions=[
            "Call memory routes during a chat turn",
            "Provide session_id when using POST /mind/call",
        ],
        confidence=1.0,
    )


def _memory_not_found(memory_id: str) -> MemoryOperationResult:
    return MemoryOperationResult(
        ok=False,
        error_code="memory.not_found",
        error_message=f"Memory {memory_id} was not found.",
        suggested_next_actions=[
            "Call GET /mind/memory/conflicts",
            "Search memory before lifecycle operations",
        ],
        confidence=1.0,
    )


def _memory_payload(
    memory: MemoryRecord,
    *,
    facts: list[MemoryFact] | None = None,
) -> dict[str, Any]:
    payload = {
        "id": memory.id,
        "type": memory.memory_type,
        "scope": memory.scope,
        "status": memory.status,
        "content": memory.content,
        "reason_for_storage": memory.reason_for_storage,
        "expected_future_use": memory.expected_future_use,
        "created_by": memory.created_by,
        "source_session_id": memory.source_session_id,
        "source_turn_id": memory.source_turn_id,
        "source_message_id": memory.source_message_id,
        "tags": memory.tags_json,
        "metadata": memory.metadata_json,
        "usage_count": memory.usage_count,
        "created_at": _isoformat(memory.created_at),
        "updated_at": _isoformat(memory.updated_at),
        "last_used_at": _isoformat(memory.last_used_at),
    }
    if facts is not None:
        payload["facts"] = [fact_payload(fact) for fact in facts]
    return payload


def _normalize_freeform_label(value: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-zÀ-ÖØ-öø-ÿ_ -]+", " ", value.strip().casefold())
    cleaned = re.sub(r"[\s-]+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned[:80] or DEFAULT_MEMORY_SCOPE


def _record_memory_activity(
    db: Session,
    *,
    context: MindAPIContext,
    memory_id: str,
    activity_kind: str,
    source: str,
    trace_id: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    repositories.add_memory_activity(
        db,
        memory_id=memory_id,
        activity_kind=activity_kind,
        source=source,
        profile_id=getattr(context.settings, "user_profile_id", None),
        session_id=context.session_id,
        turn_id=context.turn_id,
        message_id=context.source_message_id,
        trace_id=trace_id,
        metadata=metadata,
    )


def _isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()
