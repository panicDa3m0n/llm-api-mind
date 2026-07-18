from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator
from sqlmodel import Session

from app.mind.contracts import MindAPIContext, MemoryOperationResult
from app.mind.memory_shared import (
    _context_required,
    _isoformat,
    _memory_not_found,
    _memory_payload,
    _record_memory_activity,
)
from app.mind.memory_write import _ensure_memory_facts
from app.mind.search import sync_memory_retrieval_artifacts
from app.storage import repositories
from app.storage.models import MemoryFact, MemoryRecord, utc_now


class MemoryDeprecateBody(BaseModel):
    memory_id: str = Field(min_length=1, max_length=80)
    reason: str = Field(min_length=8, max_length=1000)
    superseded_by: str | None = Field(default=None, max_length=80)

    @model_validator(mode="before")
    @classmethod
    def normalize_common_aliases(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        if "memory_id" not in normalized:
            for alias in (
                "id",
                "target_id",
                "target_memory_id",
                "deprecated_memory_id",
            ):
                if alias in normalized:
                    normalized["memory_id"] = normalized.pop(alias)
                    break
        if "superseded_by" not in normalized:
            for alias in ("replacement_memory_id", "new_memory_id", "supersedes_to"):
                if alias in normalized:
                    normalized["superseded_by"] = normalized.pop(alias)
                    break
        if "reason" not in normalized:
            for alias in ("why", "rationale"):
                if alias in normalized:
                    normalized["reason"] = normalized.pop(alias)
                    break
        return normalized

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        return " ".join(value.split())


class MemorySupersedeBody(BaseModel):
    old_memory_id: str = Field(min_length=1, max_length=80)
    new_memory_id: str = Field(min_length=1, max_length=80)
    reason: str = Field(min_length=8, max_length=1000)
    deprecate_old: bool = True

    @model_validator(mode="before")
    @classmethod
    def normalize_common_aliases(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        if "old_memory_id" not in normalized:
            for alias in (
                "memory_id",
                "target_id",
                "old_id",
                "deprecated_memory_id",
                "superseded_memory_id",
            ):
                if alias in normalized:
                    normalized["old_memory_id"] = normalized.pop(alias)
                    break
        if "new_memory_id" not in normalized:
            for alias in ("replacement_memory_id", "superseded_by", "active_memory_id"):
                if alias in normalized:
                    normalized["new_memory_id"] = normalized.pop(alias)
                    break
        if "reason" not in normalized:
            for alias in ("why", "rationale"):
                if alias in normalized:
                    normalized["reason"] = normalized.pop(alias)
                    break
        return normalized

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        return " ".join(value.split())


def handle_memory_deprecate(
    body: dict[str, Any],
    context: MindAPIContext | None,
    *,
    intent: str | None = None,
) -> MemoryOperationResult:
    if context is None or context.session_id is None:
        return _context_required("deprecate")

    body_with_intent = dict(body)
    if "reason" not in body_with_intent and intent:
        body_with_intent["reason"] = intent

    try:
        request = MemoryDeprecateBody.model_validate(body_with_intent)
    except ValidationError as exc:
        return MemoryOperationResult(
            ok=False,
            error_code="memory.invalid_deprecate",
            error_message=str(exc),
            suggested_next_actions=[
                "Call GET /mind/schema",
                "Retry with memory_id and reason",
            ],
            confidence=1.0,
        )

    with Session(context.engine) as db:
        memory = repositories.get_memory(db, request.memory_id)
        if memory is None:
            return _memory_not_found(request.memory_id)
        replacement: MemoryRecord | None = None
        if request.superseded_by is not None:
            if request.superseded_by == request.memory_id:
                return _invalid_lifecycle("A memory cannot supersede itself.")
            replacement = repositories.get_memory(db, request.superseded_by)
            if replacement is None:
                return _memory_not_found(request.superseded_by)

        previous_status = memory.status
        updated_metadata = _with_lifecycle_event(
            memory.metadata_json,
            event={
                "operation": "deprecate",
                "reason": request.reason,
                "previous_status": previous_status,
                "superseded_by": request.superseded_by,
                "source_session_id": context.session_id,
                "source_turn_id": context.turn_id,
            },
        )
        updated = repositories.update_memory_lifecycle(
            db,
            memory_id=memory.id,
            status="deprecated",
            metadata=updated_metadata,
        )
        assert updated is not None

        if replacement is not None:
            replacement_metadata = _append_supersedes(
                replacement.metadata_json,
                old_memory_id=memory.id,
                reason=request.reason,
                context=context,
            )
            replacement = repositories.update_memory_lifecycle(
                db,
                memory_id=replacement.id,
                metadata=replacement_metadata,
            )

        trace = repositories.add_trace(
            db,
            session_id=context.session_id,
            turn_id=context.turn_id,
            kind="mind.memory.deprecate",
            payload={
                "operation": "memory.deprecate",
                "memory_id": updated.id,
                "previous_status": previous_status,
                "status": updated.status,
                "reason": request.reason,
                "superseded_by": request.superseded_by,
            },
        )
        facts, _ = _ensure_memory_facts(
            db,
            updated,
            source_trace_id=trace.id,
        )
        replacement_facts: list[MemoryFact] = []
        if replacement is not None:
            replacement_facts, _ = _ensure_memory_facts(
                db,
                replacement,
                source_trace_id=trace.id,
            )
        updated_facts = repositories.update_memory_facts_status(
            db,
            memory_id=updated.id,
            status="deprecated",
            superseded_by_memory_id=request.superseded_by,
        )
        sync_memory_retrieval_artifacts(
            db,
            [item for item in [updated, replacement] if item is not None],
            facts_by_memory={
                updated.id: updated_facts or facts,
                **(
                    {replacement.id: replacement_facts}
                    if replacement is not None
                    else {}
                ),
            },
        )
        memory_id = updated.id
        trace_id = trace.id
        memory_payload = _memory_payload(updated, facts=updated_facts or facts)
        replacement_payload = (
            _memory_payload(replacement, facts=replacement_facts)
            if replacement is not None
            else None
        )

    return MemoryOperationResult(
        ok=True,
        result={
            "operation": "memory.deprecate",
            "deprecated": True,
            "memory_id": memory_id,
            "memory": memory_payload,
            "superseded_by": request.superseded_by,
            "replacement": replacement_payload,
            "trace_ids": [trace_id],
        },
        cognitive_hint=(
            "The deprecated memory remains inspectable but should no longer be "
            "treated as active evidence in normal memory context."
        ),
        suggested_next_actions=[
            "Inspect conflicts to confirm the active set is now clean",
            "Use the replacement memory when relevant",
        ],
        confidence=1.0,
    )


def handle_memory_supersede(
    body: dict[str, Any],
    context: MindAPIContext | None,
    *,
    intent: str | None = None,
) -> MemoryOperationResult:
    if context is None or context.session_id is None:
        return _context_required("supersede")

    body_with_intent = dict(body)
    if "reason" not in body_with_intent and intent:
        body_with_intent["reason"] = intent

    try:
        request = MemorySupersedeBody.model_validate(body_with_intent)
    except ValidationError as exc:
        return MemoryOperationResult(
            ok=False,
            error_code="memory.invalid_supersede",
            error_message=str(exc),
            suggested_next_actions=[
                "Call GET /mind/schema",
                "Retry with old_memory_id, new_memory_id, and reason",
            ],
            confidence=1.0,
        )

    if request.old_memory_id == request.new_memory_id:
        return _invalid_lifecycle("A memory cannot supersede itself.")

    with Session(context.engine) as db:
        old_memory = repositories.get_memory(db, request.old_memory_id)
        if old_memory is None:
            return _memory_not_found(request.old_memory_id)
        new_memory = repositories.get_memory(db, request.new_memory_id)
        if new_memory is None:
            return _memory_not_found(request.new_memory_id)

        previous_status = old_memory.status
        old_metadata = _with_lifecycle_event(
            old_memory.metadata_json,
            event={
                "operation": "supersede",
                "reason": request.reason,
                "previous_status": previous_status,
                "superseded_by": new_memory.id,
                "source_session_id": context.session_id,
                "source_turn_id": context.turn_id,
            },
        )
        new_metadata = _append_supersedes(
            new_memory.metadata_json,
            old_memory_id=old_memory.id,
            reason=request.reason,
            context=context,
        )
        updated_old = repositories.update_memory_lifecycle(
            db,
            memory_id=old_memory.id,
            status="deprecated" if request.deprecate_old else old_memory.status,
            metadata=old_metadata,
        )
        updated_new = repositories.update_memory_lifecycle(
            db,
            memory_id=new_memory.id,
            metadata=new_metadata,
        )
        assert updated_old is not None
        assert updated_new is not None

        trace = repositories.add_trace(
            db,
            session_id=context.session_id,
            turn_id=context.turn_id,
            kind="mind.memory.supersede",
            payload={
                "operation": "memory.supersede",
                "old_memory_id": updated_old.id,
                "new_memory_id": updated_new.id,
                "old_previous_status": previous_status,
                "old_status": updated_old.status,
                "reason": request.reason,
                "deprecate_old": request.deprecate_old,
            },
        )
        _record_memory_activity(
            db,
            context=context,
            memory_id=updated_new.id,
            activity_kind="supersede",
            source="memory.supersede",
            trace_id=trace.id,
            metadata={"superseded_memory_id": updated_old.id},
        )
        old_facts, _ = _ensure_memory_facts(
            db,
            updated_old,
            source_trace_id=trace.id,
        )
        new_facts, _ = _ensure_memory_facts(
            db,
            updated_new,
            source_trace_id=trace.id,
        )
        if request.deprecate_old:
            old_facts = repositories.update_memory_facts_status(
                db,
                memory_id=updated_old.id,
                status="deprecated",
                superseded_by_memory_id=updated_new.id,
            )
            new_facts = repositories.list_memory_facts(
                db,
                memory_id=updated_new.id,
                include_inactive=True,
            )
        sync_memory_retrieval_artifacts(
            db,
            [updated_old, updated_new],
            facts_by_memory={
                updated_old.id: old_facts,
                updated_new.id: new_facts,
            },
        )
        old_memory_payload = _memory_payload(updated_old, facts=old_facts)
        new_memory_payload = _memory_payload(updated_new, facts=new_facts)
        old_memory_id = updated_old.id
        new_memory_id = updated_new.id
        trace_id = trace.id

    return MemoryOperationResult(
        ok=True,
        result={
            "operation": "memory.supersede",
            "superseded": True,
            "old_memory": old_memory_payload,
            "new_memory": new_memory_payload,
            "old_memory_id": old_memory_id,
            "new_memory_id": new_memory_id,
            "trace_ids": [trace_id],
        },
        cognitive_hint=(
            "The old memory is linked to its replacement. If deprecated, it "
            "will no longer appear in normal active-memory context."
        ),
        suggested_next_actions=[
            "Inspect memory conflicts",
            "Use the new memory as active evidence",
        ],
        confidence=1.0,
    )


def _invalid_lifecycle(message: str) -> MemoryOperationResult:
    return MemoryOperationResult(
        ok=False,
        error_code="memory.invalid_lifecycle",
        error_message=message,
        suggested_next_actions=[
            "Call GET /mind/schema",
            "Retry with distinct valid memory IDs",
        ],
        confidence=1.0,
    )


def _with_lifecycle_event(
    metadata: dict[str, Any],
    *,
    event: dict[str, Any],
) -> dict[str, Any]:
    updated = dict(metadata)
    lifecycle = dict(updated.get("lifecycle") or {})
    event_payload = {
        **event,
        "recorded_at": _isoformat(utc_now()),
    }
    history = list(lifecycle.get("history") or [])
    history.append(event_payload)
    lifecycle["last_event"] = event_payload
    lifecycle["history"] = history
    if event.get("operation") in {"deprecate", "supersede"}:
        lifecycle["deprecated_reason"] = event.get("reason")
        lifecycle["superseded_by"] = event.get("superseded_by")
    updated["lifecycle"] = lifecycle
    return updated


def _append_supersedes(
    metadata: dict[str, Any],
    *,
    old_memory_id: str,
    reason: str,
    context: MindAPIContext,
) -> dict[str, Any]:
    updated = dict(metadata)
    lifecycle = dict(updated.get("lifecycle") or {})
    supersedes = list(lifecycle.get("supersedes") or [])
    if old_memory_id not in supersedes:
        supersedes.append(old_memory_id)
    event_payload = {
        "operation": "supersedes",
        "old_memory_id": old_memory_id,
        "reason": reason,
        "source_session_id": context.session_id,
        "source_turn_id": context.turn_id,
        "recorded_at": _isoformat(utc_now()),
    }
    history = list(lifecycle.get("history") or [])
    history.append(event_payload)
    lifecycle["supersedes"] = supersedes
    lifecycle["last_event"] = event_payload
    lifecycle["history"] = history
    updated["lifecycle"] = lifecycle
    return updated
