import re
from dataclasses import dataclass
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)
from sqlmodel import Session

from app.mind.contracts import MindAPIContext, MemoryOperationResult
from app.mind.facts import fact_payload
from app.mind.memory_shared import (
    DEFAULT_MEMORY_SCOPE,
    MEMORY_TYPE_VALUES,
    TYPE_ALIASES,
    MemoryScope,
    MemoryType,
    _context_required,
    _memory_not_found,
    _memory_payload,
    _normalize_freeform_label,
    _normalize_memory_text,
    _record_memory_activity,
    load_memory_facts,
)
from app.mind.search import sync_memory_retrieval_artifacts
from app.storage import repositories
from app.storage.models import MemoryFact, MemoryRecord


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

NEUTRAL_STORED_CONFIDENCE = 0.5
NEUTRAL_STORED_SALIENCE = 0.5
SCORE_ALIASES = {
    "certain": 0.95,
    "high": 0.85,
    "alta": 0.85,
    "alto": 0.85,
    "medium": 0.6,
    "med": 0.6,
    "media": 0.6,
    "medio": 0.6,
    "low": 0.35,
    "bassa": 0.35,
    "basso": 0.35,
    "uncertain": 0.25,
}


@dataclass(frozen=True)
class MemoryWriteSource:
    """Backend-owned source override for a previously captured candidate."""

    session_id: str | None = None
    turn_id: str | None = None
    message_id: str | None = None
    metadata: dict[str, Any] | None = None


class MemoryWriteBody(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    memory_type: MemoryType = Field(alias="type", min_length=2, max_length=80)
    content: str = Field(min_length=12, max_length=4000)
    reason_for_storage: str = Field(min_length=8, max_length=1000)
    expected_future_use: str | None = Field(default=None, max_length=1000)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    salience: float | None = Field(default=None, ge=0.0, le=1.0)
    scope: MemoryScope = Field(
        default=DEFAULT_MEMORY_SCOPE, min_length=2, max_length=80
    )
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
            normalized["type"] = _normalize_freeform_label(
                TYPE_ALIASES.get(memory_type.casefold(), memory_type)
            )
        scope = normalized.get("scope")
        if isinstance(scope, str):
            normalized_scope = _normalize_freeform_label(scope)
            if "type" not in normalized and normalized_scope in MEMORY_TYPE_VALUES:
                normalized["type"] = normalized_scope
                normalized["scope"] = DEFAULT_MEMORY_SCOPE
            elif normalized_scope in MEMORY_TYPE_VALUES:
                normalized["scope"] = DEFAULT_MEMORY_SCOPE
            else:
                normalized["scope"] = normalized_scope
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


class MemoryFactsBackfillBody(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    memory_id: str | None = Field(default=None, max_length=80)
    include_inactive: bool = True

    @model_validator(mode="before")
    @classmethod
    def normalize_common_aliases(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        if "memory_id" not in normalized:
            for alias in ("id", "target_id"):
                if alias in normalized:
                    normalized["memory_id"] = normalized.pop(alias)
                    break
        return normalized


def handle_memory_write(
    body: dict[str, Any],
    context: MindAPIContext | None,
    *,
    intent: str | None = None,
    source: MemoryWriteSource | None = None,
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
                source=source,
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
            duplicate_facts = repositories.list_memory_facts(
                db,
                memory_id=duplicate.id,
                include_inactive=True,
            )
            trace = _trace_memory_write(
                db,
                context=context,
                request=request,
                policy=policy,
                memory=duplicate,
                stored=False,
                decision="deduplicated",
                source=source,
            )
            _record_memory_activity(
                db,
                context=context,
                memory_id=duplicate.id,
                activity_kind="write_review_candidate",
                source="memory.write",
                trace_id=trace.id,
                metadata={"decision": "deduplicated"},
            )
            return MemoryOperationResult(
                ok=True,
                result={
                    "operation": "memory.write",
                    "stored": False,
                    "policy_decision": "deduplicated",
                    "existing_memory": _memory_payload(
                        duplicate, facts=duplicate_facts
                    ),
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
            confidence=NEUTRAL_STORED_CONFIDENCE,
            salience=NEUTRAL_STORED_SALIENCE,
            scope=request.scope,
            source_session_id=source.session_id if source else context.session_id,
            source_turn_id=source.turn_id if source else context.turn_id,
            source_message_id=source.message_id if source else context.source_message_id,
            tags=[],
            metadata=_backend_memory_metadata_from_write(
                request,
                source_metadata=source.metadata if source else None,
            ),
        )
        trace = _trace_memory_write(
            db,
            context=context,
            request=request,
            policy=policy,
            memory=memory,
            stored=True,
            decision="accepted",
            source=source,
        )
        _record_memory_activity(
            db,
            context=context,
            memory_id=memory.id,
            activity_kind="write",
            source="memory.write",
            trace_id=trace.id,
        )
        facts, created_facts = load_memory_facts(
            db,
            memory,
            source_trace_id=trace.id,
        )
        sync_memory_retrieval_artifacts(
            db,
            [memory],
            facts_by_memory={memory.id: facts},
        )
        return MemoryOperationResult(
            ok=True,
            result={
                "operation": "memory.write",
                "stored": True,
                "policy_decision": "accepted",
                "memory": _memory_payload(memory, facts=facts),
                "memory_id": memory.id,
                "facts_created": len(created_facts),
                "trace_ids": [trace.id],
            },
            cognitive_hint=(
                "Memory stored. Future answers should search memory when this "
                "fact, decision, preference, or correction may be relevant."
            ),
            suggested_next_actions=[
                "Search memory before answering related future turns"
            ],
            confidence=1.0,
        )


def handle_memory_facts_backfill(
    body: dict[str, Any],
    context: MindAPIContext | None,
    *,
    intent: str | None = None,
) -> MemoryOperationResult:
    if context is None or context.session_id is None:
        return _context_required("facts.backfill")

    body_with_intent = dict(body)
    if "memory_id" not in body_with_intent and intent and "mem_" in intent:
        match = re.search(r"mem_[a-f0-9]+", intent)
        if match:
            body_with_intent["memory_id"] = match.group(0)

    try:
        request = MemoryFactsBackfillBody.model_validate(body_with_intent)
    except ValidationError as exc:
        return MemoryOperationResult(
            ok=False,
            error_code="memory.invalid_facts_backfill",
            error_message=str(exc),
            suggested_next_actions=[
                "Call GET /mind/schema",
                "Retry with optional memory_id",
            ],
            confidence=1.0,
        )

    with Session(context.engine) as db:
        if request.memory_id is not None:
            memory = repositories.get_memory(db, request.memory_id)
            if memory is None:
                return _memory_not_found(request.memory_id)
            memories = [memory]
        elif request.include_inactive:
            memories = repositories.list_all_memories(db, include_low_confidence=False)
        else:
            memories = repositories.list_memories(db, scope=None)

        trace = repositories.add_trace(
            db,
            session_id=context.session_id,
            turn_id=context.turn_id,
            kind="mind.memory.facts.backfill",
            payload={
                "operation": "memory.facts.backfill",
                "memory_id": request.memory_id,
                "include_inactive": request.include_inactive,
                "candidate_count": len(memories),
            },
        )
        all_facts: list[MemoryFact] = []
        created: list[MemoryFact] = []
        for memory in memories:
            facts, created_facts = load_memory_facts(
                db,
                memory,
                source_trace_id=trace.id,
            )
            all_facts.extend(facts)
            created.extend(created_facts)
        _sync_fact_lifecycle_from_memory_metadata(db, memories)
        facts_by_memory = {
            memory.id: repositories.list_memory_facts(
                db,
                memory_id=memory.id,
                include_inactive=True,
            )
            for memory in memories
        }
        sync_memory_retrieval_artifacts(
            db,
            memories,
            facts_by_memory=facts_by_memory,
        )
        all_facts = [
            fact
            for memory in memories
            for fact in repositories.list_memory_facts(
                db,
                memory_id=memory.id,
                include_inactive=True,
            )
        ]

        fact_payloads = [fact_payload(fact) for fact in all_facts]
        created_ids = [fact.id for fact in created]
        trace_id = trace.id

    return MemoryOperationResult(
        ok=True,
        result={
            "operation": "memory.facts.backfill",
            "memories_checked": len(memories),
            "facts": fact_payloads,
            "fact_count": len(fact_payloads),
            "created_fact_ids": created_ids,
            "created_count": len(created_ids),
            "trace_ids": [trace_id],
        },
        cognitive_hint=(
            "Heuristic fact generation is retired. Historical fact rows remain "
            "available for audit, but no new semantic propositions were created."
        ),
        suggested_next_actions=[
            "Inspect historical facts only when migration provenance matters",
            "Use the source memory and transcript as semantic evidence",
        ],
        confidence=1.0,
    )


def _evaluate_write_policy(request: MemoryWriteBody) -> dict[str, Any]:
    return {
        "accepted": True,
        "reason": (
            "candidate passed backend shape checks; dynamic retrieval scores "
            "are computed at search time, not stored from model-supplied "
            "confidence or salience"
        ),
        "deprecated_model_fields": {
            "confidence": request.confidence,
            "salience": request.salience,
            "tags": request.tags,
            "metadata_keys": sorted(request.metadata.keys()),
        },
    }


def _find_duplicate(db: Session, request: MemoryWriteBody) -> MemoryRecord | None:
    normalized = _normalize_memory_text(request.content)
    for memory in repositories.list_memories(
        db,
        scope=None,
        include_low_confidence=True,
    ):
        if _normalize_memory_text(memory.content) == normalized:
            return memory
    return None


def _trace_memory_write(
    db: Session,
    *,
    context: MindAPIContext,
    request: MemoryWriteBody,
    policy: dict[str, Any],
    memory: MemoryRecord | None,
    stored: bool,
    decision: str,
    source: MemoryWriteSource | None = None,
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
            "source_override": {
                "session_id": source.session_id,
                "turn_id": source.turn_id,
                "message_id": source.message_id,
                "metadata": source.metadata or {},
            }
            if source is not None
            else None,
        },
    )


def _sync_fact_lifecycle_from_memory_metadata(
    db: Session,
    memories: list[MemoryRecord],
) -> None:
    memory_ids = {memory.id for memory in memories}
    for memory in memories:
        lifecycle = (memory.metadata_json or {}).get("lifecycle")
        if not isinstance(lifecycle, dict):
            continue
        superseded_by = lifecycle.get("superseded_by")
        if not isinstance(superseded_by, str):
            continue
        if (
            superseded_by not in memory_ids
            and repositories.get_memory(db, superseded_by) is None
        ):
            continue
        repositories.update_memory_facts_status(
            db,
            memory_id=memory.id,
            status="deprecated",
            superseded_by_memory_id=superseded_by,
        )


def _backend_memory_metadata_from_write(
    request: MemoryWriteBody,
    *,
    source_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ignored: dict[str, Any] = {}
    if request.confidence is not None:
        ignored["confidence"] = request.confidence
    if request.salience is not None:
        ignored["salience"] = request.salience
    if request.tags:
        ignored["tags"] = request.tags
    if request.metadata:
        ignored["metadata"] = request.metadata
    metadata = {
        "write_policy": "backend_owned_dynamic_retrieval_scores_v1",
        "agent_supplied_fields_ignored_for_ranking": ignored,
    }
    if source_metadata:
        metadata["source_context"] = source_metadata
    return metadata
