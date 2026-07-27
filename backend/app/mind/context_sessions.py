"""Projection of compact session, user, and world hints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlmodel import Session

from app.mind.context_contracts import PreviousSessionHint
from app.mind.context_time import render_user_time, timezone_packet
from app.runtime.preferences import RuntimePreferences
from app.storage import repositories
from app.storage.models import ChatSession


MISSING_SUMMARY = "Sessione con riassunto mancante; ispeziona la sessione per vedere i dettagli."
STALE_SUMMARY = "Sessione con riassunto non aggiornato; ispeziona la sessione per vedere i dettagli."


def project_session_context(
    db: Session,
    *,
    chat_session: ChatSession,
    now: datetime,
    preferences: RuntimePreferences,
    previous_sessions_limit: int,
    agent_mode: dict[str, Any],
) -> dict[str, Any]:
    states = repositories.list_session_summary_states(
        db,
        exclude_session_id=chat_session.id,
        kind="human_dialogue",
        profile_id=preferences.profile_id,
    )
    previous: list[PreviousSessionHint] = []
    for state in states:
        if state.last_message_at is None:
            continue
        summary = MISSING_SUMMARY
        if state.summary_state == "current" and state.summary is not None:
            summary = state.summary.summary
        elif state.summary_state == "stale":
            summary = STALE_SUMMARY
        previous.append(
            PreviousSessionHint(
                id=state.chat_session.id,
                last_message_at=render_user_time(
                    state.last_message_at,
                    timezone_id=preferences.timezone,
                ),
                turn_count=state.turn_count,
                summary=summary,
            )
        )
        if len(previous) >= previous_sessions_limit:
            break

    return {
        "current_session": {
            "id": chat_session.id,
            "title": chat_session.title,
            "created_at": render_user_time(
                chat_session.created_at,
                timezone_id=preferences.timezone,
            ),
        },
        "user": {"name": preferences.user_display_name},
        "agent_mode": {
            "active_tag": agent_mode.get("active_tag"),
            "active_runtime_implemented": agent_mode.get(
                "active_runtime_implemented"
            ),
            "source": agent_mode.get("source"),
            "resume_tag": agent_mode.get("resume_tag"),
            "resume_runtime_implemented": agent_mode.get(
                "resume_runtime_implemented"
            ),
        },
        "now": render_user_time(now, timezone_id=preferences.timezone),
        "timezone": timezone_packet(now, timezone_id=preferences.timezone),
        "location": preferences.country_label,
        "previous_sessions": [item.model_dump(mode="json") for item in previous],
    }
