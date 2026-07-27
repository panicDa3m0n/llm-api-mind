"""Persisted scheduler and MiniMax lifecycle for Scarlet's autonomous cognition."""

from __future__ import annotations

import logging
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
from app.api.chat_provider_history import (
    updated_provider_history,
    valid_provider_history,
)
from app.config import Settings
from app.llm.factory import active_provider_max_tokens, active_provider_model
from app.llm.provider import LLMMessage, LLMProvider, LLMTextResult
from app.mind.autonomous_context import (
    autonomous_activation_envelope,
    build_autonomous_model_context,
    render_autonomous_context,
)
from app.mind.schema import MIND_SHELL_TOOL_SCHEMA
from app.prompts.system import resolve_agent_system_prompt
from app.runtime.events import (
    record_event,
    record_provider_stream_event,
    record_response_content_events,
)
from app.runtime.history_compaction import build_chronology_source_map
from app.runtime.history_runtime import route_history_for_model
from app.runtime.maintenance import schedule_history_compaction
from app.runtime.preferences import load_runtime_preferences
from app.storage import repositories
from app.storage.models import AutonomousActivation, Message, utc_now


logger = logging.getLogger(__name__)
ProviderFactory = Callable[[Settings], LLMProvider]
AUTONOMOUS_PROMPT_APPENDIX = """
## Autonomous Activation Runtime

The current input may be a backend-scheduled autonomous activation rather than
a human message. When `<autonomous_runtime_context>` is present, treat the
activation as a real interval of your own internal cognitive continuity.

Do not answer an absent user and do not turn the interval into generic
maintenance. Orient yourself, inspect or change your cognitive state through
mind_shell when useful, and use only source-labelled evidence. Before every
tool call, emit one brief personal note explaining what you are doing and why.
Finish with a concise internal checkpoint. That checkpoint belongs to your
private autonomous chronology and is not a user-facing chat answer.
""".strip()


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
        autonomous_session = repositories.get_or_create_autonomous_session(
            db,
            profile_id=settings.user_profile_id,
        )
        repositories.ensure_next_periodic_activation(
            db,
            profile_id=settings.user_profile_id,
            session_id=autonomous_session.id,
            interval_seconds=settings.autonomous_activation_interval_seconds,
            from_time=current,
        )
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
            envelope = autonomous_activation_envelope(
                activation=activation,
                now=started_at,
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
            context, context_audit = build_autonomous_model_context(
                db,
                activation=activation,
                chat_session=chat_session,
                now=started_at,
                preferences=preferences,
                settings=settings,
            )
            context_trace = repositories.add_trace(
                db,
                session_id=chat_session.id,
                turn_id=turn_id,
                kind="autonomy.context",
                payload={"document": context, "audit": context_audit},
            )
            trace_ids.append(context_trace.id)
            record_event(
                db,
                session_id=chat_session.id,
                turn_id=turn_id,
                event_type="autonomy.context.built",
                payload=context_audit,
                source="autonomy",
                actor="backend",
                visibility="private",
                trace_id=context_trace.id,
            )
            canonical_messages = _autonomous_provider_messages(
                chat_session.provider_history_json,
                repositories.list_messages(db, session_id=chat_session.id),
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
                    f"{system_prompt.content.rstrip()}\n\n{AUTONOMOUS_PROMPT_APPENDIX}",
                    render_autonomous_context(context),
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
                    "context_trace_id": context_trace.id,
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
                active_mode=context["operating_contract"]["active_mode"],
                outcome={
                    "latency_ms": latency_ms,
                    "tool_call_count": len(result.tool_calls),
                    "assistant_message_id": assistant_message.id,
                    "trace_ids": trace_ids,
                },
            )
            _schedule_autonomous_compaction(
                db,
                settings=settings,
                activation=completed,
                turn_id=turn_id,
                trigger_event_id=completed_event.id,
                context=context,
            )
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
                repositories.complete_autonomous_activation(
                    db,
                    activation_id=activation.id,
                    status="failed",
                    turn_id=turn_id,
                    active_mode=None,
                    error=error,
                )
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
        autonomous_session = repositories.get_or_create_autonomous_session(
            db,
            profile_id=settings.user_profile_id,
        )
        repositories.ensure_next_periodic_activation(
            db,
            profile_id=settings.user_profile_id,
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
