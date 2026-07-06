from datetime import datetime
from typing import Any

from sqlalchemy import func, or_
from sqlmodel import Session, select

from app.storage.models import (
    AffectState,
    AppSetting,
    ChatSession,
    CognitiveEvent,
    EmbeddingVector,
    FocusRecord,
    FocusTransition,
    IntentionLink,
    IntentionRecord,
    MaintenanceJob,
    MemoryFact,
    MemoryGraphEdge,
    MemoryGraphNode,
    MemoryProposal,
    MemoryRecord,
    MemorySurface,
    Message,
    SessionSummary,
    ToolCall,
    Trace,
    Turn,
    utc_now,
)


RESOLVED_MEMORY_PROPOSAL_STATUSES = {
    "applied_create",
    "archived_manual",
    "archived_noop_duplicate",
    "archived_rejected",
    "pending_review",
}

ACTIVE_FOCUS_STATUSES = {"active", "held"}
OPEN_INTENTION_STATUSES = {"active", "deferred", "in_review"}
ACTIVE_AFFECT_STATUSES = {"active"}


def create_chat_session(
    db: Session,
    *,
    title: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ChatSession:
    chat_session = ChatSession(title=title, metadata_json=metadata or {})
    db.add(chat_session)
    db.commit()
    db.refresh(chat_session)
    return chat_session


def get_chat_session(db: Session, session_id: str) -> ChatSession | None:
    return db.get(ChatSession, session_id)


def update_chat_session_provider_history(
    db: Session,
    *,
    session_id: str,
    provider_history: list[dict[str, Any]],
) -> ChatSession:
    chat_session = get_chat_session(db, session_id)
    if chat_session is None:
        raise ValueError(f"Session not found: {session_id}")

    chat_session.provider_history_json = provider_history
    _touch_session(db, session_id)
    db.add(chat_session)
    db.commit()
    db.refresh(chat_session)
    return chat_session


def list_chat_sessions(
    db: Session,
    *,
    limit: int = 30,
    offset: int = 0,
) -> list[ChatSession]:
    statement = (
        select(ChatSession)
        .order_by(ChatSession.updated_at.desc(), ChatSession.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.exec(statement).all())


def get_session_summary(
    db: Session,
    *,
    session_id: str,
) -> SessionSummary | None:
    statement = select(SessionSummary).where(SessionSummary.session_id == session_id)
    return db.exec(statement).first()


def upsert_session_summary(
    db: Session,
    *,
    session_id: str,
    summary: str,
    topics: list[str] | None = None,
    decisions: list[str] | None = None,
    open_questions: list[str] | None = None,
    memory_ids: list[str] | None = None,
    message_count: int = 0,
    source_turn_count: int = 0,
    last_message_id: str | None = None,
    status: str = "active",
    summary_version: str = "episodic-v1",
    metadata: dict[str, Any] | None = None,
) -> SessionSummary:
    now = utc_now()
    session_summary = get_session_summary(db, session_id=session_id)
    if session_summary is None:
        session_summary = SessionSummary(
            session_id=session_id,
            summary=summary,
            topics_json=topics or [],
            decisions_json=decisions or [],
            open_questions_json=open_questions or [],
            memory_ids_json=memory_ids or [],
            message_count=message_count,
            source_turn_count=source_turn_count,
            last_message_id=last_message_id,
            status=status,
            summary_version=summary_version,
            metadata_json=metadata or {},
            updated_at=now,
        )
    else:
        session_summary.summary = summary
        session_summary.topics_json = topics or []
        session_summary.decisions_json = decisions or []
        session_summary.open_questions_json = open_questions or []
        session_summary.memory_ids_json = memory_ids or []
        session_summary.message_count = message_count
        session_summary.source_turn_count = source_turn_count
        session_summary.last_message_id = last_message_id
        session_summary.status = status
        session_summary.summary_version = summary_version
        session_summary.metadata_json = metadata or {}
        session_summary.updated_at = now

    db.add(session_summary)
    db.commit()
    db.refresh(session_summary)
    return session_summary


def create_turn(
    db: Session,
    *,
    session_id: str,
    model: str | None = None,
) -> Turn:
    turn = Turn(session_id=session_id, model=model)
    db.add(turn)
    _touch_session(db, session_id)
    db.commit()
    db.refresh(turn)
    return turn


def complete_turn(
    db: Session,
    *,
    turn_id: str,
    status: str = "completed",
    latency_ms: int | None = None,
    error: dict[str, Any] | None = None,
) -> Turn:
    turn = db.get(Turn, turn_id)
    if turn is None:
        raise ValueError(f"Turn not found: {turn_id}")

    turn.status = status
    turn.completed_at = utc_now()
    turn.latency_ms = latency_ms
    turn.error_json = error
    _touch_session(db, turn.session_id, at=turn.completed_at)
    db.add(turn)
    db.commit()
    db.refresh(turn)
    return turn


def add_message(
    db: Session,
    *,
    session_id: str,
    role: str,
    content: str,
    turn_id: str | None = None,
    provider_message_id: str | None = None,
    raw_content: dict[str, Any] | list[Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Message:
    message = Message(
        session_id=session_id,
        turn_id=turn_id,
        role=role,
        content=content,
        provider_message_id=provider_message_id,
        raw_content_json=raw_content,
        metadata_json=metadata or {},
    )
    db.add(message)
    _touch_session(db, session_id)
    db.commit()
    db.refresh(message)
    return message


def list_messages(db: Session, *, session_id: str) -> list[Message]:
    statement = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at, Message.id)
    )
    return list(db.exec(statement).all())


def latest_message_for_turn(
    db: Session,
    *,
    turn_id: str,
    role: str | None = None,
) -> Message | None:
    statement = select(Message).where(Message.turn_id == turn_id)
    if role is not None:
        statement = statement.where(Message.role == role)
    statement = statement.order_by(Message.created_at.desc(), Message.id.desc()).limit(1)
    return db.exec(statement).first()


def add_trace(
    db: Session,
    *,
    session_id: str,
    kind: str,
    payload: dict[str, Any],
    turn_id: str | None = None,
) -> Trace:
    trace = Trace(
        session_id=session_id,
        turn_id=turn_id,
        kind=kind,
        payload_json=payload,
    )
    db.add(trace)
    _touch_session(db, session_id)
    db.commit()
    db.refresh(trace)
    return trace


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
) -> tuple[MaintenanceJob, list[MaintenanceJob]]:
    idempotency_key = f"{kind}:{session_id}:{trigger_turn_id or 'session'}"
    existing_statement = select(MaintenanceJob).where(
        MaintenanceJob.idempotency_key == idempotency_key
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
        idempotency_key=idempotency_key,
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


def latest_turn_for_session(db: Session, *, session_id: str) -> Turn | None:
    statement = (
        select(Turn)
        .where(Turn.session_id == session_id)
        .order_by(Turn.started_at.desc(), Turn.id.desc())
        .limit(1)
    )
    return db.exec(statement).first()


def list_traces_for_turn(db: Session, *, turn_id: str) -> list[Trace]:
    statement = (
        select(Trace)
        .where(Trace.turn_id == turn_id)
        .order_by(Trace.created_at, Trace.id)
    )
    return list(db.exec(statement).all())


def list_traces_for_session(
    db: Session,
    *,
    session_id: str,
    kinds: list[str] | None = None,
    limit: int = 50,
    turn_id: str | None = None,
) -> list[Trace]:
    statement = select(Trace).where(Trace.session_id == session_id)
    if kinds:
        statement = statement.where(Trace.kind.in_(kinds))
    if turn_id is not None:
        statement = statement.where(Trace.turn_id == turn_id)
    statement = statement.order_by(Trace.created_at.desc(), Trace.id.desc()).limit(limit)
    return list(db.exec(statement).all())


def add_tool_call(
    db: Session,
    *,
    tool_name: str,
    arguments: dict[str, Any],
    result: dict[str, Any],
    status: str,
    session_id: str | None = None,
    turn_id: str | None = None,
    latency_ms: int | None = None,
) -> ToolCall:
    tool_call = ToolCall(
        session_id=session_id,
        turn_id=turn_id,
        tool_name=tool_name,
        arguments_json=arguments,
        result_json=result,
        status=status,
        latency_ms=latency_ms,
    )
    db.add(tool_call)
    if session_id is not None:
        _touch_session(db, session_id)
    db.commit()
    db.refresh(tool_call)
    return tool_call


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


def update_memory_lifecycle(
    db: Session,
    *,
    memory_id: str,
    status: str | None = None,
    metadata: dict[str, Any] | None = None,
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
    if memory.source_session_id is not None:
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


def upsert_memory_surface(
    db: Session,
    *,
    surface_key: str,
    target_type: str,
    target_id: str,
    surface_kind: str,
    content: str,
    content_hash: str,
    scope: str | None = None,
    status: str = "active",
    source_session_id: str | None = None,
    source_turn_id: str | None = None,
    source_message_id: str | None = None,
    source_trace_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> tuple[MemorySurface, bool]:
    existing = get_memory_surface_by_key(db, surface_key=surface_key)
    if existing is None:
        surface = MemorySurface(
            surface_key=surface_key,
            target_type=target_type,
            target_id=target_id,
            surface_kind=surface_kind,
            content=content,
            content_hash=content_hash,
            scope=scope,
            status=status,
            source_session_id=source_session_id,
            source_turn_id=source_turn_id,
            source_message_id=source_message_id,
            source_trace_id=source_trace_id,
            metadata_json=metadata or {},
        )
        db.add(surface)
        db.commit()
        db.refresh(surface)
        return surface, True

    changed_content = existing.content_hash != content_hash
    changed = changed_content or any(
        [
            existing.content != content,
            existing.target_type != target_type,
            existing.target_id != target_id,
            existing.surface_kind != surface_kind,
            existing.scope != scope,
            existing.status != status,
            existing.source_session_id != source_session_id,
            existing.source_turn_id != source_turn_id,
            existing.source_message_id != source_message_id,
            existing.source_trace_id != source_trace_id,
            existing.metadata_json != (metadata or {}),
        ]
    )
    if changed:
        existing.target_type = target_type
        existing.target_id = target_id
        existing.surface_kind = surface_kind
        existing.content = content
        existing.content_hash = content_hash
        existing.scope = scope
        existing.status = status
        existing.source_session_id = source_session_id
        existing.source_turn_id = source_turn_id
        existing.source_message_id = source_message_id
        existing.source_trace_id = source_trace_id
        existing.metadata_json = metadata or {}
        existing.updated_at = utc_now()
        if changed_content:
            existing.embedding_status = "pending"
            existing.embedding_model = None
            existing.embedding_vector_id = None
        db.add(existing)
        db.commit()
        db.refresh(existing)
    return existing, False


def get_memory_surface_by_key(
    db: Session,
    *,
    surface_key: str,
) -> MemorySurface | None:
    statement = select(MemorySurface).where(MemorySurface.surface_key == surface_key)
    return db.exec(statement).first()


def list_memory_surfaces(
    db: Session,
    *,
    target_type: str | None = None,
    target_id: str | None = None,
    surface_kind: str | None = None,
    embedding_status: str | None = None,
    limit: int = 100,
) -> list[MemorySurface]:
    statement = select(MemorySurface)
    if target_type is not None:
        statement = statement.where(MemorySurface.target_type == target_type)
    if target_id is not None:
        statement = statement.where(MemorySurface.target_id == target_id)
    if surface_kind is not None:
        statement = statement.where(MemorySurface.surface_kind == surface_kind)
    if embedding_status is not None:
        statement = statement.where(MemorySurface.embedding_status == embedding_status)
    statement = statement.order_by(
        MemorySurface.updated_at.desc(),
        MemorySurface.id,
    ).limit(limit)
    return list(db.exec(statement).all())


def list_memory_surfaces_by_targets(
    db: Session,
    *,
    target_type: str,
    target_ids: list[str],
    surface_kind: str | None = None,
    status: str | None = "active",
    limit: int = 500,
) -> list[MemorySurface]:
    if not target_ids:
        return []
    statement = select(MemorySurface).where(
        MemorySurface.target_type == target_type,
        MemorySurface.target_id.in_(target_ids),
    )
    if surface_kind is not None:
        statement = statement.where(MemorySurface.surface_kind == surface_kind)
    if status is not None:
        statement = statement.where(MemorySurface.status == status)
    statement = statement.order_by(
        MemorySurface.updated_at.desc(),
        MemorySurface.id,
    ).limit(limit)
    return list(db.exec(statement).all())


def get_embedding_vector_by_key(
    db: Session,
    *,
    object_key: str,
) -> EmbeddingVector | None:
    statement = select(EmbeddingVector).where(EmbeddingVector.object_key == object_key)
    return db.exec(statement).first()


def upsert_embedding_vector(
    db: Session,
    *,
    object_key: str,
    provider: str,
    model: str,
    input_hash: str,
    vector: list[float],
    input_kind: str = "memory_surface",
    source_surface_id: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    surface_kind: str | None = None,
    status: str = "active",
    metadata: dict[str, Any] | None = None,
) -> tuple[EmbeddingVector, bool]:
    existing = get_embedding_vector_by_key(db, object_key=object_key)
    normalized_metadata = metadata or {}
    vector_dim = len(vector)
    if existing is None:
        record = EmbeddingVector(
            object_key=object_key,
            provider=provider,
            model=model,
            input_hash=input_hash,
            input_kind=input_kind,
            vector_dim=vector_dim,
            vector_json=vector,
            source_surface_id=source_surface_id,
            target_type=target_type,
            target_id=target_id,
            surface_kind=surface_kind,
            status=status,
            metadata_json=normalized_metadata,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record, True

    changed = any(
        [
            existing.provider != provider,
            existing.model != model,
            existing.input_hash != input_hash,
            existing.input_kind != input_kind,
            existing.vector_dim != vector_dim,
            existing.vector_json != vector,
            existing.source_surface_id != source_surface_id,
            existing.target_type != target_type,
            existing.target_id != target_id,
            existing.surface_kind != surface_kind,
            existing.status != status,
            existing.metadata_json != normalized_metadata,
        ]
    )
    if changed:
        existing.provider = provider
        existing.model = model
        existing.input_hash = input_hash
        existing.input_kind = input_kind
        existing.vector_dim = vector_dim
        existing.vector_json = vector
        existing.source_surface_id = source_surface_id
        existing.target_type = target_type
        existing.target_id = target_id
        existing.surface_kind = surface_kind
        existing.status = status
        existing.metadata_json = normalized_metadata
        existing.updated_at = utc_now()
        db.add(existing)
        db.commit()
        db.refresh(existing)
    return existing, False


def mark_memory_surface_embedded(
    db: Session,
    *,
    surface_id: str,
    embedding_model: str,
    embedding_vector_id: str,
) -> MemorySurface | None:
    surface = db.get(MemorySurface, surface_id)
    if surface is None:
        return None

    changed = any(
        [
            surface.embedding_status != "embedded",
            surface.embedding_model != embedding_model,
            surface.embedding_vector_id != embedding_vector_id,
        ]
    )
    if changed:
        surface.embedding_status = "embedded"
        surface.embedding_model = embedding_model
        surface.embedding_vector_id = embedding_vector_id
        surface.updated_at = utc_now()
        db.add(surface)
        db.commit()
        db.refresh(surface)
    return surface


def upsert_memory_graph_node(
    db: Session,
    *,
    node_key: str,
    node_type: str,
    label: str,
    scope: str | None = None,
    status: str = "active",
    aliases: list[str] | None = None,
    source_memory_id: str | None = None,
    source_fact_id: str | None = None,
    source_session_id: str | None = None,
    confidence: float = 0.7,
    salience: float = 0.7,
    metadata: dict[str, Any] | None = None,
) -> tuple[MemoryGraphNode, bool]:
    existing = get_memory_graph_node_by_key(db, node_key=node_key)
    normalized_aliases = aliases or []
    normalized_metadata = metadata or {}
    if existing is None:
        node = MemoryGraphNode(
            node_key=node_key,
            node_type=node_type,
            label=label,
            scope=scope,
            status=status,
            aliases_json=normalized_aliases,
            source_memory_id=source_memory_id,
            source_fact_id=source_fact_id,
            source_session_id=source_session_id,
            confidence=confidence,
            salience=salience,
            metadata_json=normalized_metadata,
        )
        db.add(node)
        db.commit()
        db.refresh(node)
        return node, True

    changed = any(
        [
            existing.node_type != node_type,
            existing.label != label,
            existing.scope != scope,
            existing.status != status,
            existing.aliases_json != normalized_aliases,
            existing.source_memory_id != source_memory_id,
            existing.source_fact_id != source_fact_id,
            existing.source_session_id != source_session_id,
            existing.confidence != confidence,
            existing.salience != salience,
            existing.metadata_json != normalized_metadata,
        ]
    )
    if changed:
        existing.node_type = node_type
        existing.label = label
        existing.scope = scope
        existing.status = status
        existing.aliases_json = normalized_aliases
        existing.source_memory_id = source_memory_id
        existing.source_fact_id = source_fact_id
        existing.source_session_id = source_session_id
        existing.confidence = confidence
        existing.salience = salience
        existing.metadata_json = normalized_metadata
        existing.updated_at = utc_now()
        db.add(existing)
        db.commit()
        db.refresh(existing)
    return existing, False


def get_memory_graph_node_by_key(
    db: Session,
    *,
    node_key: str,
) -> MemoryGraphNode | None:
    statement = select(MemoryGraphNode).where(MemoryGraphNode.node_key == node_key)
    return db.exec(statement).first()


def list_memory_graph_nodes(
    db: Session,
    *,
    node_type: str | None = None,
    source_memory_id: str | None = None,
    source_fact_id: str | None = None,
    source_session_id: str | None = None,
    limit: int = 100,
) -> list[MemoryGraphNode]:
    statement = select(MemoryGraphNode)
    if node_type is not None:
        statement = statement.where(MemoryGraphNode.node_type == node_type)
    if source_memory_id is not None:
        statement = statement.where(MemoryGraphNode.source_memory_id == source_memory_id)
    if source_fact_id is not None:
        statement = statement.where(MemoryGraphNode.source_fact_id == source_fact_id)
    if source_session_id is not None:
        statement = statement.where(
            MemoryGraphNode.source_session_id == source_session_id
        )
    statement = statement.order_by(
        MemoryGraphNode.updated_at.desc(),
        MemoryGraphNode.id,
    ).limit(limit)
    return list(db.exec(statement).all())


def upsert_memory_graph_edge(
    db: Session,
    *,
    edge_key: str,
    source_node_id: str,
    target_node_id: str,
    relation: str,
    status: str = "active",
    confidence: float = 0.7,
    salience: float = 0.7,
    source_memory_id: str | None = None,
    source_fact_id: str | None = None,
    source_session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> tuple[MemoryGraphEdge, bool]:
    existing = get_memory_graph_edge_by_key(db, edge_key=edge_key)
    normalized_metadata = metadata or {}
    if existing is None:
        edge = MemoryGraphEdge(
            edge_key=edge_key,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            relation=relation,
            status=status,
            confidence=confidence,
            salience=salience,
            source_memory_id=source_memory_id,
            source_fact_id=source_fact_id,
            source_session_id=source_session_id,
            metadata_json=normalized_metadata,
        )
        db.add(edge)
        db.commit()
        db.refresh(edge)
        return edge, True

    changed = any(
        [
            existing.source_node_id != source_node_id,
            existing.target_node_id != target_node_id,
            existing.relation != relation,
            existing.status != status,
            existing.confidence != confidence,
            existing.salience != salience,
            existing.source_memory_id != source_memory_id,
            existing.source_fact_id != source_fact_id,
            existing.source_session_id != source_session_id,
            existing.metadata_json != normalized_metadata,
        ]
    )
    if changed:
        existing.source_node_id = source_node_id
        existing.target_node_id = target_node_id
        existing.relation = relation
        existing.status = status
        existing.confidence = confidence
        existing.salience = salience
        existing.source_memory_id = source_memory_id
        existing.source_fact_id = source_fact_id
        existing.source_session_id = source_session_id
        existing.metadata_json = normalized_metadata
        existing.updated_at = utc_now()
        db.add(existing)
        db.commit()
        db.refresh(existing)
    return existing, False


def get_memory_graph_edge_by_key(
    db: Session,
    *,
    edge_key: str,
) -> MemoryGraphEdge | None:
    statement = select(MemoryGraphEdge).where(MemoryGraphEdge.edge_key == edge_key)
    return db.exec(statement).first()


def list_memory_graph_edges(
    db: Session,
    *,
    source_node_id: str | None = None,
    target_node_id: str | None = None,
    relation: str | None = None,
    source_memory_id: str | None = None,
    source_fact_id: str | None = None,
    source_session_id: str | None = None,
    limit: int = 100,
) -> list[MemoryGraphEdge]:
    statement = select(MemoryGraphEdge)
    if source_node_id is not None:
        statement = statement.where(MemoryGraphEdge.source_node_id == source_node_id)
    if target_node_id is not None:
        statement = statement.where(MemoryGraphEdge.target_node_id == target_node_id)
    if relation is not None:
        statement = statement.where(MemoryGraphEdge.relation == relation)
    if source_memory_id is not None:
        statement = statement.where(MemoryGraphEdge.source_memory_id == source_memory_id)
    if source_fact_id is not None:
        statement = statement.where(MemoryGraphEdge.source_fact_id == source_fact_id)
    if source_session_id is not None:
        statement = statement.where(
            MemoryGraphEdge.source_session_id == source_session_id
        )
    statement = statement.order_by(
        MemoryGraphEdge.updated_at.desc(),
        MemoryGraphEdge.id,
    ).limit(limit)
    return list(db.exec(statement).all())


def _touch_session(
    db: Session,
    session_id: str,
    *,
    at: datetime | None = None,
) -> None:
    chat_session = db.get(ChatSession, session_id)
    if chat_session is not None:
        chat_session.updated_at = at or utc_now()
        db.add(chat_session)


def _matching_replacement_fact(
    fact: MemoryFact,
    replacement_facts: list[MemoryFact],
) -> MemoryFact | None:
    for candidate in replacement_facts:
        if candidate.entity == fact.entity and candidate.predicate == fact.predicate:
            return candidate
    return None
