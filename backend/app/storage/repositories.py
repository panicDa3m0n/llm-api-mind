from datetime import datetime
from typing import Any

from sqlmodel import Session, select

from app.storage.models import ChatSession, Message, Trace, Turn, utc_now


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


def list_traces_for_turn(db: Session, *, turn_id: str) -> list[Trace]:
    statement = (
        select(Trace)
        .where(Trace.turn_id == turn_id)
        .order_by(Trace.created_at, Trace.id)
    )
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

