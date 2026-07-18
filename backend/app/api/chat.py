import time
from collections.abc import Callable, Iterator
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from pydantic import ValidationError
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.api.chat_accounting import (
    context_accounting_summary as _context_accounting_summary,
    post_turn_model_history_tokens as _post_turn_model_history_tokens,
    provider_message_stats as _provider_message_stats,
    record_context_accounting_observed as _record_context_accounting_observed,
    record_context_accounting_preflight as _record_context_accounting_preflight,
)
from app.api.chat_provider_history import (
    ProviderHistory,
    provider_history_from_result as _provider_history_from_result,
    provider_messages_for_turn as _provider_messages_for_turn,
    updated_provider_history as _updated_provider_history,
    valid_content_blocks as _valid_content_blocks,
    valid_provider_history as _valid_provider_history,
)
from app.api.chat_serialization import (
    ChatMessageResponse,
    ChatSessionResponse,
    ChatTurnResponse,
    EventResponse,
    TraceResponse,
    event_response as _event_response,
    event_stream_payload as _event_stream_payload,
    incomplete_result_details as _incomplete_result_details,
    memory_context_event_payload as _memory_context_event_payload,
    message_response as _message_response,
    metacognitive_context_event_payload as _metacognitive_context_event_payload,
    ndjson as _ndjson,
    response_event_messages as _response_event_messages,
    runtime_context_event_payload as _runtime_context_event_payload,
    session_response as _session_response,
    trace_response as _trace_response,
)
from app.config import Settings
from app.llm.factory import (
    active_provider_max_tokens,
    active_provider_model,
    build_llm_provider,
)
from app.llm.provider import (
    LLMExecutedToolCall,
    LLMConfigurationError,
    LLMIncompleteResponseError,
    LLMMessage,
    LLMProvider,
    LLMRequestError,
    LLMStreamEvent,
    LLMTextResult,
    LLMToolUse,
)
from app.mind.dispatcher import (
    MindAPIContext,
    MindAPIError,
    MindAPIRequest,
    MindAPIResponse,
)
from app.mind.context import build_memory_context
from app.mind.shell import (
    MIND_SHELL_TOOL_SCHEMA,
    MindShellRequest,
    dispatch_mind_shell,
)
from app.prompts.system import AgentSystemPromptError, resolve_agent_system_prompt
from app.runtime.events import (
    record_event,
    record_provider_stream_event,
    record_response_content_events,
    record_tool_call_completed,
    record_tool_call_started,
)
from app.runtime.maintenance import (
    schedule_history_compaction,
    schedule_session_idle_maintenance,
    schedule_summary_repairs,
)
from app.runtime.history_compaction import build_chronology_source_map
from app.runtime.history_runtime import route_history_for_model
from app.runtime.preferences import load_runtime_preferences
from app.runtime.answer_obligations import (
    AnswerObligationManifest,
    augment_with_tool_evidence,
    compile_answer_obligations,
    correction_instruction,
    render_answer_obligations,
    strip_native_final_marker,
    validate_answer_semantics,
)
from app.storage import repositories
from app.storage.models import ChatSession, CognitiveEvent


ProviderFactory = Callable[[Settings], LLMProvider]


class ChatSessionCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatTurnRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20000)
    system: str | None = Field(default=None, max_length=20000)
    max_tokens: int | None = Field(default=None, ge=1, le=131072)


def build_chat_router(
    settings: Settings,
    engine: Engine,
    provider_factory: ProviderFactory = build_llm_provider,
) -> APIRouter:
    router = APIRouter(prefix="/api/chat", tags=["chat"])

    @router.post("/sessions", response_model=ChatSessionResponse)
    def create_session(request: ChatSessionCreate) -> ChatSessionResponse:
        with Session(engine) as db:
            chat_session = repositories.create_chat_session(
                db,
                title=request.title,
                metadata=request.metadata,
            )
            schedule_summary_repairs(
                db,
                settings=settings,
                limit=1,
                exclude_session_id=chat_session.id,
            )
            return _session_response(chat_session)

    @router.get("/sessions", response_model=list[ChatSessionResponse])
    def list_sessions(
        limit: int = Query(default=30, ge=1, le=100),
    ) -> list[ChatSessionResponse]:
        with Session(engine) as db:
            sessions = repositories.list_chat_sessions(db, limit=limit)
            return [_session_response(chat_session) for chat_session in sessions]

    @router.get(
        "/sessions/{session_id}/messages",
        response_model=list[ChatMessageResponse],
    )
    def get_messages(session_id: str) -> list[ChatMessageResponse]:
        with Session(engine) as db:
            _require_session(db, session_id)
            messages = repositories.list_messages(db, session_id=session_id)
            return [_message_response(message) for message in messages]

    @router.post(
        "/sessions/{session_id}/turn",
        response_model=ChatTurnResponse,
    )
    def create_turn(session_id: str, request: ChatTurnRequest) -> ChatTurnResponse:
        started = time.perf_counter()
        trace_ids: list[str] = []

        with Session(engine) as db:
            chat_session = _require_session(db, session_id)
            turn = repositories.create_turn(
                db,
                session_id=session_id,
                model=active_provider_model(settings),
            )
            turn_id = turn.id
            record_event(
                db,
                session_id=session_id,
                turn_id=turn_id,
                event_type="turn.started",
                payload={
                    "model": active_provider_model(settings),
                    "entrypoint": "chat.turn",
                },
                source="runtime",
                actor="backend",
                visibility="debug",
                status="active",
            )
            user_message = repositories.add_message(
                db,
                session_id=session_id,
                turn_id=turn_id,
                role="user",
                content=request.message,
            )
            record_event(
                db,
                session_id=session_id,
                turn_id=turn_id,
                event_type="message.user.persisted",
                payload={
                    "message_id": user_message.id,
                    "content_chars": len(user_message.content),
                },
                source="chat",
                actor="user",
                visibility="public",
                message_id=user_message.id,
            )
            user_message_response = _message_response(user_message)
            history = repositories.list_messages(db, session_id=session_id)
            provider_history_source, canonical_llm_messages = (
                _provider_messages_for_turn(
                    chat_session=chat_session,
                    history=history,
                    current_user_message=user_message,
                )
            )
            max_tokens = request.max_tokens or active_provider_max_tokens(settings)
            try:
                system_prompt = resolve_agent_system_prompt(
                    settings,
                    override=request.system,
                )
            except AgentSystemPromptError as exc:
                repositories.add_trace(
                    db,
                    session_id=session_id,
                    turn_id=turn_id,
                    kind="llm.error",
                    payload={
                        "code": "agent.system_prompt_error",
                        "message": str(exc),
                    },
                )
                repositories.complete_turn(
                    db,
                    turn_id=turn_id,
                    status="failed",
                    latency_ms=int((time.perf_counter() - started) * 1000),
                    error={
                        "code": "agent.system_prompt_error",
                        "message": str(exc),
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={
                        "code": "agent.system_prompt_error",
                        "message": str(exc),
                        "recoverable": True,
                    },
                ) from exc

            memory_context = build_memory_context(
                db,
                chat_session=chat_session,
                turn_id=turn_id,
                current_user_message=user_message,
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
                payload=_memory_context_event_payload(memory_context.payload),
                source="memory",
                actor="backend",
                visibility="debug",
                trace_id=memory_context.trace_id,
            )
            if memory_context.metacognitive_payload is not None:
                record_event(
                    db,
                    session_id=session_id,
                    turn_id=turn_id,
                    event_type="metacognitive.context.injected"
                    if memory_context.metacognitive_payload.get("model_facing") is True
                    else "metacognitive.context.shadowed",
                    payload=_metacognitive_context_event_payload(
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
                payload=_runtime_context_event_payload(memory_context.runtime_payload),
                source="runtime",
                actor="backend",
                visibility="debug",
                trace_id=memory_context.runtime_trace_id,
            )
            history_routing = route_history_for_model(
                db,
                session_id=session_id,
                canonical_messages=canonical_llm_messages,
                chars_per_token=float(settings.context_estimated_chars_per_token),
                mode=str(settings.history_compaction_mode),
            )
            llm_messages = history_routing.model_messages
            provider_message_stats = _provider_message_stats(llm_messages)
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
            effective_system = _compose_system_with_runtime_context(
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
                answer_obligations_trace_id = _record_answer_obligations(
                    db,
                    session_id=session_id,
                    turn_id=turn_id,
                    manifest=answer_manifest,
                    mode=settings.answer_obligations_mode,
                    phase="initial",
                )
                trace_ids.append(answer_obligations_trace_id)
            answer_obligations_appendix = ""
            if settings.answer_obligations_mode == "active":
                answer_obligations_appendix = render_answer_obligations(
                    answer_manifest
                )
                effective_system += answer_obligations_appendix
            accounting_trace, accounting_payload = _record_context_accounting_preflight(
                db,
                session_id=session_id,
                turn_id=turn_id,
                model=active_provider_model(settings),
                transport="native",
                base_system=system_prompt.content,
                runtime_context=memory_context.runtime_context,
                messages=llm_messages,
                settings=settings,
                compacted_chronology=history_routing.system_appendix,
                answer_obligations=answer_obligations_appendix,
            )
            accounting_trace_id = accounting_trace.id
            trace_ids.append(accounting_trace_id)
            request_trace = repositories.add_trace(
                db,
                session_id=session_id,
                turn_id=turn_id,
                kind="llm.request",
                payload={
                    "model": active_provider_model(settings),
                    "max_tokens": max_tokens,
                    "system": effective_system,
                    "base_system": system_prompt.content,
                    "system_present": True,
                    "system_source": system_prompt.source,
                    "system_path": system_prompt.path,
                    "runtime_context_present": True,
                    "runtime_context": memory_context.runtime_context,
                    "memory_context_trace_id": memory_context.trace_id,
                    "metacognitive_context_trace_id": (
                        memory_context.metacognitive_trace_id
                    ),
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
                    "context_accounting": _context_accounting_summary(
                        accounting_payload
                    ),
                    "tool_loop_policy": "model_controlled_unbounded",
                    "provider_history_source": (
                        "history_compaction_artifact"
                        if history_routing.payload.get("status")
                        == "derived_history_active"
                        else provider_history_source
                    ),
                    "canonical_provider_history_source": provider_history_source,
                    "history_routing_trace_id": history_routing_trace_id,
                    "history_routing": history_routing.payload,
                    "provider_message_stats": provider_message_stats,
                    "canonical_provider_messages": [
                        message.model_dump(mode="json")
                        for message in canonical_llm_messages
                    ],
                    "provider_messages": [
                        message.model_dump(mode="json") for message in llm_messages
                    ],
                    "messages": [
                        {
                            "id": message.id,
                            "role": message.role,
                            "content": message.content,
                        }
                        for message in history
                        if message.role in {"user", "assistant"}
                    ],
                    "tools": [MIND_SHELL_TOOL_SCHEMA],
                    "answer_obligations_trace_id": answer_obligations_trace_id,
                    "answer_obligations": answer_manifest.model_dump(mode="json"),
                },
            )
            trace_ids.append(request_trace.id)
            record_event(
                db,
                session_id=session_id,
                turn_id=turn_id,
                event_type="llm.request.created",
                payload={
                    "model": active_provider_model(settings),
                    "max_tokens": max_tokens,
                    "provider_history_source": (
                        "history_compaction_artifact"
                        if history_routing.payload.get("status")
                        == "derived_history_active"
                        else provider_history_source
                    ),
                    "history_routing_status": history_routing.payload.get("status"),
                    "history_routing_trace_id": history_routing_trace_id,
                    "provider_message_stats": provider_message_stats,
                    "context_accounting_trace_id": accounting_trace_id,
                    "estimated_input_tokens": accounting_payload["total"][
                        "estimated_input_tokens"
                    ],
                    "tool_count": 1,
                },
                source="llm",
                actor="backend",
                visibility="debug",
                trace_id=request_trace.id,
            )

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
            )
            result = provider.generate_chat_with_tools(
                messages=llm_messages,
                system=effective_system,
                max_tokens=max_tokens,
                tools=[MIND_SHELL_TOOL_SCHEMA],
                tool_runner=tool_runner,
                max_tool_calls=None,
            )
            result, final_answer_validation_trace_id = (
                _enforce_native_answer_obligations(
                    engine=engine,
                    settings=settings,
                    provider=provider,
                    manifest=answer_manifest,
                    result=result,
                    request_messages=llm_messages,
                    system=effective_system,
                    max_tokens=max_tokens,
                    tool_runner=tool_runner,
                    session_id=session_id,
                    turn_id=turn_id,
                    trace_ids=trace_ids,
                )
            )
        except LLMConfigurationError as exc:
            _record_failed_turn(
                engine,
                session_id=session_id,
                turn_id=turn_id,
                started=started,
                code="llm.not_configured",
                message=str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "llm.not_configured",
                    "message": str(exc),
                    "recoverable": True,
                },
            ) from exc
        except LLMIncompleteResponseError as exc:
            _record_failed_turn(
                engine,
                session_id=session_id,
                turn_id=turn_id,
                started=started,
                code="llm.incomplete_response",
                message=str(exc),
                details=exc.details,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "code": "llm.incomplete_response",
                    "message": str(exc),
                    "recoverable": True,
                    "details": exc.details,
                },
            ) from exc
        except LLMRequestError as exc:
            _record_failed_turn(
                engine,
                session_id=session_id,
                turn_id=turn_id,
                started=started,
                code="llm.provider_error",
                message=str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "code": "llm.provider_error",
                    "message": str(exc),
                    "recoverable": True,
                },
            ) from exc

        if not result.text.strip():
            details = _incomplete_result_details(result)
            message = "Provider ended without public text or a tool call."
            _record_failed_turn(
                engine,
                session_id=session_id,
                turn_id=turn_id,
                started=started,
                code="llm.incomplete_response",
                message=message,
                details=details,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "code": "llm.incomplete_response",
                    "message": message,
                    "recoverable": True,
                    "details": details,
                },
            )

        latency_ms = int((time.perf_counter() - started) * 1000)
        with Session(engine) as db:
            assistant_message = repositories.add_message(
                db,
                session_id=session_id,
                turn_id=turn_id,
                role="assistant",
                content=result.text,
                provider_message_id=result.provider_message_id,
                raw_content=result.raw_content,
                metadata={
                    "model": result.model,
                    "usage": result.usage,
                    "stop_reason": result.stop_reason,
                    "completion_recovery": result.completion_recovery,
                    "answer_obligations_trace_id": answer_obligations_trace_id,
                    "answer_validation_trace_id": final_answer_validation_trace_id,
                },
            )
            response_trace = repositories.add_trace(
                db,
                session_id=session_id,
                turn_id=turn_id,
                kind="llm.response",
                payload={
                    "model": result.model,
                    "text": result.text,
                    "usage": result.usage,
                    "provider_message_id": result.provider_message_id,
                    "stop_reason": result.stop_reason,
                    "raw_content": result.raw_content,
                    "tool_calls": [
                        tool_call.model_dump(mode="json")
                        for tool_call in result.tool_calls
                    ],
                    "raw_provider_messages": result.raw_provider_messages,
                    "completion_recovery": result.completion_recovery,
                    "answer_obligations_trace_id": answer_obligations_trace_id,
                    "answer_validation_trace_id": final_answer_validation_trace_id,
                },
            )
            trace_ids.append(response_trace.id)
            observed_trace = _record_context_accounting_observed(
                db,
                session_id=session_id,
                turn_id=turn_id,
                preflight_trace_id=accounting_trace_id,
                preflight=accounting_payload,
                result=result,
            )
            trace_ids.append(observed_trace.id)
            record_event(
                db,
                session_id=session_id,
                turn_id=turn_id,
                event_type="llm.response.completed",
                payload={
                    "model": result.model,
                    "provider_message_id": result.provider_message_id,
                    "stop_reason": result.stop_reason,
                    "usage": result.usage,
                    "tool_call_count": len(result.tool_calls),
                    "completion_recovery": result.completion_recovery,
                },
                source="llm",
                actor="backend",
                visibility="debug",
                trace_id=response_trace.id,
            )
            record_event(
                db,
                session_id=session_id,
                turn_id=turn_id,
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
            record_response_content_events(
                db,
                session_id=session_id,
                turn_id=turn_id,
                raw_provider_messages=_response_event_messages(result),
                response_trace_id=response_trace.id,
                assistant_message_id=assistant_message.id,
            )
            repositories.update_chat_session_provider_history(
                db,
                session_id=session_id,
                provider_history=_updated_provider_history(
                    canonical_llm_messages,
                    result,
                ),
            )
            completed_turn = repositories.complete_turn(
                db,
                turn_id=turn_id,
                latency_ms=latency_ms,
            )
            turn_completed_event = record_event(
                db,
                session_id=session_id,
                turn_id=turn_id,
                event_type="turn.completed",
                payload={
                    "latency_ms": latency_ms,
                    "trace_ids": trace_ids,
                },
                source="runtime",
                actor="backend",
                visibility="debug",
                status=completed_turn.status,
            )
            chars_per_token = float(
                accounting_payload.get("calibration", {}).get(
                    "chars_per_token_used",
                    settings.context_estimated_chars_per_token,
                )
            )
            post_turn_source_map = build_chronology_source_map(
                db,
                session_id=session_id,
                chars_per_token=chars_per_token,
            )
            provider_channel_tokens = int(
                accounting_payload.get("channels", {})
                .get("provider_history", {})
                .get("estimated_tokens", 0)
            )
            external_context_tokens = max(
                0,
                int(
                    accounting_payload.get("total", {}).get(
                        "estimated_input_tokens",
                        0,
                    )
                )
                - provider_channel_tokens,
            )
            schedule_history_compaction(
                db,
                settings=settings,
                session_id=session_id,
                trigger_turn_id=turn_id,
                trigger_event_id=turn_completed_event.id,
                source_map=post_turn_source_map,
                external_context_tokens=external_context_tokens,
                chars_per_token=chars_per_token,
                model_history_tokens=_post_turn_model_history_tokens(
                    post_turn_source_map,
                    history_routing.payload,
                ),
            )
            if settings.maintenance_enabled:
                schedule_session_idle_maintenance(
                    db,
                    settings=settings,
                    session_id=session_id,
                    trigger_turn_id=turn_id,
                    trigger_event_id=turn_completed_event.id,
                )
            chat_session = _require_session(db, session_id)
            return ChatTurnResponse(
                session=_session_response(chat_session),
                turn_id=completed_turn.id,
                status=completed_turn.status,
                user_message=user_message_response,
                assistant_message=_message_response(assistant_message),
                trace_ids=trace_ids,
                model=result.model,
                latency_ms=latency_ms,
                usage=result.usage,
            )

    @router.post("/sessions/{session_id}/turn/stream")
    def create_streaming_turn(
        session_id: str,
        request: ChatTurnRequest,
    ) -> StreamingResponse:
        started = time.perf_counter()
        trace_ids: list[str] = []

        with Session(engine) as db:
            chat_session = _require_session(db, session_id)
            turn = repositories.create_turn(
                db,
                session_id=session_id,
                model=active_provider_model(settings),
            )
            turn_id = turn.id
            record_event(
                db,
                session_id=session_id,
                turn_id=turn_id,
                event_type="turn.started",
                payload={
                    "model": active_provider_model(settings),
                    "entrypoint": "chat.turn.stream",
                },
                source="runtime",
                actor="backend",
                visibility="debug",
                status="active",
            )
            user_message = repositories.add_message(
                db,
                session_id=session_id,
                turn_id=turn_id,
                role="user",
                content=request.message,
            )
            record_event(
                db,
                session_id=session_id,
                turn_id=turn_id,
                event_type="message.user.persisted",
                payload={
                    "message_id": user_message.id,
                    "content_chars": len(user_message.content),
                },
                source="chat",
                actor="user",
                visibility="public",
                message_id=user_message.id,
            )
            user_message_response = _message_response(user_message)
            history = repositories.list_messages(db, session_id=session_id)
            provider_history_source, canonical_llm_messages = (
                _provider_messages_for_turn(
                    chat_session=chat_session,
                    history=history,
                    current_user_message=user_message,
                )
            )
            max_tokens = request.max_tokens or active_provider_max_tokens(settings)
            try:
                system_prompt = resolve_agent_system_prompt(
                    settings,
                    override=request.system,
                )
            except AgentSystemPromptError as exc:
                repositories.add_trace(
                    db,
                    session_id=session_id,
                    turn_id=turn_id,
                    kind="llm.error",
                    payload={
                        "code": "agent.system_prompt_error",
                        "message": str(exc),
                    },
                )
                repositories.complete_turn(
                    db,
                    turn_id=turn_id,
                    status="failed",
                    latency_ms=int((time.perf_counter() - started) * 1000),
                    error={
                        "code": "agent.system_prompt_error",
                        "message": str(exc),
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={
                        "code": "agent.system_prompt_error",
                        "message": str(exc),
                        "recoverable": True,
                    },
                ) from exc

            memory_context = build_memory_context(
                db,
                chat_session=chat_session,
                turn_id=turn_id,
                current_user_message=user_message,
                history=history,
                runtime_preferences=load_runtime_preferences(db, settings),
                settings=settings,
            )
            trace_ids.append(memory_context.trace_id)
            if memory_context.metacognitive_trace_id is not None:
                trace_ids.append(memory_context.metacognitive_trace_id)
            trace_ids.append(memory_context.runtime_trace_id)
            record_event(
                db,
                session_id=session_id,
                turn_id=turn_id,
                event_type="memory.context.built",
                payload=_memory_context_event_payload(memory_context.payload),
                source="memory",
                actor="backend",
                visibility="debug",
                trace_id=memory_context.trace_id,
            )
            if memory_context.metacognitive_payload is not None:
                record_event(
                    db,
                    session_id=session_id,
                    turn_id=turn_id,
                    event_type="metacognitive.context.injected"
                    if memory_context.metacognitive_payload.get("model_facing") is True
                    else "metacognitive.context.shadowed",
                    payload=_metacognitive_context_event_payload(
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
                payload=_runtime_context_event_payload(memory_context.runtime_payload),
                source="runtime",
                actor="backend",
                visibility="debug",
                trace_id=memory_context.runtime_trace_id,
            )
            history_routing = route_history_for_model(
                db,
                session_id=session_id,
                canonical_messages=canonical_llm_messages,
                chars_per_token=float(settings.context_estimated_chars_per_token),
                mode=str(settings.history_compaction_mode),
            )
            llm_messages = history_routing.model_messages
            provider_message_stats = _provider_message_stats(llm_messages)
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
            effective_system = _compose_system_with_runtime_context(
                system_prompt.content,
                memory_context.runtime_context,
            ) + history_routing.system_appendix
            answer_manifest = compile_answer_obligations(
                transport="native",
                memory_context=memory_context.payload,
                metacognitive_context=memory_context.metacognitive_payload,
            )
            answer_obligations_trace_id = None
            if settings.answer_obligations_mode != "off":
                answer_obligations_trace_id = _record_answer_obligations(
                    db,
                    session_id=session_id,
                    turn_id=turn_id,
                    manifest=answer_manifest,
                    mode=settings.answer_obligations_mode,
                    phase="initial",
                )
                trace_ids.append(answer_obligations_trace_id)
            answer_obligations_appendix = ""
            if settings.answer_obligations_mode == "active":
                answer_obligations_appendix = render_answer_obligations(
                    answer_manifest
                )
                effective_system += answer_obligations_appendix
            accounting_trace, accounting_payload = _record_context_accounting_preflight(
                db,
                session_id=session_id,
                turn_id=turn_id,
                model=active_provider_model(settings),
                transport="native_stream",
                base_system=system_prompt.content,
                runtime_context=memory_context.runtime_context,
                messages=llm_messages,
                settings=settings,
                compacted_chronology=history_routing.system_appendix,
                answer_obligations=answer_obligations_appendix,
            )
            accounting_trace_id = accounting_trace.id
            trace_ids.append(accounting_trace_id)
            request_trace = repositories.add_trace(
                db,
                session_id=session_id,
                turn_id=turn_id,
                kind="llm.request",
                payload={
                    "model": active_provider_model(settings),
                    "max_tokens": max_tokens,
                    "system": effective_system,
                    "base_system": system_prompt.content,
                    "system_present": True,
                    "system_source": system_prompt.source,
                    "system_path": system_prompt.path,
                    "runtime_context_present": True,
                    "runtime_context": memory_context.runtime_context,
                    "memory_context_trace_id": memory_context.trace_id,
                    "metacognitive_context_trace_id": (
                        memory_context.metacognitive_trace_id
                    ),
                    "metacognitive_context_mode": (
                        memory_context.metacognitive_payload or {}
                    ).get("mode"),
                    "metacognitive_context_model_facing": (
                        memory_context.metacognitive_payload or {}
                    ).get("model_facing", False),
                    "runtime_context_trace_id": memory_context.runtime_trace_id,
                    "context_accounting_trace_id": accounting_trace_id,
                    "context_accounting": _context_accounting_summary(
                        accounting_payload
                    ),
                    "tool_loop_policy": "model_controlled_unbounded",
                    "provider_history_source": (
                        "history_compaction_artifact"
                        if history_routing.payload.get("status")
                        == "derived_history_active"
                        else provider_history_source
                    ),
                    "canonical_provider_history_source": provider_history_source,
                    "history_routing_trace_id": history_routing_trace_id,
                    "history_routing": history_routing.payload,
                    "provider_message_stats": provider_message_stats,
                    "canonical_provider_messages": [
                        message.model_dump(mode="json")
                        for message in canonical_llm_messages
                    ],
                    "provider_messages": [
                        message.model_dump(mode="json") for message in llm_messages
                    ],
                    "messages": [
                        {
                            "id": message.id,
                            "role": message.role,
                            "content": message.content,
                        }
                        for message in history
                        if message.role in {"user", "assistant"}
                    ],
                    "tools": [MIND_SHELL_TOOL_SCHEMA],
                    "stream": True,
                    "answer_obligations_trace_id": answer_obligations_trace_id,
                    "answer_obligations": answer_manifest.model_dump(mode="json"),
                },
            )
            trace_ids.append(request_trace.id)
            record_event(
                db,
                session_id=session_id,
                turn_id=turn_id,
                event_type="llm.request.created",
                payload={
                    "model": active_provider_model(settings),
                    "max_tokens": max_tokens,
                    "provider_history_source": (
                        "history_compaction_artifact"
                        if history_routing.payload.get("status")
                        == "derived_history_active"
                        else provider_history_source
                    ),
                    "history_routing_status": history_routing.payload.get("status"),
                    "history_routing_trace_id": history_routing_trace_id,
                    "provider_message_stats": provider_message_stats,
                    "context_accounting_trace_id": accounting_trace_id,
                    "estimated_input_tokens": accounting_payload["total"][
                        "estimated_input_tokens"
                    ],
                    "tool_count": 1,
                    "stream": True,
                },
                source="llm",
                actor="backend",
                visibility="debug",
                trace_id=request_trace.id,
            )

        return StreamingResponse(
            _stream_turn_events(
                settings=settings,
                engine=engine,
                provider_factory=provider_factory,
                session_id=session_id,
                turn_id=turn_id,
                started=started,
                trace_ids=trace_ids,
                user_message_response=user_message_response,
                llm_messages=llm_messages,
                canonical_llm_messages=canonical_llm_messages,
                system=effective_system,
                max_tokens=max_tokens,
                memory_context=memory_context.payload,
                metacognitive_context=memory_context.metacognitive_payload,
                runtime_context=memory_context.runtime_payload,
                accounting_trace_id=accounting_trace_id,
                accounting_payload=accounting_payload,
                history_routing_payload=history_routing.payload,
                answer_manifest=answer_manifest,
                answer_obligations_trace_id=answer_obligations_trace_id,
            ),
            media_type="application/x-ndjson",
        )

    return router


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


def _record_answer_obligations(
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
    trace_id = trace.id
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
        trace_id=trace_id,
    )
    return trace_id


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
    if settings.answer_obligations_mode != "active":
        return result, None

    current = result
    final_validation_trace_id: str | None = None
    for attempt in range(2):
        current_manifest = augment_with_tool_evidence(manifest, current.tool_calls)
        if current_manifest != manifest:
            with Session(engine) as db:
                manifest_trace_id = _record_answer_obligations(
                    db,
                    session_id=session_id,
                    turn_id=turn_id,
                    manifest=current_manifest,
                    mode=settings.answer_obligations_mode,
                    phase=f"draft_{attempt + 1}",
                )
                trace_ids.append(manifest_trace_id)

        public_answer, structural_ok = strip_native_final_marker(current.text)
        semantic_validation = (
            validate_answer_semantics(
                provider=provider,
                manifest=current_manifest,
                answer=public_answer if structural_ok else current.text,
                max_tokens=settings.answer_validation_max_tokens,
            )
            if structural_ok
            else None
        )
        accepted = structural_ok and (
            semantic_validation is None or semantic_validation.accepted
        )
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
                    "structural_final_boundary": {
                        "accepted": structural_ok,
                        "marker_stripped": structural_ok,
                    },
                    "semantic": semantic_validation.model_dump(mode="json")
                    if semantic_validation is not None
                    else None,
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
                    "structural_ok": structural_ok,
                    "hard_failure_ids": (
                        semantic_validation.hard_failure_ids
                        if semantic_validation is not None
                        else ["answer.final_boundary"]
                    ),
                },
                source="answer_control",
                actor="backend",
                visibility="debug",
                trace_id=validation_trace_id,
                status="completed" if accepted else "error",
            )
        if (
            semantic_validation is not None
            and semantic_validation.validator_status == "failed"
        ):
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
                    public_answer=public_answer,
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
                    "structural_failure": not structural_ok,
                    "hard_failure_ids": (
                        semantic_validation.hard_failure_ids
                        if semantic_validation is not None
                        else ["answer.final_boundary"]
                    ),
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
                    "structural_failure": not structural_ok,
                    "hard_failure_ids": (
                        semantic_validation.hard_failure_ids
                        if semantic_validation is not None
                        else ["answer.final_boundary"]
                    ),
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
            structural_failure=not structural_ok,
        )
        continuation_messages = [
            *request_messages,
            *[
                LLMMessage(role=item["role"], content=item["content"])
                for item in _provider_history_from_result(current)
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
    public_answer: str,
    validation_trace_id: str | None,
) -> LLMTextResult:
    raw_content = _strip_marker_from_content(result.raw_content)
    raw_messages: list[dict[str, Any]] = []
    for index, raw_message in enumerate(result.raw_provider_messages):
        item = dict(raw_message)
        if index == len(result.raw_provider_messages) - 1:
            item["content"] = _strip_marker_from_content(
                _valid_content_blocks(item.get("content"))
            )
            item["answer_disposition"] = "accepted_final"
        raw_messages.append(item)
    recovery = dict(result.completion_recovery)
    recovery_tail = _valid_provider_history(result.provider_history_tail)
    cleaned_tail: ProviderHistory = []
    if recovery_tail:
        for item in recovery_tail:
            cleaned_tail.append(
                {
                    "role": item["role"],
                    "content": _strip_marker_from_content(item["content"]),
                }
            )
    recovery["answer_obligations"] = {
        "recovered": len(raw_messages) > 1,
        "validation_trace_id": validation_trace_id,
    }
    return result.model_copy(
        update={
            "text": public_answer,
            "raw_content": raw_content,
            "raw_provider_messages": raw_messages,
            "completion_recovery": recovery,
            "provider_history_tail": cleaned_tail,
        }
    )


def _strip_marker_from_content(
    content: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for block in content:
        item = dict(block)
        if item.get("type") == "text" and isinstance(item.get("text"), str):
            text, accepted = strip_native_final_marker(item["text"])
            if accepted:
                item["text"] = text
        cleaned.append(item)
    return cleaned


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
                *_provider_history_from_result(rejected),
                {
                    "role": "user",
                    "content": [{"type": "text", "text": recovery_instruction}],
                },
                *_provider_history_from_result(corrected),
            ],
        }
    )


def _stream_turn_events(
    *,
    settings: Settings,
    engine: Engine,
    provider_factory: ProviderFactory,
    session_id: str,
    turn_id: str,
    started: float,
    trace_ids: list[str],
    user_message_response: ChatMessageResponse,
    llm_messages: list[LLMMessage],
    canonical_llm_messages: list[LLMMessage],
    system: str,
    max_tokens: int,
    memory_context: dict[str, Any],
    metacognitive_context: dict[str, Any] | None,
    runtime_context: dict[str, Any],
    accounting_trace_id: str,
    accounting_payload: dict[str, Any],
    history_routing_payload: dict[str, Any],
    answer_manifest: AnswerObligationManifest,
    answer_obligations_trace_id: str | None,
) -> Iterator[str]:
    sequence = 0
    pending_runtime_events: list[CognitiveEvent] = []

    def emit(event_type: str, data: dict[str, Any]) -> str:
        nonlocal sequence
        sequence += 1
        return _ndjson(event_type, {"seq": sequence, "turn_id": turn_id, **data})

    def emit_runtime_event(event: CognitiveEvent) -> str:
        return emit("runtime_event", {"event": _event_stream_payload(event)})

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
            _metacognitive_context_event_payload(metacognitive_context),
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
                if stream_event.type in {"assistant_note", "assistant_answer"}:
                    event_text = str(stream_event.data.get("text") or "")
                    public_event_text, marker_found = strip_native_final_marker(
                        event_text
                    )
                    if marker_found:
                        stream_event.data["text"] = public_event_text
                if stream_event.type in {
                    "assistant_note",
                    "assistant_answer",
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
        failed_event = _record_failed_turn(
            engine,
            session_id=session_id,
            turn_id=turn_id,
            started=started,
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
        failed_event = _record_failed_turn(
            engine,
            session_id=session_id,
            turn_id=turn_id,
            started=started,
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
        failed_event = _record_failed_turn(
            engine,
            session_id=session_id,
            turn_id=turn_id,
            started=started,
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
        failed_event = _record_failed_turn(
            engine,
            session_id=session_id,
            turn_id=turn_id,
            started=started,
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
        details = _incomplete_result_details(result)
        message = "Provider ended without public text or a tool call."
        failed_event = _record_failed_turn(
            engine,
            session_id=session_id,
            turn_id=turn_id,
            started=started,
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

    latency_ms = int((time.perf_counter() - started) * 1000)
    final_runtime_events: list[dict[str, Any]] = []
    with Session(engine) as db:
        assistant_message = repositories.add_message(
            db,
            session_id=session_id,
            turn_id=turn_id,
            role="assistant",
            content=result.text,
            provider_message_id=result.provider_message_id,
            raw_content=result.raw_content,
            metadata={
                "model": result.model,
                "usage": result.usage,
                "stop_reason": result.stop_reason,
                "completion_recovery": result.completion_recovery,
                "answer_obligations_trace_id": answer_obligations_trace_id,
                "answer_validation_trace_id": final_answer_validation_trace_id,
            },
        )
        response_trace = repositories.add_trace(
            db,
            session_id=session_id,
            turn_id=turn_id,
            kind="llm.response",
            payload={
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
                "stream": True,
                "answer_obligations_trace_id": answer_obligations_trace_id,
                "answer_validation_trace_id": final_answer_validation_trace_id,
            },
        )
        trace_ids.append(response_trace.id)
        accounting_trace = _record_context_accounting_observed(
            db,
            session_id=session_id,
            turn_id=turn_id,
            preflight_trace_id=accounting_trace_id,
            preflight=accounting_payload,
            result=result,
        )
        trace_ids.append(accounting_trace.id)
        final_runtime_events.append(
            _event_stream_payload(
                record_event(
                    db,
                    session_id=session_id,
                    turn_id=turn_id,
                    event_type="llm.response.completed",
                    payload={
                        "model": result.model,
                        "provider_message_id": result.provider_message_id,
                        "stop_reason": result.stop_reason,
                        "usage": result.usage,
                        "tool_call_count": len(result.tool_calls),
                        "completion_recovery": result.completion_recovery,
                        "stream": True,
                    },
                    source="llm",
                    actor="backend",
                    visibility="debug",
                    trace_id=response_trace.id,
                )
            )
        )
        final_runtime_events.append(
            _event_stream_payload(
                record_event(
                    db,
                    session_id=session_id,
                    turn_id=turn_id,
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
            )
        )
        if not semantic_content_event_seen:
            final_runtime_events.extend(
                _event_stream_payload(event)
                for event in record_response_content_events(
                    db,
                    session_id=session_id,
                    turn_id=turn_id,
                    raw_provider_messages=_response_event_messages(result),
                    response_trace_id=response_trace.id,
                    assistant_message_id=assistant_message.id,
                )
            )
        repositories.update_chat_session_provider_history(
            db,
            session_id=session_id,
            provider_history=_updated_provider_history(
                canonical_llm_messages,
                result,
            ),
        )
        completed_turn = repositories.complete_turn(
            db,
            turn_id=turn_id,
            latency_ms=latency_ms,
        )
        turn_completed_event = record_event(
            db,
            session_id=session_id,
            turn_id=turn_id,
            event_type="turn.completed",
            payload={
                "latency_ms": latency_ms,
                "trace_ids": trace_ids,
                "stream": True,
            },
            source="runtime",
            actor="backend",
            visibility="debug",
            status=completed_turn.status,
        )
        final_runtime_events.append(_event_stream_payload(turn_completed_event))
        chars_per_token = float(
            accounting_payload.get("calibration", {}).get(
                "chars_per_token_used",
                settings.context_estimated_chars_per_token,
            )
        )
        post_turn_source_map = build_chronology_source_map(
            db,
            session_id=session_id,
            chars_per_token=chars_per_token,
        )
        provider_channel_tokens = int(
            accounting_payload.get("channels", {})
            .get("provider_history", {})
            .get("estimated_tokens", 0)
        )
        external_context_tokens = max(
            0,
            int(
                accounting_payload.get("total", {}).get(
                    "estimated_input_tokens",
                    0,
                )
            )
            - provider_channel_tokens,
        )
        compaction_schedule = schedule_history_compaction(
            db,
            settings=settings,
            session_id=session_id,
            trigger_turn_id=turn_id,
            trigger_event_id=turn_completed_event.id,
            source_map=post_turn_source_map,
            external_context_tokens=external_context_tokens,
            chars_per_token=chars_per_token,
            model_history_tokens=_post_turn_model_history_tokens(
                post_turn_source_map,
                history_routing_payload,
            ),
        )
        if compaction_schedule is not None:
            _, compaction_event = compaction_schedule
            final_runtime_events.append(_event_stream_payload(compaction_event))
        if settings.maintenance_enabled:
            _, maintenance_event = schedule_session_idle_maintenance(
                db,
                settings=settings,
                session_id=session_id,
                trigger_turn_id=turn_id,
                trigger_event_id=turn_completed_event.id,
            )
            final_runtime_events.append(_event_stream_payload(maintenance_event))
        chat_session = _require_session(db, session_id)
        turn_response = ChatTurnResponse(
            session=_session_response(chat_session),
            turn_id=completed_turn.id,
            status=completed_turn.status,
            user_message=user_message_response,
            assistant_message=_message_response(assistant_message),
            trace_ids=trace_ids,
            model=result.model,
            latency_ms=latency_ms,
            usage=result.usage,
        )

    for event in final_runtime_events:
        yield emit("runtime_event", {"event": event})
    yield emit("turn_complete", turn_response.model_dump(mode="json"))


def _compose_system_with_runtime_context(
    base_system: str,
    runtime_context: str,
) -> str:
    return f"{base_system.rstrip()}\n\n{runtime_context.strip()}"


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


def build_trace_router(engine: Engine) -> APIRouter:
    router = APIRouter(prefix="/api/debug", tags=["debug"])

    @router.get("/traces/{turn_id}", response_model=list[TraceResponse])
    def get_traces(turn_id: str) -> list[TraceResponse]:
        with Session(engine) as db:
            traces = repositories.list_traces_for_turn(db, turn_id=turn_id)
            if not traces:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "code": "trace.not_found",
                        "message": f"No traces found for turn {turn_id}.",
                        "recoverable": True,
                    },
                )
            return [_trace_response(trace) for trace in traces]

    @router.get("/events", response_model=list[EventResponse])
    def get_events(
        session_id: str | None = Query(default=None),
        turn_id: str | None = Query(default=None),
        limit: int = Query(default=200, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ) -> list[EventResponse]:
        if session_id is None and turn_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "events.scope_required",
                    "message": "Pass session_id or turn_id to inspect runtime events.",
                    "recoverable": True,
                },
            )
        with Session(engine) as db:
            if turn_id is not None:
                events = repositories.list_events_for_turn(db, turn_id=turn_id)
            else:
                assert session_id is not None
                events = repositories.list_events_for_session(
                    db,
                    session_id=session_id,
                    limit=limit,
                    offset=offset,
                )
                events = list(reversed(events))
            return [_event_response(event) for event in events]

    return router


def _require_session(db: Session, session_id: str) -> ChatSession:
    chat_session = repositories.get_chat_session(db, session_id)
    if chat_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "session.not_found",
                "message": f"Session {session_id} was not found.",
                "recoverable": True,
            },
        )
    return chat_session


def _record_failed_turn(
    engine: Engine,
    *,
    session_id: str,
    turn_id: str,
    started: float,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> CognitiveEvent:
    latency_ms = int((time.perf_counter() - started) * 1000)
    error = {"code": code, "message": message}
    if details:
        error["details"] = details
    with Session(engine) as db:
        trace = repositories.add_trace(
            db,
            session_id=session_id,
            turn_id=turn_id,
            kind="llm.error",
            payload=error,
        )
        completed = repositories.complete_turn(
            db,
            turn_id=turn_id,
            status="failed",
            latency_ms=latency_ms,
            error=error,
        )
        return record_event(
            db,
            session_id=session_id,
            turn_id=turn_id,
            event_type="turn.failed",
            payload={**error, "latency_ms": latency_ms},
            source="runtime",
            actor="backend",
            visibility="debug",
            status=completed.status,
            trace_id=trace.id,
        )
