"""Compact model-facing context for one autonomous Scarlet activation."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlmodel import Session

from app.config import Settings
from app.mind.agent_modes import resolve_agent_mode
from app.mind.context_memories import project_memory_context
from app.mind.context_sessions import project_session_context
from app.runtime.preferences import RuntimePreferences
from app.storage import repositories
from app.storage.models import AutonomousActivation, ChatSession


AUTONOMOUS_CONTEXT_VERSION = "scarlet-autonomous-context-v1"


def build_autonomous_model_context(
    db: Session,
    *,
    activation: AutonomousActivation,
    chat_session: ChatSession,
    now: datetime,
    preferences: RuntimePreferences,
    settings: Settings,
) -> tuple[dict[str, Any], dict[str, Any]]:
    mode = resolve_agent_mode(
        db,
        profile_id=preferences.profile_id,
        default=settings.agent_mode_default,
    )
    recent_memories = project_memory_context(
        db,
        rich_memory_context={"selected": []},
        timezone_id=preferences.timezone,
        relevant_limit=settings.model_context_relevant_memories_limit,
        recent_user_limit=settings.model_context_recent_user_memories_limit,
        recent_general_limit=settings.model_context_recent_general_memories_limit,
    )
    focus = repositories.get_active_focus(
        db,
        owner_profile_id=preferences.profile_id,
    )
    open_intentions = repositories.list_open_intention_records(
        db,
        owner_profile_id=preferences.profile_id,
        limit=5,
    )
    due_intentions = repositories.list_due_intention_records(
        db,
        owner_profile_id=preferences.profile_id,
        now=now,
        include_unscheduled=False,
        limit=5,
    )
    affect = repositories.get_latest_affect_state(
        db,
        owner_profile_id=preferences.profile_id,
    )
    perception = repositories.perception_availability_index(
        db,
        profile_id=preferences.profile_id,
        session_id=chat_session.id,
    )
    context = {
        "schema_version": AUTONOMOUS_CONTEXT_VERSION,
        "activation": {
            "id": activation.id,
            "trigger_kind": activation.trigger_kind,
            "scheduled_at": activation.scheduled_at.isoformat(),
            "started_at": activation.started_at.isoformat()
            if activation.started_at
            else None,
            "nature": "backend_scheduled_autonomous_cognition",
            "is_human_message": False,
        },
        "continuity": project_session_context(
            db,
            chat_session=chat_session,
            now=now,
            preferences=preferences,
            previous_sessions_limit=settings.model_context_previous_sessions_limit,
            agent_mode=mode,
        ),
        "memories": recent_memories,
        "organs": {
            "focus": _focus_payload(focus),
            "open_intentions": [
                _intention_payload(item) for item in open_intentions
            ],
            "due_intentions": [
                _intention_payload(item) for item in due_intentions
            ],
            "affect": _affect_payload(affect),
        },
        "perception": {
            "availability_index": perception[
                : settings.autonomous_activation_perception_channel_limit
            ],
            "delivery": (
                "Availability only. Open a channel through mind_shell when its "
                "unseen evidence is useful; missing channels do not imply an "
                "external-world fact."
            ),
        },
        "operating_contract": {
            "active_mode": mode["active_tag"],
            "purpose": (
                "A real autonomous cognitive interval in Scarlet's persistent "
                "inner chronology, separate from human dialogue and maintenance."
            ),
            "allowed": [
                "inspect cognitive state",
                "navigate source sessions and memories",
                "review or update focus and volition",
                "inspect available perception channels",
                "write sourceable semantic memory when policy requires it",
                "choose idle or scouting mode through mind_shell",
            ],
            "forbidden": [
                "pretend a human sent this activation",
                "invent sensor evidence",
                "perform unimplemented external actions",
                "emit a user-facing chat reply",
            ],
            "tool_policy": (
                "Use mind_shell autonomously whenever evidence or a state change "
                "would improve this cycle. Emit a brief personal note before each "
                "tool call so the internal chronology remains legible."
            ),
            "completion": (
                "Finish with a concise internal checkpoint stating what mattered, "
                "what changed, and what remains open. This is not a message to the user."
            ),
        },
    }
    audit = {
        "profile_id": preferences.profile_id,
        "active_mode": mode["active_tag"],
        "previous_session_count": len(
            context["continuity"].get("previous_sessions", [])
        ),
        "recent_memory_counts": {
            key: len(value) for key, value in recent_memories.items()
        },
        "perception_channel_count": len(perception),
        "organ_presence": {
            "focus": focus is not None,
            "open_intentions": len(open_intentions),
            "due_intentions": len(due_intentions),
            "affect": affect is not None,
        },
    }
    return context, audit


def render_autonomous_context(context: dict[str, Any]) -> str:
    return (
        "<autonomous_runtime_context>\n"
        + json.dumps(context, ensure_ascii=True, indent=2)
        + "\n</autonomous_runtime_context>"
    )


def autonomous_activation_envelope(
    *,
    activation: AutonomousActivation,
    now: datetime,
) -> str:
    return (
        "[SCARLET AUTONOMOUS ACTIVATION]\n"
        f"Activation id: {activation.id}\n"
        f"Trigger: {activation.trigger_kind}\n"
        f"Runtime time: {now.isoformat()}\n"
        "This input was generated by the backend scheduler. It is not a human "
        "message and requires no user-facing reply. Live this cognitive interval "
        "using your available context and mind_shell, then leave one concise "
        "internal checkpoint."
    )


def _focus_payload(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    return {
        "id": value.id,
        "object": value.focus_object,
        "type": value.focus_type,
        "status": value.status,
        "intensity": value.intensity,
        "reason": value.reason,
        "source_session_id": value.source_session_id,
        "source_turn_id": value.source_turn_id,
        "source_message_id": value.source_message_id,
        "updated_at": value.updated_at.isoformat(),
    }


def _intention_payload(value: Any) -> dict[str, Any]:
    return {
        "id": value.id,
        "desire": value.desire,
        "status": value.status,
        "origin": value.origin,
        "horizon": value.horizon,
        "intensity": value.intensity,
        "reason": value.reason,
        "last_reviewed_at": value.last_reviewed_at.isoformat()
        if value.last_reviewed_at
        else None,
        "next_review_at": value.next_review_at.isoformat()
        if value.next_review_at
        else None,
    }


def _affect_payload(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    return {
        "id": value.id,
        "emotion": value.emotion,
        "intensity": value.intensity,
        "intensity_label": value.intensity_label,
        "valence": value.valence,
        "activation": value.activation,
        "causes": value.causes_json[:5],
        "updated_at": value.updated_at.isoformat(),
    }
