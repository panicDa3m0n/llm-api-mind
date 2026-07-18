import hashlib
import re
from itertools import combinations
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
from app.mind.memory_read import (
    MemoryFactsQueryBody as MemoryFactsQueryBody,
    MemoryGraphExploreBody as MemoryGraphExploreBody,
    MemorySearchBody as MemorySearchBody,
    _facts_by_memory,
    _score_memories,
    handle_memory_facts as handle_memory_facts,
    handle_memory_graph as handle_memory_graph,
    handle_memory_read as handle_memory_read,
    handle_memory_search as handle_memory_search,
)
from app.mind.memory_shared import (
    DEFAULT_MEMORY_SCOPE as DEFAULT_MEMORY_SCOPE,
    MEMORY_SCOPE_VALUES as MEMORY_SCOPE_VALUES,
    MEMORY_TYPE_VALUES as MEMORY_TYPE_VALUES,
    TYPE_ALIASES as TYPE_ALIASES,
    MemoryScope as MemoryScope,
    MemoryType as MemoryType,
    _context_required,
    _memory_not_found,
    _memory_payload,
    _normalize_freeform_label,
    _record_memory_activity,
    _isoformat,
)
from app.mind.facts import (
    extracted_fact_payload,
    extract_memory_facts,
    fact_payload,
)
from app.mind.search import (
    search_documents,
    sparse_results_by_source,
    sync_memory_documents,
    sync_memory_retrieval_artifacts,
)
from app.storage import repositories
from app.storage.models import (
    MemoryFact,
    MemoryProposal,
    MemoryRecord,
    utc_now,
)


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


class MemoryWriteBody(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    memory_type: MemoryType = Field(alias="type", min_length=2, max_length=80)
    content: str = Field(min_length=12, max_length=4000)
    reason_for_storage: str = Field(min_length=8, max_length=1000)
    expected_future_use: str | None = Field(default=None, max_length=1000)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    salience: float | None = Field(default=None, ge=0.0, le=1.0)
    scope: MemoryScope = Field(default=DEFAULT_MEMORY_SCOPE, min_length=2, max_length=80)
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
                    "existing_memory": _memory_payload(duplicate, facts=duplicate_facts),
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
            source_session_id=context.session_id,
            source_turn_id=context.turn_id,
            source_message_id=context.source_message_id,
            tags=[],
            metadata=_backend_memory_metadata_from_write(request),
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
        _record_memory_activity(
            db,
            context=context,
            memory_id=memory.id,
            activity_kind="write",
            source="memory.write",
            trace_id=trace.id,
        )
        facts, created_facts = _ensure_memory_facts(
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
            suggested_next_actions=["Search memory before answering related future turns"],
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
            facts, created_facts = _ensure_memory_facts(
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
            "Canonical facts are now available for inspected memories. Use "
            "them before relying on tag or token similarity."
        ),
        suggested_next_actions=[
            "Inspect facts by entity or predicate",
            "Use memory conflicts to check unresolved active fact conflicts",
        ],
        confidence=1.0,
    )






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


def handle_memory_conflicts(
    context: MindAPIContext | None,
) -> MemoryOperationResult:
    if context is None or context.session_id is None:
        return _context_required("conflicts")

    with Session(context.engine) as db:
        memories = repositories.list_memories(db, scope=None, include_low_confidence=False)
        facts_by_memory = _facts_by_memory(db, memories)
        relations = _detect_active_memory_relations(
            memories,
            facts_by_memory=facts_by_memory,
        )
        conflicts = relations["conflicts"]
        related_overlaps = relations["related_overlaps"]
        trace = repositories.add_trace(
            db,
            session_id=context.session_id,
            turn_id=context.turn_id,
            kind="memory.conflicts",
            payload={
                "operation": "memory.conflicts",
                "count": len(conflicts),
                "conflict_counts": _conflict_counts(conflicts),
                "related_overlap_count": len(related_overlaps),
                "active_memory_count": len(memories),
                "active_fact_count": sum(
                    len(facts) for facts in facts_by_memory.values()
                ),
                "conflicts": conflicts,
                "related_overlaps": related_overlaps,
            },
        )
        trace_id = trace.id

    return MemoryOperationResult(
        ok=True,
        result={
            "operation": "memory.conflicts",
            "count": len(conflicts),
            "conflict_counts": _conflict_counts(conflicts),
            "conflicts": conflicts,
            "related_overlap_count": len(related_overlaps),
            "related_overlaps": related_overlaps[:20],
            "trace_ids": [trace_id],
        },
        cognitive_hint=(
            "Unresolved atomic memory conflicts should be named before using "
            "any conflicting memory as active evidence. Related overlaps are "
            "maintenance signals, not contradictions."
        )
        if conflicts
        else "No active atomic memory conflicts were detected.",
        suggested_next_actions=[
            "Supersede or deprecate obsolete memories",
            "Continue with active memory context",
        ]
        if conflicts
        else ["Continue with active memories"],
        confidence=0.95,
    )


def create_memory_proposal_from_review_candidate(
    db: Session,
    *,
    candidate: dict[str, Any],
    context: MindAPIContext,
    source_trace_id: str,
    maintenance_job_id: str | None,
    candidate_index: int,
    source: str = "maintenance.memory_review",
) -> tuple[MemoryProposal, bool]:
    request, validation_error = _memory_request_from_review_candidate(candidate)
    if request is None:
        content = _string(candidate.get("content")) or "Invalid memory candidate"
        reason = _string(candidate.get("reason_for_storage")) or (
            _string(candidate.get("reason")) or "Memory review candidate needs repair."
        )
        decision = {
            "proposed_action": "needs_review",
            "reason": "candidate failed memory write validation",
            "validation_error": validation_error,
            "retrieval_stages": [],
            "future_ready": {
                "embedding_vector_id": None,
                "graph_node_ids": [],
            },
        }
        return repositories.upsert_memory_proposal(
            db,
            idempotency_key=_proposal_idempotency_key(
                context=context,
                source_trace_id=source_trace_id,
                candidate_index=candidate_index,
                candidate_type=_string(candidate.get("type")) or "task_context",
                candidate_scope=_string(candidate.get("scope")) or "session",
                content=content,
            ),
            source=source,
            proposed_action="needs_review",
            action_confidence=0.0,
            risk="high",
            candidate_type=_string(candidate.get("type")) or "task_context",
            candidate_scope=_string(candidate.get("scope")) or "session",
            content=content,
            reason_for_storage=reason,
            evidence=_string(candidate.get("evidence")),
            source_session_id=context.session_id,
            source_turn_id=context.turn_id,
            source_trace_id=source_trace_id,
            maintenance_job_id=maintenance_job_id,
            source_message_ids=_candidate_source_message_ids(candidate),
            tags=_list_of_strings(candidate.get("tags")),
            decision=decision,
            metadata={"source_candidate": candidate},
        )

    decision = _proposal_decision_for_request(db, request)
    idempotency_key = _proposal_idempotency_key(
        context=context,
        source_trace_id=source_trace_id,
        candidate_index=candidate_index,
        candidate_type=request.memory_type,
        candidate_scope=request.scope,
        content=request.content,
    )
    proposal, created = repositories.upsert_memory_proposal(
        db,
        idempotency_key=idempotency_key,
        source=source,
        proposed_action=decision["proposed_action"],
        action_confidence=decision["action_confidence"],
        risk=decision["risk"],
        candidate_type=request.memory_type,
        candidate_scope=request.scope,
        content=request.content,
        reason_for_storage=request.reason_for_storage,
        expected_future_use=request.expected_future_use,
        confidence=(
            request.confidence
            if request.confidence is not None
            else NEUTRAL_STORED_CONFIDENCE
        ),
        salience=(
            request.salience
            if request.salience is not None
            else NEUTRAL_STORED_SALIENCE
        ),
        evidence=_string(candidate.get("evidence")),
        source_session_id=context.session_id,
        source_turn_id=context.turn_id,
        source_trace_id=source_trace_id,
        maintenance_job_id=maintenance_job_id,
        source_message_ids=_candidate_source_message_ids(candidate),
        tags=request.tags,
        similar_memory_ids=decision["similar_memory_ids"],
        related_fact_ids=decision["related_fact_ids"],
        candidate_facts=decision["candidate_facts"],
        decision=decision,
        metadata={"source_candidate": candidate},
    )
    return proposal, created


def _memory_request_from_review_candidate(
    candidate: dict[str, Any],
) -> tuple[MemoryWriteBody | None, str | None]:
    body = {
        "type": candidate.get("type") or candidate.get("memory_type"),
        "content": candidate.get("content"),
        "reason_for_storage": (
            candidate.get("reason_for_storage") or candidate.get("reason")
        ),
        "expected_future_use": candidate.get("expected_future_use"),
        "confidence": candidate.get("confidence"),
        "salience": candidate.get("salience"),
        "scope": candidate.get("scope") or DEFAULT_MEMORY_SCOPE,
        "tags": candidate.get("tags") or [],
        "metadata": {
            "proposal_origin": "maintenance.memory_review",
        },
    }
    try:
        return MemoryWriteBody.model_validate(body), None
    except ValidationError as exc:
        return None, str(exc)


def _proposal_decision_for_request(
    db: Session,
    request: MemoryWriteBody,
) -> dict[str, Any]:
    policy = _evaluate_write_policy(request)
    candidate_facts = [
        extracted_fact_payload(fact)
        for fact in extract_memory_facts(_transient_memory(request))
    ]
    candidates = repositories.list_memories(
        db,
        scope=None,
        include_low_confidence=True,
    )
    facts_by_memory = _facts_by_memory(db, candidates)
    sync_memory_documents(db, candidates, facts_by_memory=facts_by_memory)
    sparse_matches = sparse_results_by_source(
        search_documents(
            db,
            query=request.content,
            kind="memory",
            limit=50,
        )
    )
    scored = _score_memories(
        candidates,
        request.content,
        facts_by_memory=facts_by_memory,
        sparse_matches=sparse_matches,
    )
    similar = scored[:5]
    exact_duplicate = _find_duplicate(db, request)
    matching_fact_ids, conflicting_fact_ids = _candidate_fact_matches(
        candidate_facts,
        facts_by_memory,
    )

    if not policy["accepted"]:
        action = "reject_candidate"
        action_confidence = 0.95
        risk = "low"
        reason = policy["reason"]
    elif exact_duplicate is not None or matching_fact_ids:
        action = "noop_duplicate"
        action_confidence = 0.95
        risk = "low"
        reason = "equivalent active memory or active canonical fact already exists"
    elif conflicting_fact_ids:
        action = "needs_review"
        action_confidence = 0.85
        risk = "high"
        reason = "candidate appears to conflict with active canonical facts"
    elif similar:
        action = "review_similar"
        action_confidence = 0.75
        risk = "medium"
        reason = "candidate has similar active memories; review before writing"
    else:
        action = "create_new"
        action_confidence = 0.8
        risk = "medium"
        reason = "no duplicate, fact match, or conflict detected by current preflight"

    similar_payloads = [
        {
            "id": memory.id,
            "type": memory.memory_type,
            "scope": memory.scope,
            "status": memory.status,
            "score": round(score, 4),
            "why_relevant": why,
            "content": memory.content,
            "facts": [
                fact_payload(fact)
                for fact in facts_by_memory.get(memory.id, [])
            ],
        }
        for memory, score, why in similar
    ]
    exact_duplicate_id = exact_duplicate.id if exact_duplicate is not None else None
    if exact_duplicate_id and exact_duplicate_id not in [
        item["id"] for item in similar_payloads
    ]:
        similar_payloads.insert(
            0,
            {
                "id": exact_duplicate.id,
                "type": exact_duplicate.memory_type,
                "scope": exact_duplicate.scope,
                "status": exact_duplicate.status,
                "score": None,
                "why_relevant": "exact normalized text duplicate",
                "content": exact_duplicate.content,
                "facts": [
                    fact_payload(fact)
                    for fact in facts_by_memory.get(exact_duplicate.id, [])
                ],
            },
        )
    maintenance_assessment = _proposal_maintenance_assessment(
        proposed_action=action,
        risk=risk,
        policy=policy,
        similar_payloads=similar_payloads,
        matching_fact_ids=matching_fact_ids,
        conflicting_fact_ids=conflicting_fact_ids,
        candidate_facts=candidate_facts,
    )

    return {
        "proposed_action": action,
        "action_confidence": action_confidence,
        "risk": risk,
        "reason": reason,
        "write_policy": policy,
        "normalized_request": request.model_dump(mode="json"),
        "candidate_facts": candidate_facts,
        "matching_fact_ids": matching_fact_ids,
        "conflicting_fact_ids": conflicting_fact_ids,
        "similar_memories": similar_payloads,
        "similar_memory_ids": [item["id"] for item in similar_payloads],
        "related_fact_ids": sorted(set(matching_fact_ids + conflicting_fact_ids)),
        "retrieval_stages": ["fts5_sparse_v1", "lexical_fallback_v1", "atomic_fact_v1"],
        "maintenance_assessment": maintenance_assessment,
        "future_ready": {
            "embedding_vector_id": None,
            "graph_node_ids": [
                f"{fact['entity']}::{fact['predicate']}"
                for fact in candidate_facts
                if fact.get("entity") and fact.get("predicate")
            ],
        },
    }


def _transient_memory(request: MemoryWriteBody) -> MemoryRecord:
    return MemoryRecord(
        memory_type=request.memory_type,
        scope=request.scope,
        content=request.content,
        reason_for_storage=request.reason_for_storage,
        expected_future_use=request.expected_future_use,
        confidence=NEUTRAL_STORED_CONFIDENCE,
        salience=NEUTRAL_STORED_SALIENCE,
        tags_json=request.tags,
        metadata_json=request.metadata,
    )


def _candidate_fact_matches(
    candidate_facts: list[dict[str, Any]],
    facts_by_memory: dict[str, list[MemoryFact]],
) -> tuple[list[str], list[str]]:
    matching: list[str] = []
    conflicting: list[str] = []
    for candidate in candidate_facts:
        entity = candidate.get("entity")
        predicate = candidate.get("predicate")
        value = candidate.get("value")
        if not entity or not predicate:
            continue
        for facts in facts_by_memory.values():
            for fact in facts:
                if fact.status != "active":
                    continue
                if fact.entity != entity or fact.predicate != predicate:
                    continue
                if fact.value_json == value:
                    matching.append(fact.id)
                else:
                    conflicting.append(fact.id)
    return sorted(set(matching)), sorted(set(conflicting))


def _proposal_maintenance_assessment(
    *,
    proposed_action: str,
    risk: str,
    policy: dict[str, Any],
    similar_payloads: list[dict[str, Any]],
    matching_fact_ids: list[str],
    conflicting_fact_ids: list[str],
    candidate_facts: list[dict[str, Any]],
) -> dict[str, Any]:
    if proposed_action in {"reject_candidate", "noop_duplicate"}:
        lane = "deterministic_archive"
    elif proposed_action == "create_new":
        lane = "cautious_resolution"
    else:
        lane = "pending_review"

    review_focus: list[str] = []
    if not policy.get("accepted"):
        review_focus.append("write_policy")
    if matching_fact_ids:
        review_focus.append("duplicate_fact")
    elif proposed_action == "noop_duplicate":
        review_focus.append("duplicate_memory")
    if conflicting_fact_ids:
        review_focus.append("fact_conflict")
    if similar_payloads:
        review_focus.append("similarity_merge_update_or_duplicate")
    if candidate_facts:
        review_focus.append("canonical_fact_quality")
    if not review_focus:
        review_focus.append("new_memory_candidate")

    return {
        "policy_version": "maintenance_preflight_assessment_v1",
        "lane": lane,
        "risk": risk,
        "review_focus": review_focus,
        "counts": {
            "similar_memories": len(similar_payloads),
            "matching_facts": len(matching_fact_ids),
            "conflicting_facts": len(conflicting_fact_ids),
            "candidate_facts": len(candidate_facts),
        },
        "decision_policy": {
            "safe_deterministic": [
                "reject_candidate",
                "noop_duplicate",
            ],
            "cautious_resolution": ["create_new"],
            "pending_review": [
                "review_similar",
                "needs_review",
            ],
            "auto_apply_is_owned_by": "runtime.maintenance",
        },
    }


def _proposal_idempotency_key(
    *,
    context: MindAPIContext,
    source_trace_id: str,
    candidate_index: int,
    candidate_type: str,
    candidate_scope: str,
    content: str,
) -> str:
    source = "|".join(
        [
            context.session_id or "",
            context.turn_id or "",
            source_trace_id,
            str(candidate_index),
            candidate_type,
            candidate_scope,
            _normalize_memory_text(content),
        ]
    )
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:24]
    return f"memory_proposal:{digest}"


def _candidate_source_message_ids(candidate: dict[str, Any]) -> list[str]:
    for key in ("source_message_ids", "message_ids", "evidence_message_ids"):
        value = candidate.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, str)]
    value = candidate.get("source_message_id")
    if isinstance(value, str):
        return [value]
    return []


def _list_of_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _string(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None






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










def memory_proposal_payload(proposal: MemoryProposal) -> dict[str, Any]:
    return {
        "id": proposal.id,
        "status": proposal.status,
        "source": proposal.source,
        "proposed_action": proposal.proposed_action,
        "action_confidence": proposal.action_confidence,
        "risk": proposal.risk,
        "candidate": {
            "type": proposal.candidate_type,
            "scope": proposal.candidate_scope,
            "content": proposal.content,
            "reason_for_storage": proposal.reason_for_storage,
            "expected_future_use": proposal.expected_future_use,
            "tags": proposal.tags_json,
            "evidence": proposal.evidence,
            "facts": proposal.candidate_facts_json,
        },
        "source_session_id": proposal.source_session_id,
        "source_turn_id": proposal.source_turn_id,
        "source_trace_id": proposal.source_trace_id,
        "maintenance_job_id": proposal.maintenance_job_id,
        "source_message_ids": proposal.source_message_ids_json,
        "similar_memory_ids": proposal.similar_memory_ids_json,
        "related_fact_ids": proposal.related_fact_ids_json,
        "decision": proposal.decision_json,
        "result": proposal.result_json,
        "metadata": proposal.metadata_json,
        "created_at": _isoformat(proposal.created_at),
        "updated_at": _isoformat(proposal.updated_at),
        "applied_at": _isoformat(proposal.applied_at),
    }


def apply_create_memory_proposal(
    db: Session,
    *,
    proposal: MemoryProposal,
    resolver: str,
    reason: str,
    decision: dict[str, Any] | None = None,
) -> tuple[MemoryRecord, MemoryProposal]:
    resolution = {
        "resolver": resolver,
        "outcome": "apply_create",
        "reason": reason,
        "decision": decision or {},
        "decided_at": _isoformat(utc_now()),
    }
    metadata = {
        **(proposal.metadata_json or {}),
        "proposal_id": proposal.id,
        "proposal_origin": proposal.source,
        "maintenance_job_id": proposal.maintenance_job_id,
        "resolution": resolution,
    }
    memory = repositories.add_memory(
        db,
        memory_type=proposal.candidate_type,
        scope=proposal.candidate_scope,
        content=proposal.content,
        reason_for_storage=proposal.reason_for_storage,
        expected_future_use=proposal.expected_future_use,
        confidence=NEUTRAL_STORED_CONFIDENCE,
        salience=NEUTRAL_STORED_SALIENCE,
        created_by="maintenance",
        source_session_id=proposal.source_session_id,
        source_turn_id=proposal.source_turn_id,
        source_message_id=(
            proposal.source_message_ids_json[0]
            if proposal.source_message_ids_json
            else None
        ),
        tags=proposal.tags_json,
        metadata=metadata,
    )
    repositories.add_memory_activity(
        db,
        memory_id=memory.id,
        activity_kind="write",
        source="maintenance.proposal.apply_create",
        actor="maintenance",
        session_id=proposal.source_session_id,
        turn_id=proposal.source_turn_id,
        message_id=memory.source_message_id,
        trace_id=proposal.source_trace_id,
        metadata={"proposal_id": proposal.id},
    )
    facts, _ = _ensure_memory_facts(
        db,
        memory,
        source_trace_id=proposal.source_trace_id,
    )
    sync_memory_retrieval_artifacts(
        db,
        [memory],
        facts_by_memory={memory.id: facts},
    )
    memory_snapshot = _memory_payload(memory, facts=facts)
    resolved = repositories.resolve_memory_proposal(
        db,
        proposal_id=proposal.id,
        status="applied_create",
        result={
            "resolution": resolution,
            "memory_result": {
                "memory_id": memory.id,
                "memory_snapshot": memory_snapshot,
            },
            "preflight_snapshot": proposal.decision_json,
            "dream_review_candidate": True,
        },
    )
    if resolved is None:
        raise ValueError(f"Memory proposal not found after apply: {proposal.id}")
    return memory, resolved


def _ensure_memory_facts(
    db: Session,
    memory: MemoryRecord,
    *,
    source_trace_id: str | None = None,
) -> tuple[list[MemoryFact], list[MemoryFact]]:
    extracted = extract_memory_facts(memory)
    created: list[MemoryFact] = []
    for candidate in extracted:
        existing = repositories.find_memory_fact(
            db,
            memory_id=memory.id,
            entity=candidate.entity,
            predicate=candidate.predicate,
            value=candidate.value,
        )
        if existing is not None:
            continue
        created.append(
            repositories.add_memory_fact(
                db,
                memory_id=memory.id,
                entity=candidate.entity,
                predicate=candidate.predicate,
                value=candidate.value,
                source_trace_id=source_trace_id,
                source_session_id=memory.source_session_id,
                source_turn_id=memory.source_turn_id,
                confidence=candidate.confidence,
                salience=candidate.salience,
                status=memory.status,
                metadata=candidate.metadata,
            )
        )
    facts = repositories.list_memory_facts(
        db,
        memory_id=memory.id,
        include_inactive=True,
    )
    return facts, created




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
        if superseded_by not in memory_ids and repositories.get_memory(db, superseded_by) is None:
            continue
        repositories.update_memory_facts_status(
            db,
            memory_id=memory.id,
            status="deprecated",
            superseded_by_memory_id=superseded_by,
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


def _detect_active_memory_relations(
    memories: list[MemoryRecord],
    *,
    facts_by_memory: dict[str, list[MemoryFact]] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    facts_by_memory = facts_by_memory or {}
    conflicts = _detect_fact_conflicts(memories, facts_by_memory)

    conflict_memory_sets = {
        frozenset(conflict["memory_ids"])
        for conflict in conflicts
    }
    payloads = [
        _memory_payload(memory, facts=facts_by_memory.get(memory.id, []))
        for memory in memories
    ]
    related_overlaps: list[dict[str, Any]] = []
    corpus_token_sets = {
        payload["id"]: _subject_tokens(payload["content"])
        for payload in payloads
    }
    document_frequency = _token_document_frequency(corpus_token_sets.values())
    for left, right in combinations(payloads, 2):
        if frozenset([left["id"], right["id"]]) in conflict_memory_sets:
            continue
        duplicate_candidate = _normalize_memory_text(left["content"]) == _normalize_memory_text(
            right["content"]
        )
        shared_tags = sorted(set(left["tags"]) & set(right["tags"]))
        shared_tokens = sorted(
            corpus_token_sets[left["id"]] & corpus_token_sets[right["id"]]
        )
        overlap_score = _weighted_overlap_score(
            shared_tokens,
            document_frequency=document_frequency,
        )
        if not duplicate_candidate and not shared_tags and overlap_score < 1.5:
            continue
        related_overlaps.append(
            {
                "classification": "duplicate_candidate"
                if duplicate_candidate
                else "related_overlap",
                "basis": "exact_content"
                if duplicate_candidate
                else "tag_token_similarity",
                "confidence": 0.9 if duplicate_candidate else min(0.75, overlap_score / 4),
                "memory_ids": [left["id"], right["id"]],
                "memory_claims": _memory_claims(left, right),
                "shared_tags": shared_tags,
                "shared_tokens": shared_tokens[:12],
                "overlap_score": round(overlap_score, 4),
                "reason": (
                    "active memories may describe the same stored subject"
                    if duplicate_candidate
                    else "active memories share maintenance-level semantic overlap"
                ),
            }
        )
    return {
        "conflicts": conflicts,
        "related_overlaps": related_overlaps,
    }


def _conflict_counts(conflicts: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for conflict in conflicts:
        key = str(conflict.get("classification") or conflict.get("basis") or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return counts


def _detect_fact_conflicts(
    memories: list[MemoryRecord],
    facts_by_memory: dict[str, list[MemoryFact]],
) -> list[dict[str, Any]]:
    memories_by_id = {memory.id: memory for memory in memories}
    active_facts = [
        fact
        for facts in facts_by_memory.values()
        for fact in facts
        if fact.status == "active"
    ]
    conflicts: list[dict[str, Any]] = []
    grouped: dict[tuple[str, str], list[MemoryFact]] = {}
    for fact in active_facts:
        grouped.setdefault((fact.entity, fact.predicate), []).append(fact)

    for (entity, predicate), facts in grouped.items():
        memory_ids = sorted({fact.memory_id for fact in facts})
        values = { _normalize_fact_value(fact.value_json) for fact in facts }
        if len(memory_ids) < 2 or len(values) < 2:
            continue
        memory_payloads = [
            _memory_payload(
                memories_by_id[memory_id],
                facts=facts_by_memory.get(memory_id, []),
            )
            for memory_id in memory_ids
            if memory_id in memories_by_id
        ]
        conflicts.append(
            {
                "classification": "atomic_fact_conflict",
                "basis": "atomic_fact",
                "confidence": 0.95,
                "entity": entity,
                "predicate": predicate,
                "fact_ids": [fact.id for fact in facts],
                "memory_ids": memory_ids,
                "memory_claims": [
                    {
                        "id": memory.get("id"),
                        "content": memory.get("content"),
                        "source_session_id": memory.get("source_session_id"),
                        "source_turn_id": memory.get("source_turn_id"),
                    }
                    for memory in memory_payloads
                ],
                "values": [fact.value_json for fact in facts],
                "reason": (
                    "active facts share entity and predicate but have "
                    "different values"
                ),
            }
        )
    return conflicts


def _memory_claims(*payloads: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": payload.get("id"),
            "content": payload.get("content"),
            "source_session_id": payload.get("source_session_id"),
            "source_turn_id": payload.get("source_turn_id"),
        }
        for payload in payloads
    ]


def _token_document_frequency(token_sets: Any) -> dict[str, int]:
    frequency: dict[str, int] = {}
    for tokens in token_sets:
        for token in tokens:
            frequency[token] = frequency.get(token, 0) + 1
    return frequency


def _weighted_overlap_score(
    shared_tokens: list[str],
    *,
    document_frequency: dict[str, int],
) -> float:
    score = 0.0
    for token in shared_tokens:
        frequency = max(document_frequency.get(token, 1), 1)
        score += 1 / frequency
    return score


def _normalize_fact_value(value: dict[str, Any]) -> str:
    return repr(sorted(value.items()))


def _subject_tokens(value: str) -> set[str]:
    return {
        token
        for token in _tokens(value)
        if token not in _generic_conflict_tokens() and len(token) > 2
    }


def _generic_conflict_tokens() -> set[str]:
    return {
        "a",
        "and",
        "che",
        "con",
        "di",
        "e",
        "il",
        "in",
        "la",
        "memoria",
        "memory",
        "protocol",
        "protocollo",
        "the",
    }


def _normalize_memory_text(value: str) -> str:
    return " ".join(value.casefold().split())




def _backend_memory_metadata_from_write(request: MemoryWriteBody) -> dict[str, Any]:
    ignored: dict[str, Any] = {}
    if request.confidence is not None:
        ignored["confidence"] = request.confidence
    if request.salience is not None:
        ignored["salience"] = request.salience
    if request.tags:
        ignored["tags"] = request.tags
    if request.metadata:
        ignored["metadata"] = request.metadata
    return {
        "write_policy": "backend_owned_dynamic_retrieval_scores_v1",
        "agent_supplied_fields_ignored_for_ranking": ignored,
    }




def _tokens(value: str) -> list[str]:
    return re.findall(r"\w+", value.casefold())
