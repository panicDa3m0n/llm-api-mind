"""Compile the canonical V2 model context from collected runtime evidence."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlmodel import Session

from app.mind.context_contracts import ModelContextV2
from app.mind.context_memories import project_memory_context
from app.mind.context_preserved import (
    PreservedContextProjection,
    project_preserved_context,
)
from app.mind.context_sessions import project_session_context
from app.runtime.preferences import RuntimePreferences
from app.storage.models import ChatSession


def compile_model_context_v2(
    db: Session,
    *,
    chat_session: ChatSession,
    rich_memory_context: dict[str, Any],
    legacy_runtime_payload: dict[str, Any],
    now: datetime,
    preferences: RuntimePreferences,
    settings: Any,
    agent_mode: dict[str, Any] | None = None,
) -> dict[str, Any]:
    document, _ = compile_model_context_v2_with_audit(
        db,
        chat_session=chat_session,
        rich_memory_context=rich_memory_context,
        legacy_runtime_payload=legacy_runtime_payload,
        now=now,
        preferences=preferences,
        settings=settings,
        agent_mode=agent_mode,
    )
    return document


def compile_model_context_v2_with_audit(
    db: Session,
    *,
    chat_session: ChatSession,
    rich_memory_context: dict[str, Any],
    legacy_runtime_payload: dict[str, Any],
    now: datetime,
    preferences: RuntimePreferences,
    settings: Any,
    agent_mode: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    resolved_agent_mode = agent_mode or {
        "active_tag": "idle",
        "source": "projection_default",
        "resume_tag": None,
    }
    preserved: PreservedContextProjection = project_preserved_context(
        legacy_runtime_payload,
        timezone_id=preferences.timezone,
    )
    document = ModelContextV2(
        session=project_session_context(
            db,
            chat_session=chat_session,
            now=now,
            preferences=preferences,
            previous_sessions_limit=settings.model_context_previous_sessions_limit,
            agent_mode=resolved_agent_mode,
        ),
        memories=project_memory_context(
            db,
            rich_memory_context=rich_memory_context,
            timezone_id=preferences.timezone,
            relevant_limit=settings.model_context_relevant_memories_limit,
            recent_user_limit=settings.model_context_recent_user_memories_limit,
            recent_general_limit=settings.model_context_recent_general_memories_limit,
        ),
        preserved_context=preserved.blocks,
    )
    return document.model_dump(mode="json"), preserved.audit
