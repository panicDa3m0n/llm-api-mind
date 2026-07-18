import hashlib
from typing import Any

from pydantic import ValidationError
from sqlmodel import Session

from app.mind.contracts import MindAPIContext
from app.mind.facts import extracted_fact_payload, extract_memory_facts, fact_payload
from app.mind.memory_read import _facts_by_memory, _score_memories
from app.mind.memory_shared import (
    DEFAULT_MEMORY_SCOPE,
    _isoformat,
    _memory_payload,
    _normalize_memory_text,
)
from app.mind.memory_write import (
    NEUTRAL_STORED_CONFIDENCE,
    NEUTRAL_STORED_SALIENCE,
    MemoryWriteBody,
    _ensure_memory_facts,
    _evaluate_write_policy,
    _find_duplicate,
)
from app.mind.search import (
    search_documents,
    sparse_results_by_source,
    sync_memory_documents,
    sync_memory_retrieval_artifacts,
)
from app.storage import repositories
from app.storage.models import MemoryFact, MemoryProposal, MemoryRecord, utc_now


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
        decision: dict[str, Any] = {
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
                fact_payload(fact) for fact in facts_by_memory.get(memory.id, [])
            ],
        }
        for memory, score, why in similar
    ]
    exact_duplicate_id = exact_duplicate.id if exact_duplicate is not None else None
    if exact_duplicate is not None and exact_duplicate_id not in [
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
