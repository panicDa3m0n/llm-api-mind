import hashlib
from typing import Any

from pydantic import ValidationError
from sqlmodel import Session

from app.mind.contracts import MindAPIContext
from app.mind.memory_shared import (
    DEFAULT_MEMORY_SCOPE,
    _isoformat,
    _normalize_memory_text,
    score_memory_candidates,
)
from app.mind.memory_write import (
    NEUTRAL_STORED_CONFIDENCE,
    NEUTRAL_STORED_SALIENCE,
    MemoryWriteBody,
    _evaluate_write_policy,
    _find_duplicate,
)
from app.mind.search import (
    search_documents,
    sparse_results_by_source,
    sync_memory_documents,
)
from app.storage import repositories
from app.storage.models import MemoryProposal


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
            "proposed_action": "needs_semantic_review",
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
            proposed_action="needs_semantic_review",
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
    candidates = repositories.list_memories(
        db,
        scope=None,
        include_low_confidence=True,
    )
    facts_by_memory: dict[str, list[Any]] = {}
    sync_memory_documents(db, candidates, facts_by_memory=facts_by_memory)
    sparse_matches = sparse_results_by_source(
        search_documents(
            db,
            query=request.content,
            kind="memory",
            limit=50,
        )
    )
    scored = score_memory_candidates(
        candidates,
        request.content,
        facts_by_memory=facts_by_memory,
        sparse_matches=sparse_matches,
    )
    similar = scored[:5]
    exact_duplicate = _find_duplicate(db, request)

    if not policy["accepted"]:
        action = "reject_candidate"
        action_confidence = 1.0
        risk = "low"
        reason = policy["reason"]
    elif exact_duplicate is not None:
        action = "noop_duplicate"
        action_confidence = 1.0
        risk = "low"
        reason = "an exact normalized active-memory duplicate already exists"
    elif similar:
        action = "review_similar"
        action_confidence = 0.0
        risk = "medium"
        reason = "retrieval found related memories; semantic review is required"
    else:
        action = "needs_semantic_review"
        action_confidence = 0.0
        risk = "medium"
        reason = "candidate passed structural checks and awaits Scarlet's judgment"

    similar_payloads = [
        {
            "id": memory.id,
            "type": memory.memory_type,
            "scope": memory.scope,
            "status": memory.status,
            "score": round(score, 4),
            "why_relevant": why,
            "content": memory.content,
            "facts": [],
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
                "facts": [],
            },
        )
    maintenance_assessment = _proposal_maintenance_assessment(
        proposed_action=action,
        risk=risk,
        policy=policy,
        similar_payloads=similar_payloads,
    )

    return {
        "proposed_action": action,
        "action_confidence": action_confidence,
        "risk": risk,
        "reason": reason,
        "write_policy": policy,
        "normalized_request": request.model_dump(mode="json"),
        "similar_memories": similar_payloads,
        "similar_memory_ids": [item["id"] for item in similar_payloads],
        "retrieval_stages": ["fts5_sparse_v1", "lexical_fallback_v1"],
        "maintenance_assessment": maintenance_assessment,
        "future_ready": {
            "embedding_vector_id": None,
            "graph_node_ids": [],
        },
    }


def _proposal_maintenance_assessment(
    *,
    proposed_action: str,
    risk: str,
    policy: dict[str, Any],
    similar_payloads: list[dict[str, Any]],
) -> dict[str, Any]:
    if proposed_action in {"reject_candidate", "noop_duplicate"}:
        lane = "deterministic_archive"
    elif proposed_action == "needs_semantic_review":
        lane = "semantic_review"
    else:
        lane = "pending_review"

    review_focus: list[str] = []
    if not policy.get("accepted"):
        review_focus.append("write_policy")
    if proposed_action == "noop_duplicate":
        review_focus.append("duplicate_memory")
    if similar_payloads:
        review_focus.append("similarity_merge_update_or_duplicate")
    if not review_focus:
        review_focus.append("new_memory_candidate")

    return {
        "policy_version": "maintenance_preflight_assessment_v1",
        "lane": lane,
        "risk": risk,
        "review_focus": review_focus,
        "counts": {
            "similar_memories": len(similar_payloads),
        },
        "decision_policy": {
            "safe_deterministic": [
                "reject_candidate",
                "noop_duplicate",
            ],
            "semantic_review": ["needs_semantic_review", "review_similar"],
            "pending_review": [
                "review_similar",
                "needs_semantic_review",
            ],
            "semantic_authority": "scarlet",
            "auto_apply_enabled": False,
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
