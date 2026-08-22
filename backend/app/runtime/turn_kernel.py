"""Shared lifecycle kernel for native human and autonomous model turns.

Adapters own how a turn begins and how its result is presented.  Once a
source message and canonical provider history exist, this module owns the
common cognitive turn contract: context construction, history routing,
accounting, traceability, final persistence, and compaction scheduling.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.api.chat_accounting import (
    context_accounting_summary,
    post_turn_model_history_tokens,
    provider_message_stats,
    record_context_accounting_observed,
    record_context_accounting_preflight,
)
from app.api.chat_provider_history import updated_provider_history
from app.api.chat_serialization import (
    event_stream_payload,
    incomplete_result_details,
    response_event_messages,
)
from app.config import Settings
from app.llm.provider import LLMIncompleteResponseError, LLMMessage, LLMTextResult
from app.mind.context import MemoryContextBuild, build_memory_context
from app.mind.schema import MIND_SHELL_TOOL_SCHEMA
from app.runtime.events import record_event, record_response_content_events
from app.runtime.context_events import record_context_build_events
from app.runtime.history_compaction import build_chronology_source_map
from app.runtime.history_runtime import HistoryRoutingResult, route_history_for_model
from app.runtime.maintenance import (
    schedule_history_compaction,
    schedule_session_idle_maintenance,
)
from app.runtime.preferences import RuntimePreferences, load_runtime_preferences
from app.storage import repositories
from app.storage.models import ChatSession, CognitiveEvent, Message


@dataclass
class ModelTurnPreparation:
    session_id: str
    turn_id: str
    source_message_id: str
    model: str
    started: float
    trace_ids: list[str]
    canonical_messages: list[LLMMessage]
    model_messages: list[LLMMessage]
    effective_system: str
    max_tokens: int
    memory_context: MemoryContextBuild
    accounting_trace_id: str
    accounting_payload: dict[str, Any]
    history_routing: HistoryRoutingResult
    stream: bool
    entrypoint: str
    runtime_trigger: str
    response_visibility: str


@dataclass(frozen=True)
class ModelTurnCompletion:
    assistant_message_id: str
    completed_turn_id: str
    response_trace_id: str
    turn_completed_event_id: str
    latency_ms: int
    runtime_events: list[dict[str, Any]]


def prepare_model_turn(
    db: Session,
    *,
    settings: Settings,
    chat_session: ChatSession,
    turn_id: str,
    source_message: Message,
    history: list[Message],
    canonical_messages: list[LLMMessage],
    provider_history_source: str,
    base_system: str,
    system_source: str,
    system_path: str | None,
    model: str,
    max_tokens: int,
    started: float,
    stream: bool,
    entrypoint: str,
    accounting_transport: str,
    runtime_trigger: str = "human_message",
    now: datetime | None = None,
    runtime_preferences: RuntimePreferences | None = None,
    retrieval_dialogue: list[dict[str, Any]] | None = None,
    context_event_visibility: str = "debug",
    request_event_visibility: str = "debug",
    request_event_status: str = "completed",
    request_metadata: dict[str, Any] | None = None,
    response_visibility: str = "public",
) -> ModelTurnPreparation:
    """Compile the exact model request from a persisted source message."""

    trace_ids: list[str] = []
    preferences = runtime_preferences or load_runtime_preferences(db, settings)
    memory_context = build_memory_context(
        db,
        chat_session=chat_session,
        turn_id=turn_id,
        current_user_message=source_message,
        history=history,
        now=now,
        runtime_preferences=preferences,
        settings=settings,
        runtime_trigger=runtime_trigger,
        retrieval_dialogue=retrieval_dialogue,
    )
    trace_ids.append(memory_context.trace_id)
    if memory_context.metacognitive_trace_id is not None:
        trace_ids.append(memory_context.metacognitive_trace_id)
    trace_ids.append(memory_context.runtime_trace_id)
    if memory_context.model_context_trace_id is not None:
        trace_ids.append(memory_context.model_context_trace_id)
    record_context_build_events(
        db,
        session_id=chat_session.id,
        turn_id=turn_id,
        memory_context=memory_context,
        visibility=context_event_visibility,
    )

    history_routing = route_history_for_model(
        db,
        session_id=chat_session.id,
        canonical_messages=canonical_messages,
        chars_per_token=float(settings.context_estimated_chars_per_token),
        mode=str(settings.history_compaction_mode),
    )
    model_messages = history_routing.model_messages
    message_stats = provider_message_stats(model_messages)
    history_routing_trace_id: str | None = None
    if settings.history_compaction_mode == "active":
        history_routing_trace = repositories.add_trace(
            db,
            session_id=chat_session.id,
            turn_id=turn_id,
            kind="history.routing",
            payload=history_routing.payload,
        )
        history_routing_trace_id = history_routing_trace.id
        trace_ids.append(history_routing_trace_id)
        record_event(
            db,
            session_id=chat_session.id,
            turn_id=turn_id,
            event_type="history.routing.resolved",
            payload=history_routing.payload,
            source="runtime",
            actor="backend",
            visibility=context_event_visibility,
            trace_id=history_routing_trace_id,
        )

    effective_system = compose_system_with_runtime_context(
        base_system,
        memory_context.runtime_context,
    ) + history_routing.system_appendix
    accounting_trace, accounting_payload = record_context_accounting_preflight(
        db,
        session_id=chat_session.id,
        turn_id=turn_id,
        model=model,
        transport=accounting_transport,
        base_system=base_system,
        runtime_context=memory_context.runtime_context,
        messages=model_messages,
        settings=settings,
        compacted_chronology=history_routing.system_appendix,
    )
    accounting_trace_id = accounting_trace.id
    trace_ids.append(accounting_trace_id)
    effective_provider_history_source = (
        "history_compaction_artifact"
        if history_routing.payload.get("status") == "derived_history_active"
        else provider_history_source
    )
    request_payload: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "system": effective_system,
        "base_system": base_system,
        "system_present": True,
        "system_source": system_source,
        "system_path": system_path,
        "runtime_context_present": True,
        "runtime_context": memory_context.runtime_context,
        "memory_context_trace_id": memory_context.trace_id,
        "metacognitive_context_trace_id": memory_context.metacognitive_trace_id,
        "metacognitive_context_mode": (memory_context.metacognitive_payload or {}).get(
            "mode"
        ),
        "metacognitive_context_model_facing": (
            memory_context.metacognitive_payload or {}
        ).get("model_facing", False),
        "runtime_context_trace_id": memory_context.runtime_trace_id,
        "model_context_profile": memory_context.model_context_profile,
        "model_context_trace_id": memory_context.model_context_trace_id,
        "context_accounting_trace_id": accounting_trace_id,
        "context_accounting": context_accounting_summary(accounting_payload),
        "tool_loop_policy": "model_controlled_unbounded",
        "provider_history_source": effective_provider_history_source,
        "canonical_provider_history_source": provider_history_source,
        "history_routing_trace_id": history_routing_trace_id,
        "history_routing": history_routing.payload,
        "provider_message_stats": message_stats,
        "canonical_provider_messages": [
            item.model_dump(mode="json") for item in canonical_messages
        ],
        "provider_messages": [
            item.model_dump(mode="json") for item in model_messages
        ],
        "messages": [
            {"id": item.id, "role": item.role, "content": item.content}
            for item in history
            if item.role in {"user", "assistant"}
        ],
        "tools": [MIND_SHELL_TOOL_SCHEMA],
        "finality_contract": {
            "provider_terminal_stop_reason": "end_turn",
            "response_required": True,
            "response_visibility": response_visibility,
            "semantic_validation": False,
        },
    }
    if stream:
        request_payload["stream"] = True
    if request_metadata:
        request_payload.update(request_metadata)
    request_trace = repositories.add_trace(
        db,
        session_id=chat_session.id,
        turn_id=turn_id,
        kind="llm.request",
        payload=request_payload,
    )
    trace_ids.append(request_trace.id)
    request_event_payload: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "provider_history_source": effective_provider_history_source,
        "history_routing_status": history_routing.payload.get("status"),
        "history_routing_trace_id": history_routing_trace_id,
        "provider_message_stats": message_stats,
        "context_accounting_trace_id": accounting_trace_id,
        "estimated_input_tokens": accounting_payload["total"]["estimated_input_tokens"],
        "tool_count": 1,
    }
    if stream:
        request_event_payload["stream"] = True
    if request_metadata:
        request_event_payload.update(request_metadata)
    record_event(
        db,
        session_id=chat_session.id,
        turn_id=turn_id,
        event_type="llm.request.created",
        payload=request_event_payload,
        source="llm",
        actor="backend",
        visibility=request_event_visibility,
        status=request_event_status,
        trace_id=request_trace.id,
    )
    return ModelTurnPreparation(
        session_id=chat_session.id,
        turn_id=turn_id,
        source_message_id=source_message.id,
        model=model,
        started=started,
        trace_ids=trace_ids,
        canonical_messages=canonical_messages,
        model_messages=model_messages,
        effective_system=effective_system,
        max_tokens=max_tokens,
        memory_context=memory_context,
        accounting_trace_id=accounting_trace_id,
        accounting_payload=accounting_payload,
        history_routing=history_routing,
        stream=stream,
        entrypoint=entrypoint,
        runtime_trigger=runtime_trigger,
        response_visibility=response_visibility,
    )


def complete_model_turn(
    *,
    settings: Settings,
    engine: Engine,
    prepared: ModelTurnPreparation,
    result: LLMTextResult,
    semantic_content_event_seen: bool = False,
    assistant_metadata: dict[str, Any] | None = None,
    response_metadata: dict[str, Any] | None = None,
    assistant_event_source: str = "chat",
    assistant_event_visibility: str = "public",
    response_event_visibility: str = "debug",
    turn_event_visibility: str = "debug",
    schedule_idle_maintenance: bool = True,
) -> ModelTurnCompletion:
    """Persist a successful model turn under the shared lifecycle contract."""

    latency_ms = int((time.perf_counter() - prepared.started) * 1000)
    runtime_events: list[dict[str, Any]] = []
    with Session(engine) as db:
        message_metadata = {
            "model": result.model,
            "usage": result.usage,
            "stop_reason": result.stop_reason,
            "completion_recovery": result.completion_recovery,
        }
        if assistant_metadata:
            message_metadata.update(assistant_metadata)
        assistant_message = repositories.add_message(
            db,
            session_id=prepared.session_id,
            turn_id=prepared.turn_id,
            role="assistant",
            content=result.text,
            provider_message_id=result.provider_message_id,
            raw_content=result.raw_content,
            metadata=message_metadata,
        )
        assistant_message_id = assistant_message.id
        assistant_content_chars = len(assistant_message.content)
        response_payload: dict[str, Any] = {
            "model": result.model,
            "text": result.text,
            "usage": result.usage,
            "provider_message_id": result.provider_message_id,
            "stop_reason": result.stop_reason,
            "raw_content": result.raw_content,
            "tool_calls": [
                tool_call.model_dump(mode="json") for tool_call in result.tool_calls
            ],
            "raw_provider_messages": result.raw_provider_messages,
            "completion_recovery": result.completion_recovery,
            "finality_contract": {
                "accepted": result.stop_reason == "end_turn",
                "source": "provider_stop_reason",
                "response_visibility": prepared.response_visibility,
                "semantic_validation": False,
            },
        }
        if prepared.stream:
            response_payload["stream"] = True
        if response_metadata:
            response_payload.update(response_metadata)
        response_trace = repositories.add_trace(
            db,
            session_id=prepared.session_id,
            turn_id=prepared.turn_id,
            kind="llm.response",
            payload=response_payload,
        )
        response_trace_id = response_trace.id
        prepared.trace_ids.append(response_trace_id)
        observed_trace = record_context_accounting_observed(
            db,
            session_id=prepared.session_id,
            turn_id=prepared.turn_id,
            preflight_trace_id=prepared.accounting_trace_id,
            preflight=prepared.accounting_payload,
            result=result,
        )
        prepared.trace_ids.append(observed_trace.id)
        completed_event_payload: dict[str, Any] = {
            "model": result.model,
            "provider_message_id": result.provider_message_id,
            "stop_reason": result.stop_reason,
            "usage": result.usage,
            "tool_call_count": len(result.tool_calls),
            "completion_recovery": result.completion_recovery,
        }
        if prepared.stream:
            completed_event_payload["stream"] = True
        response_completed_event = record_event(
            db,
            session_id=prepared.session_id,
            turn_id=prepared.turn_id,
            event_type="llm.response.completed",
            payload=completed_event_payload,
            source="llm",
            actor="backend",
            visibility=response_event_visibility,
            trace_id=response_trace_id,
        )
        assistant_persisted_event = record_event(
            db,
            session_id=prepared.session_id,
            turn_id=prepared.turn_id,
            event_type="message.assistant.persisted",
            payload={
                "message_id": assistant_message_id,
                "content_chars": assistant_content_chars,
            },
            source=assistant_event_source,
            actor="scarlet",
            visibility=assistant_event_visibility,
            message_id=assistant_message_id,
        )
        if prepared.stream:
            runtime_events.extend(
                [
                    event_stream_payload(response_completed_event),
                    event_stream_payload(assistant_persisted_event),
                ]
            )

        if not semantic_content_event_seen:
            content_events = record_response_content_events(
                db,
                session_id=prepared.session_id,
                turn_id=prepared.turn_id,
                raw_provider_messages=response_event_messages(result),
                response_trace_id=response_trace_id,
                assistant_message_id=assistant_message_id,
                assistant_visibility=assistant_event_visibility,
            )
            if prepared.stream:
                runtime_events.extend(
                    event_stream_payload(event) for event in content_events
                )

        repositories.update_chat_session_provider_history(
            db,
            session_id=prepared.session_id,
            provider_history=updated_provider_history(
                prepared.canonical_messages,
                result,
            ),
        )
        completed_turn = repositories.complete_turn(
            db,
            turn_id=prepared.turn_id,
            latency_ms=latency_ms,
        )
        completed_turn_id = completed_turn.id
        turn_completed_payload: dict[str, Any] = {
            "latency_ms": latency_ms,
            "trace_ids": prepared.trace_ids,
        }
        if prepared.stream:
            turn_completed_payload["stream"] = True
        turn_completed_event = record_event(
            db,
            session_id=prepared.session_id,
            turn_id=prepared.turn_id,
            event_type="turn.completed",
            payload=turn_completed_payload,
            source="runtime",
            actor="backend",
            visibility=turn_event_visibility,
            status=completed_turn.status,
        )
        turn_completed_event_id = turn_completed_event.id
        if prepared.stream:
            runtime_events.append(event_stream_payload(turn_completed_event))

        chars_per_token = float(
            prepared.accounting_payload.get("calibration", {}).get(
                "chars_per_token_used",
                settings.context_estimated_chars_per_token,
            )
        )
        post_turn_source_map = build_chronology_source_map(
            db,
            session_id=prepared.session_id,
            chars_per_token=chars_per_token,
        )
        provider_channel_tokens = int(
            prepared.accounting_payload.get("channels", {})
            .get("provider_history", {})
            .get("estimated_tokens", 0)
        )
        external_context_tokens = max(
            0,
            int(
                prepared.accounting_payload.get("total", {}).get(
                    "estimated_input_tokens",
                    0,
                )
            )
            - provider_channel_tokens,
        )
        compaction_schedule = schedule_history_compaction(
            db,
            settings=settings,
            session_id=prepared.session_id,
            trigger_turn_id=prepared.turn_id,
            trigger_event_id=turn_completed_event_id,
            source_map=post_turn_source_map,
            external_context_tokens=external_context_tokens,
            chars_per_token=chars_per_token,
            model_history_tokens=post_turn_model_history_tokens(
                post_turn_source_map,
                prepared.history_routing.payload,
            ),
        )
        if prepared.stream and compaction_schedule is not None:
            _, compaction_event = compaction_schedule
            runtime_events.append(event_stream_payload(compaction_event))

        if schedule_idle_maintenance and settings.maintenance_enabled:
            maintenance_schedule = schedule_session_idle_maintenance(
                db,
                settings=settings,
                session_id=prepared.session_id,
                trigger_turn_id=prepared.turn_id,
                trigger_event_id=turn_completed_event_id,
            )
            if prepared.stream:
                _, maintenance_event = maintenance_schedule
                runtime_events.append(event_stream_payload(maintenance_event))

    return ModelTurnCompletion(
        assistant_message_id=assistant_message_id,
        completed_turn_id=completed_turn_id,
        response_trace_id=response_trace_id,
        turn_completed_event_id=turn_completed_event_id,
        latency_ms=latency_ms,
        runtime_events=runtime_events,
    )


def record_failed_model_turn(
    engine: Engine,
    *,
    prepared: ModelTurnPreparation,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    visibility: str = "debug",
) -> CognitiveEvent:
    """Close a started model turn with the same traceable failure receipt."""

    latency_ms = int((time.perf_counter() - prepared.started) * 1000)
    error: dict[str, Any] = {"code": code, "message": message}
    if details:
        error["details"] = details
    with Session(engine) as db:
        trace = repositories.add_trace(
            db,
            session_id=prepared.session_id,
            turn_id=prepared.turn_id,
            kind="llm.error",
            payload=error,
        )
        completed = repositories.complete_turn(
            db,
            turn_id=prepared.turn_id,
            status="failed",
            latency_ms=latency_ms,
            error=error,
        )
        return record_event(
            db,
            session_id=prepared.session_id,
            turn_id=prepared.turn_id,
            event_type="turn.failed",
            payload={**error, "latency_ms": latency_ms},
            source="runtime",
            actor="backend",
            visibility=visibility,
            status=completed.status,
            trace_id=trace.id,
        )


def require_terminal_end_turn(result: LLMTextResult) -> LLMTextResult:
    """Accept only the provider-native terminal lifecycle signal."""

    if result.stop_reason != "end_turn":
        raise LLMIncompleteResponseError(
            "The provider did not close the turn with end_turn.",
            details={
                "reason": "non_terminal_provider_result",
                "stop_reason": result.stop_reason,
                "provider_message_id": result.provider_message_id,
                "recoverable": False,
            },
        )
    return result


def require_terminal_response(result: LLMTextResult) -> LLMTextResult:
    """Apply the complete structural finality contract for a model turn.

    A terminal stop reason alone is insufficient when the caller's contract
    requires an answer or a private internal checkpoint. This checks only that
    a response exists; it deliberately does not assess its wording or meaning.
    """

    result = require_terminal_end_turn(result)
    if not result.text.strip():
        raise LLMIncompleteResponseError(
            "The provider ended without a required response.",
            details=incomplete_result_details(result),
        )
    return result


def compose_system_with_runtime_context(system: str, runtime_context: str) -> str:
    return f"{system.rstrip()}\n\n{runtime_context.strip()}"
