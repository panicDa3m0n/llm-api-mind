"""Compact memory hint projection and cross-block deduplication."""

from __future__ import annotations

from typing import Any

from sqlmodel import Session

from app.mind.context_contracts import CompactMemoryHint
from app.mind.context_provenance import project_source_provenance
from app.mind.context_time import render_user_time
from app.storage import repositories
from app.storage.models import MemoryRecord


def project_memory_context(
    db: Session,
    *,
    rich_memory_context: dict[str, Any],
    timezone_id: str,
    relevant_limit: int,
    recent_user_limit: int,
    recent_general_limit: int,
) -> dict[str, list[dict[str, Any]]]:
    seen: set[str] = set()
    relevant = _project_rich_candidates(
        db,
        rich_memory_context.get("selected", []),
        timezone_id=timezone_id,
        seen=seen,
        limit=relevant_limit,
    )
    recent_user = _project_records(
        db,
        repositories.list_recent_memories_by_activity(
            db,
            scope="user",
            exclude_memory_ids=seen,
            limit=recent_user_limit * 3,
        ),
        timezone_id=timezone_id,
        seen=seen,
        limit=recent_user_limit,
    )
    recent_general = _project_records(
        db,
        repositories.list_recent_memories_by_activity(
            db,
            scope=None,
            exclude_memory_ids=seen,
            limit=recent_general_limit * 3,
        ),
        timezone_id=timezone_id,
        seen=seen,
        limit=recent_general_limit,
    )
    return {
        "relevant": relevant,
        "recent_user": recent_user,
        "recent_general": recent_general,
    }


def _project_rich_candidates(
    db: Session,
    candidates: list[dict[str, Any]],
    *,
    timezone_id: str,
    seen: set[str],
    limit: int,
) -> list[dict[str, Any]]:
    projected: list[dict[str, Any]] = []
    for candidate in candidates:
        memory_id = candidate.get("id")
        if not isinstance(memory_id, str) or memory_id in seen:
            continue
        hint = _hint_from_values(db, candidate, timezone_id=timezone_id)
        if hint is None:
            continue
        seen.add(memory_id)
        projected.append(hint.model_dump(mode="json"))
        if len(projected) >= limit:
            break
    return projected


def _project_records(
    db: Session,
    records: list[MemoryRecord],
    *,
    timezone_id: str,
    seen: set[str],
    limit: int,
) -> list[dict[str, Any]]:
    projected: list[dict[str, Any]] = []
    for memory in records:
        if memory.id in seen:
            continue
        hint = _hint_from_values(
            db,
            {
                "id": memory.id,
                "content": memory.content,
                "created_at": memory.created_at,
                "updated_at": memory.updated_at,
                "source_session_id": memory.source_session_id,
                "source_turn_id": memory.source_turn_id,
                "source_message_id": memory.source_message_id,
            },
            timezone_id=timezone_id,
        )
        if hint is None:
            continue
        seen.add(memory.id)
        projected.append(hint.model_dump(mode="json"))
        if len(projected) >= limit:
            break
    return projected


def _hint_from_values(
    db: Session,
    values: dict[str, Any],
    *,
    timezone_id: str,
) -> CompactMemoryHint | None:
    memory_id = values.get("id")
    stored = (
        repositories.get_memory(db, memory_id)
        if isinstance(memory_id, str)
        else None
    )
    source_session_id = values.get("source_session_id") or (
        stored.source_session_id if stored is not None else None
    )
    source_turn_id = values.get("source_turn_id") or (
        stored.source_turn_id if stored is not None else None
    )
    source_message_id = values.get("source_message_id") or (
        stored.source_message_id if stored is not None else None
    )
    created_at = values.get("created_at") or (
        stored.created_at if stored is not None else None
    )
    updated_at = values.get("updated_at") or (
        stored.updated_at if stored is not None else None
    )
    if not all(
        [
            isinstance(source_session_id, str),
            isinstance(source_turn_id, str),
            isinstance(source_message_id, str),
            created_at is not None,
            updated_at is not None,
        ]
    ):
        return None
    source_message = repositories.get_message(db, source_message_id)
    if (
        source_message is None
        or source_message.session_id != source_session_id
        or source_message.turn_id != source_turn_id
    ):
        return None
    provenance = project_source_provenance(
        db,
        session_id=source_session_id,
        turn_id=source_turn_id,
        message_id=source_message_id,
    )
    return CompactMemoryHint(
        id=str(values["id"]),
        content=str(values.get("content") or ""),
        created_at=render_user_time(created_at, timezone_id=timezone_id),
        updated_at=render_user_time(updated_at, timezone_id=timezone_id),
        source_session_id=source_session_id,
        source_session_kind=provenance["source_session_kind"],
        source_turn_id=source_turn_id,
        source_turn_trigger=provenance["source_turn_trigger"],
        source_turn_actor=provenance["source_turn_actor"],
        source_message_id=source_message_id,
        source_message_role=provenance["source_message_role"],
        source_provenance_status=provenance["source_provenance_status"],
        source_origin=provenance["source_origin"],
    )
