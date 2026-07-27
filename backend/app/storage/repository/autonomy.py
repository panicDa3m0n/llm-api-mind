"""Persistence operations for Scarlet's autonomous activation lifecycle."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.storage.models import (
    AutonomousActivation,
    ChatSession,
    Turn,
    utc_now,
)


AUTONOMOUS_SESSION_KIND = "scarlet_autonomous"
ARCHIVED_AUTONOMOUS_SESSION_KIND = "scarlet_autonomous_archive"
HUMAN_SESSION_KIND = "human_dialogue"


def get_or_create_autonomous_session(
    db: Session,
    *,
    profile_id: str,
) -> ChatSession:
    autonomy_key = f"scarlet-autonomous:{profile_id}"
    statement = select(ChatSession).where(ChatSession.autonomy_key == autonomy_key)
    existing = db.exec(statement).first()
    if existing is not None:
        return existing

    chat_session = ChatSession(
        title="Cognizione autonoma di Scarlet",
        kind=AUTONOMOUS_SESSION_KIND,
        profile_id=profile_id,
        autonomy_key=autonomy_key,
        metadata_json={
            "visibility": "internal_cognition",
            "owner_profile_id": profile_id,
        },
    )
    db.add(chat_session)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.exec(statement).first()
        if existing is None:
            raise
        return existing
    db.refresh(chat_session)
    return chat_session


def get_autonomous_session(
    db: Session,
    *,
    profile_id: str,
) -> ChatSession | None:
    statement = select(ChatSession).where(
        ChatSession.autonomy_key == f"scarlet-autonomous:{profile_id}"
    )
    return db.exec(statement).first()


def archive_autonomous_session(
    db: Session,
    *,
    profile_id: str,
    expected_session_id: str,
    reason: str,
    archived_at: datetime | None = None,
) -> ChatSession:
    """Detach the active chronology while preserving its canonical evidence."""

    current = get_autonomous_session(db, profile_id=profile_id)
    if current is None:
        raise ValueError(f"No active autonomous session for profile: {profile_id}")
    if current.id != expected_session_id:
        raise ValueError(
            "Active autonomous session changed: "
            f"expected {expected_session_id}, received {current.id}."
        )

    timestamp = archived_at or utc_now()
    current.kind = ARCHIVED_AUTONOMOUS_SESSION_KIND
    current.autonomy_key = f"scarlet-autonomous-archive:{profile_id}:{current.id}"
    current.updated_at = timestamp
    current.metadata_json = {
        **current.metadata_json,
        "archived_at": timestamp.isoformat(),
        "archive_reason": reason,
        "visibility": "archived_internal_cognition",
    }
    db.add(current)
    db.exec(
        update(AutonomousActivation)
        .where(AutonomousActivation.session_id == current.id)
        .where(AutonomousActivation.status.in_(["pending", "running"]))
        .values(
            status="cancelled",
            completed_at=timestamp,
            lease_expires_at=None,
            updated_at=timestamp,
            error_json={"reason": "autonomous_chronology_archived"},
        )
    )
    db.commit()
    db.refresh(current)
    return current


def schedule_autonomous_activation(
    db: Session,
    *,
    profile_id: str,
    session_id: str,
    scheduled_at: datetime,
    trigger_kind: str = "periodic",
    schedule_key: str | None = None,
    candidate_id: str | None = None,
    episode_id: str | None = None,
    wake_condition_id: str | None = None,
    workspace: dict[str, Any] | None = None,
) -> AutonomousActivation:
    key = schedule_key or (
        f"{trigger_kind}:{profile_id}:{scheduled_at.astimezone().isoformat()}"
    )
    existing = db.exec(
        select(AutonomousActivation).where(
            AutonomousActivation.schedule_key == key
        )
    ).first()
    if existing is not None:
        return existing
    activation = AutonomousActivation(
        profile_id=profile_id,
        session_id=session_id,
        trigger_kind=trigger_kind,
        schedule_key=key,
        scheduled_at=scheduled_at,
        candidate_id=candidate_id,
        episode_id=episode_id,
        wake_condition_id=wake_condition_id,
        workspace_json=workspace or {},
    )
    db.add(activation)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.exec(
            select(AutonomousActivation).where(
                AutonomousActivation.schedule_key == key
            )
        ).first()
        if existing is None:
            raise
        return existing
    db.refresh(activation)
    return activation


def ensure_next_periodic_activation(
    db: Session,
    *,
    profile_id: str,
    session_id: str,
    interval_seconds: int,
    from_time: datetime | None = None,
) -> AutonomousActivation:
    pending = db.exec(
        select(AutonomousActivation)
        .where(AutonomousActivation.profile_id == profile_id)
        .where(AutonomousActivation.status.in_(["pending", "running"]))
        .order_by(
            AutonomousActivation.scheduled_at,
            AutonomousActivation.created_at,
        )
    ).first()
    if pending is not None:
        return pending
    scheduled_at = (from_time or utc_now()) + timedelta(seconds=interval_seconds)
    return schedule_autonomous_activation(
        db,
        profile_id=profile_id,
        session_id=session_id,
        scheduled_at=scheduled_at,
    )


def list_due_autonomous_activations(
    db: Session,
    *,
    now: datetime | None = None,
    limit: int = 5,
) -> list[AutonomousActivation]:
    current = now or utc_now()
    statement = (
        select(AutonomousActivation)
        .where(
            (AutonomousActivation.status == "pending")
            | (
                (AutonomousActivation.status == "running")
                & (AutonomousActivation.lease_expires_at <= current)
            )
        )
        .where(AutonomousActivation.scheduled_at <= current)
        .order_by(
            AutonomousActivation.scheduled_at,
            AutonomousActivation.created_at,
        )
        .limit(limit)
    )
    return list(db.exec(statement).all())


def claim_autonomous_activation(
    db: Session,
    *,
    activation_id: str,
    lease_seconds: int,
    now: datetime | None = None,
) -> AutonomousActivation | None:
    current = now or utc_now()
    lease_expires_at = current + timedelta(seconds=lease_seconds)
    statement = (
        update(AutonomousActivation)
        .where(AutonomousActivation.id == activation_id)
        .where(
            (AutonomousActivation.status == "pending")
            | (
                (AutonomousActivation.status == "running")
                & (AutonomousActivation.lease_expires_at <= current)
            )
        )
        .values(
            status="running",
            started_at=current,
            lease_expires_at=lease_expires_at,
            attempt_count=AutonomousActivation.attempt_count + 1,
            updated_at=current,
        )
    )
    result = db.exec(statement)
    db.commit()
    if int(result.rowcount or 0) != 1:
        return None
    activation = db.get(AutonomousActivation, activation_id)
    if activation is not None:
        db.refresh(activation)
    return activation


def complete_autonomous_activation(
    db: Session,
    *,
    activation_id: str,
    status: str,
    turn_id: str | None,
    active_mode: str | None,
    outcome: dict[str, Any] | None = None,
    error: dict[str, Any] | None = None,
) -> AutonomousActivation:
    activation = db.get(AutonomousActivation, activation_id)
    if activation is None:
        raise ValueError(f"Autonomous activation not found: {activation_id}")
    now = utc_now()
    activation.status = status
    activation.turn_id = turn_id
    activation.active_mode = active_mode
    activation.outcome_json = outcome or {}
    activation.error_json = error
    activation.completed_at = now
    activation.lease_expires_at = None
    activation.updated_at = now
    db.add(activation)
    db.commit()
    db.refresh(activation)
    return activation


def list_autonomous_activations(
    db: Session,
    *,
    profile_id: str | None = None,
    session_id: str | None = None,
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[AutonomousActivation]:
    statement = select(AutonomousActivation)
    if profile_id is not None:
        statement = statement.where(
            AutonomousActivation.profile_id == profile_id
        )
    if session_id is not None:
        statement = statement.where(AutonomousActivation.session_id == session_id)
    if status is not None:
        statement = statement.where(AutonomousActivation.status == status)
    statement = (
        statement.order_by(
            AutonomousActivation.scheduled_at.desc(),
            AutonomousActivation.created_at.desc(),
        )
        .offset(offset)
        .limit(limit)
    )
    return list(db.exec(statement).all())


def get_autonomous_activation_by_turn(
    db: Session,
    *,
    turn_id: str,
) -> AutonomousActivation | None:
    return db.exec(
        select(AutonomousActivation).where(
            AutonomousActivation.turn_id == turn_id
        )
    ).first()


def latest_completed_autonomous_activation(
    db: Session,
    *,
    profile_id: str,
) -> AutonomousActivation | None:
    return db.exec(
        select(AutonomousActivation)
        .where(AutonomousActivation.profile_id == profile_id)
        .where(AutonomousActivation.status == "completed")
        .order_by(
            AutonomousActivation.completed_at.desc(),
            AutonomousActivation.id.desc(),
        )
        .limit(1)
    ).first()


def attach_workspace_to_next_activation(
    db: Session,
    *,
    profile_id: str,
    workspace: dict[str, Any],
    candidate_id: str | None,
    episode_id: str | None,
    wake_condition_id: str | None,
) -> AutonomousActivation | None:
    activation = db.exec(
        select(AutonomousActivation)
        .where(AutonomousActivation.profile_id == profile_id)
        .where(AutonomousActivation.status == "pending")
        .order_by(
            AutonomousActivation.scheduled_at,
            AutonomousActivation.created_at,
        )
        .limit(1)
    ).first()
    if activation is None:
        return None
    activation.workspace_json = workspace
    activation.candidate_id = candidate_id
    activation.episode_id = episode_id
    activation.wake_condition_id = wake_condition_id
    activation.updated_at = utc_now()
    db.add(activation)
    db.commit()
    db.refresh(activation)
    return activation


def has_active_human_turn(
    db: Session,
    *,
    active_since: datetime,
) -> bool:
    statement = (
        select(Turn.id)
        .join(ChatSession, ChatSession.id == Turn.session_id)
        .where(Turn.status == "started")
        .where(Turn.started_at >= active_since)
        .where(ChatSession.kind == HUMAN_SESSION_KIND)
        .limit(1)
    )
    return db.exec(statement).first() is not None
