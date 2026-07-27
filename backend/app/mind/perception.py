"""Model-facing navigation over the append-only perception ledger."""

from __future__ import annotations

from typing import Any

from sqlmodel import Session

from app.mind.contracts import MemoryOperationResult, MindAPIContext
from app.storage import repositories


def handle_perception(
    body: dict[str, Any],
    context: MindAPIContext | None,
    *,
    intent: str,
) -> MemoryOperationResult:
    if context is None or context.engine is None:
        return _error(
            "perception.context_required",
            "Perception commands require an active Scarlet runtime context.",
        )
    profile_id = str(
        getattr(context.settings, "user_profile_id", None) or "local-user"
    )
    action = str(body.get("action") or "status").strip().casefold()
    with Session(context.engine) as db:
        if action == "status":
            channels = repositories.perception_availability_index(
                db,
                profile_id=profile_id,
                session_id=context.session_id,
            )
            return MemoryOperationResult(
                ok=True,
                result={
                    "operation": "perception.status",
                    "profile_id": profile_id,
                    "channel_count": len(channels),
                    "channels": channels,
                    "intent": intent,
                },
                cognitive_hint=(
                    "This is an availability index, not the sensory evidence "
                    "itself. Open only channels useful to the current cognition."
                ),
                suggested_next_actions=[
                    "perception open <channel> --limit 10",
                ],
            )

        if action == "open":
            if context.session_id is None:
                return _error(
                    "perception.session_required",
                    "Opening a channel requires a session-scoped cursor.",
                )
            channel = str(body.get("channel") or "").strip()
            if not channel:
                return _error(
                    "perception.channel_required",
                    "perception open requires a channel.",
                )
            limit = max(1, min(int(body.get("limit") or 10), 50))
            events = repositories.open_perception_channel(
                db,
                profile_id=profile_id,
                session_id=context.session_id,
                channel=channel,
                limit=limit,
            )
            return MemoryOperationResult(
                ok=True,
                result={
                    "operation": "perception.open",
                    "channel": channel,
                    "returned": len(events),
                    "events": [_event_payload(item) for item in events],
                    "cursor_advanced": bool(events),
                    "intent": intent,
                },
                cognitive_hint=(
                    "These are source-labelled observations. Treat them as "
                    "evidence from their declared channel, not as universal truth."
                ),
                suggested_next_actions=[
                    "perception status",
                    "perception read per_...",
                ],
            )

        if action == "read":
            event_id = str(body.get("event_id") or "").strip()
            event = repositories.get_perception_event(db, event_id)
            if event is None or event.profile_id != profile_id:
                return _error(
                    "perception.event_not_found",
                    f"Perception event not found: {event_id}",
                )
            return MemoryOperationResult(
                ok=True,
                result={
                    "operation": "perception.read",
                    "event": _event_payload(event),
                    "intent": intent,
                },
                cognitive_hint=(
                    "Use source, observed_at, and navigation fields when "
                    "triangulating this observation."
                ),
            )

    return _error(
        "perception.action_unknown",
        f"Unknown perception action: {action}",
    )


def _event_payload(event: Any) -> dict[str, Any]:
    return {
        "id": event.id,
        "channel": event.channel,
        "event_type": event.event_type,
        "source": event.source,
        "observed_at": event.observed_at.isoformat(),
        "received_at": event.received_at.isoformat(),
        "payload": event.payload_json,
        "navigation": event.navigation_json,
        "metadata": event.metadata_json,
    }


def _error(code: str, message: str) -> MemoryOperationResult:
    return MemoryOperationResult(
        ok=False,
        error_code=code,
        error_message=message,
        suggested_next_actions=["perception status", "help perception"],
    )
