"""Persisted scheduler and MiniMax lifecycle for Scarlet's autonomous cognition."""

from __future__ import annotations

import logging
import json
import threading
import time
from collections.abc import Callable
from datetime import timedelta
from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.api.chat_native_turn import (
    build_mind_tool_runner,
    compose_system_with_runtime_context,
)
from app.api.chat_serialization import (
    memory_context_event_payload,
    recent_memory_context_event_payload,
    runtime_context_event_payload,
    session_continuity_event_payload,
)
from app.api.chat_provider_history import (
    updated_provider_history,
    valid_provider_history,
)
from app.config import Settings
from app.llm.factory import active_provider_max_tokens, active_provider_model
from app.llm.provider import LLMMessage, LLMProvider, LLMTextResult
from app.mind.context import build_memory_context
from app.mind.context_time import render_user_time
from app.mind.schema import MIND_SHELL_TOOL_SCHEMA
from app.prompts.system import resolve_agent_system_prompt
from app.runtime.events import (
    record_event,
    record_provider_stream_event,
    record_response_content_events,
)
from app.runtime.endogenous_cognition import record_endogenous_activation_feedback
from app.runtime.history_compaction import build_chronology_source_map
from app.runtime.history_runtime import route_history_for_model
from app.runtime.maintenance import schedule_history_compaction
from app.runtime.preferences import load_runtime_preferences
from app.runtime.cognitive_workspace import run_cognitive_workspace_tick
from app.storage import repositories
from app.storage.models import AutonomousActivation, ChatSession, Message, utc_now


logger = logging.getLogger(__name__)
ProviderFactory = Callable[[Settings], LLMProvider]
class AutonomousYieldToHuman(RuntimeError):
    """Stop an internal cycle when a human turn takes foreground priority."""


def run_due_autonomous_activations(
    engine: Engine,
    *,
    settings: Settings,
    provider_factory: ProviderFactory,
    now: Any | None = None,
) -> list[dict[str, Any]]:
    if not settings.autonomous_activation_enabled:
        return []
    current = now or utc_now()
    with Session(engine) as db:
        preferences = load_runtime_preferences(db, settings)
        autonomous_session = repositories.get_or_create_autonomous_session(
            db,
            profile_id=preferences.profile_id,
        )
        if settings.cognitive_workspace_mode == "active":
            _cancel_pending_periodic_activations(
                db,
                profile_id=preferences.profile_id,
                session_id=autonomous_session.id,
            )
        else:
            repositories.ensure_next_periodic_activation(
                db,
                profile_id=preferences.profile_id,
                session_id=autonomous_session.id,
                interval_seconds=settings.autonomous_activation_interval_seconds,
                from_time=current,
            )
    run_cognitive_workspace_tick(
        engine,
        settings=settings,
        provider_factory=provider_factory,
        now=current,
    )
    with Session(engine) as db:
        due = repositories.list_due_autonomous_activations(
            db,
            now=current,
            limit=settings.autonomous_activation_batch_size,
        )
    return [
        run_autonomous_activation(
            engine,
            settings=settings,
            provider_factory=provider_factory,
            activation_id=item.id,
            now=current,
        )
        for item in due
    ]


def run_autonomous_activation(
    engine: Engine,
    *,
    settings: Settings,
    provider_factory: ProviderFactory,
    activation_id: str,
    now: Any | None = None,
) -> dict[str, Any]:
    started_at = now or utc_now()
    with Session(engine) as db:
        activation = repositories.claim_autonomous_activation(
            db,
            activation_id=activation_id,
            lease_seconds=settings.autonomous_activation_lease_seconds,
            now=started_at,
        )
        if activation is None:
            return {"activation_id": activation_id, "status": "not_claimed"}
        human_turn_active_since = started_at - timedelta(
            seconds=(
                settings.autonomous_activation_human_turn_freshness_seconds
            )
        )
        if repositories.has_active_human_turn(
            db,
            active_since=human_turn_active_since,
        ):
            deferred = repositories.complete_autonomous_activation(
                db,
                activation_id=activation.id,
                status="deferred",
                turn_id=None,
                active_mode=None,
                outcome={"reason": "human_turn_active"},
            )
            repositories.schedule_autonomous_activation(
                db,
                profile_id=deferred.profile_id,
                session_id=deferred.session_id,
                scheduled_at=utc_now()
                + timedelta(seconds=settings.autonomous_activation_defer_seconds),
                trigger_kind="deferred_human_active",
                candidate_id=deferred.candidate_id,
                episode_id=deferred.episode_id,
                wake_condition_id=deferred.wake_condition_id,
                workspace=deferred.workspace_json,
            )
            return {
                "activation_id": activation.id,
                "status": "deferred",
                "reason": "human_turn_active",
            }

    turn_id: str | None = None
    autonomous_session_id: str | None = None
    activation_message_id: str | None = None
    trace_ids: list[str] = []
    started_perf = time.perf_counter()
    try:
        with Session(engine) as db:
            activation = db.get(AutonomousActivation, activation_id)
            if activation is None:
                raise ValueError(f"Autonomous activation not found: {activation_id}")
            chat_session = repositories.get_chat_session(db, activation.session_id)
            if chat_session is None:
                raise ValueError(
                    f"Autonomous session not found: {activation.session_id}"
                )
            autonomous_session_id = chat_session.id
            preferences = load_runtime_preferences(db, settings)
            model = active_provider_model(settings)
            turn = repositories.create_turn(
                db,
                session_id=chat_session.id,
                model=model,
                trigger_kind="autonomous_activation",
                actor="scarlet",
            )
            turn_id = turn.id
            activation.turn_id = turn_id
            activation.updated_at = utc_now()
            db.add(activation)
            db.commit()
            record_event(
                db,
                session_id=chat_session.id,
                turn_id=turn_id,
                event_type="autonomy.activation.started",
                payload={
                    "activation_id": activation.id,
                    "trigger_kind": activation.trigger_kind,
                    "scheduled_at": activation.scheduled_at.isoformat(),
                },
                source="autonomy",
                actor="backend",
                visibility="private",
                status="active",
            )
            envelope = _autonomous_activation_envelope(
                activation=activation,
                now=started_at,
                timezone_id=preferences.timezone,
            )
            activation_message = repositories.add_message(
                db,
                session_id=chat_session.id,
                turn_id=turn_id,
                role="activation",
                content=envelope,
                metadata={
                    "activation_id": activation.id,
                    "trigger_kind": activation.trigger_kind,
                    "visibility": "internal_cognition",
                },
            )
            activation_message_id = activation_message.id
            record_event(
                db,
                session_id=chat_session.id,
                turn_id=turn_id,
                event_type="autonomy.activation.persisted",
                payload={
                    "activation_id": activation.id,
                    "message_id": activation_message.id,
                },
                source="autonomy",
                actor="backend",
                visibility="private",
                message_id=activation_message.id,
            )
            history = repositories.list_messages(db, session_id=chat_session.id)
            retrieval_dialogue = _autonomous_retrieval_dialogue(
                db,
                autonomous_session=chat_session,
                profile_id=preferences.profile_id,
                privacy_scope=preferences.privacy_scope,
            )
            memory_context = build_memory_context(
                db,
                chat_session=chat_session,
                turn_id=turn_id,
                current_user_message=activation_message,
                history=history,
                now=started_at,
                runtime_preferences=preferences,
                settings=settings,
                runtime_trigger="autonomous_activation",
                retrieval_dialogue=retrieval_dialogue,
            )
            trace_ids.extend(
                [
                    memory_context.trace_id,
                    memory_context.runtime_trace_id,
                ]
            )
            if memory_context.metacognitive_trace_id is not None:
                trace_ids.append(memory_context.metacognitive_trace_id)
            if memory_context.model_context_trace_id is not None:
                trace_ids.append(memory_context.model_context_trace_id)
            model_context = memory_context.model_context_payload or {}
            context_audit = {
                "profile": memory_context.model_context_profile,
                "turn_origin": model_context.get("turn_origin"),
                "previous_session_count": len(
                    model_context.get("session", {}).get("previous_sessions", [])
                ),
                "autonomous_session_present": (
                    model_context.get("session", {}).get("autonomous_session")
                    is not None
                ),
                "memory_counts": {
                    key: len(value)
                    for key, value in model_context.get("memories", {}).items()
                },
                "source_trace_ids": [
                    memory_context.trace_id,
                    memory_context.runtime_trace_id,
                    memory_context.model_context_trace_id,
                ],
            }
            record_event(
                db,
                session_id=chat_session.id,
                turn_id=turn_id,
                event_type="autonomy.context.built",
                payload=context_audit,
                source="autonomy",
                actor="backend",
                visibility="private",
                trace_id=memory_context.model_context_trace_id,
            )
            record_event(
                db,
                session_id=chat_session.id,
                turn_id=turn_id,
                event_type="memory.context.built",
                payload=memory_context_event_payload(memory_context.payload),
                source="memory",
                actor="backend",
                visibility="private",
                trace_id=memory_context.trace_id,
            )
            if memory_context.model_context_payload is not None:
                record_event(
                    db,
                    session_id=chat_session.id,
                    turn_id=turn_id,
                    event_type="memory.recent_context.built",
                    payload=recent_memory_context_event_payload(
                        memory_context.model_context_payload
                    ),
                    source="memory",
                    actor="backend",
                    visibility="private",
                    trace_id=memory_context.model_context_trace_id,
                )
                record_event(
                    db,
                    session_id=chat_session.id,
                    turn_id=turn_id,
                    event_type="session.continuity.built",
                    payload=session_continuity_event_payload(
                        memory_context.model_context_payload
                    ),
                    source="session",
                    actor="backend",
                    visibility="private",
                    trace_id=memory_context.model_context_trace_id,
                )
            record_event(
                db,
                session_id=chat_session.id,
                turn_id=turn_id,
                event_type="runtime.context.built",
                payload=runtime_context_event_payload(
                    memory_context.runtime_payload
                ),
                source="runtime",
                actor="backend",
                visibility="private",
                trace_id=memory_context.runtime_trace_id,
            )
            canonical_messages = _autonomous_provider_messages(
                chat_session.provider_history_json,
                history,
                activation_message,
            )
            history_routing = route_history_for_model(
                db,
                session_id=chat_session.id,
                canonical_messages=canonical_messages,
                chars_per_token=float(settings.context_estimated_chars_per_token),
                mode=settings.history_compaction_mode,
            )
            system_prompt = resolve_agent_system_prompt(settings)
            effective_system = (
                compose_system_with_runtime_context(
                    system_prompt.content,
                    memory_context.runtime_context,
                )
                + history_routing.system_appendix
            )
            request_trace = repositories.add_trace(
                db,
                session_id=chat_session.id,
                turn_id=turn_id,
                kind="llm.request",
                payload={
                    "entrypoint": "autonomy.activation",
                    "activation_id": activation.id,
                    "model": model,
                    "max_tokens": active_provider_max_tokens(settings),
                    "system_source": system_prompt.source,
                    "context_trace_id": memory_context.model_context_trace_id
                    or memory_context.runtime_trace_id,
                    "history_routing": history_routing.payload,
                    "provider_messages": [
                        item.model_dump(mode="json")
                        for item in history_routing.model_messages
                    ],
                    "tools": [MIND_SHELL_TOOL_SCHEMA],
                },
            )
            trace_ids.append(request_trace.id)
            record_event(
                db,
                session_id=chat_session.id,
                turn_id=turn_id,
                event_type="llm.request.created",
                payload={
                    "entrypoint": "autonomy.activation",
                    "activation_id": activation.id,
                    "model": model,
                },
                source="llm",
                actor="backend",
                visibility="private",
                status="active",
                trace_id=request_trace.id,
            )

        provider = provider_factory(settings)
        if autonomous_session_id is None or activation_message_id is None:
            raise RuntimeError("Autonomous turn preparation did not retain its ids.")
        base_tool_runner = build_mind_tool_runner(
            engine,
            settings=settings,
            provider_factory=provider_factory,
            session_id=autonomous_session_id,
            turn_id=turn_id,
            source_message_id=activation_message_id,
            trace_ids=trace_ids,
            runtime_trigger="autonomous_activation",
        )

        def tool_runner(tool_use: Any) -> Any:
            if _has_active_human_turn(engine, settings=settings):
                raise AutonomousYieldToHuman(
                    "A human turn started before the next autonomous tool call."
                )
            return base_tool_runner(tool_use)

        if _has_active_human_turn(engine, settings=settings):
            raise AutonomousYieldToHuman(
                "A human turn started before autonomous provider execution."
            )
        result: LLMTextResult | None = None
        semantic_events_seen = False
        for stream_event in provider.stream_chat_with_tools(
            messages=history_routing.model_messages,
            system=effective_system,
            max_tokens=active_provider_max_tokens(settings),
            tools=[MIND_SHELL_TOOL_SCHEMA],
            tool_runner=tool_runner,
            max_tool_calls=None,
        ):
            if (
                stream_event.type
                in {
                    "model_request",
                    "model_stop",
                    "tool_call",
                    "tool_result",
                    "assistant_note",
                    "assistant_answer",
                }
                and _has_active_human_turn(engine, settings=settings)
            ):
                raise AutonomousYieldToHuman(
                    "A human turn started during autonomous provider execution."
                )
            if stream_event.type == "final_result":
                result = LLMTextResult.model_validate(stream_event.data["result"])
                continue
            recorded = record_provider_stream_event(
                engine,
                session_id=autonomous_session_id,
                turn_id=turn_id,
                stream_event=stream_event,
                assistant_visibility="private",
            )
            if recorded is not None and recorded.type in {
                "assistant.note.emitted",
                "assistant.response.continued",
                "assistant.answer.completed",
                "llm.thinking.captured",
            }:
                semantic_events_seen = True
        if result is None:
            raise RuntimeError("Autonomous provider stream ended without final_result.")

        latency_ms = int((time.perf_counter() - started_perf) * 1000)
        with Session(engine) as db:
            assistant_message = repositories.add_message(
                db,
                session_id=autonomous_session_id,
                turn_id=turn_id,
                role="assistant",
                content=result.text,
                provider_message_id=result.provider_message_id,
                raw_content=result.raw_content,
                metadata={
                    "activation_id": activation_id,
                    "visibility": "internal_cognition",
                    "model": result.model,
                    "usage": result.usage,
                    "stop_reason": result.stop_reason,
                    "completion_recovery": result.completion_recovery,
                },
            )
            response_trace = repositories.add_trace(
                db,
                session_id=autonomous_session_id,
                turn_id=turn_id,
                kind="llm.response",
                payload={
                    "entrypoint": "autonomy.activation",
                    "activation_id": activation_id,
                    "model": result.model,
                    "text": result.text,
                    "usage": result.usage,
                    "provider_message_id": result.provider_message_id,
                    "stop_reason": result.stop_reason,
                    "raw_content": result.raw_content,
                    "tool_calls": [
                        item.model_dump(mode="json") for item in result.tool_calls
                    ],
                    "raw_provider_messages": result.raw_provider_messages,
                    "completion_recovery": result.completion_recovery,
                },
            )
            trace_ids.append(response_trace.id)
            if not semantic_events_seen:
                record_response_content_events(
                    db,
                    session_id=autonomous_session_id,
                    turn_id=turn_id,
                    raw_provider_messages=result.raw_provider_messages
                    or [
                        {
                            "id": result.provider_message_id,
                            "stop_reason": result.stop_reason,
                            "content": result.raw_content
                            or [{"type": "text", "text": result.text}],
                        }
                    ],
                    response_trace_id=response_trace.id,
                    assistant_message_id=assistant_message.id,
                    assistant_visibility="private",
                )
            repositories.update_chat_session_provider_history(
                db,
                session_id=autonomous_session_id,
                provider_history=updated_provider_history(
                    canonical_messages,
                    result,
                ),
            )
            completed_turn = repositories.complete_turn(
                db,
                turn_id=turn_id,
                latency_ms=latency_ms,
            )
            completed_event = record_event(
                db,
                session_id=autonomous_session_id,
                turn_id=turn_id,
                event_type="autonomy.activation.completed",
                payload={
                    "activation_id": activation_id,
                    "latency_ms": latency_ms,
                    "tool_call_count": len(result.tool_calls),
                    "assistant_message_id": assistant_message.id,
                    "trace_ids": trace_ids,
                },
                source="autonomy",
                actor="scarlet",
                visibility="private",
                status=completed_turn.status,
                trace_id=response_trace.id,
                message_id=assistant_message.id,
            )
            completed = repositories.complete_autonomous_activation(
                db,
                activation_id=activation_id,
                status="completed",
                turn_id=turn_id,
                active_mode=(
                    model_context.get("session", {})
                    .get("agent_mode", {})
                    .get("active_tag")
                ),
                outcome={
                    "latency_ms": latency_ms,
                    "tool_call_count": len(result.tool_calls),
                    "assistant_message_id": assistant_message.id,
                    "trace_ids": trace_ids,
                },
            )
            _reconcile_workspace_activation(
                db,
                settings=settings,
                activation=completed,
            )
            record_endogenous_activation_feedback(
                db,
                activation=completed,
            )
            _schedule_autonomous_compaction(
                db,
                settings=settings,
                activation=completed,
                turn_id=turn_id,
                trigger_event_id=completed_event.id,
                context=model_context or memory_context.runtime_payload,
            )
            if settings.cognitive_workspace_mode != "active":
                repositories.ensure_next_periodic_activation(
                    db,
                    profile_id=completed.profile_id,
                    session_id=completed.session_id,
                    interval_seconds=settings.autonomous_activation_interval_seconds,
                    from_time=utc_now(),
                )
        return {
            "activation_id": activation_id,
            "session_id": autonomous_session_id,
            "turn_id": turn_id,
            "status": "completed",
            "latency_ms": latency_ms,
            "tool_call_count": len(result.tool_calls),
        }
    except AutonomousYieldToHuman as exc:
        return _defer_started_activation(
            engine,
            settings=settings,
            activation_id=activation_id,
            turn_id=turn_id,
            started_perf=started_perf,
            reason=str(exc),
        )
    except Exception as exc:
        error = {"type": type(exc).__name__, "message": str(exc)}
        logger.exception("Autonomous activation %s failed.", activation_id)
        with Session(engine) as db:
            activation = db.get(AutonomousActivation, activation_id)
            if activation is not None:
                if turn_id is not None:
                    repositories.complete_turn(
                        db,
                        turn_id=turn_id,
                        status="failed",
                        latency_ms=int((time.perf_counter() - started_perf) * 1000),
                        error=error,
                    )
                    record_event(
                        db,
                        session_id=activation.session_id,
                        turn_id=turn_id,
                        event_type="autonomy.activation.failed",
                        payload={"activation_id": activation.id, "error": error},
                        source="autonomy",
                        actor="backend",
                        visibility="private",
                        status="failed",
                    )
                failed = repositories.complete_autonomous_activation(
                    db,
                    activation_id=activation.id,
                    status="failed",
                    turn_id=turn_id,
                    active_mode=None,
                    error=error,
                )
                _reconcile_workspace_activation(
                    db,
                    settings=settings,
                    activation=failed,
                )
                record_endogenous_activation_feedback(
                    db,
                    activation=failed,
                )
                if settings.cognitive_workspace_mode != "active":
                    repositories.ensure_next_periodic_activation(
                        db,
                        profile_id=activation.profile_id,
                        session_id=activation.session_id,
                        interval_seconds=settings.autonomous_activation_interval_seconds,
                        from_time=utc_now(),
                    )
        return {
            "activation_id": activation_id,
            "turn_id": turn_id,
            "status": "failed",
            "error": error,
        }


def start_autonomous_activation_worker(
    engine: Engine,
    *,
    settings: Settings,
    provider_factory: ProviderFactory,
) -> Callable[[], None]:
    if not settings.autonomous_activation_enabled:
        return lambda: None

    with Session(engine) as db:
        preferences = load_runtime_preferences(db, settings)
        autonomous_session = repositories.get_or_create_autonomous_session(
            db,
            profile_id=preferences.profile_id,
        )
        if settings.cognitive_workspace_mode == "active":
            _cancel_pending_periodic_activations(
                db,
                profile_id=preferences.profile_id,
                session_id=autonomous_session.id,
            )
        else:
            repositories.ensure_next_periodic_activation(
                db,
                profile_id=preferences.profile_id,
                session_id=autonomous_session.id,
                interval_seconds=settings.autonomous_activation_interval_seconds,
            )

    stop_event = threading.Event()

    def loop() -> None:
        while not stop_event.wait(
            settings.autonomous_activation_worker_interval_seconds
        ):
            try:
                run_due_autonomous_activations(
                    engine,
                    settings=settings,
                    provider_factory=provider_factory,
                )
            except Exception:
                logger.exception("Autonomous activation worker batch failed.")

    thread = threading.Thread(
        target=loop,
        name="scarlet-autonomous-cognition",
        daemon=True,
    )
    thread.start()

    def stop() -> None:
        stop_event.set()
        thread.join(timeout=2)

    return stop


def _cancel_pending_periodic_activations(
    db: Session,
    *,
    profile_id: str,
    session_id: str,
) -> None:
    pending = repositories.list_autonomous_activations(
        db,
        profile_id=profile_id,
        session_id=session_id,
        status="pending",
        limit=100,
    )
    for activation in pending:
        if activation.trigger_kind != "periodic":
            continue
        cancelled = repositories.complete_autonomous_activation(
            db,
            activation_id=activation.id,
            status="cancelled",
            turn_id=None,
            active_mode=None,
            outcome={
                "reason": "periodic_wake_retired_by_active_workspace",
            },
        )
        record_event(
            db,
            session_id=session_id,
            turn_id=None,
            event_type="autonomy.activation.cancelled",
            payload={
                "activation_id": cancelled.id,
                "reason": "periodic_wake_retired_by_active_workspace",
            },
            source="cognitive_workspace",
            actor="backend",
            visibility="private",
        )


def _has_active_human_turn(
    engine: Engine,
    *,
    settings: Settings,
) -> bool:
    active_since = utc_now() - timedelta(
        seconds=settings.autonomous_activation_human_turn_freshness_seconds
    )
    with Session(engine) as db:
        return repositories.has_active_human_turn(
            db,
            active_since=active_since,
        )


def _defer_started_activation(
    engine: Engine,
    *,
    settings: Settings,
    activation_id: str,
    turn_id: str | None,
    started_perf: float,
    reason: str,
) -> dict[str, Any]:
    with Session(engine) as db:
        activation = db.get(AutonomousActivation, activation_id)
        if activation is None:
            return {
                "activation_id": activation_id,
                "turn_id": turn_id,
                "status": "deferred",
                "reason": reason,
            }
        latency_ms = int((time.perf_counter() - started_perf) * 1000)
        if turn_id is not None:
            repositories.complete_turn(
                db,
                turn_id=turn_id,
                status="deferred",
                latency_ms=latency_ms,
            )
            record_event(
                db,
                session_id=activation.session_id,
                turn_id=turn_id,
                event_type="autonomy.activation.deferred",
                payload={
                    "activation_id": activation.id,
                    "reason": "human_turn_started",
                    "detail": reason,
                    "latency_ms": latency_ms,
                },
                source="autonomy",
                actor="backend",
                visibility="private",
                status="deferred",
            )
        deferred = repositories.complete_autonomous_activation(
            db,
            activation_id=activation.id,
            status="deferred",
            turn_id=turn_id,
            active_mode=None,
            outcome={
                "reason": "human_turn_started",
                "detail": reason,
                "latency_ms": latency_ms,
            },
        )
        repositories.schedule_autonomous_activation(
            db,
            profile_id=deferred.profile_id,
            session_id=deferred.session_id,
            scheduled_at=utc_now()
            + timedelta(seconds=settings.autonomous_activation_defer_seconds),
            trigger_kind="deferred_human_active",
            candidate_id=deferred.candidate_id,
            episode_id=deferred.episode_id,
            wake_condition_id=deferred.wake_condition_id,
            workspace=deferred.workspace_json,
        )
    return {
        "activation_id": activation_id,
        "turn_id": turn_id,
        "status": "deferred",
        "reason": "human_turn_started",
    }


def _autonomous_provider_messages(
    provider_history_value: Any,
    history: list[Message],
    current_activation: Message,
) -> list[LLMMessage]:
    provider_history = valid_provider_history(provider_history_value)
    if provider_history:
        return [
            LLMMessage(role=item["role"], content=item["content"])
            for item in [
                *provider_history,
                {
                    "role": "user",
                    "content": [{"type": "text", "text": current_activation.content}],
                },
            ]
        ]
    messages: list[LLMMessage] = []
    for message in history:
        if message.id == current_activation.id:
            messages.append(LLMMessage(role="user", content=message.content))
        elif message.role == "activation":
            messages.append(LLMMessage(role="user", content=message.content))
        elif message.role == "assistant":
            messages.append(LLMMessage(role="assistant", content=message.content))
    return messages


def _reconcile_workspace_activation(
    db: Session,
    *,
    settings: Settings,
    activation: AutonomousActivation,
) -> None:
    candidate_ids = [
        item
        for item in activation.workspace_json.get("selected_candidate_ids", [])
        if isinstance(item, str)
    ]
    if activation.candidate_id is not None:
        candidate_ids.insert(0, activation.candidate_id)
    candidate_ids = list(dict.fromkeys(candidate_ids))
    if not candidate_ids:
        return
    volition_links = repositories.list_intention_links_by_targets(
        db,
        target_type="candidate",
        target_ids=candidate_ids,
    )
    volition_by_candidate = {
        item.target_id: item.intention_id for item in volition_links
    }
    for candidate_id in candidate_ids:
        candidate = repositories.get_candidate(db, candidate_id)
        if candidate is None or candidate.status in {
            "selected",
            "resolved",
            "rejected",
            "invalidated",
        }:
            continue
        intention_id = volition_by_candidate.get(candidate.id)
        if intention_id is not None:
            repositories.update_candidate(
                db,
                candidate_id=candidate.id,
                status="resolved",
                resolution=f"endorsed_as_volition:{intention_id}",
            )
            record_event(
                db,
                session_id=activation.session_id,
                turn_id=activation.turn_id,
                event_type="cognition.candidate.endorsed_as_volition",
                payload={
                    "candidate_id": candidate.id,
                    "intention_id": intention_id,
                    "activation_id": activation.id,
                },
                source="cognitive_workspace",
                actor="backend",
                visibility="private",
            )
            continue
        repositories.update_candidate(
            db,
            candidate_id=candidate.id,
            status="suspended",
            deferred_until=utc_now()
            + timedelta(seconds=settings.autonomous_activation_interval_seconds),
            increment_deferral=True,
        )
        record_event(
            db,
            session_id=activation.session_id,
            turn_id=activation.turn_id,
            event_type="cognition.candidate.suspended",
            payload={
                "candidate_id": candidate.id,
                "activation_id": activation.id,
                "reason": "no_explicit_episode_or_volition_decision",
            },
            source="cognitive_workspace",
            actor="backend",
            visibility="private",
        )


def _autonomous_activation_envelope(
    *,
    activation: AutonomousActivation,
    now: Any,
    timezone_id: str,
) -> str:
    base = (
        "[SCARLET INTERNAL COGNITIVE ACTIVATION]\n"
        f"Activation id: {activation.id}\n"
        f"Trigger: {activation.trigger_kind}\n"
        f"Runtime time: {render_user_time(now, timezone_id=timezone_id)}\n"
        "Origin: autonomous_cognition. This is not a human message. Use the "
        "same runtime context and API Mind available in interactive turns, "
        "then leave one concise internal checkpoint instead of a user-facing "
        "answer."
    )
    if not activation.workspace_json:
        return base
    workspace = json.dumps(
        activation.workspace_json,
        ensure_ascii=False,
        sort_keys=True,
    )
    return (
        f"{base}\n\n"
        "[COGNITIVE WORKSPACE - PROVISIONAL]\n"
        f"{workspace}\n"
        "This packet proposes attention; it does not establish facts or command "
        "an outcome. Inspect its source references. Use episode commands to open, "
        "resume, checkpoint, suspend, resolve, or reject the proposed work."
    )


def _autonomous_retrieval_dialogue(
    db: Session,
    *,
    autonomous_session: ChatSession,
    profile_id: str,
    privacy_scope: str,
) -> list[dict[str, Any]]:
    """Provide the shared retriever with recent source-labelled continuity."""

    candidates: list[Message] = []
    human_states = repositories.list_session_summary_states(
        db,
        exclude_session_id=autonomous_session.id,
        kind="human_dialogue",
        profile_id=None if privacy_scope == "local_single_user" else profile_id,
        limit=2,
    )
    for state in human_states:
        human_messages = repositories.list_messages(
            db,
            session_id=state.chat_session.id,
        )
        candidates.extend(
            message
            for message in human_messages[-4:]
            if message.role in {"user", "assistant"}
        )
    autonomous_messages = repositories.list_messages(
        db,
        session_id=autonomous_session.id,
    )
    candidates.extend(
        message
        for message in autonomous_messages[-6:]
        if message.role == "assistant"
    )
    candidates.sort(key=lambda item: (item.created_at, item.id))
    return [
        {
            "id": message.id,
            "session_id": message.session_id,
            "turn_id": message.turn_id,
            "role": message.role,
            "content": message.content[:1200],
            "source_origin": (
                "autonomous_cognition"
                if message.session_id == autonomous_session.id
                else "human_interaction"
            ),
        }
        for message in candidates[-8:]
    ]


def _schedule_autonomous_compaction(
    db: Session,
    *,
    settings: Settings,
    activation: AutonomousActivation,
    turn_id: str,
    trigger_event_id: str,
    context: dict[str, Any],
) -> None:
    chars_per_token = float(settings.context_estimated_chars_per_token)
    source_map = build_chronology_source_map(
        db,
        session_id=activation.session_id,
        chars_per_token=chars_per_token,
    )
    external_context_tokens = max(
        1,
        int(len(str(context)) / chars_per_token),
    )
    schedule_history_compaction(
        db,
        settings=settings,
        session_id=activation.session_id,
        trigger_turn_id=turn_id,
        trigger_event_id=trigger_event_id,
        source_map=source_map,
        external_context_tokens=external_context_tokens,
        chars_per_token=chars_per_token,
    )
