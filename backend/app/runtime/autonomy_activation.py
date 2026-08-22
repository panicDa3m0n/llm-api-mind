"""Provider execution lifecycle for one persisted autonomous activation.

Scheduling stays in :mod:`app.runtime.autonomy`.  This module owns the single
activation after it has become eligible, while delegating shared turn semantics
to ``turn_kernel`` just as the interactive adapter does.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.api.chat_provider_history import valid_provider_history
from app.config import Settings
from app.llm.factory import active_provider_max_tokens, active_provider_model
from app.llm.provider import (
    LLMIncompleteResponseError,
    LLMProvider,
    LLMTextResult,
)
from app.mind.schema import MIND_SHELL_TOOL_SCHEMA
from app.prompts.system import resolve_agent_system_prompt
from app.runtime.autonomy_schedule import (
    activation_min_gap_deadline,
    coalesce_autonomous_activation,
)
from app.runtime.autonomy_support import (
    AutonomousYieldToHuman,
    autonomous_activation_envelope,
    autonomous_provider_messages,
    autonomous_retrieval_dialogue,
    defer_started_activation,
    has_active_human_turn,
    reconcile_workspace_activation,
)
from app.runtime.endogenous_cognition import record_endogenous_activation_feedback
from app.runtime.events import record_event, record_provider_stream_event
from app.runtime.mind_tool_runner import build_mind_tool_runner
from app.runtime.preferences import load_runtime_preferences
from app.runtime.turn_kernel import (
    ModelTurnPreparation,
    complete_model_turn,
    prepare_model_turn,
    record_failed_model_turn,
    require_terminal_response,
)
from app.storage import repositories
from app.storage.models import AutonomousActivation, utc_now


logger = logging.getLogger(__name__)
ProviderFactory = Callable[[Settings], LLMProvider]


@dataclass
class AutonomousActivationRun:
    """Transient ids and kernel output belonging to one activation attempt."""

    activation_id: str
    started_at: Any
    started_perf: float
    turn_id: str | None = None
    session_id: str | None = None
    activation_message_id: str | None = None
    trace_ids: list[str] = field(default_factory=list)
    model_context: dict[str, Any] = field(default_factory=dict)
    prepared: ModelTurnPreparation | None = None


def run_autonomous_activation(
    engine: Engine,
    *,
    settings: Settings,
    provider_factory: ProviderFactory,
    activation_id: str,
    now: Any | None = None,
) -> dict[str, Any]:
    """Run one due activation without changing its scheduling semantics."""

    started_at = now or utc_now()
    immediate_result = _claim_or_defer_activation(
        engine,
        settings=settings,
        activation_id=activation_id,
        started_at=started_at,
    )
    if immediate_result is not None:
        return immediate_result

    run = AutonomousActivationRun(
        activation_id=activation_id,
        started_at=started_at,
        started_perf=time.perf_counter(),
    )
    try:
        _prepare_activation_turn(engine, settings=settings, run=run)
        result, semantic_events_seen = _stream_activation_provider(
            engine,
            settings=settings,
            provider_factory=provider_factory,
            run=run,
        )
        return _complete_activation(
            engine,
            settings=settings,
            run=run,
            result=result,
            semantic_events_seen=semantic_events_seen,
        )
    except AutonomousYieldToHuman as exc:
        return defer_started_activation(
            engine,
            settings=settings,
            activation_id=activation_id,
            turn_id=run.turn_id,
            started_perf=run.started_perf,
            reason=str(exc),
        )
    except Exception as exc:
        return _fail_activation(
            engine,
            settings=settings,
            run=run,
            exception=exc,
        )


def _claim_or_defer_activation(
    engine: Engine,
    *,
    settings: Settings,
    activation_id: str,
    started_at: Any,
) -> dict[str, Any] | None:
    """Claim the record or persist the pre-provider deferral outcome."""

    with Session(engine) as db:
        activation = repositories.claim_autonomous_activation(
            db,
            activation_id=activation_id,
            lease_seconds=settings.autonomous_activation_lease_seconds,
            now=started_at,
        )
        if activation is None:
            return {"activation_id": activation_id, "status": "not_claimed"}
        min_gap_deadline = activation_min_gap_deadline(
            db,
            profile_id=activation.profile_id,
            min_gap_seconds=settings.autonomous_activation_min_gap_seconds,
            now=started_at,
        )
        if min_gap_deadline is not None:
            deferred = repositories.complete_autonomous_activation(
                db,
                activation_id=activation.id,
                status="deferred",
                turn_id=None,
                active_mode=None,
                outcome={
                    "reason": "minimum_m3_gap_not_elapsed",
                    "eligible_at": min_gap_deadline.isoformat(),
                },
            )
            rescheduled = coalesce_autonomous_activation(
                db,
                profile_id=deferred.profile_id,
                session_id=deferred.session_id,
                trigger_kind=deferred.trigger_kind,
                candidate_id=deferred.candidate_id,
                episode_id=deferred.episode_id,
                wake_condition_id=deferred.wake_condition_id,
                workspace=deferred.workspace_json,
                min_gap_seconds=settings.autonomous_activation_min_gap_seconds,
                now=started_at,
            )
            record_event(
                db,
                session_id=deferred.session_id,
                event_type="autonomy.activation.deferred",
                payload={
                    "activation_id": deferred.id,
                    "reason": "minimum_m3_gap_not_elapsed",
                    "eligible_at": min_gap_deadline.isoformat(),
                    "rescheduled_activation_id": rescheduled.activation.id,
                },
                source="autonomy",
                actor="backend",
                visibility="private",
                status="deferred",
            )
            return {
                "activation_id": activation.id,
                "status": "deferred",
                "reason": "minimum_m3_gap_not_elapsed",
                "eligible_at": min_gap_deadline.isoformat(),
            }
        human_turn_active_since = started_at - timedelta(
            seconds=settings.autonomous_activation_human_turn_freshness_seconds
        )
        if not repositories.has_active_human_turn(
            db,
            active_since=human_turn_active_since,
        ):
            return None
        deferred = repositories.complete_autonomous_activation(
            db,
            activation_id=activation.id,
            status="deferred",
            turn_id=None,
            active_mode=None,
            outcome={"reason": "human_turn_active"},
        )
        coalesce_autonomous_activation(
            db,
            profile_id=deferred.profile_id,
            session_id=deferred.session_id,
            trigger_kind="deferred_human_active",
            candidate_id=deferred.candidate_id,
            episode_id=deferred.episode_id,
            wake_condition_id=deferred.wake_condition_id,
            workspace=deferred.workspace_json,
            min_gap_seconds=settings.autonomous_activation_min_gap_seconds,
            now=(
                utc_now()
                + timedelta(seconds=settings.autonomous_activation_defer_seconds)
            ),
        )
        return {
            "activation_id": activation.id,
            "status": "deferred",
            "reason": "human_turn_active",
        }


def _prepare_activation_turn(
    engine: Engine,
    *,
    settings: Settings,
    run: AutonomousActivationRun,
) -> None:
    """Persist the activation message and compile its shared kernel request."""

    with Session(engine) as db:
        activation = db.get(AutonomousActivation, run.activation_id)
        if activation is None:
            raise ValueError(
                f"Autonomous activation not found: {run.activation_id}"
            )
        chat_session = repositories.get_chat_session(db, activation.session_id)
        if chat_session is None:
            raise ValueError(
                f"Autonomous session not found: {activation.session_id}"
            )
        run.session_id = chat_session.id
        preferences = load_runtime_preferences(db, settings)
        model = active_provider_model(settings)
        turn = repositories.create_turn(
            db,
            session_id=chat_session.id,
            model=model,
            trigger_kind="autonomous_activation",
            actor="scarlet",
        )
        run.turn_id = turn.id
        activation.turn_id = run.turn_id
        activation.updated_at = utc_now()
        db.add(activation)
        db.commit()
        record_event(
            db,
            session_id=chat_session.id,
            turn_id=run.turn_id,
            event_type="turn.started",
            payload={"model": model, "entrypoint": "autonomy.activation"},
            source="runtime",
            actor="backend",
            visibility="private",
            status="active",
        )
        record_event(
            db,
            session_id=chat_session.id,
            turn_id=run.turn_id,
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
            now=run.started_at,
            timezone_id=preferences.timezone,
        )
        activation_message = repositories.add_message(
            db,
            session_id=chat_session.id,
            turn_id=run.turn_id,
            role="activation",
            content=envelope,
            metadata={
                "activation_id": activation.id,
                "trigger_kind": activation.trigger_kind,
                "visibility": "internal_cognition",
            },
        )
        run.activation_message_id = activation_message.id
        record_event(
            db,
            session_id=chat_session.id,
            turn_id=run.turn_id,
            event_type="autonomy.activation.persisted",
            payload={
                "activation_id": activation.id,
                "message_id": run.activation_message_id,
            },
            source="autonomy",
            actor="backend",
            visibility="private",
            message_id=run.activation_message_id,
        )
        history = repositories.list_messages(db, session_id=chat_session.id)
        retrieval_dialogue = autonomous_retrieval_dialogue(
            db,
            autonomous_session=chat_session,
            profile_id=preferences.profile_id,
            privacy_scope=preferences.privacy_scope,
        )
        canonical_messages = autonomous_provider_messages(
            chat_session.provider_history_json,
            history,
            activation_message,
        )
        provider_history_source = (
            "session.provider_history_json"
            if valid_provider_history(chat_session.provider_history_json)
            else "messages.text_reconstructed"
        )
        system_prompt = resolve_agent_system_prompt(settings)
        prepared = prepare_model_turn(
            db,
            settings=settings,
            chat_session=chat_session,
            turn_id=run.turn_id,
            source_message=activation_message,
            history=history,
            canonical_messages=canonical_messages,
            provider_history_source=provider_history_source,
            base_system=system_prompt.content,
            system_source=system_prompt.source,
            system_path=system_prompt.path,
            model=model,
            max_tokens=active_provider_max_tokens(settings),
            started=run.started_perf,
            stream=False,
            entrypoint="autonomy.activation",
            accounting_transport="autonomous_stream",
            runtime_trigger="autonomous_activation",
            now=run.started_at,
            runtime_preferences=preferences,
            retrieval_dialogue=retrieval_dialogue,
            context_event_visibility="private",
            request_event_visibility="private",
            request_event_status="active",
            request_metadata={
                "entrypoint": "autonomy.activation",
                "activation_id": activation.id,
            },
            response_visibility="private",
        )
        run.prepared = prepared
        run.trace_ids = prepared.trace_ids
        memory_context = prepared.memory_context
        run.model_context = memory_context.model_context_payload or {}
        context_audit = {
            "profile": memory_context.model_context_profile,
            "turn_origin": run.model_context.get("turn_origin"),
            "previous_session_count": len(
                run.model_context.get("session", {}).get("previous_sessions", [])
            ),
            "autonomous_session_present": (
                run.model_context.get("session", {}).get("autonomous_session")
                is not None
            ),
            "memory_counts": {
                key: len(value)
                for key, value in run.model_context.get("memories", {}).items()
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
            turn_id=run.turn_id,
            event_type="autonomy.context.built",
            payload=context_audit,
            source="autonomy",
            actor="backend",
            visibility="private",
            trace_id=memory_context.model_context_trace_id,
        )


def _stream_activation_provider(
    engine: Engine,
    *,
    settings: Settings,
    provider_factory: ProviderFactory,
    run: AutonomousActivationRun,
) -> tuple[LLMTextResult, bool]:
    """Run the provider stream while yielding immediately to a human turn."""

    session_id = run.session_id
    turn_id = run.turn_id
    prepared = run.prepared
    if (
        session_id is None
        or turn_id is None
        or run.activation_message_id is None
        or prepared is None
    ):
        raise RuntimeError("Autonomous turn preparation did not retain its ids.")
    provider = provider_factory(settings)
    base_tool_runner = build_mind_tool_runner(
        engine,
        settings=settings,
        provider_factory=provider_factory,
        session_id=session_id,
        turn_id=turn_id,
        source_message_id=prepared.source_message_id,
        trace_ids=run.trace_ids,
        runtime_trigger="autonomous_activation",
    )

    def tool_runner(tool_use: Any) -> Any:
        if has_active_human_turn(engine, settings=settings):
            raise AutonomousYieldToHuman(
                "A human turn started before the next autonomous tool call."
            )
        return base_tool_runner(tool_use)

    if has_active_human_turn(engine, settings=settings):
        raise AutonomousYieldToHuman(
            "A human turn started before autonomous provider execution."
        )
    result: LLMTextResult | None = None
    semantic_events_seen = False
    for stream_event in provider.stream_chat_with_tools(
        messages=prepared.model_messages,
        system=prepared.effective_system,
        max_tokens=prepared.max_tokens,
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
            and has_active_human_turn(engine, settings=settings)
        ):
            raise AutonomousYieldToHuman(
                "A human turn started during autonomous provider execution."
            )
        if stream_event.type == "final_result":
            result = LLMTextResult.model_validate(stream_event.data["result"])
            continue
        recorded = record_provider_stream_event(
            engine,
            session_id=session_id,
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
    return require_terminal_response(result), semantic_events_seen


def _complete_activation(
    engine: Engine,
    *,
    settings: Settings,
    run: AutonomousActivationRun,
    result: LLMTextResult,
    semantic_events_seen: bool,
) -> dict[str, Any]:
    """Persist the kernel completion and its activation-specific outcome."""

    if run.prepared is None or run.session_id is None:
        raise RuntimeError("Autonomous turn preparation was lost before completion.")
    completion = complete_model_turn(
        settings=settings,
        engine=engine,
        prepared=run.prepared,
        result=result,
        semantic_content_event_seen=semantic_events_seen,
        assistant_metadata={
            "activation_id": run.activation_id,
            "visibility": "internal_cognition",
        },
        response_metadata={
            "entrypoint": "autonomy.activation",
            "activation_id": run.activation_id,
        },
        assistant_event_source="autonomy",
        assistant_event_visibility="private",
        response_event_visibility="private",
        turn_event_visibility="private",
        schedule_idle_maintenance=False,
    )
    with Session(engine) as db:
        activation = db.get(AutonomousActivation, run.activation_id)
        if activation is None:
            raise ValueError(
                f"Autonomous activation not found: {run.activation_id}"
            )
        completed_event = record_event(
            db,
            session_id=activation.session_id,
            turn_id=run.prepared.turn_id,
            event_type="autonomy.activation.completed",
            payload={
                "activation_id": run.activation_id,
                "latency_ms": completion.latency_ms,
                "tool_call_count": len(result.tool_calls),
                "assistant_message_id": completion.assistant_message_id,
                "trace_ids": run.prepared.trace_ids,
            },
            source="autonomy",
            actor="scarlet",
            visibility="private",
            status="completed",
            trace_id=completion.response_trace_id,
            message_id=completion.assistant_message_id,
        )
        completed = repositories.complete_autonomous_activation(
            db,
            activation_id=run.activation_id,
            status="completed",
            turn_id=run.prepared.turn_id,
            active_mode=(
                run.model_context.get("session", {})
                .get("agent_mode", {})
                .get("active_tag")
            ),
            outcome={
                "latency_ms": completion.latency_ms,
                "tool_call_count": len(result.tool_calls),
                "assistant_message_id": completion.assistant_message_id,
                "trace_ids": run.prepared.trace_ids,
                "turn_completed_event_id": completion.turn_completed_event_id,
                "activation_completed_event_id": completed_event.id,
            },
        )
        reconcile_workspace_activation(db, activation=completed)
        record_endogenous_activation_feedback(db, activation=completed)
        if settings.cognitive_workspace_mode != "active":
            repositories.ensure_next_periodic_activation(
                db,
                profile_id=completed.profile_id,
                session_id=completed.session_id,
                interval_seconds=settings.autonomous_activation_interval_seconds,
                from_time=utc_now(),
            )
    return {
        "activation_id": run.activation_id,
        "session_id": run.session_id,
        "turn_id": run.turn_id,
        "status": "completed",
        "latency_ms": completion.latency_ms,
        "tool_call_count": len(result.tool_calls),
    }


def _fail_activation(
    engine: Engine,
    *,
    settings: Settings,
    run: AutonomousActivationRun,
    exception: Exception,
) -> dict[str, Any]:
    """Record exactly the previous failed-turn and failed-activation outcome."""

    error = {"type": type(exception).__name__, "message": str(exception)}
    logger.exception("Autonomous activation %s failed.", run.activation_id)
    failed_turn_event = None
    if run.prepared is not None:
        failure_details: dict[str, Any] = {
            "exception_type": type(exception).__name__,
        }
        if isinstance(exception, LLMIncompleteResponseError):
            failure_details["provider_details"] = exception.details
        failed_turn_event = record_failed_model_turn(
            engine,
            prepared=run.prepared,
            code="autonomy.activation_failed",
            message=str(exception) or type(exception).__name__,
            details=failure_details,
            visibility="private",
        )
    with Session(engine) as db:
        activation = db.get(AutonomousActivation, run.activation_id)
        if activation is not None:
            if run.turn_id is not None and run.prepared is None:
                repositories.complete_turn(
                    db,
                    turn_id=run.turn_id,
                    status="failed",
                    latency_ms=int((time.perf_counter() - run.started_perf) * 1000),
                    error=error,
                )
            if run.turn_id is not None:
                record_event(
                    db,
                    session_id=activation.session_id,
                    turn_id=run.turn_id,
                    event_type="autonomy.activation.failed",
                    payload={"activation_id": activation.id, "error": error},
                    source="autonomy",
                    actor="backend",
                    visibility="private",
                    status="failed",
                    parent_event_id=(
                        failed_turn_event.id
                        if failed_turn_event is not None
                        else None
                    ),
                )
            failed = repositories.complete_autonomous_activation(
                db,
                activation_id=activation.id,
                status="failed",
                turn_id=run.turn_id,
                active_mode=None,
                error=error,
            )
            reconcile_workspace_activation(db, activation=failed)
            record_endogenous_activation_feedback(db, activation=failed)
            if settings.cognitive_workspace_mode != "active":
                repositories.ensure_next_periodic_activation(
                    db,
                    profile_id=activation.profile_id,
                    session_id=activation.session_id,
                    interval_seconds=settings.autonomous_activation_interval_seconds,
                    from_time=utc_now(),
                )
    return {
        "activation_id": run.activation_id,
        "turn_id": run.turn_id,
        "status": "failed",
        "error": error,
    }
