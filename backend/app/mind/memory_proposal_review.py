from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from sqlmodel import Session

from app.mind.contracts import MindAPIContext, MemoryOperationResult
from app.mind.memory_lifecycle import handle_memory_supersede
from app.mind.memory_proposals import memory_proposal_payload
from app.mind.memory_shared import (
    _context_required,
    _isoformat,
    _memory_payload,
)
from app.mind.memory_write import (
    MemoryWriteSource,
    handle_memory_write,
)
from app.storage import repositories
from app.storage.models import MemoryProposal, utc_now


ProposalDecision = Literal["accept", "reject", "duplicate", "supersede"]


class MemoryProposalListBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = Field(default="open", min_length=1, max_length=40)
    limit: int = Field(default=10, ge=1, le=50)
    offset: int = Field(default=0, ge=0)


class MemoryProposalDecisionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_id: str = Field(min_length=1, max_length=80)
    decision: ProposalDecision
    reason: str = Field(min_length=8, max_length=1000)
    target_memory_id: str | None = Field(default=None, max_length=80)
    memory_type: str | None = Field(default=None, alias="type", max_length=80)
    scope: str | None = Field(default=None, max_length=80)
    content: str | None = Field(default=None, min_length=12, max_length=4000)
    expected_future_use: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_target(self) -> "MemoryProposalDecisionBody":
        if self.decision in {"duplicate", "supersede"} and not self.target_memory_id:
            raise ValueError(
                f"{self.decision} requires target_memory_id selected by Scarlet."
            )
        if self.decision in {"accept", "reject"} and self.target_memory_id:
            raise ValueError(
                f"{self.decision} does not accept target_memory_id."
            )
        return self


def handle_memory_proposal_list(
    body: dict[str, Any],
    context: MindAPIContext | None,
) -> MemoryOperationResult:
    if context is None or context.session_id is None:
        return _context_required("proposals")
    try:
        request = MemoryProposalListBody.model_validate(body)
    except ValidationError as exc:
        return _proposal_error(
            code="memory.invalid_proposal_list",
            message=str(exc),
            actions=["memory proposals --status open --limit 10"],
        )

    status, statuses = _proposal_status_filter(request.status)
    with Session(context.engine) as db:
        proposals = repositories.list_memory_proposals(
            db,
            status=status,
            statuses=statuses,
            limit=request.limit + 1,
            offset=request.offset,
        )
        has_more = len(proposals) > request.limit
        visible = proposals[: request.limit]
        trace = repositories.add_trace(
            db,
            session_id=context.session_id,
            turn_id=context.turn_id,
            kind="mind.memory.proposals.list",
            payload={
                "operation": "memory.proposals.list",
                "status": request.status,
                "returned": len(visible),
                "has_more": has_more,
                "proposal_ids": [proposal.id for proposal in visible],
            },
        )
        proposal_hints = [_proposal_hint(proposal) for proposal in visible]
        trace_id = trace.id

    return MemoryOperationResult(
        ok=True,
        result={
            "operation": "memory.proposals.list",
            "status": request.status,
            "returned": len(visible),
            "has_more": has_more,
            "next_offset": request.offset + request.limit if has_more else None,
            "proposals": proposal_hints,
            "trace_ids": [trace_id],
        },
        cognitive_hint=(
            "These are source-backed memory candidates, not memories. Open the "
            "proposal and its sources before making a semantic decision."
        ),
        suggested_next_actions=["memory proposal prop_..."],
        confidence=1.0,
    )


def handle_memory_proposal_read(
    proposal_id: str,
    context: MindAPIContext | None,
) -> MemoryOperationResult:
    if context is None or context.session_id is None:
        return _context_required("proposal")
    with Session(context.engine) as db:
        proposal = repositories.get_memory_proposal(db, proposal_id)
        if proposal is None:
            return _proposal_not_found(proposal_id)
        similar_memories = [
            memory
            for memory_id in proposal.similar_memory_ids_json
            if (memory := repositories.get_memory(db, memory_id)) is not None
        ]
        trace = repositories.add_trace(
            db,
            session_id=context.session_id,
            turn_id=context.turn_id,
            kind="mind.memory.proposal.read",
            payload={
                "operation": "memory.proposal.read",
                "proposal_id": proposal.id,
                "status": proposal.status,
                "similar_memory_ids": [
                    memory.id for memory in similar_memories
                ],
            },
        )
        payload = _proposal_for_scarlet(
            proposal,
            similar_memories=[
                _memory_payload(memory) for memory in similar_memories
            ],
        )
        trace_id = trace.id

    return MemoryOperationResult(
        ok=True,
        result={
            "operation": "memory.proposal.read",
            "proposal": payload,
            "trace_ids": [trace_id],
        },
        cognitive_hint=(
            "The proposal is only a candidate. Use its session, turn, message, "
            "and related-memory hooks to judge it before deciding."
        ),
        suggested_next_actions=_decision_actions(proposal),
        confidence=1.0,
    )


def handle_memory_proposal_decide(
    body: dict[str, Any],
    context: MindAPIContext | None,
    *,
    intent: str | None = None,
) -> MemoryOperationResult:
    if context is None or context.session_id is None:
        return _context_required("proposal decision")

    body_with_intent = dict(body)
    if "reason" not in body_with_intent and intent:
        body_with_intent["reason"] = intent
    try:
        request = MemoryProposalDecisionBody.model_validate(body_with_intent)
    except ValidationError as exc:
        return _proposal_error(
            code="memory.invalid_proposal_decision",
            message=str(exc),
            actions=["help memory", "memory proposal prop_..."],
        )

    with Session(context.engine) as db:
        proposal = repositories.get_memory_proposal(db, request.proposal_id)
        if proposal is None:
            return _proposal_not_found(request.proposal_id)
        if proposal.status not in repositories.OPEN_MEMORY_PROPOSAL_STATUSES:
            return _proposal_error(
                code="memory.proposal_already_resolved",
                message=(
                    f"Proposal {proposal.id} is already in terminal status "
                    f"{proposal.status}."
                ),
                actions=[f"memory proposal {proposal.id}"],
                recoverable=False,
            )
        proposal_snapshot = memory_proposal_payload(proposal)

    if request.decision == "reject":
        return _complete_proposal_decision(
            context=context,
            proposal_snapshot=proposal_snapshot,
            request=request,
            status="rejected_by_scarlet",
            outcome={"memory_id": None},
        )

    if request.decision == "duplicate":
        assert request.target_memory_id is not None
        with Session(context.engine) as db:
            target = repositories.get_memory(db, request.target_memory_id)
            if target is None:
                return _proposal_error(
                    code="memory.proposal_target_not_found",
                    message=f"Memory {request.target_memory_id} was not found.",
                    actions=["memory search \"related memory\" --top 5"],
                )
        return _complete_proposal_decision(
            context=context,
            proposal_snapshot=proposal_snapshot,
            request=request,
            status="resolved_duplicate",
            outcome={"memory_id": target.id, "existing_memory": _memory_payload(target)},
        )

    proposal_candidate = proposal_snapshot["candidate"]
    write_body = {
        "type": request.memory_type or proposal_candidate["type"],
        "scope": request.scope or proposal_candidate["scope"],
        "content": request.content or proposal_candidate["content"],
        "reason_for_storage": proposal_candidate["reason_for_storage"],
        "expected_future_use": (
            request.expected_future_use
            if request.expected_future_use is not None
            else proposal_candidate.get("expected_future_use")
        ),
    }
    source_message_ids = proposal_snapshot.get("source_message_ids") or []
    write_result = handle_memory_write(
        write_body,
        context,
        intent=request.reason,
        source=MemoryWriteSource(
            session_id=proposal_snapshot.get("source_session_id"),
            turn_id=proposal_snapshot.get("source_turn_id"),
            message_id=source_message_ids[0] if source_message_ids else None,
            metadata={
                "proposal_id": request.proposal_id,
                "accepted_by_session_id": context.session_id,
                "accepted_by_turn_id": context.turn_id,
            },
        ),
    )
    if not write_result.ok:
        return write_result
    memory_id = str(write_result.result["memory_id"])

    if request.decision == "supersede":
        assert request.target_memory_id is not None
        if request.target_memory_id == memory_id:
            return _proposal_error(
                code="memory.proposal_invalid_supersession",
                message=(
                    "The proposal resolved to the same memory selected for "
                    "supersession. Choose duplicate or a different old memory."
                ),
                actions=[
                    (
                        f"memory proposal-duplicate {request.proposal_id} "
                        f"{memory_id} --reason \"...\""
                    )
                ],
            )
        lifecycle = handle_memory_supersede(
            {
                "old_memory_id": request.target_memory_id,
                "new_memory_id": memory_id,
                "reason": request.reason,
                "deprecate_old": True,
            },
            context,
            intent=request.reason,
        )
        if not lifecycle.ok:
            return lifecycle
        return _complete_proposal_decision(
            context=context,
            proposal_snapshot=proposal_snapshot,
            request=request,
            status="accepted_supersede",
            outcome={
                "memory_id": memory_id,
                "stored": write_result.result.get("stored"),
                "superseded_memory_id": request.target_memory_id,
                "write_trace_ids": write_result.result.get("trace_ids", []),
                "lifecycle_trace_ids": lifecycle.result.get("trace_ids", []),
            },
        )

    status = (
        "accepted_create"
        if write_result.result.get("stored")
        else "resolved_duplicate"
    )
    return _complete_proposal_decision(
        context=context,
        proposal_snapshot=proposal_snapshot,
        request=request,
        status=status,
        outcome={
            "memory_id": memory_id,
            "stored": write_result.result.get("stored"),
            "write_trace_ids": write_result.result.get("trace_ids", []),
        },
    )


def _complete_proposal_decision(
    *,
    context: MindAPIContext,
    proposal_snapshot: dict[str, Any],
    request: MemoryProposalDecisionBody,
    status: str,
    outcome: dict[str, Any],
) -> MemoryOperationResult:
    with Session(context.engine) as db:
        proposal = repositories.get_memory_proposal(db, request.proposal_id)
        if proposal is None:
            return _proposal_not_found(request.proposal_id)
        if proposal.status not in repositories.OPEN_MEMORY_PROPOSAL_STATUSES:
            return _proposal_error(
                code="memory.proposal_already_resolved",
                message=(
                    f"Proposal {proposal.id} was resolved concurrently as "
                    f"{proposal.status}."
                ),
                actions=[f"memory proposal {proposal.id}"],
                recoverable=False,
            )
        trace = repositories.add_trace(
            db,
            session_id=context.session_id or "",
            turn_id=context.turn_id,
            kind="mind.memory.proposal.decide",
            payload={
                "operation": "memory.proposal.decide",
                "proposal_id": proposal.id,
                "decision": request.decision,
                "reason": request.reason,
                "target_memory_id": request.target_memory_id,
                "outcome": outcome,
                "semantic_authority": "scarlet",
            },
        )
        trace_id = trace.id
        result = {
            "resolution": {
                "resolver": "scarlet",
                "semantic_authority": True,
                "decision": request.decision,
                "reason": request.reason,
                "target_memory_id": request.target_memory_id,
                "outcome": outcome,
                "decision_session_id": context.session_id,
                "decision_turn_id": context.turn_id,
                "trace_id": trace_id,
                "decided_at": _isoformat(utc_now()),
            },
            "preflight_snapshot": proposal_snapshot.get("decision", {}),
            "prior_review": proposal_snapshot.get("result", {}),
        }
        resolved = repositories.resolve_memory_proposal(
            db,
            proposal_id=proposal.id,
            status=status,
            result=result,
        )
        assert resolved is not None
        resolved_payload = _proposal_for_scarlet(resolved)

    return MemoryOperationResult(
        ok=True,
        result={
            "operation": "memory.proposal.decide",
            "proposal": resolved_payload,
            "decision": request.decision,
            "status": status,
            "outcome": outcome,
            "trace_ids": [trace_id],
        },
        cognitive_hint=(
            "Scarlet's semantic decision was persisted with its source "
            "proposal, evidence hooks, lifecycle result, and decision trace."
        ),
        suggested_next_actions=(
            [f"memory open {outcome['memory_id']}"]
            if outcome.get("memory_id")
            else ["memory proposals --status open --limit 10"]
        ),
        confidence=1.0,
    )


def _proposal_status_filter(
    requested: str,
) -> tuple[str | None, list[str] | None]:
    normalized = requested.strip().casefold()
    if normalized == "open":
        return None, sorted(repositories.OPEN_MEMORY_PROPOSAL_STATUSES)
    if normalized == "resolved":
        return None, sorted(repositories.RESOLVED_MEMORY_PROPOSAL_STATUSES)
    if normalized in {"all", "any", "*"}:
        return None, None
    return requested, None


def _proposal_hint(proposal: MemoryProposal) -> dict[str, Any]:
    review = proposal.result_json.get("resolution", {})
    decision = review.get("decision", {})
    return {
        "id": proposal.id,
        "status": proposal.status,
        "candidate": {
            "type": proposal.candidate_type,
            "scope": proposal.candidate_scope,
            "content": proposal.content,
        },
        "source_session_id": proposal.source_session_id,
        "source_turn_id": proposal.source_turn_id,
        "source_message_ids": proposal.source_message_ids_json,
        "similar_memory_ids": proposal.similar_memory_ids_json,
        "maintenance_recommendation": (
            decision.get("recommendation") if isinstance(decision, dict) else None
        ),
        "created_at": _isoformat(proposal.created_at),
        "updated_at": _isoformat(proposal.updated_at),
    }


def _proposal_for_scarlet(
    proposal: MemoryProposal,
    *,
    similar_memories: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    payload = _proposal_hint(proposal)
    payload["candidate"].update(
        {
            "reason_for_storage": proposal.reason_for_storage,
            "expected_future_use": proposal.expected_future_use,
            "evidence": proposal.evidence,
        }
    )
    payload["similar_memories"] = similar_memories or []
    payload["resolution"] = proposal.result_json.get("resolution")
    return payload


def _decision_actions(proposal: MemoryProposal) -> list[str]:
    if proposal.status not in repositories.OPEN_MEMORY_PROPOSAL_STATUSES:
        return ["memory proposals --status open --limit 10"]
    return [
        f'memory proposal-accept {proposal.id} --reason "..."',
        f'memory proposal-reject {proposal.id} --reason "..."',
        (
            f"memory proposal-duplicate {proposal.id} mem_... "
            '--reason "..."'
        ),
        (
            f"memory proposal-supersede {proposal.id} mem_old "
            '--reason "..."'
        ),
    ]


def _proposal_not_found(proposal_id: str) -> MemoryOperationResult:
    return _proposal_error(
        code="memory.proposal_not_found",
        message=f"Memory proposal {proposal_id} was not found.",
        actions=["memory proposals --status open --limit 10"],
    )


def _proposal_error(
    *,
    code: str,
    message: str,
    actions: list[str],
    recoverable: bool = True,
) -> MemoryOperationResult:
    return MemoryOperationResult(
        ok=False,
        error_code=code,
        error_message=message,
        error_recoverable=recoverable,
        suggested_next_actions=actions,
        confidence=1.0,
    )
