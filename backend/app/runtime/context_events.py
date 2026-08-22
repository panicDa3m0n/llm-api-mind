"""Persist the shared observable receipts for a compiled turn context."""

from __future__ import annotations

from sqlmodel import Session

from app.api.chat_serialization import (
    memory_context_event_payload,
    metacognitive_context_event_payload,
    recent_memory_context_event_payload,
    runtime_context_event_payload,
    session_continuity_event_payload,
)
from app.mind.context import MemoryContextBuild
from app.runtime.events import record_event


def record_context_build_events(
    db: Session,
    *,
    session_id: str,
    turn_id: str,
    memory_context: MemoryContextBuild,
    visibility: str,
) -> None:
    """Write the context receipts shared by native, autonomous, and GPT turns."""

    record_event(
        db,
        session_id=session_id,
        turn_id=turn_id,
        event_type="memory.context.built",
        payload=memory_context_event_payload(memory_context.payload),
        source="memory",
        actor="backend",
        visibility=visibility,
        trace_id=memory_context.trace_id,
    )
    if memory_context.model_context_payload is not None:
        record_event(
            db,
            session_id=session_id,
            turn_id=turn_id,
            event_type="memory.recent_context.built",
            payload=recent_memory_context_event_payload(
                memory_context.model_context_payload
            ),
            source="memory",
            actor="backend",
            visibility=visibility,
            trace_id=memory_context.model_context_trace_id,
        )
        record_event(
            db,
            session_id=session_id,
            turn_id=turn_id,
            event_type="session.continuity.built",
            payload=session_continuity_event_payload(
                memory_context.model_context_payload
            ),
            source="session",
            actor="backend",
            visibility=visibility,
            trace_id=memory_context.model_context_trace_id,
        )
    if memory_context.metacognitive_payload is not None:
        record_event(
            db,
            session_id=session_id,
            turn_id=turn_id,
            event_type=(
                "metacognitive.context.injected"
                if memory_context.metacognitive_payload.get("model_facing") is True
                else "metacognitive.context.shadowed"
            ),
            payload=metacognitive_context_event_payload(
                memory_context.metacognitive_payload
            ),
            source="metacognition",
            actor="backend",
            visibility=visibility,
            trace_id=memory_context.metacognitive_trace_id,
        )
    record_event(
        db,
        session_id=session_id,
        turn_id=turn_id,
        event_type="runtime.context.built",
        payload=runtime_context_event_payload(memory_context.runtime_payload),
        source="runtime",
        actor="backend",
        visibility=visibility,
        trace_id=memory_context.runtime_trace_id,
    )
