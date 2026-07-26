"""Shared native-turn preparation, completion, and transport-neutral state."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.api.chat_accounting import (
    context_accounting_summary,
    post_turn_model_history_tokens,
    provider_message_stats,
    record_context_accounting_observed,
    record_context_accounting_preflight,
)
from app.api.chat_provider_history import (
    provider_history_from_result,
    provider_messages_for_turn,
    updated_provider_history,
)
from app.api.chat_serialization import (
    ChatMessageResponse,
    ChatTurnResponse,
    event_stream_payload,
    incomplete_result_details,
    memory_context_event_payload,
    message_response,
    metacognitive_context_event_payload,
    ndjson,
    recent_memory_context_event_payload,
    response_event_messages,
    runtime_context_event_payload,
    session_continuity_event_payload,
    session_response,
)
from app.config import Settings
from app.llm.factory import active_provider_max_tokens, active_provider_model
from app.llm.provider import (
    LLMConfigurationError,
    LLMExecutedToolCall,
    LLMIncompleteResponseError,
    LLMMessage,
    LLMProvider,
    LLMRequestError,
    LLMStreamEvent,
    LLMTextResult,
    LLMToolUse,
)
from app.mind.context import MemoryContextBuild, build_memory_context
from app.mind.dispatcher import (
    MindAPIContext,
    MindAPIError,
    MindAPIRequest,
    MindAPIResponse,
)
from app.mind.schema import MIND_SHELL_TOOL_SCHEMA
from app.mind.shell import MindShellRequest, dispatch_mind_shell
from app.prompts.system import AgentSystemPromptError, resolve_agent_system_prompt
from app.runtime.answer_obligations import (
    AnswerObligationManifest,
    augment_with_tool_evidence,
    compile_answer_obligations,
    correction_instruction,
    render_answer_obligations,
    validate_answer_semantics,
)
from app.runtime.events import (
    record_event,
    record_provider_stream_event,
    record_response_content_events,
    record_tool_call_completed,
    record_tool_call_started,
)
from app.runtime.history_compaction import build_chronology_source_map
from app.runtime.history_runtime import HistoryRoutingResult, route_history_for_model
from app.runtime.maintenance import (
    schedule_history_compaction,
    schedule_session_idle_maintenance,
)
from app.runtime.preferences import load_runtime_preferences
from app.storage import repositories
from app.storage.models import CognitiveEvent


ProviderFactory = Callable[[Settings], LLMProvider]


class NativeTurnFailure(RuntimeError):
    """A pre-response native failure that the HTTP facade can map verbatim."""

    def __init__(self, *, status_code: int, detail: dict[str, Any]) -> None:
        super().__init__(str(detail.get("message") or detail.get("code") or "failure"))
        self.status_code = status_code
        self.detail = detail


@dataclass
class NativeTurnPreparation:
    session_id: str
    turn_id: str
    started: float
    trace_ids: list[str]
    user_message: ChatMessageResponse
    canonical_messages: list[LLMMessage]
    model_messages: list[LLMMessage]
    effective_system: str
    max_tokens: int
    memory_context: MemoryContextBuild
    accounting_trace_id: str
    accounting_payload: dict[str, Any]
    history_routing: HistoryRoutingResult
    answer_manifest: AnswerObligationManifest
    answer_obligations_trace_id: str | None
    stream: bool


@dataclass(frozen=True)
class NativeTurnCompletion:
    response: ChatTurnResponse
    runtime_events: list[dict[str, Any]]


def prepare_native_turn(
    *,
    settings: Settings,
    engine: Engine,
    session_id: str,
    message: str,
    system_override: str | None,
    requested_max_tokens: int | None,
    stream: bool,
) -> NativeTurnPreparation:
    """Persist and compile the one shared native request preflight."""

    started = time.perf_counter()
    trace_ids: list[str] = []
    model = active_provider_model(settings)
    entrypoint = "chat.turn.stream" if stream else "chat.turn"
    accounting_transport = "native_stream" if stream else "native"

    with Session(engine) as db:
        chat_session = repositories.get_chat_session(db, session_id)
        if chat_session is None:
            raise NativeTurnFailure(
                status_code=404,
                detail={
                    "code": "session.not_found",
                    "message": f"Session {session_id} was not found.",
                    "recoverable": True,
                },
            )

        turn = repositories.create_turn(db, session_id=session_id, model=model)
        turn_id = turn.id
        record_event(
            db,
            session_id=session_id,
            turn_id=turn_id,
            event_type="turn.started",
            payload={"model": model, "entrypoint": entrypoint},
            source="runtime",
            actor="backend",
            visibility="debug",
            status="active",
        )
        stored_user_message = repositories.add_message(
            db,
            session_id=session_id,
            turn_id=turn_id,
            role="user",
            content=message,
        )
        record_event(
            db,
            session_id=session_id,
            turn_id=turn_id,
            event_type="message.user.persisted",
            payload={
                "message_id": stored_user_message.id,
                "content_chars": len(stored_user_message.content),
            },
            source="chat",
            actor="user",
            visibility="public",
            message_id=stored_user_message.id,
        )
        user_message = message_response(stored_user_message)
        history = repositories.list_messages(db, session_id=session_id)
        provider_history_source, canonical_messages = provider_messages_for_turn(
            chat_session=chat_session,
            history=history,
            current_user_message=stored_user_message,
        )
        max_tokens = requested_max_tokens or active_provider_max_tokens(settings)

        try:
            system_prompt = resolve_agent_system_prompt(
                settings,
                override=system_override,
            )
        except AgentSystemPromptError as exc:
            error = {
                "code": "agent.system_prompt_error",
                "message": str(exc),
            }
            repositories.add_trace(
                db,
                session_id=session_id,
                turn_id=turn_id,
                kind="llm.error",
                payload=error,
            )
            repositories.complete_turn(
                db,
                turn_id=turn_id,
                status="failed",
                latency_ms=int((time.perf_counter() - started) * 1000),
                error=error,
            )
            raise NativeTurnFailure(
                status_code=503,
                detail={**error, "recoverable": True},
            ) from exc

        memory_context = build_memory_context(
            db,
            chat_session=chat_session,
            turn_id=turn_id,
            current_user_message=stored_user_message,
            history=history,
            runtime_preferences=load_runtime_preferences(db, settings),
            settings=settings,
        )
        trace_ids.append(memory_context.trace_id)
        if memory_context.metacognitive_trace_id is not None:
            trace_ids.append(memory_context.metacognitive_trace_id)
        trace_ids.append(memory_context.runtime_trace_id)
        if memory_context.model_context_trace_id is not None:
            trace_ids.append(memory_context.model_context_trace_id)

        record_event(
            db,
            session_id=session_id,
            turn_id=turn_id,
            event_type="memory.context.built",
            payload=memory_context_event_payload(memory_context.payload),
            source="memory",
            actor="backend",
            visibility="debug",
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
                visibility="debug",
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
                visibility="debug",
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
                visibility="debug",
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
            visibility="debug",
            trace_id=memory_context.runtime_trace_id,
        )

        history_routing = route_history_for_model(
            db,
            session_id=session_id,
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
                session_id=session_id,
                turn_id=turn_id,
                kind="history.routing",
                payload=history_routing.payload,
            )
            history_routing_trace_id = history_routing_trace.id
            trace_ids.append(history_routing_trace_id)
            record_event(
                db,
                session_id=session_id,
                turn_id=turn_id,
                event_type="history.routing.resolved",
                payload=history_routing.payload,
                source="runtime",
                actor="backend",
                visibility="debug",
                trace_id=history_routing_trace_id,
            )

        effective_system = compose_system_with_runtime_context(
            system_prompt.content,
            memory_context.runtime_context,
        ) + history_routing.system_appendix
        answer_manifest = compile_answer_obligations(
            transport="native",
            memory_context=memory_context.payload,
            metacognitive_context=memory_context.metacognitive_payload,
        )
        answer_obligations_trace_id: str | None = None
        if settings.answer_obligations_mode != "off":
            answer_obligations_trace_id = record_answer_obligations(
                db,
                session_id=session_id,
                turn_id=turn_id,
                manifest=answer_manifest,
                mode=settings.answer_obligations_mode,
                phase="initial",
            )
            trace_ids.append(answer_obligations_trace_id)

        answer_obligations_appendix = ""
        if (
            settings.answer_obligations_mode == "active"
            and answer_manifest.obligations
        ):
            answer_obligations_appendix = render_answer_obligations(answer_manifest)
            effective_system += answer_obligations_appendix

        accounting_trace, accounting_payload = record_context_accounting_preflight(
            db,
            session_id=session_id,
            turn_id=turn_id,
            model=model,
            transport=accounting_transport,
            base_system=system_prompt.content,
            runtime_context=memory_context.runtime_context,
            messages=model_messages,
            settings=settings,
            compacted_chronology=history_routing.system_appendix,
            answer_obligations=answer_obligations_appendix,
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
            "base_system": system_prompt.content,
            "system_present": True,
            "system_source": system_prompt.source,
            "system_path": system_prompt.path,
            "runtime_context_present": True,
            "runtime_context": memory_context.runtime_context,
            "memory_context_trace_id": memory_context.trace_id,
            "metacognitive_context_trace_id": memory_context.metacognitive_trace_id,
            "metacognitive_context_mode": (
                memory_context.metacognitive_payload or {}
            ).get("mode"),
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
            "answer_obligations_trace_id": answer_obligations_trace_id,
            "answer_obligations": answer_manifest.model_dump(mode="json"),
        }
        if stream:
            request_payload["stream"] = True
        request_trace = repositories.add_trace(
            db,
            session_id=session_id,
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
            "estimated_input_tokens": accounting_payload["total"][
                "estimated_input_tokens"
            ],
            "tool_count": 1,
        }
        if stream:
            request_event_payload["stream"] = True
        record_event(
            db,
            session_id=session_id,
            turn_id=turn_id,
            event_type="llm.request.created",
            payload=request_event_payload,
            source="llm",
            actor="backend",
            visibility="debug",
            trace_id=request_trace.id,
        )

    return NativeTurnPreparation(
        session_id=session_id,
        turn_id=turn_id,
        started=started,
        trace_ids=trace_ids,
        user_message=user_message,
        canonical_messages=canonical_messages,
        model_messages=model_messages,
        effective_system=effective_system,
        max_tokens=max_tokens,
        memory_context=memory_context,
        accounting_trace_id=accounting_trace_id,
        accounting_payload=accounting_payload,
        history_routing=history_routing,
        answer_manifest=answer_manifest,
        answer_obligations_trace_id=answer_obligations_trace_id,
        stream=stream,
    )


def complete_native_turn(
    *,
    settings: Settings,
    engine: Engine,
    prepared: NativeTurnPreparation,
    result: LLMTextResult,
    answer_validation_trace_id: str | None,
    semantic_content_event_seen: bool = False,
) -> NativeTurnCompletion:
    """Persist the one shared successful native-turn completion."""

    latency_ms = int((time.perf_counter() - prepared.started) * 1000)
    runtime_events: list[dict[str, Any]] = []
    with Session(engine) as db:
        assistant_message = repositories.add_message(
            db,
            session_id=prepared.session_id,
            turn_id=prepared.turn_id,
            role="assistant",
            content=result.text,
            provider_message_id=result.provider_message_id,
            raw_content=result.raw_content,
            metadata={
                "model": result.model,
                "usage": result.usage,
                "stop_reason": result.stop_reason,
                "completion_recovery": result.completion_recovery,
                "answer_obligations_trace_id": (
                    prepared.answer_obligations_trace_id
                ),
                "answer_validation_trace_id": answer_validation_trace_id,
            },
        )
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
            "answer_obligations_trace_id": prepared.answer_obligations_trace_id,
            "answer_validation_trace_id": answer_validation_trace_id,
        }
        if prepared.stream:
            response_payload["stream"] = True
        response_trace = repositories.add_trace(
            db,
            session_id=prepared.session_id,
            turn_id=prepared.turn_id,
            kind="llm.response",
            payload=response_payload,
        )
        prepared.trace_ids.append(response_trace.id)
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
            visibility="debug",
            trace_id=response_trace.id,
        )
        assistant_persisted_event = record_event(
            db,
            session_id=prepared.session_id,
            turn_id=prepared.turn_id,
            event_type="message.assistant.persisted",
            payload={
                "message_id": assistant_message.id,
                "content_chars": len(assistant_message.content),
            },
            source="chat",
            actor="scarlet",
            visibility="public",
            message_id=assistant_message.id,
        )
        if prepared.stream:
            runtime_events.extend(
                [
                    event_stream_payload(response_completed_event),
                    event_stream_payload(assistant_persisted_event),
                ]
            )

        if not prepared.stream or not semantic_content_event_seen:
            content_events = record_response_content_events(
                db,
                session_id=prepared.session_id,
                turn_id=prepared.turn_id,
                raw_provider_messages=response_event_messages(result),
                response_trace_id=response_trace.id,
                assistant_message_id=assistant_message.id,
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
            visibility="debug",
            status=completed_turn.status,
        )
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
            trigger_event_id=turn_completed_event.id,
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

        if settings.maintenance_enabled:
            maintenance_schedule = schedule_session_idle_maintenance(
                db,
                settings=settings,
                session_id=prepared.session_id,
                trigger_turn_id=prepared.turn_id,
                trigger_event_id=turn_completed_event.id,
            )
            if prepared.stream:
                _, maintenance_event = maintenance_schedule
                runtime_events.append(event_stream_payload(maintenance_event))

        chat_session = repositories.get_chat_session(db, prepared.session_id)
        if chat_session is None:
            raise RuntimeError(
                f"Completed session {prepared.session_id} disappeared during turn."
            )
        response = ChatTurnResponse(
            session=session_response(chat_session),
            turn_id=completed_turn.id,
            status=completed_turn.status,
            user_message=prepared.user_message,
            assistant_message=message_response(assistant_message),
            trace_ids=prepared.trace_ids,
            model=result.model,
            latency_ms=latency_ms,
            usage=result.usage,
        )

    return NativeTurnCompletion(response=response, runtime_events=runtime_events)


def record_answer_obligations(
    db: Session,
    *,
    session_id: str,
    turn_id: str,
    manifest: AnswerObligationManifest,
    mode: str,
    phase: str,
) -> str:
    trace = repositories.add_trace(
        db,
        session_id=session_id,
        turn_id=turn_id,
        kind="answer.obligations",
        payload={
            "mode": mode,
            "phase": phase,
            "manifest": manifest.model_dump(mode="json"),
            "hard_count": sum(
                1 for item in manifest.obligations if item.severity == "hard"
            ),
            "semantic_count": len(manifest.semantic),
        },
    )
    record_event(
        db,
        session_id=session_id,
        turn_id=turn_id,
        event_type="answer.obligations.compiled",
        payload={
            "mode": mode,
            "phase": phase,
            "obligation_ids": [item.id for item in manifest.obligations],
            "semantic_count": len(manifest.semantic),
        },
        source="answer_control",
        actor="backend",
        visibility="debug",
        trace_id=trace.id,
    )
    return trace.id


def record_failed_native_turn(
    engine: Engine,
    *,
    prepared: NativeTurnPreparation,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> CognitiveEvent:
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
            visibility="debug",
            status=completed.status,
            trace_id=trace.id,
        )


def compose_system_with_runtime_context(system: str, runtime_context: str) -> str:
    return f"{system.rstrip()}\n\n{runtime_context.strip()}"


def execute_native_turn(
    *,
    settings: Settings,
    engine: Engine,
    provider_factory: ProviderFactory,
    prepared: NativeTurnPreparation,
) -> ChatTurnResponse:
    try:
        provider = provider_factory(settings)
        tool_runner = _build_mind_tool_runner(
            engine,
            settings=settings,
            provider_factory=provider_factory,
            session_id=prepared.session_id,
            turn_id=prepared.turn_id,
            source_message_id=prepared.user_message.id,
            trace_ids=prepared.trace_ids,
        )
        result = provider.generate_chat_with_tools(
            messages=prepared.model_messages,
            system=prepared.effective_system,
            max_tokens=prepared.max_tokens,
            tools=[MIND_SHELL_TOOL_SCHEMA],
            tool_runner=tool_runner,
            max_tool_calls=None,
        )
        result, final_answer_validation_trace_id = (
            _enforce_native_answer_obligations(
                engine=engine,
                settings=settings,
                provider=provider,
                manifest=prepared.answer_manifest,
                result=result,
                request_messages=prepared.model_messages,
                system=prepared.effective_system,
                max_tokens=prepared.max_tokens,
                tool_runner=tool_runner,
                session_id=prepared.session_id,
                turn_id=prepared.turn_id,
                trace_ids=prepared.trace_ids,
            )
        )
    except LLMConfigurationError as exc:
        record_failed_native_turn(
            engine,
            prepared=prepared,
            code="llm.not_configured",
            message=str(exc),
        )
        raise NativeTurnFailure(
            status_code=503,
            detail={
                "code": "llm.not_configured",
                "message": str(exc),
                "recoverable": True,
            },
        ) from exc
    except LLMIncompleteResponseError as exc:
        record_failed_native_turn(
            engine,
            prepared=prepared,
            code="llm.incomplete_response",
            message=str(exc),
            details=exc.details,
        )
        raise NativeTurnFailure(
            status_code=502,
            detail={
                "code": "llm.incomplete_response",
                "message": str(exc),
                "recoverable": True,
                "details": exc.details,
            },
        ) from exc
    except LLMRequestError as exc:
        record_failed_native_turn(
            engine,
            prepared=prepared,
            code="llm.provider_error",
            message=str(exc),
        )
        raise NativeTurnFailure(
            status_code=502,
            detail={
                "code": "llm.provider_error",
                "message": str(exc),
                "recoverable": True,
            },
        ) from exc

    if not result.text.strip():
        details = incomplete_result_details(result)
        message = "Provider ended without public text or a tool call."
        record_failed_native_turn(
            engine,
            prepared=prepared,
            code="llm.incomplete_response",
            message=message,
            details=details,
        )
        raise NativeTurnFailure(
            status_code=502,
            detail={
                "code": "llm.incomplete_response",
                "message": message,
                "recoverable": True,
                "details": details,
            },
        )

    return complete_native_turn(
        settings=settings,
        engine=engine,
        prepared=prepared,
        result=result,
        answer_validation_trace_id=final_answer_validation_trace_id,
    ).response


def _build_mind_tool_runner(
    engine: Engine,
    *,
    settings: Settings,
    provider_factory: ProviderFactory,
    session_id: str,
    turn_id: str,
    source_message_id: str,
    trace_ids: list[str],
    event_sink: list[CognitiveEvent] | None = None,
) -> Callable[[LLMToolUse], LLMExecutedToolCall]:
    def run(tool_use: LLMToolUse) -> LLMExecutedToolCall:
        started = time.perf_counter()
        started_event_id: str | None = None
        with Session(engine) as db:
            started_event = record_tool_call_started(
                db,
                session_id=session_id,
                turn_id=turn_id,
                provider_tool_use_id=tool_use.id,
                tool_name=tool_use.name,
                arguments=tool_use.input,
            )
            started_event_id = started_event.id
            if event_sink is not None:
                event_sink.append(started_event)

        mind_request, mind_response = _dispatch_tool_use(
            tool_use,
            context=MindAPIContext(
                engine=engine,
                session_id=session_id,
                turn_id=turn_id,
                source_message_id=source_message_id,
                settings=settings,
                provider_factory=provider_factory,
            ),
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        result_payload = mind_response.model_dump(mode="json")
        _append_unique_trace_ids(trace_ids, _result_trace_ids(result_payload))

        with Session(engine) as db:
            tool_call = repositories.add_tool_call(
                db,
                session_id=session_id,
                turn_id=turn_id,
                tool_name=tool_use.name,
                arguments=mind_request.model_dump(mode="json")
                if mind_request is not None
                else {"raw_input": tool_use.input},
                result=result_payload,
                status="completed" if mind_response.ok else "error",
                latency_ms=latency_ms,
            )
            tool_call_id = tool_call.id
            tool_call_status = tool_call.status
            trace = repositories.add_trace(
                db,
                session_id=session_id,
                turn_id=turn_id,
                kind="mind.tool_call",
                payload={
                    "provider_tool_use_id": tool_use.id,
                    "tool_call_id": tool_call_id,
                    "tool_name": tool_use.name,
                    "arguments": mind_request.model_dump(mode="json")
                    if mind_request is not None
                    else {"raw_input": tool_use.input},
                    "result": result_payload,
                    "status": tool_call_status,
                    "latency_ms": latency_ms,
                },
            )
            trace_id = trace.id
            trace_ids.append(trace_id)

        mind_response.trace_id = trace_id
        result_payload = mind_response.model_dump(mode="json")
        executed = LLMExecutedToolCall(
            provider_tool_use_id=tool_use.id,
            tool_name=tool_use.name,
            arguments=mind_request.model_dump(mode="json")
            if mind_request is not None
            else {"raw_input": tool_use.input},
            result=result_payload,
            status=tool_call_status,
            latency_ms=latency_ms,
            tool_call_id=tool_call_id,
            trace_id=trace_id,
        )
        with Session(engine) as db:
            completed_event = record_tool_call_completed(
                db,
                session_id=session_id,
                turn_id=turn_id,
                started_event_id=started_event_id,
                executed=executed,
            )
            if event_sink is not None:
                event_sink.append(completed_event)
        return executed

    return run


def _enforce_native_answer_obligations(
    *,
    engine: Engine,
    settings: Settings,
    provider: LLMProvider,
    manifest: AnswerObligationManifest,
    result: LLMTextResult,
    request_messages: list[LLMMessage],
    system: str,
    max_tokens: int,
    tool_runner: Callable[[LLMToolUse], LLMExecutedToolCall],
    session_id: str,
    turn_id: str,
    trace_ids: list[str],
) -> tuple[LLMTextResult, str | None]:
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
    if settings.answer_obligations_mode != "active":
        return result, None

    current = result
    final_validation_trace_id: str | None = None
    for attempt in range(2):
        current_manifest = augment_with_tool_evidence(manifest, current.tool_calls)
        if current_manifest != manifest:
            with Session(engine) as db:
                manifest_trace_id = record_answer_obligations(
                    db,
                    session_id=session_id,
                    turn_id=turn_id,
                    manifest=current_manifest,
                    mode=settings.answer_obligations_mode,
                    phase=f"draft_{attempt + 1}",
                )
                trace_ids.append(manifest_trace_id)

        if not current_manifest.semantic:
            return current, final_validation_trace_id
        with Session(engine) as db:
            record_event(
                db,
                session_id=session_id,
                turn_id=turn_id,
                event_type="answer.validation.started",
                payload={"attempt": attempt + 1},
                source="answer_control",
                actor="backend",
                visibility="debug",
                status="active",
            )
        semantic_validation = validate_answer_semantics(
            provider=provider,
            manifest=current_manifest,
            answer=current.text,
            max_tokens=settings.answer_validation_max_tokens,
        )
        accepted = semantic_validation.accepted
        with Session(engine) as db:
            validation_trace = repositories.add_trace(
                db,
                session_id=session_id,
                turn_id=turn_id,
                kind="answer.validation",
                payload={
                    "transport": "native",
                    "attempt": attempt + 1,
                    "accepted": accepted,
                    "provider_finality": {
                        "accepted": current.stop_reason == "end_turn",
                        "stop_reason": current.stop_reason,
                        "source": "provider_stop_reason",
                    },
                    "semantic": semantic_validation.model_dump(mode="json"),
                    "manifest": current_manifest.model_dump(mode="json"),
                    "draft": {
                        "provider_message_id": current.provider_message_id,
                        "chars": len(current.text),
                        "text": current.text,
                    },
                },
            )
            validation_trace_id = validation_trace.id
            trace_ids.append(validation_trace_id)
            final_validation_trace_id = validation_trace_id
            record_event(
                db,
                session_id=session_id,
                turn_id=turn_id,
                event_type="answer.validation.accepted"
                if accepted
                else "answer.validation.rejected",
                payload={
                    "attempt": attempt + 1,
                    "provider_stop_reason": current.stop_reason,
                    "hard_failure_ids": semantic_validation.hard_failure_ids,
                },
                source="answer_control",
                actor="backend",
                visibility="debug",
                trace_id=validation_trace_id,
                status="completed" if accepted else "error",
            )
        if semantic_validation.validator_status == "failed":
            raise LLMIncompleteResponseError(
                "The answer validator could not evaluate the hard obligations.",
                details={
                    "reason": "answer_validation_unavailable",
                    "recoverable": True,
                    "validator_error": semantic_validation.validator_error,
                    "answer_validation_trace_id": final_validation_trace_id,
                },
            )
        if accepted:
            return (
                _accepted_native_result(
                    current,
                    validation_trace_id=final_validation_trace_id,
                ),
                final_validation_trace_id,
            )
        if attempt == 1:
            raise LLMIncompleteResponseError(
                "Scarlet did not satisfy the hard final-answer obligations.",
                details={
                    "reason": "answer_obligation_failed",
                    "attempt_count": 2,
                    "hard_failure_ids": semantic_validation.hard_failure_ids,
                    "answer_validation_trace_id": final_validation_trace_id,
                },
            )

        with Session(engine) as db:
            record_event(
                db,
                session_id=session_id,
                turn_id=turn_id,
                event_type="answer.recovery.requested",
                payload={
                    "attempt": 1,
                    "validation_trace_id": final_validation_trace_id,
                    "hard_failure_ids": semantic_validation.hard_failure_ids,
                },
                source="answer_control",
                actor="backend",
                visibility="debug",
                status="active",
                trace_id=final_validation_trace_id,
            )
        recovery_instruction = correction_instruction(
            manifest=current_manifest,
            validation=semantic_validation,
        )
        continuation_messages = [
            *request_messages,
            *[
                LLMMessage(role=item["role"], content=item["content"])
                for item in provider_history_from_result(current)
            ],
            LLMMessage(
                role="user",
                content=recovery_instruction,
            ),
        ]
        corrected = provider.generate_chat_with_tools(
            messages=continuation_messages,
            system=system,
            max_tokens=max_tokens,
            tools=[MIND_SHELL_TOOL_SCHEMA],
            tool_runner=tool_runner,
            max_tool_calls=None,
        )
        current = _merge_answer_recovery_results(
            current,
            corrected,
            recovery_instruction=recovery_instruction,
        )

    raise AssertionError("answer obligation recovery loop must return or raise")


def _accepted_native_result(
    result: LLMTextResult,
    *,
    validation_trace_id: str | None,
) -> LLMTextResult:
    raw_messages: list[dict[str, Any]] = []
    for index, raw_message in enumerate(result.raw_provider_messages):
        item = dict(raw_message)
        if index == len(result.raw_provider_messages) - 1:
            item["answer_disposition"] = "accepted_final"
        raw_messages.append(item)
    recovery = dict(result.completion_recovery)
    recovery["answer_obligations"] = {
        "recovered": len(raw_messages) > 1,
        "validation_trace_id": validation_trace_id,
    }
    return result.model_copy(
        update={
            "raw_provider_messages": raw_messages,
            "completion_recovery": recovery,
        }
    )


def _merge_answer_recovery_results(
    rejected: LLMTextResult,
    corrected: LLMTextResult,
    *,
    recovery_instruction: str,
) -> LLMTextResult:
    rejected_messages = [
        {**item, "answer_disposition": "rejected_progress"}
        for item in rejected.raw_provider_messages
    ]
    usage = dict(rejected.usage)
    for key, value in corrected.usage.items():
        if isinstance(value, (int, float)) and isinstance(usage.get(key), (int, float)):
            usage[key] += value
        else:
            usage[key] = value
    return corrected.model_copy(
        update={
            "usage": usage,
            "tool_calls": [*rejected.tool_calls, *corrected.tool_calls],
            "raw_provider_messages": [
                *rejected_messages,
                *corrected.raw_provider_messages,
            ],
            "completion_recovery": {
                **corrected.completion_recovery,
                "answer_obligation_attempted": True,
                "answer_obligation_recovered": True,
                "rejected_provider_message_id": rejected.provider_message_id,
            },
            "provider_history_tail": [
                *provider_history_from_result(rejected),
                {
                    "role": "user",
                    "content": [{"type": "text", "text": recovery_instruction}],
                },
                *provider_history_from_result(corrected),
            ],
        }
    )


def stream_native_turn(
    *,
    settings: Settings,
    engine: Engine,
    provider_factory: ProviderFactory,
    prepared: NativeTurnPreparation,
) -> Iterator[str]:
    session_id = prepared.session_id
    turn_id = prepared.turn_id
    trace_ids = prepared.trace_ids
    user_message_response = prepared.user_message
    llm_messages = prepared.model_messages
    system = prepared.effective_system
    max_tokens = prepared.max_tokens
    memory_context = prepared.memory_context.payload
    metacognitive_context = prepared.memory_context.metacognitive_payload
    runtime_context = prepared.memory_context.runtime_payload
    answer_manifest = prepared.answer_manifest
    sequence = 0
    pending_runtime_events: list[CognitiveEvent] = []

    def emit(event_type: str, data: dict[str, Any]) -> str:
        nonlocal sequence
        sequence += 1
        return ndjson(event_type, {"seq": sequence, "turn_id": turn_id, **data})

    def emit_runtime_event(event: CognitiveEvent) -> str:
        return emit("runtime_event", {"event": event_stream_payload(event)})

    def flush_pending_runtime_events() -> Iterator[str]:
        while pending_runtime_events:
            yield emit_runtime_event(pending_runtime_events.pop(0))

    yield emit(
        "turn_started",
        {
            "turn_id": turn_id,
            "session_id": session_id,
            "user_message": user_message_response.model_dump(mode="json"),
            "trace_ids": trace_ids,
        },
    )
    with Session(engine) as db:
        for event in repositories.list_events_for_turn(db, turn_id=turn_id):
            yield emit_runtime_event(event)
    yield emit(
        "memory_context",
        {
            "trace_id": memory_context.get("trace_id"),
            "searched": memory_context.get("searched"),
            "selected_count": memory_context.get("selected_count"),
            "candidate_count": memory_context.get("candidate_count"),
            "selected": memory_context.get("selected", []),
            "near_miss": memory_context.get("near_miss", []),
            "excluded": memory_context.get("excluded", []),
            "conflicts": memory_context.get("conflicts", []),
            "negative_evidence": memory_context.get("negative_evidence"),
        },
    )
    if metacognitive_context is not None:
        yield emit(
            "metacognitive_context",
            metacognitive_context_event_payload(metacognitive_context),
        )
    yield emit(
        "runtime_context",
        {
            "trace_id": runtime_context.get("trace_id"),
            "schema_version": runtime_context.get("schema_version"),
            "block_index": runtime_context.get("block_index", []),
            "blocks": runtime_context.get("blocks", []),
        },
    )

    result: LLMTextResult | None = None
    final_answer_validation_trace_id: str | None = None
    semantic_content_event_seen = False
    try:
        provider = provider_factory(settings)
        tool_runner = _build_mind_tool_runner(
            engine,
            settings=settings,
            provider_factory=provider_factory,
            session_id=session_id,
            turn_id=turn_id,
            source_message_id=user_message_response.id,
            trace_ids=trace_ids,
            event_sink=pending_runtime_events,
        )
        for stream_event in provider.stream_chat_with_tools(
            messages=llm_messages,
            system=system,
            max_tokens=max_tokens,
            tools=[MIND_SHELL_TOOL_SCHEMA],
            tool_runner=tool_runner,
            max_tool_calls=None,
        ):
            yield from flush_pending_runtime_events()
            if stream_event.type == "final_result":
                result = LLMTextResult.model_validate(stream_event.data["result"])
            else:
                if (
                    settings.answer_obligations_mode == "active"
                    and stream_event.type
                    in {"assistant_answer", "text_delta", "text_start"}
                ):
                    continue
                if stream_event.type in {
                    "assistant_note",
                    "assistant_answer",
                    "assistant_continuation",
                    "thinking_captured",
                }:
                    semantic_content_event_seen = True
                provider_event = record_provider_stream_event(
                    engine,
                    session_id=session_id,
                    turn_id=turn_id,
                    stream_event=stream_event,
                )
                if provider_event is not None:
                    yield emit_runtime_event(provider_event)
                yield emit(stream_event.type, stream_event.data)
        yield from flush_pending_runtime_events()
        if result is not None:
            original_provider_message_id = result.provider_message_id
            result, final_answer_validation_trace_id = _enforce_native_answer_obligations(
                engine=engine,
                settings=settings,
                provider=provider,
                manifest=answer_manifest,
                result=result,
                request_messages=llm_messages,
                system=system,
                max_tokens=max_tokens,
                tool_runner=tool_runner,
                session_id=session_id,
                turn_id=turn_id,
                trace_ids=trace_ids,
            )
            if result.provider_message_id != original_provider_message_id:
                yield emit(
                    "completion_recovery",
                    {
                        "reason": "answer_obligation_failed",
                        "answer_validation_trace_id": final_answer_validation_trace_id,
                    },
                )
            if settings.answer_obligations_mode == "active":
                accepted_answer_event = LLMStreamEvent(
                    type="assistant_answer",
                    data={
                        "model_step": len(result.raw_provider_messages) or 1,
                        "index": 0,
                        "provider_message_id": result.provider_message_id,
                        "stop_reason": result.stop_reason,
                        "text": result.text,
                        "answer_validation_trace_id": (
                            final_answer_validation_trace_id
                        ),
                    },
                )
                provider_event = record_provider_stream_event(
                    engine,
                    session_id=session_id,
                    turn_id=turn_id,
                    stream_event=accepted_answer_event,
                )
                if provider_event is not None:
                    yield emit_runtime_event(provider_event)
                yield emit(accepted_answer_event.type, accepted_answer_event.data)
                semantic_content_event_seen = True
    except LLMConfigurationError as exc:
        failed_event = record_failed_native_turn(
            engine,
            prepared=prepared,
            code="llm.not_configured",
            message=str(exc),
        )
        yield emit_runtime_event(failed_event)
        yield emit(
            "error",
            {"code": "llm.not_configured", "message": str(exc), "recoverable": True},
        )
        return
    except LLMIncompleteResponseError as exc:
        failed_event = record_failed_native_turn(
            engine,
            prepared=prepared,
            code="llm.incomplete_response",
            message=str(exc),
            details=exc.details,
        )
        yield emit_runtime_event(failed_event)
        yield emit(
            "error",
            {
                "code": "llm.incomplete_response",
                "message": str(exc),
                "recoverable": True,
                "details": exc.details,
            },
        )
        return
    except LLMRequestError as exc:
        failed_event = record_failed_native_turn(
            engine,
            prepared=prepared,
            code="llm.provider_error",
            message=str(exc),
        )
        yield emit_runtime_event(failed_event)
        yield emit(
            "error",
            {"code": "llm.provider_error", "message": str(exc), "recoverable": True},
        )
        return

    if result is None:
        message = "Provider stream ended without a final result."
        failed_event = record_failed_native_turn(
            engine,
            prepared=prepared,
            code="llm.stream_incomplete",
            message=message,
        )
        yield emit_runtime_event(failed_event)
        yield emit(
            "error",
            {"code": "llm.stream_incomplete", "message": message, "recoverable": True},
        )
        return

    if not result.text.strip():
        details = incomplete_result_details(result)
        message = "Provider ended without public text or a tool call."
        failed_event = record_failed_native_turn(
            engine,
            prepared=prepared,
            code="llm.incomplete_response",
            message=message,
            details=details,
        )
        yield emit_runtime_event(failed_event)
        yield emit(
            "error",
            {
                "code": "llm.incomplete_response",
                "message": message,
                "recoverable": True,
                "details": details,
            },
        )
        return

    completion = complete_native_turn(
        settings=settings,
        engine=engine,
        prepared=prepared,
        result=result,
        answer_validation_trace_id=final_answer_validation_trace_id,
        semantic_content_event_seen=semantic_content_event_seen,
    )
    for event in completion.runtime_events:
        yield emit("runtime_event", {"event": event})
    yield emit("turn_complete", completion.response.model_dump(mode="json"))


def _dispatch_tool_use(
    tool_use: LLMToolUse,
    *,
    context: MindAPIContext,
) -> tuple[MindAPIRequest | MindShellRequest | None, MindAPIResponse]:
    if tool_use.name != "mind_shell":
        return None, MindAPIResponse(
            ok=False,
            error=MindAPIError(
                code="tool.unknown",
                message=f"Unknown tool: {tool_use.name}",
                recoverable=True,
            ),
            result={
                "expected_tool": "mind_shell",
                "expected_tool_schema": MIND_SHELL_TOOL_SCHEMA["input_schema"],
            },
            suggested_next_actions=["Use the mind_shell tool with a command string"],
            confidence=1.0,
        )

    try:
        mind_request = MindShellRequest.model_validate(tool_use.input)
    except ValidationError as exc:
        return None, MindAPIResponse(
            ok=False,
            result={
                "expected_tool": "mind_shell",
                "expected_tool_schema": MIND_SHELL_TOOL_SCHEMA["input_schema"],
            },
            error=MindAPIError(
                code="mind_shell.invalid_request",
                message=str(exc),
                recoverable=True,
            ),
            suggested_next_actions=["Call help", "Retry with a valid command string"],
            confidence=1.0,
        )

    return mind_request, dispatch_mind_shell(mind_request, context=context)


def _result_trace_ids(result_payload: dict[str, Any]) -> list[str]:
    result = result_payload.get("result")
    if not isinstance(result, dict):
        return []
    trace_ids = result.get("trace_ids")
    if not isinstance(trace_ids, list):
        data = result.get("data")
        trace_ids = data.get("trace_ids") if isinstance(data, dict) else None
    if not isinstance(trace_ids, list):
        return []
    return [trace_id for trace_id in trace_ids if isinstance(trace_id, str)]


def _append_unique_trace_ids(target: list[str], source: list[str]) -> None:
    for trace_id in source:
        if trace_id not in target:
            target.append(trace_id)
