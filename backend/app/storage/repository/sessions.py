"""Persistence operations for chat sessions, turns, messages, traces, and tools."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlmodel import Session, select

from app.storage.models import (
    ChatSession,
    Message,
    SessionSummary,
    ToolCall,
    Trace,
    Turn,
    utc_now,
)
from app.storage.repository._shared import touch_session as _touch_session

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
