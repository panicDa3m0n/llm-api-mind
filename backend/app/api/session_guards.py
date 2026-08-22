"""Shared HTTP guards for persisted chat-session resources."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlmodel import Session

from app.storage import repositories
from app.storage.models import ChatSession


def require_chat_session(db: Session, session_id: str) -> ChatSession:
    """Return a session or raise the canonical recoverable 404 envelope."""

    chat_session = repositories.get_chat_session(db, session_id)
    if chat_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "session.not_found",
                "message": f"Session {session_id} was not found.",
                "recoverable": True,
            },
        )
    return chat_session
