from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlmodel import Session

from app.mind.memory import MemoryOperationResult, MindAPIContext
from app.mind.organs import ORGAN_EVENT_TYPES, ORGAN_TRACE_KINDS
from app.storage import repositories
from app.storage.models import FocusRecord, FocusTransition


FOCUS_STATUS_VALUES = {
    "active",
    "held",
    "deferred",
    "resolved",
    "impossible",
    "superseded",
}
FOCUS_TRANSITION_RELATIONS = {
    "started",
    "shifted_to",
    "held",
    "updated",
    "deferred",
    "resolved_into",
    "blocked_by",
}


class FocusBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal[
        "set",
        "update",
        "hold",
        "shift",
        "defer",
        "resolve",
        "impossible",
        "read",
        "list",
        "search",
        "timeline",
    ]
    focus_id: str | None = Field(default=None, max_length=80)
    object: str | None = Field(default=None, min_length=2, max_length=500)
    type: str | None = Field(default=None, min_length=2, max_length=80)
    intensity: float | None = Field(default=None, ge=0.0, le=1.0)
    duration_policy: str | None = Field(default=None, max_length=200)
    reason: str | None = Field(default=None, max_length=1200)
    resolution: str | None = Field(default=None, max_length=1200)
    impossible_reason: str | None = Field(default=None, max_length=1200)
    status: str | None = Field(default=None, max_length=80)
    query: str | None = Field(default=None, max_length=500)
    limit: int = Field(default=10, ge=1, le=50)
    offset: int = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "object",
        "type",
        "duration_policy",
        "reason",
        "resolution",
        "impossible_reason",
        "status",
        "query",
    )
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        return cleaned or None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value not in FOCUS_STATUS_VALUES:
            raise ValueError(
                "status must be one of: " + ", ".join(sorted(FOCUS_STATUS_VALUES))
            )
        return value

    @field_validator("type")
    @classmethod
    def normalize_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().lower().replace(" ", "_")[:80]


def handle_focus(
    body: dict[str, Any],
    context: MindAPIContext | None,
    *,
    intent: str,
) -> MemoryOperationResult:
    if context is None:
        return _error(
            code="focus.context_missing",
            message=(
                "/mind/focus needs an active Mind API context so the backend "
                "can attach profile and provenance."
            ),
            hint="Retry /mind/focus inside a chat/session context.",
            actions=["Retry with session_id through /mind/call"],
        )
    try:
        request = FocusBody.model_validate(body)
    except ValidationError as exc:
        return _error(
            code="focus.invalid_body",
            message=str(exc),
            result={
                "operation": "focus",
                "validation_errors": exc.errors(),
                "expected_schema_hint": "Use the /mind/focus usage_guide to correct the body.",
            },
            hint="Retry /mind/focus with a valid action body.",
            actions=["Retry POST /mind/focus with valid parameters"],
        )

    with Session(context.engine) as db:
        owner_profile_id = _owner_profile_id(context)
        source = _source_payload(db, context)
        if request.action in {"set", "shift"}:
            result = _set_or_shift_focus(
                db,
                request=request,
                owner_profile_id=owner_profile_id,
                source=source,
                intent=intent,
            )
        elif request.action in {"update", "hold"}:
            result = _update_or_hold_focus(
                db,
                request=request,
                owner_profile_id=owner_profile_id,
                source=source,
                intent=intent,
            )
        elif request.action in {"defer", "resolve", "impossible"}:
            result = _close_focus(
                db,
                request=request,
                owner_profile_id=owner_profile_id,
                source=source,
                intent=intent,
            )
        elif request.action == "read":
            result = _read_focus(
                db,
                request=request,
                owner_profile_id=owner_profile_id,
            )
        elif request.action == "timeline":
            result = _focus_timeline(
                db,
                request=request,
                owner_profile_id=owner_profile_id,
            )
        else:
            result = _list_or_search_focus(
                db,
                request=request,
                owner_profile_id=owner_profile_id,
            )
        return result


def _set_or_shift_focus(
    db: Session,
    *,
    request: FocusBody,
    owner_profile_id: str,
    source: dict[str, str | None],
    intent: str,
) -> MemoryOperationResult:
    if request.object is None:
        return _error(
            code="focus.missing_object",
            message="set and shift actions require object.",
            hint="Provide the focus object Scarlet wants to hold in the foreground.",
            actions=["Retry with object and reason"],
        )
    reason = request.reason or intent
    previous_records = repositories.list_active_focus_records(
        db,
        owner_profile_id=owner_profile_id,
    )
    previous = previous_records[0] if previous_records else None
    for previous_record in previous_records:
        closed_previous = repositories.close_focus_record(
            db,
            focus_id=previous_record.id,
            status="superseded",
            resolution=f"Replaced by a new focus through action={request.action}.",
        )
        assert closed_previous is not None
        _record_focus_event(
            db,
            event_name="closed",
            focus=closed_previous,
            source=source,
            payload={"closed_as": "superseded", "reason": reason},
        )

    focus = repositories.create_focus_record(
        db,
        owner_profile_id=owner_profile_id,
        focus_object=request.object,
        focus_type=request.type or "general",
        reason=reason,
        intensity=request.intensity if request.intensity is not None else 0.5,
        duration_policy=request.duration_policy,
        source_session_id=source["session_id"],
        source_turn_id=source["turn_id"],
        source_message_id=source["message_id"],
        metadata=request.metadata,
    )
    relation = "shifted_to" if previous is not None else "started"
    transition = repositories.add_focus_transition(
        db,
        owner_profile_id=owner_profile_id,
        from_focus_id=previous.id if previous is not None else None,
        to_focus_id=focus.id,
        relation=relation,
        reason=reason,
        source_session_id=source["session_id"],
        source_turn_id=source["turn_id"],
        source_message_id=source["message_id"],
    )
    _record_focus_event(
        db,
        event_name="created",
        focus=focus,
        source=source,
        payload={
            "action": request.action,
            "transition": _transition_payload(transition),
            "previous_focus_id": previous.id if previous is not None else None,
        },
    )
    _trace_focus_operation(
        db,
        source=source,
        operation=f"focus.{request.action}",
        payload={
            "focus": _focus_payload(focus),
            "previous_focus": _focus_payload(previous) if previous else None,
            "transition": _transition_payload(transition),
        },
    )
    return MemoryOperationResult(
        ok=True,
        result={
            "operation": f"focus.{request.action}",
            "active_focus": _focus_payload(focus),
            "previous_focus": _focus_payload(previous) if previous else None,
            "transition": _transition_payload(transition),
            "focus_policy": _focus_policy(),
        },
        cognitive_hint=(
            "Focus is now Scarlet's foreground attention packet. It does not "
            "filter memory retrieval; use memory and session tools normally when needed."
        ),
        suggested_next_actions=[
            "Use this focus as foreground state in the current reasoning",
            "Use /mind/focus action=resolve, defer, impossible, or shift when it changes",
        ],
    )


def _update_or_hold_focus(
    db: Session,
    *,
    request: FocusBody,
    owner_profile_id: str,
    source: dict[str, str | None],
    intent: str,
) -> MemoryOperationResult:
    focus = _target_focus(db, request=request, owner_profile_id=owner_profile_id)
    if focus is None:
        return _error(
            code="focus.not_found",
            message="No target focus found for update/hold.",
            hint="Read active focus or set one before updating it.",
            actions=["Call POST /mind/focus action=read", "Call POST /mind/focus action=set"],
        )
    updated = repositories.update_focus_record(
        db,
        focus_id=focus.id,
        focus_object=request.object,
        focus_type=request.type,
        reason=request.reason or (intent if request.action == "hold" else None),
        intensity=request.intensity,
        duration_policy=request.duration_policy,
        metadata=request.metadata,
    )
    assert updated is not None
    transition = repositories.add_focus_transition(
        db,
        owner_profile_id=owner_profile_id,
        from_focus_id=focus.id,
        to_focus_id=focus.id,
        relation="held" if request.action == "hold" else "updated",
        reason=request.reason or intent,
        source_session_id=source["session_id"],
        source_turn_id=source["turn_id"],
        source_message_id=source["message_id"],
    )
    _record_focus_event(
        db,
        event_name="updated",
        focus=updated,
        source=source,
        payload={"action": request.action, "transition": _transition_payload(transition)},
    )
    _trace_focus_operation(
        db,
        source=source,
        operation=f"focus.{request.action}",
        payload={
            "focus": _focus_payload(updated),
            "transition": _transition_payload(transition),
        },
    )
    return MemoryOperationResult(
        ok=True,
        result={
            "operation": f"focus.{request.action}",
            "active_focus": _focus_payload(updated),
            "transition": _transition_payload(transition),
            "focus_policy": _focus_policy(),
        },
        cognitive_hint="The active focus was updated without touching memory retrieval.",
        suggested_next_actions=[
            "Continue with this focus unless the foreground attention changes",
        ],
    )


def _close_focus(
    db: Session,
    *,
    request: FocusBody,
    owner_profile_id: str,
    source: dict[str, str | None],
    intent: str,
) -> MemoryOperationResult:
    focus = _target_focus(db, request=request, owner_profile_id=owner_profile_id)
    if focus is None:
        return _error(
            code="focus.not_found",
            message="No target focus found to close.",
            hint="Read active focus or provide focus_id before closing it.",
            actions=["Call POST /mind/focus action=read"],
        )
    status = {
        "defer": "deferred",
        "resolve": "resolved",
        "impossible": "impossible",
    }[request.action]
    if request.action == "resolve" and not (request.resolution or request.reason):
        return _error(
            code="focus.missing_resolution",
            message="resolve requires resolution or reason.",
            hint="Explain how the focus was resolved.",
            actions=["Retry with resolution"],
        )
    if request.action == "impossible" and not (
        request.impossible_reason or request.reason
    ):
        return _error(
            code="focus.missing_impossible_reason",
            message="impossible requires impossible_reason or reason.",
            hint="Explain why this focus cannot be completed right now.",
            actions=["Retry with impossible_reason"],
        )
    closed = repositories.close_focus_record(
        db,
        focus_id=focus.id,
        status=status,
        resolution=request.resolution or (request.reason if status == "resolved" else None),
        impossible_reason=request.impossible_reason
        or (request.reason if status == "impossible" else None),
        metadata=request.metadata,
    )
    assert closed is not None
    relation = {
        "defer": "deferred",
        "resolve": "resolved_into",
        "impossible": "blocked_by",
    }[request.action]
    transition = repositories.add_focus_transition(
        db,
        owner_profile_id=owner_profile_id,
        from_focus_id=closed.id,
        to_focus_id=None,
        relation=relation,
        reason=request.reason or request.resolution or request.impossible_reason or intent,
        source_session_id=source["session_id"],
        source_turn_id=source["turn_id"],
        source_message_id=source["message_id"],
    )
    _record_focus_event(
        db,
        event_name="closed",
        focus=closed,
        source=source,
        payload={
            "action": request.action,
            "closed_as": status,
            "transition": _transition_payload(transition),
        },
    )
    _trace_focus_operation(
        db,
        source=source,
        operation=f"focus.{request.action}",
        payload={
            "focus": _focus_payload(closed),
            "transition": _transition_payload(transition),
        },
    )
    return MemoryOperationResult(
        ok=True,
        result={
            "operation": f"focus.{request.action}",
            "closed_focus": _focus_payload(closed),
            "active_focus": None,
            "transition": _transition_payload(transition),
            "focus_policy": _focus_policy(),
        },
        cognitive_hint="The focus left the foreground and remains archived.",
        suggested_next_actions=[
            "Set or shift to a new focus if Scarlet needs a new foreground thread",
        ],
    )


def _read_focus(
    db: Session,
    *,
    request: FocusBody,
    owner_profile_id: str,
) -> MemoryOperationResult:
    focus = _target_focus(db, request=request, owner_profile_id=owner_profile_id)
    if focus is None:
        return MemoryOperationResult(
            ok=True,
            result={
                "operation": "focus.read",
                "active_focus": None,
                "focus": None,
                "transitions": [],
                "focus_policy": _focus_policy(),
            },
            cognitive_hint="No active focus is currently stored.",
        )
    transitions = repositories.list_focus_transitions(
        db,
        owner_profile_id=owner_profile_id,
        focus_id=focus.id,
        limit=10,
    )
    return MemoryOperationResult(
        ok=True,
        result={
            "operation": "focus.read",
            "active_focus": _focus_payload(focus)
            if focus.status in repositories.ACTIVE_FOCUS_STATUSES
            else None,
            "focus": _focus_payload(focus),
            "transitions": [_transition_payload(item) for item in transitions],
            "focus_policy": _focus_policy(),
        },
        cognitive_hint="Use focus as foreground attention state, not as proof or memory.",
    )


def _list_or_search_focus(
    db: Session,
    *,
    request: FocusBody,
    owner_profile_id: str,
) -> MemoryOperationResult:
    records = repositories.list_focus_records(
        db,
        owner_profile_id=owner_profile_id,
        status=request.status,
        query=request.query if request.action == "search" else None,
        limit=request.limit,
        offset=request.offset,
    )
    return MemoryOperationResult(
        ok=True,
        result={
            "operation": f"focus.{request.action}",
            "items": [_focus_payload(item) for item in records],
            "limit": request.limit,
            "offset": request.offset,
            "query": request.query,
            "status": request.status,
            "focus_policy": _focus_policy(),
        },
        cognitive_hint=(
            "Focus archive results describe Scarlet's attention history, not "
            "semantic memories or user facts."
        ),
    )


def _focus_timeline(
    db: Session,
    *,
    request: FocusBody,
    owner_profile_id: str,
) -> MemoryOperationResult:
    focus_id = request.focus_id
    records = repositories.list_focus_records(
        db,
        owner_profile_id=owner_profile_id,
        status=request.status,
        query=request.query,
        limit=request.limit,
        offset=request.offset,
    )
    transitions = repositories.list_focus_transitions(
        db,
        owner_profile_id=owner_profile_id,
        focus_id=focus_id,
        limit=request.limit,
    )
    node_ids = {
        item
        for transition in transitions
        for item in (transition.from_focus_id, transition.to_focus_id)
        if item is not None
    }
    if focus_id is not None:
        node_ids.add(focus_id)
    record_by_id = {record.id: record for record in records}
    for node_id in node_ids:
        if node_id not in record_by_id:
            record = repositories.get_focus_record(db, node_id)
            if record is not None and record.owner_profile_id == owner_profile_id:
                record_by_id[node_id] = record
    return MemoryOperationResult(
        ok=True,
        result={
            "operation": "focus.timeline",
            "nodes": [_focus_payload(item) for item in record_by_id.values()],
            "edges": [_transition_payload(item) for item in transitions],
            "focus_id": focus_id,
            "query": request.query,
            "status": request.status,
            "limit": request.limit,
            "offset": request.offset,
            "focus_policy": _focus_policy(),
        },
        cognitive_hint=(
            "This is Scarlet's focus transition timeline. Use it to understand "
            "how foreground attention moved, not as semantic memory evidence."
        ),
        suggested_next_actions=[
            "Use source sessions or memories if factual proof is needed",
            "Use focus.read for one active or targeted focus",
        ],
    )


def _target_focus(
    db: Session,
    *,
    request: FocusBody,
    owner_profile_id: str,
) -> FocusRecord | None:
    if request.focus_id:
        focus = repositories.get_focus_record(db, request.focus_id)
        if focus is not None and focus.owner_profile_id == owner_profile_id:
            return focus
        return None
    return repositories.get_active_focus(db, owner_profile_id=owner_profile_id)


def _owner_profile_id(context: MindAPIContext) -> str:
    return str(getattr(context.settings, "user_profile_id", None) or "local-user")


def _source_payload(db: Session, context: MindAPIContext) -> dict[str, str | None]:
    message_id = None
    if context.turn_id is not None:
        message = repositories.latest_message_for_turn(
            db,
            turn_id=context.turn_id,
            role="user",
        )
        message_id = message.id if message is not None else None
    return {
        "session_id": context.session_id,
        "turn_id": context.turn_id,
        "message_id": message_id,
    }


def _focus_payload(focus: FocusRecord | None) -> dict[str, Any] | None:
    if focus is None:
        return None
    return {
        "id": focus.id,
        "owner_profile_id": focus.owner_profile_id,
        "status": focus.status,
        "object": focus.focus_object,
        "type": focus.focus_type,
        "intensity": focus.intensity,
        "duration_policy": focus.duration_policy,
        "reason": focus.reason,
        "resolution": focus.resolution,
        "impossible_reason": focus.impossible_reason,
        "created_by": focus.created_by,
        "source_session_id": focus.source_session_id,
        "source_turn_id": focus.source_turn_id,
        "source_message_id": focus.source_message_id,
        "created_at": focus.created_at.isoformat(),
        "updated_at": focus.updated_at.isoformat(),
        "closed_at": focus.closed_at.isoformat() if focus.closed_at else None,
        "metadata": focus.metadata_json,
    }


def _transition_payload(transition: FocusTransition | None) -> dict[str, Any] | None:
    if transition is None:
        return None
    return {
        "id": transition.id,
        "owner_profile_id": transition.owner_profile_id,
        "from_focus_id": transition.from_focus_id,
        "to_focus_id": transition.to_focus_id,
        "relation": transition.relation,
        "reason": transition.reason,
        "source_session_id": transition.source_session_id,
        "source_turn_id": transition.source_turn_id,
        "source_message_id": transition.source_message_id,
        "created_at": transition.created_at.isoformat(),
        "metadata": transition.metadata_json,
    }


def _focus_policy() -> dict[str, Any]:
    return {
        "one_active_focus": True,
        "profile_scoped": True,
        "separate_from_memory_retrieval": True,
        "does_not_filter_memory_by_default": True,
        "meaning": (
            "Focus is Scarlet's current foreground attention packet. It helps "
            "her keep a thread, shift intentionally, and archive why attention "
            "moved, but it is not a semantic memory and not evidence by itself."
        ),
    }


def _record_focus_event(
    db: Session,
    *,
    event_name: Literal["created", "updated", "closed", "surfaced"],
    focus: FocusRecord,
    source: dict[str, str | None],
    payload: dict[str, Any] | None = None,
) -> None:
    session_id = source.get("session_id")
    if session_id is None:
        return
    event_type = ORGAN_EVENT_TYPES["focus"][event_name]
    repositories.add_event(
        db,
        session_id=session_id,
        turn_id=source.get("turn_id"),
        event_type=event_type,
        payload={
            "focus": _focus_payload(focus),
            **(payload or {}),
        },
        source="api_mind.focus",
        actor="scarlet" if event_name in {"created", "updated", "closed"} else "backend",
        visibility="debug",
        status="completed",
        message_id=source.get("message_id"),
    )


def _trace_focus_operation(
    db: Session,
    *,
    source: dict[str, str | None],
    operation: str,
    payload: dict[str, Any],
) -> None:
    session_id = source.get("session_id")
    if session_id is None:
        return
    repositories.add_trace(
        db,
        session_id=session_id,
        turn_id=source.get("turn_id"),
        kind=ORGAN_TRACE_KINDS["focus"],
        payload={
            "operation": operation,
            **payload,
        },
    )


def _error(
    *,
    code: str,
    message: str,
    result: dict[str, Any] | None = None,
    hint: str,
    actions: list[str],
) -> MemoryOperationResult:
    return MemoryOperationResult(
        ok=False,
        result=result or {"operation": "focus"},
        cognitive_hint=hint,
        suggested_next_actions=actions,
        confidence=1.0,
        error_code=code,
        error_message=message,
        error_recoverable=True,
    )
