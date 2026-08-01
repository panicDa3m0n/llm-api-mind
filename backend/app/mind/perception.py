"""Model-facing navigation over the append-only perception ledger."""

from __future__ import annotations

from typing import Any

from sqlmodel import Session

from app.mind.contracts import (
    LivePerceptionError,
    MemoryOperationResult,
    MindAPIContext,
)
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
    if action == "look":
        if context.settings is None:
            return _error(
                "perception.settings_required",
                "Camera perception requires runtime settings.",
            )
        if context.live_perception_capture is None:
            return _error(
                "perception.live_source_unavailable",
                "The active model transport has no live perception source attached.",
            )
        source = str(body.get("source") or "camera").strip().casefold()
        if source != "camera":
            return _error(
                "perception.source_unsupported",
                f"Unsupported live perception source: {source}",
            )
        try:
            seconds = float(
                body.get("seconds")
                or context.settings.camera_perception_default_window_seconds
            )
            metadata, provider_parts = context.live_perception_capture(
                context.settings,
                seconds,
            )
        except (LivePerceptionError, TypeError, ValueError) as exc:
            return _error("perception.camera_capture_failed", str(exc))
        return MemoryOperationResult(
            ok=True,
            result={
                "operation": "perception.look",
                "source": "camera",
                "observation": metadata,
                "provider_delivery": "attached_multimodal_content",
                "delivery_contract": {
                    "mode": "bounded_one_shot",
                    "included_modalities": ["video"],
                    "excluded_modalities": ["audio"],
                    "continuous_monitoring": False,
                },
                "intent": intent,
            },
            cognitive_hint=(
                "Inspect the attached current camera evidence directly. Treat "
                "its system interval as authoritative timing. This result has "
                "video only and is one bounded observation: do not infer sound, "
                "ongoing monitoring, memory, or automatic context."
            ),
            suggested_next_actions=[
                "perception look --source camera --seconds 3",
            ],
            provider_content_parts=provider_parts,
        )
    with Session(context.engine) as db:
        if action == "status":
            channels = repositories.perception_availability_index(
                db,
                profile_id=profile_id,
                session_id=context.session_id,
            )
            live_sources: list[dict[str, Any]] = []
            if (
                context.live_perception_capture is not None
                and context.settings is not None
                and bool(context.settings.camera_perception_enabled)
            ):
                live_sources.append(
                    {
                        "source": "camera",
                        "status": "available",
                        "access": "bounded_on_demand",
                        "command": "perception look --source camera --seconds 3",
                        "included_modalities": ["video"],
                        "excluded_modalities": ["audio"],
                        "continuous_monitoring": False,
                    }
                )
            return MemoryOperationResult(
                ok=True,
                result={
                    "operation": "perception.status",
                    "scope": "external_observation_channels",
                    "excludes": [
                        "autonomous_cognition",
                        "session_history",
                        "semantic_memory",
                    ],
                    "profile_id": profile_id,
                    "channel_count": len(channels),
                    "channels": channels,
                    "live_source_count": len(live_sources),
                    "live_sources": live_sources,
                    "intent": intent,
                },
                cognitive_hint=(
                    "Channels are persisted source-labelled observations; live "
                    "sources are separate bounded on-demand evidence. Neither "
                    "is autonomous chronology, session history, or semantic memory."
                ),
                suggested_next_actions=[
                    "perception open <channel> --limit 10",
                    *(
                        ["perception look --source camera --seconds 3"]
                        if live_sources
                        else []
                    ),
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
