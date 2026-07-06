from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlmodel import Session

from app.mind.memory import MemoryOperationResult, MindAPIContext
from app.mind.organs import ORGAN_EVENT_TYPES, ORGAN_TRACE_KINDS
from app.storage import repositories
from app.storage.models import IntentionLink, IntentionRecord, utc_now


INTENTION_STATUS_VALUES = {
    "active",
    "deferred",
    "in_review",
    "resolved",
    "impossible",
    "deprecated",
}
OPEN_INTENTION_STATUS_VALUES = {"active", "deferred", "in_review"}
INTENTION_LINK_TARGET_TYPES = {
    "memory",
    "focus",
    "lesson",
    "session",
    "message",
    "metacognition",
    "goal",
    "task",
    "user",
    "project",
    "other",
}


class IntentionLinkBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_type: str = Field(min_length=2, max_length=80)
    target_id: str = Field(min_length=2, max_length=120)
    relation: str = Field(default="related_to", min_length=2, max_length=80)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("target_type", "relation")
    @classmethod
    def normalize_label(cls, value: str) -> str:
        cleaned = value.strip().lower().replace(" ", "_")
        return cleaned[:80]

    @field_validator("target_type")
    @classmethod
    def validate_target_type(cls, value: str) -> str:
        if value not in INTENTION_LINK_TARGET_TYPES:
            raise ValueError(
                "target_type must be one of: "
                + ", ".join(sorted(INTENTION_LINK_TARGET_TYPES))
            )
        return value

    @field_validator("target_id")
    @classmethod
    def normalize_target_id(cls, value: str) -> str:
        return " ".join(value.split())[:120]


class VolitionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal[
        "create",
        "read",
        "list_active",
        "list_due",
        "search",
        "update",
        "defer",
        "review",
        "promote_to_focus_candidate",
        "resolve",
        "mark_impossible",
        "deprecate",
    ]
    intention_id: str | None = Field(default=None, max_length=100)
    desire: str | None = Field(default=None, min_length=4, max_length=1200)
    origin: str | None = Field(default=None, max_length=120)
    horizon: str | None = Field(default=None, max_length=120)
    intensity: float | None = Field(default=None, ge=0.0, le=1.0)
    autonomy_level: str | None = Field(default=None, max_length=120)
    reason: str | None = Field(default=None, max_length=1500)
    next_possible_reflection: str | None = Field(default=None, max_length=2000)
    next_review_at: datetime | None = None
    review_interval_seconds: int | None = Field(default=None, ge=1, le=31_536_000)
    resolution: str | None = Field(default=None, max_length=2000)
    impossible_reason: str | None = Field(default=None, max_length=2000)
    status: str | None = Field(default=None, max_length=80)
    query: str | None = Field(default=None, max_length=600)
    limit: int = Field(default=10, ge=1, le=50)
    offset: int = Field(default=0, ge=0)
    include_unscheduled: bool = False
    links: list[IntentionLinkBody] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "intention_id",
        "desire",
        "origin",
        "horizon",
        "autonomy_level",
        "reason",
        "next_possible_reflection",
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

    @field_validator("origin", "horizon", "autonomy_level")
    @classmethod
    def normalize_label(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().lower().replace(" ", "_")[:120]

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower().replace(" ", "_")
        if normalized not in INTENTION_STATUS_VALUES:
            raise ValueError(
                "status must be one of: " + ", ".join(sorted(INTENTION_STATUS_VALUES))
            )
        return normalized


def handle_volition(
    body: dict[str, Any],
    context: MindAPIContext | None,
    *,
    intent: str,
) -> MemoryOperationResult:
    if context is None:
        return _error(
            code="volition.context_missing",
            message=(
                "/mind/volition needs an active Mind API context so the backend "
                "can attach profile and provenance."
            ),
            hint="Retry /mind/volition inside a chat/session context.",
            actions=["Retry with session_id through /mind/call"],
        )
    try:
        request = VolitionBody.model_validate(body)
    except ValidationError as exc:
        return _error(
            code="volition.invalid_body",
            message=str(exc),
            result={
                "operation": "volition",
                "validation_errors": exc.errors(),
                "expected_schema_hint": "Use the /mind/volition usage_guide to correct the body.",
            },
            hint="Retry /mind/volition with a valid action body.",
            actions=["Retry POST /mind/volition with valid parameters"],
        )

    with Session(context.engine) as db:
        owner_profile_id = _owner_profile_id(context)
        source = _source_payload(db, context, owner_profile_id=owner_profile_id)
        if request.action == "create":
            return _create_intention(
                db,
                request=request,
                owner_profile_id=owner_profile_id,
                source=source,
                intent=intent,
            )
        if request.action == "read":
            return _read_intention(
                db,
                request=request,
                owner_profile_id=owner_profile_id,
            )
        if request.action in {"list_active", "list_due", "search"}:
            return _list_or_search_intentions(
                db,
                request=request,
                owner_profile_id=owner_profile_id,
            )
        if request.action == "update":
            return _update_intention(
                db,
                request=request,
                owner_profile_id=owner_profile_id,
                source=source,
                intent=intent,
            )
        if request.action == "defer":
            return _defer_intention(
                db,
                request=request,
                owner_profile_id=owner_profile_id,
                source=source,
                intent=intent,
            )
        if request.action == "review":
            return _review_intention(
                db,
                request=request,
                owner_profile_id=owner_profile_id,
                source=source,
                intent=intent,
            )
        if request.action == "promote_to_focus_candidate":
            return _promote_to_focus_candidate(
                db,
                request=request,
                owner_profile_id=owner_profile_id,
                source=source,
                intent=intent,
            )
        return _close_intention(
            db,
            request=request,
            owner_profile_id=owner_profile_id,
            source=source,
            intent=intent,
        )


def _create_intention(
    db: Session,
    *,
    request: VolitionBody,
    owner_profile_id: str,
    source: dict[str, str | None],
    intent: str,
) -> MemoryOperationResult:
    if request.desire is None:
        return _error(
            code="volition.missing_desire",
            message="create requires desire.",
            hint="Describe the internal direction Scarlet wants to keep latent.",
            actions=["Retry with desire and reason"],
        )
    if request.reason is None:
        return _error(
            code="volition.missing_reason",
            message="create requires reason.",
            hint="Explain why this is a self-owned intention rather than a task or memory.",
            actions=["Retry with reason"],
        )
    intention = repositories.create_intention_record(
        db,
        owner_profile_id=owner_profile_id,
        desire=request.desire,
        reason=request.reason,
        origin=request.origin or "scarlet",
        horizon=request.horizon,
        intensity=request.intensity if request.intensity is not None else 0.5,
        autonomy_level=request.autonomy_level or "self_generated",
        next_possible_reflection=request.next_possible_reflection,
        next_review_at=request.next_review_at,
        review_interval_seconds=request.review_interval_seconds,
        source_session_id=source["session_id"],
        source_turn_id=source["turn_id"],
        source_message_id=source["message_id"],
        source_focus_id=source["focus_id"],
        metadata=request.metadata,
    )
    links = _add_links(db, intention_id=intention.id, links=request.links)
    _record_volition_event(
        db,
        event_name="created",
        intention=intention,
        source=source,
        payload={"action": request.action, "links": [_link_payload(item) for item in links]},
    )
    _trace_volition_operation(
        db,
        source=source,
        operation="volition.create",
        payload={
            "intention": _intention_payload(intention, links=links),
            "volition_policy": _volition_policy(),
        },
    )
    return MemoryOperationResult(
        ok=True,
        result={
            "operation": "volition.create",
            "intention": _intention_payload(intention, links=links),
            "volition_policy": _volition_policy(),
        },
        cognitive_hint=(
            "This intention is stored as Scarlet's latent self-direction. It is "
            "not a memory, not a user task, and will not be injected automatically "
            "into every chat turn."
        ),
        suggested_next_actions=[
            "Leave the intention latent unless the conversation gives a real reason to inspect it",
            "Use /mind/volition action=review, defer, resolve, or deprecate when its state changes",
        ],
    )


def _read_intention(
    db: Session,
    *,
    request: VolitionBody,
    owner_profile_id: str,
) -> MemoryOperationResult:
    intention = _target_intention(db, request=request, owner_profile_id=owner_profile_id)
    if intention is None:
        return _error(
            code="volition.not_found",
            message="No target intention found.",
            hint="Provide intention_id or list active intentions first.",
            actions=["Call POST /mind/volition action=list_active"],
        )
    links = repositories.list_intention_links(db, intention_id=intention.id)
    return MemoryOperationResult(
        ok=True,
        result={
            "operation": "volition.read",
            "intention": _intention_payload(intention, links=links),
            "volition_policy": _volition_policy(),
        },
        cognitive_hint="Use intentions as latent self-direction, not as proof about external facts.",
    )


def _list_or_search_intentions(
    db: Session,
    *,
    request: VolitionBody,
    owner_profile_id: str,
) -> MemoryOperationResult:
    if request.action == "list_active":
        intentions = repositories.list_open_intention_records(
            db,
            owner_profile_id=owner_profile_id,
            limit=request.limit,
            offset=request.offset,
        )
    elif request.action == "list_due":
        intentions = repositories.list_due_intention_records(
            db,
            owner_profile_id=owner_profile_id,
            include_unscheduled=request.include_unscheduled,
            limit=request.limit,
            offset=request.offset,
        )
    else:
        if request.query is None:
            return _error(
                code="volition.missing_query",
                message="search requires query.",
                hint="Provide a natural phrase for the intention archive lookup.",
                actions=["Retry with query"],
            )
        intentions = repositories.list_intention_records(
            db,
            owner_profile_id=owner_profile_id,
            status=request.status,
            query=request.query,
            limit=request.limit,
            offset=request.offset,
        )
    return MemoryOperationResult(
        ok=True,
        result={
            "operation": f"volition.{request.action}",
            "items": [
                _intention_payload(
                    item,
                    links=repositories.list_intention_links(db, intention_id=item.id),
                )
                for item in intentions
            ],
            "limit": request.limit,
            "offset": request.offset,
            "query": request.query,
            "status": request.status,
            "included_statuses": sorted(OPEN_INTENTION_STATUS_VALUES)
            if request.action in {"list_active", "list_due"}
            else None,
            "include_unscheduled": request.include_unscheduled
            if request.action == "list_due"
            else None,
            "volition_policy": _volition_policy(),
        },
        cognitive_hint=(
            "Volition results describe Scarlet's latent internal directions. "
            "Do not let them override the user's current request."
        ),
    )


def _update_intention(
    db: Session,
    *,
    request: VolitionBody,
    owner_profile_id: str,
    source: dict[str, str | None],
    intent: str,
) -> MemoryOperationResult:
    intention = _target_intention(db, request=request, owner_profile_id=owner_profile_id)
    if intention is None:
        return _error(
            code="volition.not_found",
            message="No target intention found for update.",
            hint="Read or list intentions before updating one.",
            actions=["Call POST /mind/volition action=list_active"],
        )
    if request.status in {"resolved", "impossible", "deprecated"}:
        return _error(
            code="volition.use_close_action",
            message="update cannot apply terminal statuses.",
            hint="Use resolve, mark_impossible, or deprecate so closure is traced clearly.",
            actions=["Retry with the dedicated terminal lifecycle action"],
        )
    updated = repositories.update_intention_record(
        db,
        intention_id=intention.id,
        desire=request.desire,
        status=request.status,
        origin=request.origin,
        horizon=request.horizon,
        intensity=request.intensity,
        autonomy_level=request.autonomy_level,
        reason=request.reason,
        next_possible_reflection=request.next_possible_reflection,
        next_review_at=request.next_review_at,
        review_interval_seconds=request.review_interval_seconds,
        metadata=request.metadata,
    )
    assert updated is not None
    links = _add_links(db, intention_id=updated.id, links=request.links)
    all_links = repositories.list_intention_links(db, intention_id=updated.id)
    _record_volition_event(
        db,
        event_name="updated",
        intention=updated,
        source=source,
        payload={
            "action": request.action,
            "reason": request.reason or intent,
            "new_links": [_link_payload(item) for item in links],
        },
    )
    _trace_volition_operation(
        db,
        source=source,
        operation="volition.update",
        payload={"intention": _intention_payload(updated, links=all_links)},
    )
    return MemoryOperationResult(
        ok=True,
        result={
            "operation": "volition.update",
            "intention": _intention_payload(updated, links=all_links),
            "volition_policy": _volition_policy(),
        },
        cognitive_hint="The intention changed state without changing memory or focus.",
    )


def _defer_intention(
    db: Session,
    *,
    request: VolitionBody,
    owner_profile_id: str,
    source: dict[str, str | None],
    intent: str,
) -> MemoryOperationResult:
    intention = _target_intention(db, request=request, owner_profile_id=owner_profile_id)
    if intention is None:
        return _error(
            code="volition.not_found",
            message="No target intention found to defer.",
            hint="Provide intention_id or list active intentions first.",
            actions=["Call POST /mind/volition action=list_active"],
        )
    deferred = repositories.update_intention_record(
        db,
        intention_id=intention.id,
        status="deferred",
        reason=request.reason or intent,
        next_possible_reflection=request.next_possible_reflection,
        next_review_at=request.next_review_at,
        review_interval_seconds=request.review_interval_seconds,
        metadata=request.metadata,
    )
    assert deferred is not None
    _record_volition_event(
        db,
        event_name="updated",
        intention=deferred,
        source=source,
        payload={"action": request.action, "deferred_as": "deferred"},
    )
    _trace_volition_operation(
        db,
        source=source,
        operation="volition.defer",
        payload={"intention": _intention_payload(deferred)},
    )
    return MemoryOperationResult(
        ok=True,
        result={
            "operation": "volition.defer",
            "intention": _intention_payload(deferred),
            "volition_policy": _volition_policy(),
        },
        cognitive_hint="The intention remains latent and deferred for later review.",
    )


def _review_intention(
    db: Session,
    *,
    request: VolitionBody,
    owner_profile_id: str,
    source: dict[str, str | None],
    intent: str,
) -> MemoryOperationResult:
    intention = _target_intention(db, request=request, owner_profile_id=owner_profile_id)
    if intention is None:
        return _error(
            code="volition.not_found",
            message="No target intention found to review.",
            hint="Provide intention_id or list active intentions first.",
            actions=["Call POST /mind/volition action=list_active"],
        )
    if request.status in {"resolved", "impossible", "deprecated"}:
        return _error(
            code="volition.use_close_action",
            message="review cannot apply terminal statuses.",
            hint="Use resolve, mark_impossible, or deprecate for terminal lifecycle changes.",
            actions=["Retry with resolve, mark_impossible, or deprecate"],
        )
    reviewed = repositories.update_intention_record(
        db,
        intention_id=intention.id,
        status=request.status or "in_review",
        desire=request.desire,
        horizon=request.horizon,
        intensity=request.intensity,
        reason=request.reason or intent,
        next_possible_reflection=request.next_possible_reflection,
        last_reviewed_at=utc_now(),
        next_review_at=request.next_review_at,
        review_interval_seconds=request.review_interval_seconds,
        increment_review_count=True,
        metadata=request.metadata,
    )
    assert reviewed is not None
    links = _add_links(db, intention_id=reviewed.id, links=request.links)
    all_links = repositories.list_intention_links(db, intention_id=reviewed.id)
    _record_volition_event(
        db,
        event_name="reviewed",
        intention=reviewed,
        source=source,
        payload={
            "action": request.action,
            "new_links": [_link_payload(item) for item in links],
        },
    )
    _trace_volition_operation(
        db,
        source=source,
        operation="volition.review",
        payload={"intention": _intention_payload(reviewed, links=all_links)},
    )
    return MemoryOperationResult(
        ok=True,
        result={
            "operation": "volition.review",
            "intention": _intention_payload(reviewed, links=all_links),
            "volition_policy": _volition_policy(),
        },
        cognitive_hint="The intention was reviewed; it is still latent unless explicitly acted on.",
    )


def _promote_to_focus_candidate(
    db: Session,
    *,
    request: VolitionBody,
    owner_profile_id: str,
    source: dict[str, str | None],
    intent: str,
) -> MemoryOperationResult:
    intention = _target_intention(db, request=request, owner_profile_id=owner_profile_id)
    if intention is None:
        return _error(
            code="volition.not_found",
            message="No target intention found to promote.",
            hint="Provide intention_id or list active intentions first.",
            actions=["Call POST /mind/volition action=list_active"],
        )
    focus_candidate = {
        "method": "POST",
        "path": "/mind/focus",
        "body": {
            "action": "set",
            "object": intention.desire,
            "type": "volition",
            "intensity": intention.intensity,
            "duration_policy": "until_resolved",
            "reason": request.reason
            or f"Promoted from latent intention {intention.id}: {intention.reason}",
            "metadata": {
                "source_intention_id": intention.id,
                "source_intention_status": intention.status,
            },
        },
    }
    _record_volition_event(
        db,
        event_name="reviewed",
        intention=intention,
        source=source,
        payload={"action": request.action, "focus_candidate": focus_candidate},
    )
    _trace_volition_operation(
        db,
        source=source,
        operation="volition.promote_to_focus_candidate",
        payload={
            "intention": _intention_payload(intention),
            "focus_candidate": focus_candidate,
        },
    )
    return MemoryOperationResult(
        ok=True,
        result={
            "operation": "volition.promote_to_focus_candidate",
            "intention": _intention_payload(intention),
            "focus_candidate": focus_candidate,
            "applied": False,
            "volition_policy": _volition_policy(),
        },
        cognitive_hint=(
            "This produced a focus candidate only. It did not change active focus; "
            "call /mind/focus explicitly if Scarlet chooses to foreground it."
        ),
        suggested_next_actions=["Call POST /mind/focus only if this intention should become foreground focus"],
    )


def _close_intention(
    db: Session,
    *,
    request: VolitionBody,
    owner_profile_id: str,
    source: dict[str, str | None],
    intent: str,
) -> MemoryOperationResult:
    intention = _target_intention(db, request=request, owner_profile_id=owner_profile_id)
    if intention is None:
        return _error(
            code="volition.not_found",
            message="No target intention found to close.",
            hint="Provide intention_id or list active intentions first.",
            actions=["Call POST /mind/volition action=list_active"],
        )
    status = {
        "resolve": "resolved",
        "mark_impossible": "impossible",
        "deprecate": "deprecated",
    }[request.action]
    if request.action == "resolve" and not (request.resolution or request.reason):
        return _error(
            code="volition.missing_resolution",
            message="resolve requires resolution or reason.",
            hint="Explain how this intention reached closure.",
            actions=["Retry with resolution"],
        )
    if request.action == "mark_impossible" and not (
        request.impossible_reason or request.reason
    ):
        return _error(
            code="volition.missing_impossible_reason",
            message="mark_impossible requires impossible_reason or reason.",
            hint="Explain why this intention cannot be fulfilled or kept alive.",
            actions=["Retry with impossible_reason"],
        )
    if request.action == "deprecate" and request.reason is None:
        return _error(
            code="volition.missing_deprecation_reason",
            message="deprecate requires reason.",
            hint="Explain why this intention is no longer valid.",
            actions=["Retry with reason"],
        )
    closed = repositories.close_intention_record(
        db,
        intention_id=intention.id,
        status=status,
        resolution=request.resolution or (request.reason if status == "resolved" else None),
        impossible_reason=request.impossible_reason
        or (request.reason if status == "impossible" else None),
        metadata=request.metadata,
    )
    assert closed is not None
    _record_volition_event(
        db,
        event_name="closed",
        intention=closed,
        source=source,
        payload={"action": request.action, "closed_as": status},
    )
    _trace_volition_operation(
        db,
        source=source,
        operation=f"volition.{request.action}",
        payload={"intention": _intention_payload(closed)},
    )
    return MemoryOperationResult(
        ok=True,
        result={
            "operation": f"volition.{request.action}",
            "closed_intention": _intention_payload(closed),
            "volition_policy": _volition_policy(),
        },
        cognitive_hint="The intention left the open volition register and remains archived.",
    )


def _target_intention(
    db: Session,
    *,
    request: VolitionBody,
    owner_profile_id: str,
) -> IntentionRecord | None:
    if not request.intention_id:
        return None
    intention = repositories.get_intention_record(db, request.intention_id)
    if intention is not None and intention.owner_profile_id == owner_profile_id:
        return intention
    return None


def _add_links(
    db: Session,
    *,
    intention_id: str,
    links: list[IntentionLinkBody],
) -> list[IntentionLink]:
    return [
        repositories.add_intention_link(
            db,
            intention_id=intention_id,
            target_type=link.target_type,
            target_id=link.target_id,
            relation=link.relation,
            metadata=link.metadata,
        )
        for link in links
    ]


def _owner_profile_id(context: MindAPIContext) -> str:
    return str(getattr(context.settings, "user_profile_id", None) or "local-user")


def _source_payload(
    db: Session,
    context: MindAPIContext,
    *,
    owner_profile_id: str,
) -> dict[str, str | None]:
    message_id = None
    if context.turn_id is not None:
        message = repositories.latest_message_for_turn(
            db,
            turn_id=context.turn_id,
            role="user",
        )
        message_id = message.id if message is not None else None
    active_focus = repositories.get_active_focus(db, owner_profile_id=owner_profile_id)
    return {
        "session_id": context.session_id,
        "turn_id": context.turn_id,
        "message_id": message_id,
        "focus_id": active_focus.id if active_focus is not None else None,
    }


def _intention_payload(
    intention: IntentionRecord,
    *,
    links: list[IntentionLink] | None = None,
) -> dict[str, Any]:
    return {
        "id": intention.id,
        "owner_profile_id": intention.owner_profile_id,
        "status": intention.status,
        "desire": intention.desire,
        "origin": intention.origin,
        "horizon": intention.horizon,
        "intensity": intention.intensity,
        "autonomy_level": intention.autonomy_level,
        "reason": intention.reason,
        "next_possible_reflection": intention.next_possible_reflection,
        "last_reviewed_at": intention.last_reviewed_at.isoformat()
        if intention.last_reviewed_at
        else None,
        "next_review_at": intention.next_review_at.isoformat()
        if intention.next_review_at
        else None,
        "review_interval_seconds": intention.review_interval_seconds,
        "review_count": intention.review_count,
        "resolution": intention.resolution,
        "impossible_reason": intention.impossible_reason,
        "created_by": intention.created_by,
        "source_session_id": intention.source_session_id,
        "source_turn_id": intention.source_turn_id,
        "source_message_id": intention.source_message_id,
        "source_focus_id": intention.source_focus_id,
        "created_at": intention.created_at.isoformat(),
        "updated_at": intention.updated_at.isoformat(),
        "closed_at": intention.closed_at.isoformat() if intention.closed_at else None,
        "links": [_link_payload(link) for link in links] if links is not None else [],
        "metadata": intention.metadata_json,
    }


def _link_payload(link: IntentionLink) -> dict[str, Any]:
    return {
        "id": link.id,
        "intention_id": link.intention_id,
        "target_type": link.target_type,
        "target_id": link.target_id,
        "relation": link.relation,
        "created_at": link.created_at.isoformat(),
        "metadata": link.metadata_json,
    }


def _volition_policy() -> dict[str, Any]:
    return {
        "profile_scoped": True,
        "not_a_task_manager": True,
        "not_semantic_memory": True,
        "does_not_override_user_request": True,
        "automatic_chat_injection": False,
        "primary_processing_space": "future_autonomous_cycles",
        "meaning": (
            "Volition is Scarlet's latent self-generated direction: what she "
            "chooses to keep wanting, understanding, or returning to over time. "
            "It can be inspected manually, reviewed, closed, or promoted to a "
            "focus candidate, but it is not proof about external facts and does "
            "not automatically steer normal user chat."
        ),
    }


def _record_volition_event(
    db: Session,
    *,
    event_name: Literal["created", "updated", "reviewed", "closed"],
    intention: IntentionRecord,
    source: dict[str, str | None],
    payload: dict[str, Any] | None = None,
) -> None:
    session_id = source.get("session_id")
    if session_id is None:
        return
    repositories.add_event(
        db,
        session_id=session_id,
        turn_id=source.get("turn_id"),
        event_type=ORGAN_EVENT_TYPES["volition"][event_name],
        payload={
            "intention": _intention_payload(intention),
            **(payload or {}),
        },
        source="api_mind.volition",
        actor="scarlet",
        visibility="debug",
        status="completed",
        message_id=source.get("message_id"),
    )


def _trace_volition_operation(
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
        kind=ORGAN_TRACE_KINDS["volition"],
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
        result=result or {"operation": "volition"},
        cognitive_hint=hint,
        suggested_next_actions=actions,
        confidence=1.0,
        error_code=code,
        error_message=message,
        error_recoverable=True,
    )
