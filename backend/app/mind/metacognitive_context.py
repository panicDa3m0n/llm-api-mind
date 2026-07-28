from datetime import datetime, timezone
from typing import Any

from app.runtime.preferences import RuntimePreferences
from app.storage.models import ChatSession, Message


METACOGNITIVE_CONTEXT_VERSION = "metacognitive-context-observation-v2"


def build_metacognitive_context_payload(
    *,
    chat_session: ChatSession,
    turn_id: str,
    current_user_message: Message,
    history: list[Message],
    memory_context: dict[str, Any],
    timestamp: datetime,
    runtime_preferences: RuntimePreferences,
    mode: str = "shadow",
    max_lessons: int = 3,
) -> dict[str, Any]:
    """Record metacognitive inputs without lexically classifying the turn.

    Semantic metacognition belongs to Scarlet through ``metacognition step``.
    The backend keeps this observational seam so experiments remain traceable,
    but it no longer infers intent or injects advice from keyword patterns.
    """

    normalized_mode = _normalize_mode(mode)
    return {
        "operation": "metacognitive.context",
        "schema_version": METACOGNITIVE_CONTEXT_VERSION,
        "mode": normalized_mode,
        "model_facing": False,
        "generated_at": timestamp.astimezone(timezone.utc).isoformat(),
        "session_id": chat_session.id,
        "turn_id": turn_id,
        "source": "backend.metacognitive_observation",
        "policy": {
            "purpose": (
                "Observable metacognitive inputs only. The backend does not "
                "classify natural-language intent or prescribe reasoning."
            ),
            "semantic_authority": "scarlet_via_metacognition_step",
            "injection_policy": "disabled_without_semantic_component",
            "lexical_triggering": False,
        },
        "selection": {
            "selected_count": 0,
            "max_lessons": max_lessons,
            "negative_evidence": "no_backend_semantic_lesson_selection",
        },
        "triggers": [],
        "lessons": [],
        "runtime_inputs": {
            "message_chars": len(current_user_message.content),
            "visible_history_messages": len(
                [
                    message
                    for message in history
                    if message.role in {"user", "assistant"}
                ]
            ),
            "memory_selected_count": memory_context.get("selected_count", 0),
            "memory_near_miss_count": len(memory_context.get("near_miss", [])),
            "runtime_language": runtime_preferences.language,
        },
    }


def metacognitive_context_runtime_block(
    metacognitive_context: dict[str, Any],
) -> dict[str, Any]:
    """Return no model block until semantic metacognition owns the content."""

    return {
        "id": "turn.metacognitive_context",
        "type": "metacognitive_context",
        "scope": "turn",
        "lifetime": "turn",
        "source": "backend.metacognitive_observation",
        "content": {
            "policy": metacognitive_context.get("policy", {}),
            "selection": metacognitive_context.get("selection", {}),
            "triggers": [],
            "lessons": [],
        },
    }


def _normalize_mode(mode: str) -> str:
    lowered = mode.strip().lower()
    if lowered in {"off", "shadow", "inject"}:
        return lowered
    return "shadow"
