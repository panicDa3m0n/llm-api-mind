import json
import time
from collections.abc import Callable, Iterator
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from pydantic import ValidationError
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.config import Settings
from app.llm.factory import (
    active_provider_max_tokens,
    active_provider_model,
    build_llm_provider,
)
from app.llm.provider import (
    LLMExecutedToolCall,
    LLMConfigurationError,
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
from app.mind.dispatcher import dispatch_mind_api
from app.mind.context import build_memory_context
from app.mind.schema import MIND_API_TOOL_SCHEMA
from app.mind.schema import schema_metadata
from app.prompts.system import AgentSystemPromptError, resolve_agent_system_prompt
from app.runtime.events import (
    event_payload,
    record_event,
    record_provider_stream_event,
    record_response_content_events,
    record_tool_call_completed,
    record_tool_call_started,
)
from app.runtime.maintenance import schedule_session_idle_maintenance
from app.runtime.preferences import load_runtime_preferences
from app.storage import repositories
from app.storage.models import ChatSession, CognitiveEvent, Message, Trace, Turn


ProviderFactory = Callable[[Settings], LLMProvider]
ProviderHistory = list[dict[str, Any]]


class ChatSessionCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatSessionResponse(BaseModel):
    id: str
    title: str | None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any]


class ChatMessageResponse(BaseModel):
    id: str
    session_id: str
    turn_id: str | None
    role: str
    content: str
    created_at: datetime
    metadata: dict[str, Any]


class ChatTurnRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20000)
    system: str | None = Field(default=None, max_length=20000)
    max_tokens: int | None = Field(default=None, ge=1, le=131072)


class ChatTurnResponse(BaseModel):
    session: ChatSessionResponse
    turn_id: str
    status: str
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse
    trace_ids: list[str]
    model: str
    latency_ms: int
    usage: dict[str, Any]


class TraceResponse(BaseModel):
    id: str
    session_id: str
    turn_id: str | None
    kind: str
    payload: dict[str, Any]
    created_at: datetime


class EventResponse(BaseModel):
    id: str
    session_id: str
    turn_id: str | None
    seq: int
    type: str
    source: str
    actor: str
    visibility: str
    status: str
    parent_event_id: str | None
    trace_id: str | None
    tool_call_id: str | None
    message_id: str | None
    payload: dict[str, Any]
    created_at: datetime


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
            provider_history_source, llm_messages = _provider_messages_for_turn(
                chat_session=chat_session,
                history=history,
                current_user_message=user_message,
            )
            provider_message_stats = _provider_message_stats(llm_messages)
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
            )
            trace_ids.append(memory_context.trace_id)
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
            effective_system = _compose_system_with_runtime_context(
                system_prompt.content,
                memory_context.runtime_context,
            )
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
                    "runtime_context_trace_id": memory_context.runtime_trace_id,
                    "tool_loop_policy": "model_controlled_unbounded",
                    "provider_history_source": provider_history_source,
                    "provider_message_stats": provider_message_stats,
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
                    "tools": [MIND_API_TOOL_SCHEMA],
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
                    "provider_history_source": provider_history_source,
                    "provider_message_stats": provider_message_stats,
                    "tool_count": 1,
                },
                source="llm",
                actor="backend",
                visibility="debug",
                trace_id=request_trace.id,
            )

        try:
            provider = provider_factory(settings)
            result = provider.generate_chat_with_tools(
                messages=llm_messages,
                system=effective_system,
                max_tokens=max_tokens,
                tools=[MIND_API_TOOL_SCHEMA],
                tool_runner=_build_mind_tool_runner(
                    engine,
                    settings=settings,
                    provider_factory=provider_factory,
                    session_id=session_id,
                    turn_id=turn_id,
                    trace_ids=trace_ids,
                ),
                max_tool_calls=None,
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
                },
            )
            trace_ids.append(response_trace.id)
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
                provider_history=_updated_provider_history(llm_messages, result),
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
            provider_history_source, llm_messages = _provider_messages_for_turn(
                chat_session=chat_session,
                history=history,
                current_user_message=user_message,
            )
            provider_message_stats = _provider_message_stats(llm_messages)
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
            )
            trace_ids.append(memory_context.trace_id)
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
            effective_system = _compose_system_with_runtime_context(
                system_prompt.content,
                memory_context.runtime_context,
            )
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
                    "runtime_context_trace_id": memory_context.runtime_trace_id,
                    "tool_loop_policy": "model_controlled_unbounded",
                    "provider_history_source": provider_history_source,
                    "provider_message_stats": provider_message_stats,
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
                    "tools": [MIND_API_TOOL_SCHEMA],
                    "stream": True,
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
                    "provider_history_source": provider_history_source,
                    "provider_message_stats": provider_message_stats,
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
                system=effective_system,
                max_tokens=max_tokens,
                memory_context=memory_context.payload,
                runtime_context=memory_context.runtime_payload,
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
    system: str,
    max_tokens: int,
    memory_context: dict[str, Any],
    runtime_context: dict[str, Any],
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
    try:
        provider = provider_factory(settings)
        for stream_event in provider.stream_chat_with_tools(
            messages=llm_messages,
            system=system,
            max_tokens=max_tokens,
            tools=[MIND_API_TOOL_SCHEMA],
            tool_runner=_build_mind_tool_runner(
                engine,
                settings=settings,
                provider_factory=provider_factory,
                session_id=session_id,
                turn_id=turn_id,
                trace_ids=trace_ids,
                event_sink=pending_runtime_events,
            ),
            max_tool_calls=None,
        ):
            yield from flush_pending_runtime_events()
            if stream_event.type == "final_result":
                result = LLMTextResult.model_validate(stream_event.data["result"])
            else:
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
                "stream": True,
            },
        )
        trace_ids.append(response_trace.id)
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
            provider_history=_updated_provider_history(llm_messages, result),
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


def _ndjson(event_type: str, data: dict[str, Any]) -> str:
    return json.dumps({"type": event_type, "data": data}, ensure_ascii=True) + "\n"


def _compose_system_with_runtime_context(
    base_system: str,
    runtime_context: str,
) -> str:
    return f"{base_system.rstrip()}\n\n{runtime_context.strip()}"


def _dispatch_tool_use(
    tool_use: LLMToolUse,
    *,
    context: MindAPIContext,
) -> tuple[MindAPIRequest | None, MindAPIResponse]:
    if tool_use.name != "mind_api":
        return None, MindAPIResponse(
            ok=False,
            error=MindAPIError(
                code="tool.unknown",
                message=f"Unknown tool: {tool_use.name}",
                recoverable=True,
            ),
            suggested_next_actions=["Use the mind_api tool only"],
            confidence=1.0,
        )

    try:
        mind_request = MindAPIRequest.model_validate(tool_use.input)
    except ValidationError as exc:
        return None, MindAPIResponse(
            ok=False,
            result={
                "schema": schema_metadata(),
                "expected_tool_schema": MIND_API_TOOL_SCHEMA["input_schema"],
            },
            error=MindAPIError(
                code="mind.invalid_request",
                message=str(exc),
                recoverable=True,
            ),
            suggested_next_actions=["Call GET /mind/schema", "Retry with valid input"],
            confidence=1.0,
        )

    return mind_request, dispatch_mind_api(mind_request, context=context)


def _result_trace_ids(result_payload: dict[str, Any]) -> list[str]:
    result = result_payload.get("result")
    if not isinstance(result, dict):
        return []
    trace_ids = result.get("trace_ids")
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


def _provider_messages_for_turn(
    *,
    chat_session: ChatSession,
    history: list[Message],
    current_user_message: Message,
) -> tuple[str, list[LLMMessage]]:
    provider_history = _valid_provider_history(chat_session.provider_history_json)
    if provider_history:
        return (
            "session.provider_history_json",
            [
                LLMMessage(role=item["role"], content=item["content"])
                for item in [
                    *provider_history,
                    _provider_user_text_message(current_user_message.content),
                ]
            ],
        )

    return (
        "messages.text_reconstructed",
        [
            LLMMessage(role=item["role"], content=item["content"])
            for item in _text_provider_history(history)
        ],
    )


def _updated_provider_history(
    request_messages: list[LLMMessage],
    result: LLMTextResult,
) -> ProviderHistory:
    history = [
        _llm_message_to_provider_history_item(message)
        for message in request_messages
    ]
    history.extend(_provider_history_from_result(result))
    return history


def _provider_history_from_result(result: LLMTextResult) -> ProviderHistory:
    if result.raw_provider_messages:
        return _provider_history_from_raw_messages(
            result.raw_provider_messages,
            tool_calls=result.tool_calls,
        )

    raw_content = _valid_content_blocks(result.raw_content)
    if not raw_content and result.text:
        raw_content = [{"type": "text", "text": result.text}]
    if not raw_content:
        return []
    return [{"role": "assistant", "content": raw_content}]


def _response_event_messages(result: LLMTextResult) -> list[dict[str, Any]]:
    if result.raw_provider_messages:
        return result.raw_provider_messages

    raw_content = _valid_content_blocks(result.raw_content)
    if not raw_content and result.text:
        raw_content = [{"type": "text", "text": result.text}]
    if not raw_content:
        return []
    return [
        {
            "id": result.provider_message_id,
            "stop_reason": result.stop_reason,
            "content": raw_content,
        }
    ]


def _provider_history_from_raw_messages(
    raw_provider_messages: list[dict[str, Any]],
    *,
    tool_calls: list[LLMExecutedToolCall],
) -> ProviderHistory:
    tool_calls_by_id = {
        tool_call.provider_tool_use_id: tool_call for tool_call in tool_calls
    }
    history: ProviderHistory = []
    for raw_message in raw_provider_messages:
        content = _valid_content_blocks(raw_message.get("content"))
        if not content:
            continue
        history.append({"role": "assistant", "content": content})
        tool_results = [
            _tool_result_block(tool_calls_by_id[tool_use_id])
            for tool_use_id in _tool_use_ids(content)
            if tool_use_id in tool_calls_by_id
        ]
        if tool_results:
            history.append({"role": "user", "content": tool_results})
    return history


def _tool_result_block(tool_call: LLMExecutedToolCall) -> dict[str, Any]:
    return {
        "type": "tool_result",
        "tool_use_id": tool_call.provider_tool_use_id,
        "content": json.dumps(tool_call.result, ensure_ascii=True),
        "is_error": tool_call.status != "completed",
    }


def _tool_use_ids(content_blocks: list[dict[str, Any]]) -> list[str]:
    ids: list[str] = []
    for block in content_blocks:
        if block.get("type") != "tool_use":
            continue
        tool_use_id = block.get("id")
        if isinstance(tool_use_id, str) and tool_use_id:
            ids.append(tool_use_id)
    return ids


def _valid_provider_history(value: Any) -> ProviderHistory:
    if not isinstance(value, list):
        return []
    history: ProviderHistory = []
    for item in value:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = _valid_content_blocks(item.get("content"))
        if role in {"user", "assistant"} and content:
            history.append({"role": role, "content": content})
    return history


def _text_provider_history(messages: list[Message]) -> ProviderHistory:
    return [
        _provider_user_text_message(message.content)
        if message.role == "user"
        else _provider_assistant_text_message(message.content)
        for message in messages
        if message.role in {"user", "assistant"}
    ]


def _provider_user_text_message(content: str) -> dict[str, Any]:
    return {"role": "user", "content": [{"type": "text", "text": content}]}


def _provider_assistant_text_message(content: str) -> dict[str, Any]:
    return {"role": "assistant", "content": [{"type": "text", "text": content}]}


def _llm_message_to_provider_history_item(message: LLMMessage) -> dict[str, Any]:
    content = message.content
    if isinstance(content, str):
        return {
            "role": message.role,
            "content": [{"type": "text", "text": content}],
        }
    return {
        "role": message.role,
        "content": _valid_content_blocks(content),
    }


def _valid_content_blocks(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    blocks: list[dict[str, Any]] = []
    for block in value:
        if not isinstance(block, dict):
            continue
        block_type = block.get("type")
        if isinstance(block_type, str) and block_type:
            blocks.append(block)
    return blocks


def _provider_message_stats(messages: list[LLMMessage]) -> dict[str, Any]:
    serializable = [message.model_dump(mode="json") for message in messages]
    serialized = json.dumps(serializable, ensure_ascii=False)
    block_count = 0
    for message in messages:
        if isinstance(message.content, list):
            block_count += len(message.content)
        else:
            block_count += 1
    return {
        "message_count": len(messages),
        "content_block_count": block_count,
        "json_chars": len(serialized),
        "approx_tokens": max(1, len(serialized) // 4) if serialized else 0,
    }


def _record_failed_turn(
    engine: Engine,
    *,
    session_id: str,
    turn_id: str,
    started: float,
    code: str,
    message: str,
) -> CognitiveEvent:
    latency_ms = int((time.perf_counter() - started) * 1000)
    with Session(engine) as db:
        trace = repositories.add_trace(
            db,
            session_id=session_id,
            turn_id=turn_id,
            kind="llm.error",
            payload={"code": code, "message": message},
        )
        completed = repositories.complete_turn(
            db,
            turn_id=turn_id,
            status="failed",
            latency_ms=latency_ms,
            error={"code": code, "message": message},
        )
        return record_event(
            db,
            session_id=session_id,
            turn_id=turn_id,
            event_type="turn.failed",
            payload={"code": code, "message": message, "latency_ms": latency_ms},
            source="runtime",
            actor="backend",
            visibility="debug",
            status=completed.status,
            trace_id=trace.id,
        )


def _session_response(chat_session: ChatSession) -> ChatSessionResponse:
    return ChatSessionResponse(
        id=chat_session.id,
        title=chat_session.title,
        created_at=chat_session.created_at,
        updated_at=chat_session.updated_at,
        metadata=chat_session.metadata_json,
    )


def _message_response(message: Message) -> ChatMessageResponse:
    return ChatMessageResponse(
        id=message.id,
        session_id=message.session_id,
        turn_id=message.turn_id,
        role=message.role,
        content=message.content,
        created_at=message.created_at,
        metadata=message.metadata_json,
    )


def _trace_response(trace: Trace) -> TraceResponse:
    return TraceResponse(
        id=trace.id,
        session_id=trace.session_id,
        turn_id=trace.turn_id,
        kind=trace.kind,
        payload=trace.payload_json,
        created_at=trace.created_at,
    )


def _event_response(event: CognitiveEvent) -> EventResponse:
    payload = event_payload(event)
    return EventResponse(
        id=payload["id"],
        session_id=payload["session_id"],
        turn_id=payload["turn_id"],
        seq=payload["seq"],
        type=payload["type"],
        source=payload["source"],
        actor=payload["actor"],
        visibility=payload["visibility"],
        status=payload["status"],
        parent_event_id=payload["parent_event_id"],
        trace_id=payload["trace_id"],
        tool_call_id=payload["tool_call_id"],
        message_id=payload["message_id"],
        payload=payload["payload"],
        created_at=event.created_at,
    )


def _event_stream_payload(event: CognitiveEvent) -> dict[str, Any]:
    return _event_response(event).model_dump(mode="json")


def _memory_context_event_payload(memory_context: dict[str, Any]) -> dict[str, Any]:
    return {
        "operation": memory_context.get("operation"),
        "trace_id": memory_context.get("trace_id"),
        "searched": memory_context.get("searched"),
        "selected_count": memory_context.get("selected_count"),
        "candidate_count": memory_context.get("candidate_count"),
        "ranked_candidate_count": memory_context.get("ranked_candidate_count"),
        "negative_evidence": memory_context.get("negative_evidence"),
        "selected": memory_context.get("selected", []),
        "near_miss": memory_context.get("near_miss", []),
        "excluded": memory_context.get("excluded", []),
        "conflicts": memory_context.get("conflicts", []),
    }


def _runtime_context_event_payload(runtime_context: dict[str, Any]) -> dict[str, Any]:
    blocks = runtime_context.get("blocks", [])
    return {
        "operation": "runtime.context",
        "trace_id": runtime_context.get("trace_id"),
        "schema_version": runtime_context.get("schema_version"),
        "session_id": runtime_context.get("session_id"),
        "turn_id": runtime_context.get("turn_id"),
        "block_count": len(blocks) if isinstance(blocks, list) else 0,
        "block_index": runtime_context.get("block_index", []),
        "blocks": blocks if isinstance(blocks, list) else [],
    }
