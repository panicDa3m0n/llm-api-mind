"""Deterministic provenance shared by every model-facing lifecycle."""

from __future__ import annotations

from typing import Any

from sqlmodel import Session

from app.storage import repositories
from app.storage.models import ChatSession, Message, Turn


HUMAN_SESSION_KIND = "human_dialogue"
AUTONOMOUS_SESSION_KIND = "scarlet_autonomous"


def project_turn_origin(
    db: Session,
    *,
    chat_session: ChatSession,
    turn_id: str | None,
    message: Message | None,
    runtime_trigger: str | None = None,
) -> dict[str, Any]:
    turn = repositories.get_turn(db, turn_id) if turn_id else None
    trigger = runtime_trigger or (turn.trigger_kind if turn is not None else None)
    return {
        "origin": classify_origin(
            chat_session=chat_session,
            turn=turn,
            message=message,
            runtime_trigger=trigger,
        ),
        "session_id": chat_session.id,
        "session_kind": chat_session.kind,
        "turn_id": turn_id,
        "turn_trigger": trigger,
        "turn_actor": turn.actor if turn is not None else None,
        "message_id": message.id if message is not None else None,
        "message_role": message.role if message is not None else None,
    }


def project_source_provenance(
    db: Session,
    *,
    session_id: str | None,
    turn_id: str | None,
    message_id: str | None,
) -> dict[str, Any]:
    chat_session = repositories.get_chat_session(db, session_id) if session_id else None
    turn = repositories.get_turn(db, turn_id) if turn_id else None
    message = repositories.get_message(db, message_id) if message_id else None
    status = _source_status(
        session_id=session_id,
        turn_id=turn_id,
        message_id=message_id,
        chat_session=chat_session,
        turn=turn,
        message=message,
    )
    return {
        "source_session_kind": chat_session.kind if chat_session is not None else None,
        "source_turn_trigger": turn.trigger_kind if turn is not None else None,
        "source_turn_actor": turn.actor if turn is not None else None,
        "source_message_role": message.role if message is not None else None,
        "source_provenance_status": status,
        "source_origin": (
            classify_origin(
                chat_session=chat_session,
                turn=turn,
                message=message,
                runtime_trigger=turn.trigger_kind if turn is not None else None,
            )
            if status != "inconsistent"
            else "unknown_legacy"
        ),
    }


def _source_status(
    *,
    session_id: str | None,
    turn_id: str | None,
    message_id: str | None,
    chat_session: ChatSession | None,
    turn: Turn | None,
    message: Message | None,
) -> str:
    requested = (session_id, turn_id, message_id)
    resolved = (chat_session, turn, message)
    if any(value is not None for value in requested) and any(
        expected is not None and actual is None
        for expected, actual in zip(requested, resolved)
    ):
        return "partial"
    if (
        (chat_session is not None and turn is not None and turn.session_id != chat_session.id)
        or (
            chat_session is not None
            and message is not None
            and message.session_id != chat_session.id
        )
        or (
            turn is not None
            and message is not None
            and message.turn_id != turn.id
        )
    ):
        return "inconsistent"
    if all(value is not None for value in resolved):
        return "complete"
    return "partial"


def classify_origin(
    *,
    chat_session: ChatSession | None,
    turn: Turn | None,
    message: Message | None,
    runtime_trigger: str | None,
) -> str:
    if (
        (chat_session is not None and chat_session.kind == AUTONOMOUS_SESSION_KIND)
        or runtime_trigger == "autonomous_activation"
        or (turn is not None and turn.trigger_kind == "autonomous_activation")
        or (message is not None and message.role == "activation")
    ):
        return "autonomous_cognition"
    if (
        (chat_session is not None and chat_session.kind == HUMAN_SESSION_KIND)
        or runtime_trigger == "human_message"
        or (turn is not None and turn.trigger_kind == "human_message")
        or (message is not None and message.role == "user")
    ):
        return "human_interaction"
    if runtime_trigger and "maintenance" in runtime_trigger:
        return "system_maintenance"
    return "unknown_legacy"
