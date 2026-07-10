"""Persistence operations for focus and latent-intention organs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import or_
from sqlmodel import Session, select

from app.storage.models import (
    FocusRecord,
    FocusTransition,
    IntentionLink,
    IntentionRecord,
    utc_now,
)
from app.storage.repository._shared import touch_session as _touch_session


ACTIVE_FOCUS_STATUSES = {"active", "held"}
OPEN_INTENTION_STATUSES = {"active", "deferred", "in_review"}

def get_focus_record(db: Session, focus_id: str) -> FocusRecord | None:
    return db.get(FocusRecord, focus_id)


def get_active_focus(
    db: Session,
    *,
    owner_profile_id: str = "local-user",
) -> FocusRecord | None:
    statement = (
        select(FocusRecord)
        .where(FocusRecord.owner_profile_id == owner_profile_id)
        .where(FocusRecord.status.in_(ACTIVE_FOCUS_STATUSES))
        .order_by(FocusRecord.updated_at.desc(), FocusRecord.created_at.desc())
        .limit(1)
    )
    return db.exec(statement).first()


def list_active_focus_records(
    db: Session,
    *,
    owner_profile_id: str = "local-user",
) -> list[FocusRecord]:
    statement = (
        select(FocusRecord)
        .where(FocusRecord.owner_profile_id == owner_profile_id)
        .where(FocusRecord.status.in_(ACTIVE_FOCUS_STATUSES))
        .order_by(FocusRecord.updated_at.desc(), FocusRecord.created_at.desc())
    )
    return list(db.exec(statement).all())


def list_focus_records(
    db: Session,
    *,
    owner_profile_id: str = "local-user",
    status: str | None = None,
    query: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[FocusRecord]:
    statement = select(FocusRecord).where(
        FocusRecord.owner_profile_id == owner_profile_id
    )
    if status is not None:
        statement = statement.where(FocusRecord.status == status)
    if query:
        needle = f"%{query.strip()}%"
        statement = statement.where(
            (FocusRecord.focus_object.ilike(needle))
            | (FocusRecord.focus_type.ilike(needle))
            | (FocusRecord.reason.ilike(needle))
            | (FocusRecord.resolution.ilike(needle))
            | (FocusRecord.impossible_reason.ilike(needle))
        )
    statement = (
        statement.order_by(FocusRecord.updated_at.desc(), FocusRecord.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.exec(statement).all())


def create_focus_record(
    db: Session,
    *,
    owner_profile_id: str,
    focus_object: str,
    focus_type: str,
    reason: str,
    intensity: float = 0.5,
    duration_policy: str | None = None,
    created_by: str = "scarlet",
    source_session_id: str | None = None,
    source_turn_id: str | None = None,
    source_message_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> FocusRecord:
    now = utc_now()
    focus = FocusRecord(
        owner_profile_id=owner_profile_id,
        focus_object=focus_object,
        focus_type=focus_type,
        reason=reason,
        intensity=intensity,
        duration_policy=duration_policy,
        created_by=created_by,
        source_session_id=source_session_id,
        source_turn_id=source_turn_id,
        source_message_id=source_message_id,
        metadata_json=metadata or {},
        created_at=now,
        updated_at=now,
    )
    db.add(focus)
    if source_session_id is not None:
        _touch_session(db, source_session_id, at=now)
    db.commit()
    db.refresh(focus)
    return focus


def update_focus_record(
    db: Session,
    *,
    focus_id: str,
    focus_object: str | None = None,
    focus_type: str | None = None,
    reason: str | None = None,
    intensity: float | None = None,
    duration_policy: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> FocusRecord | None:
    focus = get_focus_record(db, focus_id)
    if focus is None:
        return None
    if focus_object is not None:
        focus.focus_object = focus_object
    if focus_type is not None:
        focus.focus_type = focus_type
    if reason is not None:
        focus.reason = reason
    if intensity is not None:
        focus.intensity = intensity
    if duration_policy is not None:
        focus.duration_policy = duration_policy
    if metadata:
        focus.metadata_json = {**focus.metadata_json, **metadata}
    focus.updated_at = utc_now()
    db.add(focus)
    if focus.source_session_id is not None:
        _touch_session(db, focus.source_session_id, at=focus.updated_at)
    db.commit()
    db.refresh(focus)
    return focus


def close_focus_record(
    db: Session,
    *,
    focus_id: str,
    status: str,
    resolution: str | None = None,
    impossible_reason: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> FocusRecord | None:
    focus = get_focus_record(db, focus_id)
    if focus is None:
        return None
    now = utc_now()
    focus.status = status
    focus.resolution = resolution
    focus.impossible_reason = impossible_reason
    focus.closed_at = now
    focus.updated_at = now
    if metadata:
        focus.metadata_json = {**focus.metadata_json, **metadata}
    db.add(focus)
    if focus.source_session_id is not None:
        _touch_session(db, focus.source_session_id, at=now)
    db.commit()
    db.refresh(focus)
    return focus


def add_focus_transition(
    db: Session,
    *,
    owner_profile_id: str,
    relation: str,
    from_focus_id: str | None = None,
    to_focus_id: str | None = None,
    reason: str | None = None,
    source_session_id: str | None = None,
    source_turn_id: str | None = None,
    source_message_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> FocusTransition:
    transition = FocusTransition(
        owner_profile_id=owner_profile_id,
        from_focus_id=from_focus_id,
        to_focus_id=to_focus_id,
        relation=relation,
        reason=reason,
        source_session_id=source_session_id,
        source_turn_id=source_turn_id,
        source_message_id=source_message_id,
        metadata_json=metadata or {},
    )
    db.add(transition)
    if source_session_id is not None:
        _touch_session(db, source_session_id)
    db.commit()
    db.refresh(transition)
    return transition


def list_focus_transitions(
    db: Session,
    *,
    owner_profile_id: str = "local-user",
    focus_id: str | None = None,
    limit: int = 20,
) -> list[FocusTransition]:
    statement = select(FocusTransition).where(
        FocusTransition.owner_profile_id == owner_profile_id
    )
    if focus_id is not None:
        statement = statement.where(
            (FocusTransition.from_focus_id == focus_id)
            | (FocusTransition.to_focus_id == focus_id)
        )
    statement = statement.order_by(
        FocusTransition.created_at.desc(),
        FocusTransition.id,
    ).limit(limit)
    return list(db.exec(statement).all())


def get_intention_record(db: Session, intention_id: str) -> IntentionRecord | None:
    return db.get(IntentionRecord, intention_id)


def list_open_intention_records(
    db: Session,
    *,
    owner_profile_id: str = "local-user",
    limit: int = 20,
    offset: int = 0,
) -> list[IntentionRecord]:
    statement = (
        select(IntentionRecord)
        .where(IntentionRecord.owner_profile_id == owner_profile_id)
        .where(IntentionRecord.status.in_(OPEN_INTENTION_STATUSES))
        .order_by(IntentionRecord.updated_at.desc(), IntentionRecord.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.exec(statement).all())


def list_due_intention_records(
    db: Session,
    *,
    owner_profile_id: str = "local-user",
    now: datetime | None = None,
    include_unscheduled: bool = False,
    limit: int = 20,
    offset: int = 0,
) -> list[IntentionRecord]:
    due_at = now or utc_now()
    statement = (
        select(IntentionRecord)
        .where(IntentionRecord.owner_profile_id == owner_profile_id)
        .where(IntentionRecord.status.in_(OPEN_INTENTION_STATUSES))
    )
    if include_unscheduled:
        statement = statement.where(
            or_(
                IntentionRecord.next_review_at.is_(None),
                IntentionRecord.next_review_at <= due_at,
            )
        )
    else:
        statement = statement.where(IntentionRecord.next_review_at <= due_at)
    statement = (
        statement.order_by(
            IntentionRecord.next_review_at,
            IntentionRecord.updated_at.desc(),
            IntentionRecord.created_at.desc(),
        )
        .offset(offset)
        .limit(limit)
    )
    return list(db.exec(statement).all())


def list_intention_records(
    db: Session,
    *,
    owner_profile_id: str = "local-user",
    status: str | None = None,
    query: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[IntentionRecord]:
    statement = select(IntentionRecord).where(
        IntentionRecord.owner_profile_id == owner_profile_id
    )
    if status is not None:
        statement = statement.where(IntentionRecord.status == status)
    if query:
        needle = f"%{query.strip()}%"
        statement = statement.where(
            (IntentionRecord.desire.ilike(needle))
            | (IntentionRecord.origin.ilike(needle))
            | (IntentionRecord.horizon.ilike(needle))
            | (IntentionRecord.autonomy_level.ilike(needle))
            | (IntentionRecord.reason.ilike(needle))
            | (IntentionRecord.next_possible_reflection.ilike(needle))
            | (IntentionRecord.resolution.ilike(needle))
            | (IntentionRecord.impossible_reason.ilike(needle))
        )
    statement = (
        statement.order_by(
            IntentionRecord.updated_at.desc(),
            IntentionRecord.created_at.desc(),
        )
        .offset(offset)
        .limit(limit)
    )
    return list(db.exec(statement).all())


def create_intention_record(
    db: Session,
    *,
    owner_profile_id: str,
    desire: str,
    reason: str,
    origin: str = "scarlet",
    horizon: str | None = None,
    intensity: float = 0.5,
    autonomy_level: str = "self_generated",
    next_possible_reflection: str | None = None,
    next_review_at: datetime | None = None,
    review_interval_seconds: int | None = None,
    created_by: str = "scarlet",
    source_session_id: str | None = None,
    source_turn_id: str | None = None,
    source_message_id: str | None = None,
    source_focus_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> IntentionRecord:
    now = utc_now()
    intention = IntentionRecord(
        owner_profile_id=owner_profile_id,
        desire=desire,
        origin=origin,
        horizon=horizon,
        intensity=intensity,
        autonomy_level=autonomy_level,
        reason=reason,
        next_possible_reflection=next_possible_reflection,
        next_review_at=next_review_at,
        review_interval_seconds=review_interval_seconds,
        created_by=created_by,
        source_session_id=source_session_id,
        source_turn_id=source_turn_id,
        source_message_id=source_message_id,
        source_focus_id=source_focus_id,
        metadata_json=metadata or {},
        created_at=now,
        updated_at=now,
    )
    db.add(intention)
    if source_session_id is not None:
        _touch_session(db, source_session_id, at=now)
    db.commit()
    db.refresh(intention)
    return intention


def update_intention_record(
    db: Session,
    *,
    intention_id: str,
    desire: str | None = None,
    status: str | None = None,
    origin: str | None = None,
    horizon: str | None = None,
    intensity: float | None = None,
    autonomy_level: str | None = None,
    reason: str | None = None,
    next_possible_reflection: str | None = None,
    last_reviewed_at: datetime | None = None,
    next_review_at: datetime | None = None,
    review_interval_seconds: int | None = None,
    increment_review_count: bool = False,
    resolution: str | None = None,
    impossible_reason: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> IntentionRecord | None:
    intention = get_intention_record(db, intention_id)
    if intention is None:
        return None
    if desire is not None:
        intention.desire = desire
    if status is not None:
        intention.status = status
    if origin is not None:
        intention.origin = origin
    if horizon is not None:
        intention.horizon = horizon
    if intensity is not None:
        intention.intensity = intensity
    if autonomy_level is not None:
        intention.autonomy_level = autonomy_level
    if reason is not None:
        intention.reason = reason
    if next_possible_reflection is not None:
        intention.next_possible_reflection = next_possible_reflection
    if last_reviewed_at is not None:
        intention.last_reviewed_at = last_reviewed_at
    if next_review_at is not None:
        intention.next_review_at = next_review_at
    if review_interval_seconds is not None:
        intention.review_interval_seconds = review_interval_seconds
    if increment_review_count:
        intention.review_count += 1
    if resolution is not None:
        intention.resolution = resolution
    if impossible_reason is not None:
        intention.impossible_reason = impossible_reason
    if metadata:
        intention.metadata_json = {**intention.metadata_json, **metadata}
    intention.updated_at = utc_now()
    db.add(intention)
    if intention.source_session_id is not None:
        _touch_session(db, intention.source_session_id, at=intention.updated_at)
    db.commit()
    db.refresh(intention)
    return intention


def close_intention_record(
    db: Session,
    *,
    intention_id: str,
    status: str,
    resolution: str | None = None,
    impossible_reason: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> IntentionRecord | None:
    intention = get_intention_record(db, intention_id)
    if intention is None:
        return None
    now = utc_now()
    intention.status = status
    intention.resolution = resolution
    intention.impossible_reason = impossible_reason
    intention.closed_at = now
    intention.updated_at = now
    if metadata:
        intention.metadata_json = {**intention.metadata_json, **metadata}
    db.add(intention)
    if intention.source_session_id is not None:
        _touch_session(db, intention.source_session_id, at=now)
    db.commit()
    db.refresh(intention)
    return intention


def add_intention_link(
    db: Session,
    *,
    intention_id: str,
    target_type: str,
    target_id: str,
    relation: str = "related_to",
    metadata: dict[str, Any] | None = None,
) -> IntentionLink:
    link = IntentionLink(
        intention_id=intention_id,
        target_type=target_type,
        target_id=target_id,
        relation=relation,
        metadata_json=metadata or {},
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def list_intention_links(
    db: Session,
    *,
    intention_id: str,
    limit: int = 50,
) -> list[IntentionLink]:
    statement = (
        select(IntentionLink)
        .where(IntentionLink.intention_id == intention_id)
        .order_by(IntentionLink.created_at.desc(), IntentionLink.id)
        .limit(limit)
    )
    return list(db.exec(statement).all())

