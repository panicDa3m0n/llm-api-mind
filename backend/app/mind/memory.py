import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.storage import repositories
from app.storage.models import MemoryRecord


MemoryType = Literal[
    "project_fact",
    "user_preference",
    "decision",
    "correction",
    "task_context",
    "behavioral_pattern",
    "episodic",
]
MemoryScope = Literal["project", "user", "session"]
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
CANONICAL_WRITE_KEYS = {
    "type",
    "content",
    "reason_for_storage",
    "expected_future_use",
    "confidence",
    "salience",
    "scope",
    "tags",
    "metadata",
}

MIN_WRITE_CONFIDENCE = 0.2
MIN_WRITE_SALIENCE = 0.25
TYPE_ALIASES = {
    "pref": "user_preference",
    "preference": "user_preference",
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
SCORE_ALIASES = {
    "certain": 0.95,
    "high": 0.85,
    "medium": 0.6,
    "med": 0.6,
    "low": 0.35,
    "uncertain": 0.25,
}


@dataclass(frozen=True)
class MindAPIContext:
    engine: Engine
    session_id: str | None = None
    turn_id: str | None = None


@dataclass(frozen=True)
class MemoryOperationResult:
    ok: bool
    result: dict[str, Any] = field(default_factory=dict)
    cognitive_hint: str | None = None
    suggested_next_actions: list[str] = field(default_factory=list)
    confidence: float = 1.0
    error_code: str | None = None
    error_message: str | None = None
    error_recoverable: bool = True


class MemoryWriteBody(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    memory_type: MemoryType = Field(alias="type")
    content: str = Field(min_length=12, max_length=4000)
    reason_for_storage: str = Field(min_length=8, max_length=1000)
    expected_future_use: str | None = Field(default=None, max_length=1000)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    salience: float = Field(default=0.7, ge=0.0, le=1.0)
    scope: MemoryScope = "project"
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def normalize_common_aliases(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        memory_type = normalized.get("type") or normalized.get("memory_type")
        if isinstance(memory_type, str):
            normalized["type"] = TYPE_ALIASES.get(memory_type.casefold(), memory_type)
        scope = normalized.get("scope")
        if isinstance(scope, str):
            normalized_scope = TYPE_ALIASES.get(scope.casefold(), scope)
            if "type" not in normalized and normalized_scope in MEMORY_TYPE_VALUES:
                normalized["type"] = normalized_scope
                normalized["scope"] = "project"
            elif normalized_scope in MEMORY_TYPE_VALUES:
                normalized["scope"] = "project"
        if "reason_for_storage" not in normalized and "why" in normalized:
            normalized["reason_for_storage"] = normalized.pop("why")
        elif "reason_for_storage" not in normalized and "reason" in normalized:
            normalized["reason_for_storage"] = normalized.pop("reason")
        elif "reason_for_storage" not in normalized and "rationale" in normalized:
            normalized["reason_for_storage"] = normalized.pop("rationale")
        else:
            normalized.pop("why", None)
            normalized.pop("reason", None)
            normalized.pop("rationale", None)
        if "expected_future_use" not in normalized and "use_case" in normalized:
            normalized["expected_future_use"] = normalized.pop("use_case")
        elif "expected_future_use" not in normalized and "use" in normalized:
            normalized["expected_future_use"] = normalized.pop("use")
        elif "expected_future_use" not in normalized and "future_use" in normalized:
            normalized["expected_future_use"] = normalized.pop("future_use")
        elif "expected_future_use" not in normalized and "use_during" in normalized:
            normalized["expected_future_use"] = normalized.pop("use_during")
        else:
            normalized.pop("use_case", None)
            normalized.pop("use", None)
            normalized.pop("future_use", None)
            normalized.pop("use_during", None)
        if "id" in normalized:
            metadata = normalized.get("metadata") or {}
            if isinstance(metadata, dict):
                metadata = dict(metadata)
                metadata["model_suggested_id"] = normalized.pop("id")
                normalized["metadata"] = metadata
            else:
                normalized.pop("id", None)
        normalized.pop("memory_type", None)
        extras = {
            key: normalized.pop(key)
            for key in list(normalized)
            if key not in CANONICAL_WRITE_KEYS
        }
        if extras:
            metadata = normalized.get("metadata") or {}
            if isinstance(metadata, dict):
                metadata = dict(metadata)
                metadata["model_extra"] = extras
                normalized["metadata"] = metadata
        return normalized

    @field_validator("content", "reason_for_storage", "expected_future_use")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return " ".join(value.split())

    @field_validator("confidence", "salience", mode="before")
    @classmethod
    def normalize_score(cls, value: Any) -> Any:
        if isinstance(value, str):
            lowered = value.strip().casefold()
            return SCORE_ALIASES.get(lowered, value)
        return value

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for tag in value[:20]:
            cleaned = re.sub(r"\s+", "-", tag.strip().lower())
            if cleaned and cleaned not in seen:
                normalized.append(cleaned[:60])
                seen.add(cleaned)
        return normalized


class MemorySearchBody(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    query: str = Field(min_length=1, max_length=1000)
    memory_types: list[MemoryType] = Field(default_factory=list, alias="types")
    scope: MemoryScope | None = "project"
    top_k: int = Field(default=5, ge=1, le=20)
    include_low_confidence: bool = False

    @model_validator(mode="before")
    @classmethod
    def normalize_common_aliases(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        if "top_k" not in normalized and "limit" in normalized:
            normalized["top_k"] = normalized.pop("limit")
        else:
            normalized.pop("limit", None)
        memory_types = normalized.get("types")
        if isinstance(memory_types, str):
            normalized["types"] = [TYPE_ALIASES.get(memory_types.casefold(), memory_types)]
        elif isinstance(memory_types, list):
            normalized["types"] = [
                TYPE_ALIASES.get(item.casefold(), item) if isinstance(item, str) else item
                for item in memory_types
            ]
        return normalized

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        return " ".join(value.split())


def handle_memory_write(
    body: dict[str, Any],
    context: MindAPIContext | None,
    *,
    intent: str | None = None,
) -> MemoryOperationResult:
    if context is None or context.session_id is None:
        return _context_required("write")

    body_with_intent = dict(body)
    if (
        not any(
            key in body_with_intent
            for key in ("reason_for_storage", "why", "reason", "rationale")
        )
        and intent
    ):
        body_with_intent["reason_for_storage"] = intent

    try:
        request = MemoryWriteBody.model_validate(body_with_intent)
    except ValidationError as exc:
        return MemoryOperationResult(
            ok=False,
            error_code="memory.invalid_write",
            error_message=str(exc),
            suggested_next_actions=[
                "Call GET /mind/schema",
                "Retry with a valid memory write body",
            ],
            confidence=1.0,
        )

    policy = _evaluate_write_policy(request)

    with Session(context.engine) as db:
        if not policy["accepted"]:
            trace = _trace_memory_write(
                db,
                context=context,
                request=request,
                policy=policy,
                memory=None,
                stored=False,
                decision="rejected",
            )
            return MemoryOperationResult(
                ok=False,
                result={
                    "operation": "memory.write",
                    "stored": False,
                    "policy_decision": "rejected",
                    "policy": policy,
                    "trace_ids": [trace.id],
                },
                cognitive_hint="The candidate memory was rejected by the v0 write policy.",
                suggested_next_actions=[
                    "Continue without storing this item",
                    "Only write reusable, sourceable memories",
                ],
                confidence=1.0,
                error_code="memory.policy_rejected",
                error_message=policy["reason"],
                error_recoverable=True,
            )

        duplicate = _find_duplicate(db, request)
        if duplicate is not None:
            trace = _trace_memory_write(
                db,
                context=context,
                request=request,
                policy=policy,
                memory=duplicate,
                stored=False,
                decision="deduplicated",
            )
            return MemoryOperationResult(
                ok=True,
                result={
                    "operation": "memory.write",
                    "stored": False,
                    "policy_decision": "deduplicated",
                    "existing_memory": _memory_payload(duplicate),
                    "memory_id": duplicate.id,
                    "trace_ids": [trace.id],
                },
                cognitive_hint=(
                    "An equivalent memory already exists; reuse the existing "
                    "memory instead of creating a duplicate."
                ),
                suggested_next_actions=["Use the existing memory when relevant"],
                confidence=0.95,
            )

        memory = repositories.add_memory(
            db,
            memory_type=request.memory_type,
            content=request.content,
            reason_for_storage=request.reason_for_storage,
            expected_future_use=request.expected_future_use,
            confidence=request.confidence,
            salience=request.salience,
            scope=request.scope,
            source_session_id=context.session_id,
            source_turn_id=context.turn_id,
            tags=request.tags,
            metadata=request.metadata,
        )
        trace = _trace_memory_write(
            db,
            context=context,
            request=request,
            policy=policy,
            memory=memory,
            stored=True,
            decision="accepted",
        )
        return MemoryOperationResult(
            ok=True,
            result={
                "operation": "memory.write",
                "stored": True,
                "policy_decision": "accepted",
                "memory": _memory_payload(memory),
                "memory_id": memory.id,
                "trace_ids": [trace.id],
            },
            cognitive_hint=(
                "Memory stored. Future answers should search memory when this "
                "fact, decision, preference, or correction may be relevant."
            ),
            suggested_next_actions=["Search memory before answering related future turns"],
            confidence=1.0,
        )


def handle_memory_search(
    body: dict[str, Any],
    context: MindAPIContext | None,
    *,
    intent: str | None = None,
) -> MemoryOperationResult:
    if context is None or context.session_id is None:
        return _context_required("search")

    body_with_intent = dict(body)
    if "query" not in body_with_intent and intent:
        body_with_intent["query"] = intent

    try:
        request = MemorySearchBody.model_validate(body_with_intent)
    except ValidationError as exc:
        return MemoryOperationResult(
            ok=False,
            error_code="memory.invalid_search",
            error_message=str(exc),
            suggested_next_actions=[
                "Call GET /mind/schema",
                "Retry with a valid memory search body",
            ],
            confidence=1.0,
        )

    with Session(context.engine) as db:
        candidates = repositories.list_memories(
            db,
            memory_types=list(request.memory_types),
            scope=request.scope,
            include_low_confidence=request.include_low_confidence,
        )
        scored = _score_memories(candidates, request.query)
        selected = scored[: request.top_k]
        refreshed: list[tuple[MemoryRecord, float, str]] = []
        for memory, score, reason in selected:
            updated = repositories.mark_memory_used(db, memory_id=memory.id) or memory
            refreshed.append((updated, score, reason))

        trace = repositories.add_trace(
            db,
            session_id=context.session_id,
            turn_id=context.turn_id,
            kind="mind.memory.search",
            payload={
                "operation": "memory.search",
                "query": request.query,
                "types": list(request.memory_types),
                "scope": request.scope,
                "top_k": request.top_k,
                "returned_memory_ids": [memory.id for memory, _, _ in refreshed],
                "candidate_count": len(candidates),
            },
        )

        memories = [
            {
                **_memory_payload(memory),
                "score": round(score, 4),
                "why_relevant": reason,
            }
            for memory, score, reason in refreshed
        ]

    return MemoryOperationResult(
        ok=True,
        result={
            "operation": "memory.search",
            "query": request.query,
            "memories": memories,
            "count": len(memories),
            "trace_ids": [trace.id],
        },
        cognitive_hint=(
            "Use returned memories as sourceable context, not as hidden truth. "
            "If no memories are returned, answer from current conversation only."
        ),
        suggested_next_actions=[
            "Use relevant memories with their provenance",
            "Do not invent memory content when search returns no result",
        ],
        confidence=0.95 if memories else 0.8,
    )


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


def _evaluate_write_policy(request: MemoryWriteBody) -> dict[str, Any]:
    if request.confidence < MIN_WRITE_CONFIDENCE:
        return {
            "accepted": False,
            "reason": "confidence below v0 write threshold",
            "thresholds": {
                "min_confidence": MIN_WRITE_CONFIDENCE,
                "min_salience": MIN_WRITE_SALIENCE,
            },
        }
    if request.salience < MIN_WRITE_SALIENCE:
        return {
            "accepted": False,
            "reason": "salience below v0 write threshold",
            "thresholds": {
                "min_confidence": MIN_WRITE_CONFIDENCE,
                "min_salience": MIN_WRITE_SALIENCE,
            },
        }
    return {
        "accepted": True,
        "reason": "candidate passed v0 confidence, salience, and shape checks",
        "thresholds": {
            "min_confidence": MIN_WRITE_CONFIDENCE,
            "min_salience": MIN_WRITE_SALIENCE,
        },
    }


def _find_duplicate(db: Session, request: MemoryWriteBody) -> MemoryRecord | None:
    normalized = _normalize_memory_text(request.content)
    for memory in repositories.list_memories(
        db,
        memory_types=[request.memory_type],
        scope=request.scope,
        include_low_confidence=True,
    ):
        if _normalize_memory_text(memory.content) == normalized:
            return memory
    return None


def _score_memories(
    memories: list[MemoryRecord],
    query: str,
) -> list[tuple[MemoryRecord, float, str]]:
    query_text = query.lower()
    query_tokens = set(_tokens(query))
    scored: list[tuple[MemoryRecord, float, str]] = []

    for memory in memories:
        haystack = " ".join(
            item
            for item in [
                memory.content,
                memory.reason_for_storage,
                memory.expected_future_use or "",
                memory.memory_type,
                " ".join(memory.tags_json),
            ]
            if item
        ).lower()
        haystack_tokens = set(_tokens(haystack))
        overlap = query_tokens & haystack_tokens
        score = 0.0
        reasons: list[str] = []
        if query_text in haystack:
            score += 3.0
            reasons.append("query substring match")
        if overlap:
            token_score = len(overlap) / max(len(query_tokens), 1)
            score += token_score
            reasons.append(f"token overlap: {', '.join(sorted(overlap))}")
        tag_overlap = query_tokens & set(memory.tags_json)
        if tag_overlap:
            score += 0.5
            reasons.append(f"tag overlap: {', '.join(sorted(tag_overlap))}")
        if score <= 0:
            continue

        score *= 1.0 + memory.salience + memory.confidence
        scored.append((memory, score, "; ".join(reasons)))

    return sorted(
        scored,
        key=lambda item: (item[1], item[0].salience, item[0].created_at),
        reverse=True,
    )


def _trace_memory_write(
    db: Session,
    *,
    context: MindAPIContext,
    request: MemoryWriteBody,
    policy: dict[str, Any],
    memory: MemoryRecord | None,
    stored: bool,
    decision: str,
):
    return repositories.add_trace(
        db,
        session_id=context.session_id or "",
        turn_id=context.turn_id,
        kind="mind.memory.write",
        payload={
            "operation": "memory.write",
            "stored": stored,
            "policy_decision": decision,
            "policy": policy,
            "request": request.model_dump(mode="json"),
            "memory_id": memory.id if memory is not None else None,
        },
    )


def _memory_payload(memory: MemoryRecord) -> dict[str, Any]:
    return {
        "id": memory.id,
        "type": memory.memory_type,
        "scope": memory.scope,
        "status": memory.status,
        "content": memory.content,
        "reason_for_storage": memory.reason_for_storage,
        "expected_future_use": memory.expected_future_use,
        "confidence": memory.confidence,
        "salience": memory.salience,
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


def _normalize_memory_text(value: str) -> str:
    return " ".join(value.casefold().split())


def _tokens(value: str) -> list[str]:
    return re.findall(r"\w+", value.casefold())


def _isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()
