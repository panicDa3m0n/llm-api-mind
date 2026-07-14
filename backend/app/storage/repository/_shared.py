"""Small persistence helpers shared by repository domains."""

from __future__ import annotations

from datetime import datetime

from sqlmodel import Session

from app.storage.models import ChatSession, utc_now


def touch_session(
    db: Session,
    session_id: str,
    *,
    at: datetime | None = None,
) -> None:
    """Mark a session as recently changed within the caller's transaction."""

    chat_session = db.get(ChatSession, session_id)
    if chat_session is not None:
        chat_session.updated_at = at or utc_now()
        db.add(chat_session)
