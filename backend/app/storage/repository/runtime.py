"""Persistence operations for runtime events, affect, settings, and maintenance."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlmodel import Session, select

from app.storage.models import (
    AffectState,
    AppSetting,
    CognitiveEvent,
    MaintenanceJob,
    utc_now,
)


ACTIVE_AFFECT_STATUSES = {"active"}

def add_event(
    db: Session,
    *,
    session_id: str,
    event_type: str,
    payload: dict[str, Any] | None = None,
    turn_id: str | None = None,
    source: str = "runtime",
    actor: str = "backend",
    visibility: str = "debug",
    status: str = "completed",
    parent_event_id: str | None = None,
    trace_id: str | None = None,
    tool_call_id: str | None = None,
    message_id: str | None = None,
    seq: int | None = None,
) -> CognitiveEvent:
    event = CognitiveEvent(
        session_id=session_id,
        turn_id=turn_id,
        seq=seq if seq is not None else next_event_seq(db, session_id=session_id),
        type=event_type,
        source=source,
        actor=actor,
        visibility=visibility,
        status=status,
        parent_event_id=parent_event_id,
        trace_id=trace_id,
        tool_call_id=tool_call_id,
        message_id=message_id,
        payload_json=payload or {},
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def create_affect_state(
    db: Session,
    *,
    owner_profile_id: str,
    session_id: str | None,
    turn_id: str | None,
    mode: str,
    emotion: str,
    intensity: float,
    intensity_label: str,
    valence: float,
    activation: float,
    prototype_version: str,
    variables: dict[str, Any],
    causes: list[dict[str, Any]],
    tendencies: dict[str, Any],
    pack: dict[str, Any],
    decays_at: datetime | None = None,
    metadata: dict[str, Any] | None = None,
) -> AffectState:
    state = AffectState(
        owner_profile_id=owner_profile_id,
        session_id=session_id,
        turn_id=turn_id,
        mode=mode,
        emotion=emotion,
        intensity=intensity,
        intensity_label=intensity_label,
        valence=valence,
        activation=activation,
        prototype_version=prototype_version,
        variables_json=variables,
        causes_json=causes,
        tendencies_json=tendencies,
        pack_json=pack,
        decays_at=decays_at,
        metadata_json=metadata or {},
    )
    db.add(state)
    db.commit()
    db.refresh(state)
    return state


def get_latest_affect_state(
    db: Session,
    *,
    owner_profile_id: str,
    include_inactive: bool = False,
) -> AffectState | None:
    statement = select(AffectState).where(
        AffectState.owner_profile_id == owner_profile_id
    )
    if not include_inactive:
        statement = statement.where(AffectState.status.in_(ACTIVE_AFFECT_STATUSES))
    statement = statement.order_by(AffectState.created_at.desc(), AffectState.id.desc())
    return db.exec(statement.limit(1)).first()


def get_affect_state(db: Session, affect_id: str) -> AffectState | None:
    return db.get(AffectState, affect_id)


def list_affect_states(
    db: Session,
    *,
    owner_profile_id: str | None = None,
    session_id: str | None = None,
    turn_id: str | None = None,
    status: str | None = None,
    emotion: str | None = None,
    mode: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[AffectState]:
    statement = select(AffectState)
    if owner_profile_id is not None:
        statement = statement.where(AffectState.owner_profile_id == owner_profile_id)
    if session_id is not None:
        statement = statement.where(AffectState.session_id == session_id)
    if turn_id is not None:
        statement = statement.where(AffectState.turn_id == turn_id)
    if status is not None:
        statement = statement.where(AffectState.status == status)
    if emotion is not None:
        statement = statement.where(AffectState.emotion == emotion)
    if mode is not None:
        statement = statement.where(AffectState.mode == mode)
    statement = (
        statement.order_by(AffectState.created_at.desc(), AffectState.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.exec(statement).all())


def next_event_seq(db: Session, *, session_id: str) -> int:
    statement = select(func.max(CognitiveEvent.seq)).where(
        CognitiveEvent.session_id == session_id
    )
    current = db.exec(statement).one()
    return int(current or 0) + 1


def list_events_for_turn(db: Session, *, turn_id: str) -> list[CognitiveEvent]:
    statement = (
        select(CognitiveEvent)
        .where(CognitiveEvent.turn_id == turn_id)
        .order_by(CognitiveEvent.seq, CognitiveEvent.created_at, CognitiveEvent.id)
    )
    return list(db.exec(statement).all())


def list_events_for_session(
    db: Session,
    *,
    session_id: str,
    limit: int = 200,
    offset: int = 0,
    exclude_turn_id: str | None = None,
) -> list[CognitiveEvent]:
    statement = select(CognitiveEvent).where(CognitiveEvent.session_id == session_id)
    if exclude_turn_id is not None:
        statement = statement.where(
            (CognitiveEvent.turn_id.is_(None))
            | (CognitiveEvent.turn_id != exclude_turn_id)
        )
    statement = (
        statement.order_by(CognitiveEvent.seq.desc(), CognitiveEvent.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.exec(statement).all())


def get_app_setting(db: Session, key: str) -> AppSetting | None:
    return db.get(AppSetting, key)


def list_app_settings(db: Session) -> list[AppSetting]:
    statement = select(AppSetting).order_by(AppSetting.key)
    return list(db.exec(statement).all())


def upsert_app_setting(
    db: Session,
    *,
    key: str,
    value: Any,
) -> AppSetting:
    now = utc_now()
    setting = get_app_setting(db, key)
    if setting is None:
        setting = AppSetting(key=key, value_json={"value": value}, updated_at=now)
    else:
        setting.value_json = {"value": value}
        setting.updated_at = now
    db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting


def schedule_session_maintenance_job(
    db: Session,
    *,
    kind: str,
    session_id: str,
    trigger_turn_id: str | None,
    trigger_event_id: str | None,
    due_at: datetime,
    input_payload: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
) -> tuple[MaintenanceJob, list[MaintenanceJob]]:
    resolved_idempotency_key = idempotency_key or (
        f"{kind}:{session_id}:{trigger_turn_id or 'session'}"
    )
    existing_statement = select(MaintenanceJob).where(
        MaintenanceJob.idempotency_key == resolved_idempotency_key
    )
    existing = db.exec(existing_statement).first()
    if existing is not None:
        return existing, []

    pending_statement = (
        select(MaintenanceJob)
        .where(MaintenanceJob.session_id == session_id)
        .where(MaintenanceJob.kind == kind)
        .where(MaintenanceJob.status == "pending")
        .order_by(MaintenanceJob.created_at, MaintenanceJob.id)
    )
    pending_jobs = list(db.exec(pending_statement).all())
    job = MaintenanceJob(
        kind=kind,
        status="pending",
        session_id=session_id,
        trigger_turn_id=trigger_turn_id,
        trigger_event_id=trigger_event_id,
        due_at=due_at,
        idempotency_key=resolved_idempotency_key,
        input_json=input_payload or {},
    )
    now = utc_now()
    for pending in pending_jobs:
        pending.status = "superseded"
        pending.completed_at = now
        pending.updated_at = now
        pending.superseded_by_job_id = job.id
        db.add(pending)
    db.add(job)
    db.commit()
    db.refresh(job)
    for pending in pending_jobs:
        db.refresh(pending)
    return job, pending_jobs


def list_due_maintenance_jobs(
    db: Session,
    *,
    now: datetime | None = None,
    limit: int = 10,
) -> list[MaintenanceJob]:
    due = now or utc_now()
    statement = (
        select(MaintenanceJob)
        .where(MaintenanceJob.status == "pending")
        .where(MaintenanceJob.due_at <= due)
        .order_by(MaintenanceJob.due_at, MaintenanceJob.created_at, MaintenanceJob.id)
        .limit(limit)
    )
    return list(db.exec(statement).all())


def list_maintenance_jobs(
    db: Session,
    *,
    status: str | None = None,
    kind: str | None = None,
    session_id: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[MaintenanceJob]:
    statement = select(MaintenanceJob)
    if status is not None:
        statement = statement.where(MaintenanceJob.status == status)
    if kind is not None:
        statement = statement.where(MaintenanceJob.kind == kind)
    if session_id is not None:
        statement = statement.where(MaintenanceJob.session_id == session_id)
    statement = (
        statement.order_by(
            MaintenanceJob.created_at.desc(),
            MaintenanceJob.due_at.desc(),
            MaintenanceJob.id,
        )
        .offset(offset)
        .limit(limit)
    )
    return list(db.exec(statement).all())


def get_maintenance_job(db: Session, job_id: str) -> MaintenanceJob | None:
    return db.get(MaintenanceJob, job_id)


def start_maintenance_job(db: Session, *, job_id: str) -> MaintenanceJob | None:
    job = get_maintenance_job(db, job_id)
    if job is None or job.status != "pending":
        return None
    now = utc_now()
    job.status = "running"
    job.started_at = now
    job.updated_at = now
    db.add(job)
    db.commit()
    db.refresh(job)
    return job

def complete_maintenance_job(
    db: Session,
    *,
    job_id: str,
    result: dict[str, Any],
    status: str = "completed",
    error: dict[str, Any] | None = None,
) -> MaintenanceJob:
    job = get_maintenance_job(db, job_id)
    if job is None:
        raise ValueError(f"Maintenance job not found: {job_id}")
    now = utc_now()
    job.status = status
    job.completed_at = now
    job.updated_at = now
    job.result_json = result
    job.error_json = error
    db.add(job)
    db.commit()
    db.refresh(job)
    return job
