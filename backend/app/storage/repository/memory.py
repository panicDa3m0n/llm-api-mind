"""Persistence operations for canonical memories, facts, and proposal lifecycle."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlmodel import Session, select

from app.storage.models import (
    MemoryActivity,
    MemoryFact,
    MemoryProposal,
    MemoryRecord,
    utc_now,
)
from app.storage.repository._shared import touch_session as _touch_session


RESOLVED_MEMORY_PROPOSAL_STATUSES = {
    "applied_create",
    "archived_manual",
    "archived_noop_duplicate",
    "archived_rejected",
    "pending_review",
}


def add_memory_activity(
    db: Session,
    *,
    memory_id: str,
    activity_kind: str,
    source: str,
    profile_id: str | None = None,
    actor: str = "scarlet",
    session_id: str | None = None,
    turn_id: str | None = None,
    message_id: str | None = None,
    trace_id: str | None = None,
    eligible_for_recent: bool = True,
    metadata: dict[str, Any] | None = None,
) -> MemoryActivity:
    activity = MemoryActivity(
        memory_id=memory_id,
        activity_kind=activity_kind,
        profile_id=profile_id,
        actor=actor,
        source=source,
        session_id=session_id,
        turn_id=turn_id,
        message_id=message_id,
        trace_id=trace_id,
        eligible_for_recent=eligible_for_recent,
        metadata_json=metadata or {},
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


def list_memory_activities(
    db: Session,
    *,
    memory_id: str | None = None,
    eligible_for_recent: bool | None = None,
    limit: int | None = None,
) -> list[MemoryActivity]:
    statement = select(MemoryActivity)
    if memory_id is not None:
        statement = statement.where(MemoryActivity.memory_id == memory_id)
    if eligible_for_recent is not None:
        statement = statement.where(
            MemoryActivity.eligible_for_recent == eligible_for_recent
        )
    statement = statement.order_by(
        MemoryActivity.occurred_at.desc(),
        MemoryActivity.id.desc(),
    )
    if limit is not None:
        statement = statement.limit(limit)
    return list(db.exec(statement).all())


def list_recent_memories_by_activity(
    db: Session,
    *,
    scope: str | None = None,
    exclude_memory_ids: set[str] | None = None,
    limit: int = 5,
) -> list[MemoryRecord]:
    """Return active memories ordered by meaningful use, then creation time."""

    if limit <= 0:
        return []
    excluded = exclude_memory_ids or set()
    latest_activity = (
        select(
            MemoryActivity.memory_id.label("memory_id"),
            func.max(MemoryActivity.occurred_at).label("last_activity_at"),
        )
        .where(MemoryActivity.eligible_for_recent == True)  # noqa: E712
        .group_by(MemoryActivity.memory_id)
        .subquery()
    )
    statement = (
        select(MemoryRecord)
        .join(latest_activity, latest_activity.c.memory_id == MemoryRecord.id)
        .where(MemoryRecord.status == "active")
        .order_by(
            latest_activity.c.last_activity_at.desc(),
            MemoryRecord.created_at.desc(),
            MemoryRecord.id.desc(),
        )
    )
    if scope is not None:
        statement = statement.where(MemoryRecord.scope == scope)
    if excluded:
        statement = statement.where(MemoryRecord.id.notin_(excluded))
    recent = list(db.exec(statement.limit(limit)).all())
    if len(recent) >= limit:
        return recent

    selected_ids = excluded | {memory.id for memory in recent}
    fallback = select(MemoryRecord).where(MemoryRecord.status == "active")
    if scope is not None:
        fallback = fallback.where(MemoryRecord.scope == scope)
    if selected_ids:
        fallback = fallback.where(MemoryRecord.id.notin_(selected_ids))
    fallback = fallback.order_by(
        MemoryRecord.created_at.desc(),
        MemoryRecord.id.desc(),
    ).limit(limit - len(recent))
    return recent + list(db.exec(fallback).all())

def add_memory(
    db: Session,
    *,
    memory_type: str,
    content: str,
    reason_for_storage: str,
    expected_future_use: str | None = None,
    confidence: float = 0.7,
    salience: float = 0.7,
    scope: str = "project",
    created_by: str = "scarlet",
    source_session_id: str | None = None,
    source_turn_id: str | None = None,
    source_message_id: str | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> MemoryRecord:
    memory = MemoryRecord(
        memory_type=memory_type,
        content=content,
        reason_for_storage=reason_for_storage,
        expected_future_use=expected_future_use,
        confidence=confidence,
        salience=salience,
        scope=scope,
        created_by=created_by,
        source_session_id=source_session_id,
        source_turn_id=source_turn_id,
        source_message_id=source_message_id,
        tags_json=tags or [],
        metadata_json=metadata or {},
    )
    db.add(memory)
    if source_session_id is not None:
        _touch_session(db, source_session_id)
    db.commit()
    db.refresh(memory)
    return memory


def add_memory_fact(
    db: Session,
    *,
    memory_id: str,
    entity: str,
    predicate: str,
    value: dict[str, Any],
    valid_from: datetime | None = None,
    valid_to: datetime | None = None,
    source_trace_id: str | None = None,
    source_session_id: str | None = None,
    source_turn_id: str | None = None,
    confidence: float = 0.7,
    salience: float = 0.7,
    status: str = "active",
    supersedes_fact_id: str | None = None,
    superseded_by_fact_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> MemoryFact:
    fact = MemoryFact(
        memory_id=memory_id,
        entity=entity,
        predicate=predicate,
        value_json=value,
        valid_from=valid_from,
        valid_to=valid_to,
        source_trace_id=source_trace_id,
        source_session_id=source_session_id,
        source_turn_id=source_turn_id,
        confidence=confidence,
        salience=salience,
        status=status,
        supersedes_fact_id=supersedes_fact_id,
        superseded_by_fact_id=superseded_by_fact_id,
        metadata_json=metadata or {},
    )
    db.add(fact)
    if source_session_id is not None:
        _touch_session(db, source_session_id)
    db.commit()
    db.refresh(fact)
    return fact


def find_memory_fact(
    db: Session,
    *,
    memory_id: str,
    entity: str,
    predicate: str,
    value: dict[str, Any],
) -> MemoryFact | None:
    statement = (
        select(MemoryFact)
        .where(MemoryFact.memory_id == memory_id)
        .where(MemoryFact.entity == entity)
        .where(MemoryFact.predicate == predicate)
    )
    for fact in db.exec(statement).all():
        if fact.value_json == value:
            return fact
    return None


def list_memory_facts(
    db: Session,
    *,
    memory_id: str | None = None,
    entity: str | None = None,
    predicate: str | None = None,
    status: str = "active",
    include_inactive: bool = False,
) -> list[MemoryFact]:
    statement = select(MemoryFact)
    if memory_id is not None:
        statement = statement.where(MemoryFact.memory_id == memory_id)
    if entity is not None:
        statement = statement.where(MemoryFact.entity == entity)
    if predicate is not None:
        statement = statement.where(MemoryFact.predicate == predicate)
    if not include_inactive:
        statement = statement.where(MemoryFact.status == status)
    statement = statement.order_by(
        MemoryFact.recorded_at.desc(),
        MemoryFact.id,
    )
    return list(db.exec(statement).all())


def upsert_memory_proposal(
    db: Session,
    *,
    idempotency_key: str,
    source: str,
    proposed_action: str,
    action_confidence: float,
    risk: str,
    candidate_type: str,
    candidate_scope: str,
    content: str,
    reason_for_storage: str,
    expected_future_use: str | None = None,
    confidence: float = 0.7,
    salience: float = 0.7,
    evidence: str | None = None,
    source_session_id: str | None = None,
    source_turn_id: str | None = None,
    source_trace_id: str | None = None,
    maintenance_job_id: str | None = None,
    source_message_ids: list[str] | None = None,
    tags: list[str] | None = None,
    similar_memory_ids: list[str] | None = None,
    related_fact_ids: list[str] | None = None,
    candidate_facts: list[dict[str, Any]] | None = None,
    decision: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> tuple[MemoryProposal, bool]:
    existing = get_memory_proposal_by_idempotency_key(
        db,
        idempotency_key=idempotency_key,
    )
    if existing is not None:
        return existing, False

    proposal = MemoryProposal(
        idempotency_key=idempotency_key,
        source=source,
        proposed_action=proposed_action,
        action_confidence=action_confidence,
        risk=risk,
        candidate_type=candidate_type,
        candidate_scope=candidate_scope,
        content=content,
        reason_for_storage=reason_for_storage,
        expected_future_use=expected_future_use,
        confidence=confidence,
        salience=salience,
        evidence=evidence,
        source_session_id=source_session_id,
        source_turn_id=source_turn_id,
        source_trace_id=source_trace_id,
        maintenance_job_id=maintenance_job_id,
        source_message_ids_json=source_message_ids or [],
        tags_json=tags or [],
        similar_memory_ids_json=similar_memory_ids or [],
        related_fact_ids_json=related_fact_ids or [],
        candidate_facts_json=candidate_facts or [],
        decision_json=decision or {},
        metadata_json=metadata or {},
    )
    db.add(proposal)
    if source_session_id is not None:
        _touch_session(db, source_session_id)
    db.commit()
    db.refresh(proposal)
    return proposal, True


def get_memory_proposal(
    db: Session,
    proposal_id: str,
) -> MemoryProposal | None:
    return db.get(MemoryProposal, proposal_id)


def get_memory_proposal_by_idempotency_key(
    db: Session,
    *,
    idempotency_key: str,
) -> MemoryProposal | None:
    statement = select(MemoryProposal).where(
        MemoryProposal.idempotency_key == idempotency_key
    )
    return db.exec(statement).first()


def list_memory_proposals(
    db: Session,
    *,
    status: str | None = "pending",
    statuses: list[str] | None = None,
    source_session_id: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    resolved_from: datetime | None = None,
    resolved_to: datetime | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[MemoryProposal]:
    statement = select(MemoryProposal)
    if statuses is not None:
        statement = statement.where(MemoryProposal.status.in_(statuses))
    elif status is not None:
        statement = statement.where(MemoryProposal.status == status)
    if source_session_id is not None:
        statement = statement.where(
            MemoryProposal.source_session_id == source_session_id
        )
    if created_from is not None:
        statement = statement.where(MemoryProposal.created_at >= created_from)
    if created_to is not None:
        statement = statement.where(MemoryProposal.created_at <= created_to)
    if resolved_from is not None:
        statement = statement.where(MemoryProposal.applied_at >= resolved_from)
    if resolved_to is not None:
        statement = statement.where(MemoryProposal.applied_at <= resolved_to)
    statement = (
        statement.order_by(
            MemoryProposal.created_at.desc(),
            MemoryProposal.id,
        )
        .offset(offset)
        .limit(limit)
    )
    return list(db.exec(statement).all())


def resolve_memory_proposal(
    db: Session,
    *,
    proposal_id: str,
    status: str,
    result: dict[str, Any] | None = None,
) -> MemoryProposal | None:
    proposal = get_memory_proposal(db, proposal_id)
    if proposal is None:
        return None

    now = utc_now()
    proposal.status = status
    proposal.result_json = result or {}
    proposal.applied_at = now
    proposal.updated_at = now
    if proposal.source_session_id is not None:
        _touch_session(db, proposal.source_session_id, at=now)
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return proposal


def archive_memory_proposal(
    db: Session,
    *,
    proposal_id: str,
    result: dict[str, Any] | None = None,
) -> MemoryProposal | None:
    return resolve_memory_proposal(
        db,
        proposal_id=proposal_id,
        status="archived_manual",
        result=result,
    )


def update_memory_facts_status(
    db: Session,
    *,
    memory_id: str,
    status: str,
    superseded_by_memory_id: str | None = None,
) -> list[MemoryFact]:
    facts = list_memory_facts(db, memory_id=memory_id, include_inactive=True)
    replacement_facts = (
        list_memory_facts(
            db,
            memory_id=superseded_by_memory_id,
            include_inactive=True,
        )
        if superseded_by_memory_id is not None
        else []
    )
    updated: list[MemoryFact] = []
    for fact in facts:
        fact.status = status
        if status == "deprecated" and fact.valid_to is None:
            fact.valid_to = utc_now()
        replacement = _matching_replacement_fact(fact, replacement_facts)
        if replacement is not None:
            fact.superseded_by_fact_id = replacement.id
            replacement.supersedes_fact_id = fact.id
            db.add(replacement)
        db.add(fact)
        updated.append(fact)
    db.commit()
    for fact in updated:
        db.refresh(fact)
    return updated


def list_memories(
    db: Session,
    *,
    status: str = "active",
    memory_types: list[str] | None = None,
    scope: str | None = None,
    include_low_confidence: bool = False,
) -> list[MemoryRecord]:
    statement = select(MemoryRecord).where(MemoryRecord.status == status)
    if memory_types:
        statement = statement.where(MemoryRecord.memory_type.in_(memory_types))
    if scope:
        statement = statement.where(MemoryRecord.scope == scope)
    statement = statement.order_by(
        MemoryRecord.created_at.desc(),
        MemoryRecord.id,
    )
    return list(db.exec(statement).all())


def list_memories_for_session(
    db: Session,
    *,
    session_id: str,
    include_inactive: bool = True,
) -> list[MemoryRecord]:
    statement = select(MemoryRecord).where(
        MemoryRecord.source_session_id == session_id
    )
    if not include_inactive:
        statement = statement.where(MemoryRecord.status == "active")
    statement = statement.order_by(
        MemoryRecord.created_at.desc(),
        MemoryRecord.id,
    )
    return list(db.exec(statement).all())


def list_all_memories(
    db: Session,
    *,
    include_low_confidence: bool = False,
) -> list[MemoryRecord]:
    statement = select(MemoryRecord)
    statement = statement.order_by(
        MemoryRecord.created_at.desc(),
        MemoryRecord.id,
    )
    return list(db.exec(statement).all())


def get_memory(db: Session, memory_id: str) -> MemoryRecord | None:
    return db.get(MemoryRecord, memory_id)


def update_memory_source_message(
    db: Session,
    *,
    memory_id: str,
    source_message_id: str,
) -> MemoryRecord | None:
    """Repair provenance without pretending the semantic content changed."""

    memory = db.get(MemoryRecord, memory_id)
    if memory is None:
        return None
    memory.source_message_id = source_message_id
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory


def update_memory_lifecycle(
    db: Session,
    *,
    memory_id: str,
    status: str | None = None,
    metadata: dict[str, Any] | None = None,
    touch_source_session: bool = True,
) -> MemoryRecord | None:
    memory = db.get(MemoryRecord, memory_id)
    if memory is None:
        return None

    if status is not None:
        memory.status = status
    if metadata is not None:
        memory.metadata_json = metadata
    memory.updated_at = utc_now()
    db.add(memory)
    if touch_source_session and memory.source_session_id is not None:
        _touch_session(db, memory.source_session_id)
    db.commit()
    db.refresh(memory)
    return memory


def mark_memory_used(db: Session, *, memory_id: str) -> MemoryRecord | None:
    memory = db.get(MemoryRecord, memory_id)
    if memory is None:
        return None

    memory.usage_count += 1
    memory.last_used_at = utc_now()
    memory.updated_at = memory.last_used_at
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory

def _matching_replacement_fact(
    fact: MemoryFact,
    replacement_facts: list[MemoryFact],
) -> MemoryFact | None:
    for candidate in replacement_facts:
        if candidate.entity == fact.entity and candidate.predicate == fact.predicate:
            return candidate
    return None
