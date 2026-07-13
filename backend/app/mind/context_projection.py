"""Compile the canonical V2 model context from collected runtime evidence."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlmodel import Session

from app.mind.context_contracts import ModelContextV2
from app.mind.context_memories import project_memory_context
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
) -> dict[str, Any]:
    preserved_types = {
        "focus_context",
        "affective_context",
        "scarlet_state",
        "metacognitive_context",
    }
    preserved = [
        block
        for block in legacy_runtime_payload.get("blocks", [])
        if block.get("type") in preserved_types
    ]
    message_block = next(
        (
            block
            for block in legacy_runtime_payload.get("blocks", [])
            if block.get("type") == "message_context"
        ),
        None,
    )
    if isinstance(message_block, dict):
        content = message_block.get("content")
        if isinstance(content, dict):
            preserved.append(
                {
                    "id": "turn.undiscussed_context",
                    "type": "undiscussed_context",
                    "scope": "turn",
                    "lifetime": "turn",
                    "source": "legacy_runtime_projection",
                    "content": {
                        key: content[key]
                        for key in (
                            "recent_dialogue",
                            "recent_runtime_events",
                            "api_mind",
                        )
                        if key in content
                    },
                }
            )
    document = ModelContextV2(
        session=project_session_context(
            db,
            chat_session=chat_session,
            now=now,
            preferences=preferences,
            previous_sessions_limit=settings.model_context_previous_sessions_limit,
        ),
        memories=project_memory_context(
            db,
            rich_memory_context=rich_memory_context,
            timezone_id=preferences.timezone,
            relevant_limit=settings.model_context_relevant_memories_limit,
            recent_user_limit=settings.model_context_recent_user_memories_limit,
            recent_general_limit=settings.model_context_recent_general_memories_limit,
        ),
        preserved_context=preserved,
    )
    return document.model_dump(mode="json")
