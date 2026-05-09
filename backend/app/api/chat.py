import time
from collections.abc import Callable
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from pydantic import ValidationError
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.config import Settings
from app.llm.minimax_client import MiniMaxProvider
from app.llm.provider import (
    LLMExecutedToolCall,
    LLMConfigurationError,
    LLMMessage,
    LLMProvider,
    LLMRequestError,
    LLMToolUse,
)
from app.mind.dispatcher import MindAPIError, MindAPIRequest, MindAPIResponse
from app.mind.dispatcher import dispatch_mind_api
from app.mind.schema import MIND_API_TOOL_SCHEMA
from app.prompts.system import AgentSystemPromptError, resolve_agent_system_prompt
from app.storage import repositories
from app.storage.models import ChatSession, Message, Trace, Turn


ProviderFactory = Callable[[Settings], LLMProvider]


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
    max_tokens: int | None = Field(default=None, ge=1, le=65536)


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


def build_chat_router(
    settings: Settings,
    engine: Engine,
    provider_factory: ProviderFactory = MiniMaxProvider,
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
                model=settings.minimax_model,
            )
            turn_id = turn.id
            user_message = repositories.add_message(
                db,
                session_id=session_id,
                turn_id=turn_id,
                role="user",
                content=request.message,
            )
            user_message_response = _message_response(user_message)
            history = repositories.list_messages(db, session_id=session_id)
            llm_messages = _to_llm_messages(history)
            max_tokens = request.max_tokens or settings.minimax_max_tokens
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

            request_trace = repositories.add_trace(
                db,
                session_id=session_id,
                turn_id=turn_id,
                kind="llm.request",
                payload={
                    "model": settings.minimax_model,
                    "max_tokens": max_tokens,
                    "system": system_prompt.content,
                    "system_present": True,
                    "system_source": system_prompt.source,
                    "system_path": system_prompt.path,
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

        try:
            provider = provider_factory(settings)
            result = provider.generate_chat_with_tools(
                messages=llm_messages,
                system=system_prompt.content,
                max_tokens=max_tokens,
                tools=[MIND_API_TOOL_SCHEMA],
                tool_runner=_build_mind_tool_runner(
                    engine,
                    session_id=session_id,
                    turn_id=turn_id,
                    trace_ids=trace_ids,
                ),
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
            completed_turn = repositories.complete_turn(
                db,
                turn_id=turn_id,
                latency_ms=latency_ms,
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

    return router


def _build_mind_tool_runner(
    engine: Engine,
    *,
    session_id: str,
    turn_id: str,
    trace_ids: list[str],
) -> Callable[[LLMToolUse], LLMExecutedToolCall]:
    def run(tool_use: LLMToolUse) -> LLMExecutedToolCall:
        started = time.perf_counter()
        mind_request, mind_response = _dispatch_tool_use(tool_use)
        latency_ms = int((time.perf_counter() - started) * 1000)
        result_payload = mind_response.model_dump(mode="json")

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
        return LLMExecutedToolCall(
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

    return run


def _dispatch_tool_use(
    tool_use: LLMToolUse,
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
            error=MindAPIError(
                code="mind.invalid_request",
                message=str(exc),
                recoverable=True,
            ),
            suggested_next_actions=["Call GET /mind/schema", "Retry with valid input"],
            confidence=1.0,
        )

    return mind_request, dispatch_mind_api(mind_request)


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


def _to_llm_messages(messages: list[Message]) -> list[LLMMessage]:
    return [
        LLMMessage(role=message.role, content=message.content)
        for message in messages
        if message.role in {"user", "assistant"}
    ]


def _record_failed_turn(
    engine: Engine,
    *,
    session_id: str,
    turn_id: str,
    started: float,
    code: str,
    message: str,
) -> None:
    latency_ms = int((time.perf_counter() - started) * 1000)
    with Session(engine) as db:
        repositories.add_trace(
            db,
            session_id=session_id,
            turn_id=turn_id,
            kind="llm.error",
            payload={"code": code, "message": message},
        )
        repositories.complete_turn(
            db,
            turn_id=turn_id,
            status="failed",
            latency_ms=latency_ms,
            error={"code": code, "message": message},
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
