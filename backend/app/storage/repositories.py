from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlmodel import Session, select

from app.storage.models import (
    AppSetting,
    ChatSession,
    CognitiveEvent,
    MaintenanceJob,
    MemoryFact,
    MemoryRecord,
    Message,
    SessionSummary,
    ToolCall,
    Trace,
    Turn,
    utc_now,
)


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
        MemoryFact.salience.desc(),
        MemoryFact.recorded_at.desc(),
        MemoryFact.id,
    )
    return list(db.exec(statement).all())


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
    if not include_low_confidence:
        statement = statement.where(MemoryRecord.confidence >= 0.2)
    statement = statement.order_by(
        MemoryRecord.salience.desc(),
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
        MemoryRecord.salience.desc(),
        MemoryRecord.id,
    )
    return list(db.exec(statement).all())


def list_all_memories(
    db: Session,
    *,
    include_low_confidence: bool = False,
) -> list[MemoryRecord]:
    statement = select(MemoryRecord)
    if not include_low_confidence:
        statement = statement.where(MemoryRecord.confidence >= 0.2)
    statement = statement.order_by(
        MemoryRecord.salience.desc(),
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
