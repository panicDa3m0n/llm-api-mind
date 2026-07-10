import json
import time
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.api.chat import (
    ChatMessageResponse,
    ChatSessionResponse,
    _compose_system_with_runtime_context,
    _memory_context_event_payload,
    _message_response,
    _metacognitive_context_event_payload,
    _provider_message_stats,
    _provider_messages_for_turn,
    _runtime_context_event_payload,
    _session_response,
    _valid_provider_history,
)
from app.config import Settings
from app.llm.factory import active_provider_max_tokens, active_provider_model
from app.llm.provider import LLMExecutedToolCall
from app.mind.context import build_memory_context
from app.mind.dispatcher import MindAPIContext, MindAPIResponse
from app.mind.schema import MIND_SHELL_TOOL_SCHEMA
from app.mind.shell import MindShellRequest, dispatch_mind_shell
from app.prompts.system import AgentSystemPromptError, resolve_agent_system_prompt
from app.runtime.events import (
    record_event,
    record_response_content_events,
    record_tool_call_completed,
    record_tool_call_started,
)
from app.runtime.maintenance import schedule_session_idle_maintenance
from app.runtime.preferences import load_runtime_preferences
from app.storage import repositories
from app.storage.models import ChatSession, Message, Trace, Turn, new_id

ProviderFactory = Any

_GPT_BRIDGE_PROVIDER_MESSAGE_LIMIT = 8
_GPT_BRIDGE_PROVIDER_MESSAGE_TEXT_LIMIT = 1200
_MCP_PROTOCOL_VERSION = "2025-06-18"
_MCP_SERVER_NAME = "scarlet-api-mind"
_MCP_SERVER_VERSION = "1.25.2"


class GPTBridgeBootstrapRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=20000,
        description="Full user message received by the external GPT.",
    )
    session_id: str | None = Field(
        default=None,
        description=(
            "Existing Scarlet session id to continue. Omit to create a new "
            "bridge-backed session."
        ),
    )
    title: str | None = Field(
        default=None,
        max_length=200,
        description="Optional title when creating a new bridge session.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional external GPT metadata stored on newly created sessions.",
    )


class GPTBridgeActionRequest(BaseModel):
    session_id: str = Field(description="Session id returned by /gpt/bootstrap.")
    turn_id: str = Field(description="Turn id returned by /gpt/bootstrap.")
    command: str = Field(
        min_length=1,
        max_length=4000,
        description="Mind shell command, e.g. 'memory search \"...\" --top 5'.",
    )
    intent: str = Field(
        min_length=1,
        max_length=1000,
        description="Short reason why this cognitive action is useful now.",
    )


class GPTBridgeFinalizeRequest(BaseModel):
    session_id: str = Field(description="Session id returned by /gpt/bootstrap.")
    turn_id: str = Field(description="Turn id returned by /gpt/bootstrap.")
    answer: str = Field(
        min_length=1,
        max_length=100000,
        description=(
            "Exact final answer the GPT will show to the user after finalize succeeds."
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional external GPT metadata for audit/debug traces.",
    )


class GPTBridgeBootstrapResponse(BaseModel):
    ok: bool
    session_id: str
    session: ChatSessionResponse
    turn_id: str
    user_message: ChatMessageResponse
    trace_ids: list[str]
    model: str
    context: dict[str, Any]
    required_next_steps: list[str]
    action_policy: dict[str, Any] | None = None
    required_actions: list[dict[str, Any]] = Field(default_factory=list)
    recommended_actions: list[dict[str, Any]] = Field(default_factory=list)


class GPTBridgeActionResponse(BaseModel):
    ok: bool
    session_id: str
    turn_id: str
    tool_call_id: str
    trace_id: str | None
    response: MindAPIResponse


class GPTBridgeFinalizeResponse(BaseModel):
    ok: bool
    session: ChatSessionResponse
    turn_id: str
    status: str
    assistant_message: ChatMessageResponse
    final_answer_to_show: str
    trace_ids: list[str]
    already_finalized: bool = False
    required_next_steps: list[str]


def build_gpt_bridge_router(
    engine: Engine,
    settings: Settings,
    provider_factory: ProviderFactory,
) -> APIRouter:
    router = APIRouter(tags=["gpt-bridge"])
    mcp_sessions: dict[str, dict[str, Any]] = {}

    @router.post(
        "/gpt/bootstrap",
        response_model=GPTBridgeBootstrapResponse,
        operation_id="bootstrapScarletBeforeEveryAnswer",
        summary="Start an external GPT turn and return Scarlet's active context",
        description=(
            "Mandatory first call for every ChatGPT GPT user turn. Creates or "
            "resumes a Scarlet session, persists the user message, builds the "
            "same runtime/memory/session context local Scarlet receives, and "
            "returns the context plus the mind_shell tool schema."
        ),
    )
    def bootstrap(
        request: GPTBridgeBootstrapRequest,
        authorization: str | None = Header(default=None),
        x_gpt_bridge_key: str | None = Header(default=None),
        key: str | None = Query(default=None, include_in_schema=False),
    ) -> GPTBridgeBootstrapResponse:
        _require_bridge_auth(
            settings,
            authorization=authorization,
            x_gpt_bridge_key=x_gpt_bridge_key,
            query_key=key,
        )
        started = time.perf_counter()
        trace_ids: list[str] = []

        with Session(engine) as db:
            chat_session = _get_or_create_bridge_session(db, request)
            session_id = chat_session.id
            turn = repositories.create_turn(
                db,
                session_id=session_id,
                model="external-gpt",
            )
            turn_id = turn.id
            record_event(
                db,
                session_id=session_id,
                turn_id=turn_id,
                event_type="turn.started",
                payload={
                    "model": "external-gpt",
                    "entrypoint": "gpt.bootstrap",
                    "bridge": "chatgpt_gpt_actions",
                },
                source="gpt_bridge",
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
                metadata={"source": "gpt_bridge"},
            )
            record_event(
                db,
                session_id=session_id,
                turn_id=turn_id,
                event_type="message.user.persisted",
                payload={
                    "message_id": user_message.id,
                    "content_chars": len(user_message.content),
                    "source": "gpt_bridge",
                },
                source="chat",
                actor="user",
                visibility="public",
                message_id=user_message.id,
            )
            history = repositories.list_messages(db, session_id=session_id)
            provider_history_source, llm_messages = _provider_messages_for_turn(
                chat_session=chat_session,
                history=history,
                current_user_message=user_message,
            )
            provider_message_stats = _provider_message_stats(llm_messages)
            system_prompt = _resolve_system_prompt(settings, db, session_id, turn_id)
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
            effective_system = _compose_system_with_runtime_context(
                system_prompt["content"],
                memory_context.runtime_context,
            )
            request_trace = repositories.add_trace(
                db,
                session_id=session_id,
                turn_id=turn_id,
                kind="llm.request",
                payload={
                    "model": "external-gpt",
                    "provider_model_reference": active_provider_model(settings),
                    "max_tokens": active_provider_max_tokens(settings),
                    "system": effective_system,
                    "base_system": system_prompt["content"],
                    "system_present": True,
                    "system_source": system_prompt["source"],
                    "system_path": system_prompt["path"],
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
                    "tool_loop_policy": "external_gpt_required_action_finalize",
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
                    "tools": [MIND_SHELL_TOOL_SCHEMA],
                    "entrypoint": "gpt.bootstrap",
                    "latency_ms": int((time.perf_counter() - started) * 1000),
                },
            )
            trace_ids.append(request_trace.id)
            record_event(
                db,
                session_id=session_id,
                turn_id=turn_id,
                event_type="llm.request.created",
                payload={
                    "model": "external-gpt",
                    "provider_model_reference": active_provider_model(settings),
                    "provider_history_source": provider_history_source,
                    "provider_message_stats": provider_message_stats,
                    "tool_count": 1,
                    "entrypoint": "gpt.bootstrap",
                },
                source="llm",
                actor="backend",
                visibility="debug",
                trace_id=request_trace.id,
            )
            chat_session = _require_session(db, session_id)
            return GPTBridgeBootstrapResponse(
                ok=True,
                session_id=session_id,
                session=_session_response(chat_session),
                turn_id=turn_id,
                user_message=_message_response(user_message),
                trace_ids=trace_ids,
                model="external-gpt",
                context=_gpt_bootstrap_context_payload(
                    runtime_context=memory_context.runtime_context,
                    runtime_payload=memory_context.runtime_payload,
                    memory_payload=memory_context.payload,
                    metacognitive_payload=memory_context.metacognitive_payload,
                    llm_messages=llm_messages,
                    provider_history_source=provider_history_source,
                    provider_message_stats=provider_message_stats,
                    trace_ids=trace_ids,
                ),
                required_next_steps=[
                    "Use this returned context as Scarlet's active turn context.",
                    "Call POST /gpt/action for every mind_shell command you need.",
                    "Call POST /gpt/finalize with the exact final answer before showing it to the user.",
                ],
                action_policy={
                    "action_required": False,
                    "note": (
                        "Bootstrap/finalize are mandatory. Middle API Mind "
                        "actions depend on the user request and returned context."
                    ),
                },
            )

    @router.post(
        "/gpt/action",
        response_model=GPTBridgeActionResponse,
        operation_id="runScarletMindAction",
        summary="Execute one Scarlet mind_shell command for an external GPT turn",
        description=(
            "Use this endpoint for every mind_shell command needed after "
            "bootstrap and before finalize. The command is executed through "
            "the same controlled Mind shell runtime used by local Scarlet."
        ),
    )
    def action(
        request: GPTBridgeActionRequest,
        authorization: str | None = Header(default=None),
        x_gpt_bridge_key: str | None = Header(default=None),
        key: str | None = Query(default=None, include_in_schema=False),
    ) -> GPTBridgeActionResponse:
        _require_bridge_auth(
            settings,
            authorization=authorization,
            x_gpt_bridge_key=x_gpt_bridge_key,
            query_key=key,
        )
        started = time.perf_counter()
        with Session(engine) as db:
            _require_active_turn(db, request.session_id, request.turn_id)
            started_event = record_tool_call_started(
                db,
                session_id=request.session_id,
                turn_id=request.turn_id,
                provider_tool_use_id=new_id("gpt_tool_use"),
                tool_name="mind_shell",
                arguments={
                    "command": request.command,
                    "intent": request.intent,
                    "source": "gpt_bridge",
                },
            )

        mind_request = MindShellRequest(command=request.command, intent=request.intent)
        mind_response = dispatch_mind_shell(
            mind_request,
            context=MindAPIContext(
                engine=engine,
                session_id=request.session_id,
                turn_id=request.turn_id,
                settings=settings,
                provider_factory=provider_factory,
            ),
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        result_payload = mind_response.model_dump(mode="json")

        with Session(engine) as db:
            provider_tool_use_id = started_event.payload_json.get("provider_tool_use_id")
            tool_call = repositories.add_tool_call(
                db,
                session_id=request.session_id,
                turn_id=request.turn_id,
                tool_name="mind_shell",
                arguments=mind_request.model_dump(mode="json"),
                result=result_payload,
                status="completed" if mind_response.ok else "error",
                latency_ms=latency_ms,
            )
            trace = repositories.add_trace(
                db,
                session_id=request.session_id,
                turn_id=request.turn_id,
                kind="mind.tool_call",
                payload={
                    "provider_tool_use_id": provider_tool_use_id,
                    "tool_call_id": tool_call.id,
                    "tool_name": "mind_shell",
                    "arguments": mind_request.model_dump(mode="json"),
                    "result": result_payload,
                    "status": tool_call.status,
                    "latency_ms": latency_ms,
                    "entrypoint": "gpt.action",
                },
            )
            mind_response.trace_id = trace.id
            result_payload = mind_response.model_dump(mode="json")
            executed = LLMExecutedToolCall(
                provider_tool_use_id=str(provider_tool_use_id),
                tool_name="mind_shell",
                arguments=mind_request.model_dump(mode="json"),
                result=result_payload,
                status=tool_call.status,
                latency_ms=latency_ms,
                tool_call_id=tool_call.id,
                trace_id=trace.id,
            )
            record_tool_call_completed(
                db,
                session_id=request.session_id,
                turn_id=request.turn_id,
                started_event_id=started_event.id,
                executed=executed,
            )
            return GPTBridgeActionResponse(
                ok=mind_response.ok,
                session_id=request.session_id,
                turn_id=request.turn_id,
                tool_call_id=tool_call.id,
                trace_id=trace.id,
                response=mind_response,
            )

    @router.post(
        "/gpt/finalize",
        response_model=GPTBridgeFinalizeResponse,
        operation_id="finalizeScarletBeforeAnswer",
        summary="Persist the external GPT final answer and complete the turn",
        description=(
            "Mandatory before showing the final answer to the user. Stores the "
            "assistant answer, updates provider history, records traces/events, "
            "completes the turn, and schedules idle maintenance when enabled."
        ),
    )
    def finalize(
        request: GPTBridgeFinalizeRequest,
        authorization: str | None = Header(default=None),
        x_gpt_bridge_key: str | None = Header(default=None),
        key: str | None = Query(default=None, include_in_schema=False),
    ) -> GPTBridgeFinalizeResponse:
        _require_bridge_auth(
            settings,
            authorization=authorization,
            x_gpt_bridge_key=x_gpt_bridge_key,
            query_key=key,
        )
        started = time.perf_counter()
        trace_ids: list[str] = []
        with Session(engine) as db:
            chat_session = _require_session(db, request.session_id)
            turn = _require_turn(db, request.turn_id, session_id=request.session_id)
            existing_assistant = repositories.latest_message_for_turn(
                db,
                turn_id=request.turn_id,
                role="assistant",
            )
            if turn.status == "completed" and existing_assistant is not None:
                return GPTBridgeFinalizeResponse(
                    ok=True,
                    session=_session_response(chat_session),
                    turn_id=turn.id,
                    status=turn.status,
                    assistant_message=_message_response(existing_assistant),
                    final_answer_to_show=existing_assistant.content,
                    trace_ids=[],
                    already_finalized=True,
                    required_next_steps=[
                        "This turn was already finalized. Show the persisted answer to the user.",
                    ],
                )
            if turn.status != "started":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "gpt_bridge.turn_not_active",
                        "message": f"Turn {turn.id} is not active.",
                        "recoverable": False,
                    },
                )

            provider_message_id = new_id("gpt_msg")
            raw_content = [{"type": "text", "text": request.answer}]
            assistant_message = repositories.add_message(
                db,
                session_id=request.session_id,
                turn_id=request.turn_id,
                role="assistant",
                content=request.answer,
                provider_message_id=provider_message_id,
                raw_content=raw_content,
                metadata={
                    "source": "gpt_bridge",
                    "model": "external-gpt",
                    **request.metadata,
                },
            )
            response_trace = repositories.add_trace(
                db,
                session_id=request.session_id,
                turn_id=request.turn_id,
                kind="llm.response",
                payload={
                    "model": "external-gpt",
                    "text": request.answer,
                    "usage": {},
                    "provider_message_id": provider_message_id,
                    "stop_reason": "external_finalize",
                    "raw_content": raw_content,
                    "tool_calls": _tool_call_summaries(db, turn_id=request.turn_id),
                    "raw_provider_messages": [
                        {
                            "id": provider_message_id,
                            "stop_reason": "end_turn",
                            "content": raw_content,
                        }
                    ],
                    "metadata": request.metadata,
                    "entrypoint": "gpt.finalize",
                },
            )
            trace_ids.append(response_trace.id)
            record_event(
                db,
                session_id=request.session_id,
                turn_id=request.turn_id,
                event_type="llm.response.completed",
                payload={
                    "model": "external-gpt",
                    "provider_message_id": provider_message_id,
                    "stop_reason": "external_finalize",
                    "usage": {},
                    "tool_call_count": len(
                        _tool_call_summaries(db, turn_id=request.turn_id)
                    ),
                    "entrypoint": "gpt.finalize",
                },
                source="llm",
                actor="backend",
                visibility="debug",
                trace_id=response_trace.id,
            )
            record_event(
                db,
                session_id=request.session_id,
                turn_id=request.turn_id,
                event_type="message.assistant.persisted",
                payload={
                    "message_id": assistant_message.id,
                    "content_chars": len(assistant_message.content),
                    "source": "gpt_bridge",
                },
                source="chat",
                actor="scarlet",
                visibility="public",
                message_id=assistant_message.id,
            )
            record_response_content_events(
                db,
                session_id=request.session_id,
                turn_id=request.turn_id,
                raw_provider_messages=[
                    {
                        "id": provider_message_id,
                        "stop_reason": "end_turn",
                        "content": raw_content,
                    }
                ],
                response_trace_id=response_trace.id,
                assistant_message_id=assistant_message.id,
            )
            _update_provider_history_from_bootstrap(
                db,
                session_id=request.session_id,
                turn_id=request.turn_id,
                assistant_text=request.answer,
            )
            completed_turn = repositories.complete_turn(
                db,
                turn_id=request.turn_id,
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
            turn_completed_event = record_event(
                db,
                session_id=request.session_id,
                turn_id=request.turn_id,
                event_type="turn.completed",
                payload={
                    "latency_ms": completed_turn.latency_ms,
                    "trace_ids": trace_ids,
                    "entrypoint": "gpt.finalize",
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
                    session_id=request.session_id,
                    trigger_turn_id=request.turn_id,
                    trigger_event_id=turn_completed_event.id,
                )
            chat_session = _require_session(db, request.session_id)
            return GPTBridgeFinalizeResponse(
                ok=True,
                session=_session_response(chat_session),
                turn_id=completed_turn.id,
                status=completed_turn.status,
                assistant_message=_message_response(assistant_message),
                final_answer_to_show=assistant_message.content,
                trace_ids=trace_ids,
                required_next_steps=[
                    "Now show the exact finalized answer to the user.",
                ],
            )

    @router.post(
        "/mcp",
        summary="Deprecated Scarlet MCP/App bridge endpoint",
        description=(
            "Deprecated Streamable HTTP MCP endpoint for ChatGPT Apps. It is "
            "kept temporarily for traceability while the active custom GPT "
            "surface remains the /gpt/* Actions bridge."
        ),
        include_in_schema=False,
    )
    async def mcp_post(
        http_request: Request,
        response: Response,
        authorization: str | None = Header(default=None),
        x_gpt_bridge_key: str | None = Header(default=None),
        mcp_session_id: str | None = Header(default=None, alias="Mcp-Session-Id"),
        key: str | None = Query(default=None, include_in_schema=False),
    ) -> Response:
        _require_bridge_auth(
            settings,
            authorization=authorization,
            x_gpt_bridge_key=x_gpt_bridge_key,
            query_key=key,
        )
        try:
            message = await http_request.json()
        except Exception as exc:
            return _mcp_json_error(
                request_id=None,
                code=-32700,
                message=f"Invalid JSON-RPC payload: {exc}",
            )
        if isinstance(message, list):
            return _mcp_json_error(
                request_id=None,
                code=-32600,
                message="Batch JSON-RPC messages are not supported by this bridge.",
            )
        if not isinstance(message, dict):
            return _mcp_json_error(
                request_id=None,
                code=-32600,
                message="JSON-RPC payload must be an object.",
            )

        request_id = message.get("id")
        method = message.get("method")
        params = message.get("params") if isinstance(message.get("params"), dict) else {}
        is_notification = request_id is None

        if is_notification:
            if method == "notifications/initialized":
                return Response(status_code=status.HTTP_202_ACCEPTED)
            return Response(status_code=status.HTTP_202_ACCEPTED)

        state_id = mcp_session_id or new_id("mcp")
        state = mcp_sessions.setdefault(
            state_id,
            {
                "scarlet_session_id": None,
                "active_turn_id": None,
                "last_turn_id": None,
            },
        )
        response.headers["Mcp-Session-Id"] = state_id

        if method == "initialize":
            result = {
                "protocolVersion": params.get("protocolVersion")
                or _MCP_PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {
                    "name": _MCP_SERVER_NAME,
                    "title": "Scarlet API Mind",
                    "version": _MCP_SERVER_VERSION,
                },
                "instructions": (
                    "Scarlet MCP bridge. Use start_scarlet_turn_required at "
                    "the start of every user turn and "
                    "finish_scarlet_turn_required before the final answer. Use "
                    "the cognitive command tools whenever Scarlet needs API Mind."
                ),
            }
            return _mcp_json_response(request_id=request_id, result=result, headers=response.headers)

        if method == "ping":
            return _mcp_json_response(request_id=request_id, result={}, headers=response.headers)

        if method == "tools/list":
            return _mcp_json_response(
                request_id=request_id,
                result={"tools": _mcp_tool_descriptors()},
                headers=response.headers,
            )

        if method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments")
            if not isinstance(tool_name, str) or not isinstance(arguments, dict):
                return _mcp_json_error(
                    request_id=request_id,
                    code=-32602,
                    message="tools/call requires params.name and params.arguments.",
                    headers=response.headers,
                )
            tool_result = _call_mcp_tool(
                tool_name,
                arguments,
                state=state,
                bootstrap=bootstrap,
                action=action,
                finalize=finalize,
                authorization=authorization,
                x_gpt_bridge_key=x_gpt_bridge_key or key,
            )
            return _mcp_json_response(
                request_id=request_id,
                result=tool_result,
                headers=response.headers,
            )

        if method == "resources/list":
            return _mcp_json_response(
                request_id=request_id,
                result={"resources": []},
                headers=response.headers,
            )
        if method == "prompts/list":
            return _mcp_json_response(
                request_id=request_id,
                result={"prompts": []},
                headers=response.headers,
            )

        return _mcp_json_error(
            request_id=request_id,
            code=-32601,
            message=f"Unsupported MCP method: {method}",
            headers=response.headers,
        )

    @router.get(
        "/mcp",
        summary="Scarlet MCP/App SSE endpoint placeholder",
        include_in_schema=False,
    )
    def mcp_get() -> Response:
        return Response(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            headers={"Allow": "POST"},
        )

    return router


def _mcp_json_response(
    *,
    request_id: Any,
    result: dict[str, Any],
    headers: Any | None = None,
) -> JSONResponse:
    return JSONResponse(
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result,
        },
        headers=dict(headers or {}),
    )


def _mcp_json_error(
    *,
    request_id: Any,
    code: int,
    message: str,
    data: dict[str, Any] | None = None,
    headers: Any | None = None,
) -> JSONResponse:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return JSONResponse(
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": error,
        },
        status_code=status.HTTP_200_OK,
        headers=dict(headers or {}),
    )


def _mcp_tool_descriptors() -> list[dict[str, Any]]:
    return [
        {
            "name": "start_scarlet_turn_required",
            "title": "Start Scarlet turn",
            "description": (
                "Usa sempre a inizio di ogni turno. Starts or resumes Scarlet's "
                "current turn, persists the exact user message, and returns the "
                "runtime, memory, session, focus, affect, and API Mind context "
                "that Scarlet must read before answering."
            ),
            "inputSchema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["message"],
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Exact user message received in ChatGPT.",
                    },
                    "session_id": {
                        "type": "string",
                        "description": (
                            "Optional Scarlet session id. Usually omit it; the MCP "
                            "bridge will reuse the active session for this connector."
                        ),
                    },
                    "title": {
                        "type": "string",
                        "description": "Optional title for a newly created session.",
                    },
                    "metadata": {
                        "type": "object",
                        "additionalProperties": True,
                        "description": "Optional debug metadata.",
                    },
                },
            },
            "outputSchema": _mcp_lifecycle_output_schema(),
            "annotations": {
                "readOnlyHint": False,
                "openWorldHint": False,
                "destructiveHint": False,
            },
        },
        {
            "name": "finish_scarlet_turn_required",
            "title": "Finish Scarlet turn",
            "description": (
                "Usa sempre prima della tua risposta finale. Persists the exact "
                "final answer into Scarlet history, completes the active turn, "
                "and only then allows the model to show that same answer to the "
                "user."
            ),
            "inputSchema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["answer"],
                "properties": {
                    "answer": {
                        "type": "string",
                        "description": (
                            "Exact final answer that will be shown to the user "
                            "after this tool succeeds."
                        ),
                    },
                    "session_id": {
                        "type": "string",
                        "description": (
                            "Optional override. Usually omit it and use the active "
                            "MCP bridge state."
                        ),
                    },
                    "turn_id": {
                        "type": "string",
                        "description": (
                            "Optional override. Usually omit it and use the active "
                            "MCP bridge state."
                        ),
                    },
                    "metadata": {
                        "type": "object",
                        "additionalProperties": True,
                        "description": "Optional debug metadata.",
                    },
                },
            },
            "outputSchema": _mcp_lifecycle_output_schema(),
            "annotations": {
                "readOnlyHint": False,
                "openWorldHint": False,
                "destructiveHint": False,
            },
        },
        _mcp_command_tool(
            name="scarlet_help_command",
            title="Scarlet help command",
            description=(
                "Run API Mind help commands through Scarlet's cognitive shell. "
                "Use for current command syntax, command families, capability "
                "checks, and recovery after malformed commands."
            ),
            read_only=True,
        ),
        _mcp_command_tool(
            name="scarlet_memory_command",
            title="Scarlet memory command",
            description=(
                "Run memory shell commands such as memory search/open/write/graph/"
                "conflicts. Use whenever Scarlet needs durable memories, sourceable "
                "anchors, memory writes, conflict inspection, or memory provenance."
            ),
            read_only=False,
        ),
        _mcp_command_tool(
            name="scarlet_session_command",
            title="Scarlet session command",
            description=(
                "Run session shell commands such as session list/open/summarize. "
                "Use for episodic recall, exact prior transcripts, dates, prior "
                "conversation reconstruction, and source-session checks."
            ),
            read_only=False,
        ),
        _mcp_command_tool(
            name="scarlet_metacognition_command",
            title="Scarlet metacognition command",
            description=(
                "Run metacognition shell commands. Use for complex judgment, "
                "claim checking, evidence discipline, source-sensitive synthesis, "
                "previous-turn audits, and reasoning drift checks."
            ),
            read_only=False,
        ),
        _mcp_command_tool(
            name="scarlet_focus_command",
            title="Scarlet focus command",
            description=(
                "Run focus shell commands. Use to inspect, set, hold, shift, "
                "defer, resolve, or mark impossible Scarlet's foreground attention."
            ),
            read_only=False,
        ),
        _mcp_command_tool(
            name="scarlet_affect_command",
            title="Scarlet affect command",
            description=(
                "Run affect shell commands. Use to inspect or update Scarlet's "
                "backend-appraised affective context when tone, caution, warmth, "
                "or emotional posture matters."
            ),
            read_only=False,
        ),
        _mcp_command_tool(
            name="scarlet_volition_command",
            title="Scarlet volition command",
            description=(
                "Run volition shell commands. Use for Scarlet's latent intentions, "
                "deferred inner threads, goals-in-view, and self-generated "
                "directions when relevant."
            ),
            read_only=False,
        ),
        _mcp_command_tool(
            name="scarlet_shell_command",
            title="Scarlet generic shell command",
            description=(
                "Advanced fallback for any supported API Mind shell command. Use "
                "when a command does not fit the more specific Scarlet MCP tools."
            ),
            read_only=False,
        ),
    ]


def _mcp_command_tool(
    *,
    name: str,
    title: str,
    description: str,
    read_only: bool,
) -> dict[str, Any]:
    return {
        "name": name,
        "title": title,
        "description": description,
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["command"],
            "properties": {
                "command": {
                    "type": "string",
                    "description": (
                        "Single API Mind shell command string. You may include "
                        "quoted text, flags, and parameters exactly as in the "
                        "mind shell."
                    ),
                },
                "intent": {
                    "type": "string",
                    "description": "Short reason why this command is useful now.",
                },
            },
        },
        "outputSchema": _mcp_command_output_schema(),
        "annotations": {
            "readOnlyHint": read_only,
            "openWorldHint": False,
            "destructiveHint": False,
        },
    }


def _mcp_lifecycle_output_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": True,
        "required": ["ok", "summary"],
        "properties": {
            "ok": {"type": "boolean"},
            "summary": {"type": "string"},
            "session": {"type": "object", "additionalProperties": True},
            "turn_id": {"type": "string"},
            "context": {"type": "object", "additionalProperties": True},
            "status": {"type": "string"},
            "assistant_message": {"type": "object", "additionalProperties": True},
            "error": {"type": "object", "additionalProperties": True},
        },
    }


def _mcp_command_output_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": True,
        "required": ["ok", "summary"],
        "properties": {
            "ok": {"type": "boolean"},
            "summary": {"type": "string"},
            "session_id": {"type": "string"},
            "turn_id": {"type": "string"},
            "tool_call_id": {"type": "string"},
            "trace_id": {"type": ["string", "null"]},
            "response": {"type": "object", "additionalProperties": True},
            "error": {"type": "object", "additionalProperties": True},
        },
    }


def _call_mcp_tool(
    tool_name: str,
    arguments: dict[str, Any],
    *,
    state: dict[str, Any],
    bootstrap: Any,
    action: Any,
    finalize: Any,
    authorization: str | None,
    x_gpt_bridge_key: str | None,
) -> dict[str, Any]:
    try:
        if tool_name == "start_scarlet_turn_required":
            return _mcp_start_turn(
                arguments,
                state=state,
                bootstrap=bootstrap,
                authorization=authorization,
                x_gpt_bridge_key=x_gpt_bridge_key,
            )
        if tool_name == "finish_scarlet_turn_required":
            return _mcp_finish_turn(
                arguments,
                state=state,
                finalize=finalize,
                authorization=authorization,
                x_gpt_bridge_key=x_gpt_bridge_key,
            )
        namespace = _mcp_tool_namespace(tool_name)
        if namespace is None:
            return _mcp_tool_result(
                ok=False,
                summary=f"Unknown Scarlet MCP tool: {tool_name}",
                structured={
                    "ok": False,
                    "error": {
                        "code": "mcp_bridge.unknown_tool",
                        "message": f"Unknown Scarlet MCP tool: {tool_name}",
                    },
                },
            )
        return _mcp_run_shell_command(
            arguments,
            namespace=namespace,
            state=state,
            action=action,
            authorization=authorization,
            x_gpt_bridge_key=x_gpt_bridge_key,
        )
    except HTTPException as exc:
        return _mcp_tool_result(
            ok=False,
            summary=f"Scarlet bridge HTTP error: {exc.detail}",
            structured={
                "ok": False,
                "error": exc.detail,
                "status_code": exc.status_code,
            },
        )
    except Exception as exc:
        return _mcp_tool_result(
            ok=False,
            summary=f"Scarlet MCP tool failed: {exc}",
            structured={
                "ok": False,
                "error": {
                    "code": "mcp_bridge.tool_failed",
                    "message": str(exc),
                },
            },
        )


def _mcp_start_turn(
    arguments: dict[str, Any],
    *,
    state: dict[str, Any],
    bootstrap: Any,
    authorization: str | None,
    x_gpt_bridge_key: str | None,
) -> dict[str, Any]:
    message = arguments.get("message")
    if not isinstance(message, str) or not message.strip():
        return _mcp_tool_result(
            ok=False,
            summary="start_scarlet_turn_required needs the exact user message.",
            structured={
                "ok": False,
                "error": {
                    "code": "mcp_bridge.start_missing_message",
                    "message": "The message argument is required.",
                },
            },
        )
    session_id = arguments.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        session_id = state.get("scarlet_session_id")
    title = arguments.get("title")
    metadata = arguments.get("metadata") if isinstance(arguments.get("metadata"), dict) else {}
    result = bootstrap(
        GPTBridgeBootstrapRequest(
            message=message,
            session_id=session_id,
            title=title if isinstance(title, str) else None,
            metadata={"source": "mcp_bridge", **metadata},
        ),
        authorization=authorization,
        x_gpt_bridge_key=x_gpt_bridge_key,
    )
    payload = result.model_dump(mode="json")
    state["scarlet_session_id"] = payload["session"]["id"]
    state["active_turn_id"] = payload["turn_id"]
    state["last_turn_id"] = payload["turn_id"]
    return _mcp_tool_result(
        ok=True,
        summary=(
            "Scarlet turn started. Read the returned context before answering "
            "or using cognitive command tools."
        ),
        structured=payload,
    )


def _mcp_finish_turn(
    arguments: dict[str, Any],
    *,
    state: dict[str, Any],
    finalize: Any,
    authorization: str | None,
    x_gpt_bridge_key: str | None,
) -> dict[str, Any]:
    answer = arguments.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        return _mcp_tool_result(
            ok=False,
            summary="finish_scarlet_turn_required needs the exact final answer.",
            structured={
                "ok": False,
                "error": {
                    "code": "mcp_bridge.finish_missing_answer",
                    "message": "The answer argument is required.",
                },
            },
        )
    session_id = arguments.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        session_id = state.get("scarlet_session_id")
    turn_id = arguments.get("turn_id")
    if not isinstance(turn_id, str) or not turn_id:
        turn_id = state.get("active_turn_id")
    if not session_id or not turn_id:
        return _mcp_tool_result(
            ok=False,
            summary="No active Scarlet turn is available to finish.",
            structured={
                "ok": False,
                "error": {
                    "code": "mcp_bridge.finish_without_active_turn",
                    "message": (
                        "Call start_scarlet_turn_required before finalizing, or "
                        "pass both session_id and turn_id."
                    ),
                },
            },
        )
    metadata = arguments.get("metadata") if isinstance(arguments.get("metadata"), dict) else {}
    result = finalize(
        GPTBridgeFinalizeRequest(
            session_id=session_id,
            turn_id=turn_id,
            answer=answer,
            metadata={"source": "mcp_bridge", **metadata},
        ),
        authorization=authorization,
        x_gpt_bridge_key=x_gpt_bridge_key,
    )
    payload = result.model_dump(mode="json")
    state["scarlet_session_id"] = payload["session"]["id"]
    if payload.get("already_finalized") is not True:
        state["active_turn_id"] = None
    return _mcp_tool_result(
        ok=True,
        summary="Scarlet turn finalized. Now show the exact finalized answer.",
        structured=payload,
    )


def _mcp_run_shell_command(
    arguments: dict[str, Any],
    *,
    namespace: str,
    state: dict[str, Any],
    action: Any,
    authorization: str | None,
    x_gpt_bridge_key: str | None,
) -> dict[str, Any]:
    raw_command = arguments.get("command")
    if not isinstance(raw_command, str) or not raw_command.strip():
        return _mcp_tool_result(
            ok=False,
            summary="Scarlet cognitive command tool needs a command string.",
            structured={
                "ok": False,
                "error": {
                    "code": "mcp_bridge.command_missing",
                    "message": "The command argument is required.",
                },
            },
        )
    session_id = state.get("scarlet_session_id")
    turn_id = state.get("active_turn_id")
    if not session_id or not turn_id:
        return _mcp_tool_result(
            ok=False,
            summary="No active Scarlet turn is available for cognitive commands.",
            structured={
                "ok": False,
                "error": {
                    "code": "mcp_bridge.command_without_active_turn",
                    "message": (
                        "Call start_scarlet_turn_required before using Scarlet "
                        "cognitive command tools."
                    ),
                },
            },
        )
    command = _mcp_normalize_command(raw_command, namespace=namespace)
    intent = arguments.get("intent")
    result = action(
        GPTBridgeActionRequest(
            session_id=session_id,
            turn_id=turn_id,
            command=command,
            intent=(
                intent
                if isinstance(intent, str) and intent.strip()
                else f"Execute deprecated MCP {namespace or 'shell'} command."
            ),
        ),
        authorization=authorization,
        x_gpt_bridge_key=x_gpt_bridge_key,
    )
    payload = result.model_dump(mode="json")
    return _mcp_tool_result(
        ok=bool(payload.get("ok")),
        summary=f"Executed Scarlet shell command: {command}",
        structured=payload,
    )


def _mcp_tool_namespace(tool_name: str) -> str | None:
    return {
        "scarlet_help_command": "help",
        "scarlet_memory_command": "memory",
        "scarlet_session_command": "session",
        "scarlet_metacognition_command": "metacognition",
        "scarlet_focus_command": "focus",
        "scarlet_affect_command": "affect",
        "scarlet_volition_command": "volition",
        "scarlet_shell_command": "",
    }.get(tool_name)


def _mcp_normalize_command(command: str, *, namespace: str) -> str:
    stripped = command.strip()
    if not namespace:
        return stripped
    first = stripped.split(maxsplit=1)[0].casefold() if stripped else ""
    aliases = {
        "help": {"help", "?", "schema", "capabilities"},
        "memory": {"memory", "mem", "remember"},
        "session": {"session", "sessions", "episodic"},
        "metacognition": {"metacognition", "meta", "reflect"},
        "focus": {"focus", "attention"},
        "affect": {"affect", "emotion", "emotions"},
        "volition": {"volition", "intention", "intentions"},
    }
    if first in aliases.get(namespace, {namespace}):
        return stripped
    if namespace == "help":
        return f"help {stripped}" if stripped else "help"
    return f"{namespace} {stripped}"


def _mcp_tool_result(
    *,
    ok: bool,
    summary: str,
    structured: dict[str, Any],
) -> dict[str, Any]:
    structured = {
        "ok": ok,
        "summary": summary,
        **structured,
    }
    return {
        "content": [
            {
                "type": "text",
                "text": _truncate_text(
                    json.dumps(structured, ensure_ascii=False, sort_keys=True),
                    limit=6000,
                ),
            }
        ],
        "structuredContent": structured,
        "isError": not ok,
        "_meta": {
            "bridge": "scarlet_mcp_bridge",
            "full_result_in_structured_content": True,
        },
    }


def _gpt_bootstrap_context_payload(
    *,
    runtime_context: str,
    runtime_payload: dict[str, Any],
    memory_payload: dict[str, Any],
    metacognitive_payload: dict[str, Any] | None,
    llm_messages: list[Any],
    provider_history_source: str,
    provider_message_stats: dict[str, Any],
    trace_ids: list[str],
) -> dict[str, Any]:
    """Return a GPT Actions-sized context packet.

    Full raw diagnostics are still persisted in traces. The external GPT needs
    the model-facing runtime context and compact navigation hints, not the full
    memory query plan, system prompt copy, or provider-history dump.
    """

    return {
        "profile": "gpt-bootstrap-compact-v1",
        "runtime_context": runtime_context,
        "runtime_payload_summary": _compact_runtime_payload(runtime_payload),
        "memory_context": _compact_memory_payload(memory_payload),
        "metacognitive_context": _compact_metacognitive_payload(
            metacognitive_payload
        ),
        "provider_history_source": provider_history_source,
        "provider_message_stats": provider_message_stats,
        "provider_messages_recent": _compact_provider_messages(llm_messages),
        "tools": [
            {
                "name": MIND_SHELL_TOOL_SCHEMA.get("name"),
                "description": MIND_SHELL_TOOL_SCHEMA.get("description"),
            }
        ],
        "mind_shell_action_endpoint": "POST /gpt/action",
        "finalize_endpoint": "POST /gpt/finalize",
        "full_diagnostics": {
            "available_in_trace_ids": trace_ids,
            "omitted_from_action_response": [
                "full_effective_system_prompt",
                "base_system_prompt",
                "raw_memory_query_plan",
                "raw_runtime_payload",
                "full_provider_messages",
                "retrieval_shadow",
                "retrieval_graph",
                "retrieval_hybrid_debug",
            ],
            "reason": "ChatGPT Actions has a practical response-size limit; full diagnostics remain in backend traces.",
        },
    }


def _compact_runtime_payload(runtime_payload: dict[str, Any]) -> dict[str, Any]:
    blocks = runtime_payload.get("blocks") or []
    block_summaries: list[dict[str, Any]] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        content = block.get("content") if isinstance(block.get("content"), dict) else {}
        summary: dict[str, Any] = {
            "id": block.get("id"),
            "type": block.get("type"),
            "scope": block.get("scope"),
            "lifetime": block.get("lifetime"),
            "source": block.get("source"),
        }
        if block.get("type") == "session_context":
            current_session = content.get("current_session")
            previous_sessions = content.get("previous_sessions") or []
            previous_session_memories = content.get("previous_session_memories") or []
            summary["current_session_id"] = (
                current_session or {}
            ).get("id") if isinstance(current_session, dict) else None
            summary["previous_session_count"] = len(previous_sessions)
            summary["previous_session_memory_count"] = len(previous_session_memories)
        elif block.get("type") == "message_context":
            memory_context = content.get("memory_context") or {}
            recent_events = content.get("recent_runtime_events") or []
            summary["memory_selected_count"] = len(memory_context.get("selected") or [])
            summary["memory_near_miss_count"] = len(
                memory_context.get("near_miss") or []
            )
            summary["recent_runtime_event_count"] = len(recent_events)
        elif block.get("type") in {"focus_context", "affective_context", "scarlet_state"}:
            summary["content_keys"] = sorted(content.keys())
        block_summaries.append(summary)

    return {
        "schema_version": runtime_payload.get("schema_version"),
        "rendering_profile": runtime_payload.get("rendering_profile"),
        "generated_at": runtime_payload.get("generated_at"),
        "session_id": runtime_payload.get("session_id"),
        "turn_id": runtime_payload.get("turn_id"),
        "block_index": runtime_payload.get("block_index", []),
        "blocks": block_summaries,
        "temporal_context": runtime_payload.get("temporal_context"),
        "mind_shell": runtime_payload.get("mind_shell"),
        "capabilities": runtime_payload.get("capabilities"),
        "trace_id": runtime_payload.get("trace_id"),
    }


def _compact_memory_payload(memory_payload: dict[str, Any]) -> dict[str, Any]:
    query_plan = memory_payload.get("query_plan")
    compact_query_plan: dict[str, Any] | None = None
    if isinstance(query_plan, dict):
        retrieval_hybrid = query_plan.get("retrieval_hybrid")
        compact_query_plan = {
            "lexical_queries": query_plan.get("lexical_queries", []),
            "semantic_queries": query_plan.get("semantic_queries", []),
            "sparse_query": query_plan.get("sparse_query"),
            "retrieval_stages": query_plan.get("retrieval_stages", []),
        }
        if isinstance(retrieval_hybrid, dict):
            compact_query_plan["retrieval_hybrid"] = {
                "enabled": retrieval_hybrid.get("enabled"),
                "ok": retrieval_hybrid.get("ok"),
                "mode": retrieval_hybrid.get("mode"),
                "ranking_policy": retrieval_hybrid.get("ranking_policy"),
                "thresholds": retrieval_hybrid.get("thresholds"),
            }

    return {
        "operation": memory_payload.get("operation"),
        "searched": memory_payload.get("searched"),
        "trace_id": memory_payload.get("trace_id"),
        "packet_profile": memory_payload.get("packet_profile"),
        "temporal_context": memory_payload.get("temporal_context"),
        "query_plan": compact_query_plan,
        "selected": memory_payload.get("selected", []),
        "near_miss": memory_payload.get("near_miss", []),
        "excluded": memory_payload.get("excluded", []),
        "conflicts": memory_payload.get("conflicts", []),
        "negative_evidence": memory_payload.get("negative_evidence"),
        "candidate_count": memory_payload.get("candidate_count"),
        "ranked_candidate_count": memory_payload.get("ranked_candidate_count"),
        "selected_count": memory_payload.get("selected_count"),
        "budget": memory_payload.get("budget"),
        "omitted_debug": [
            "turn_frame",
            "raw_retrieval_readiness",
            "raw_retrieval_graph",
            "raw_retrieval_shadow",
            "raw_retrieval_hybrid_debug",
        ],
    }


def _compact_metacognitive_payload(
    metacognitive_payload: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if metacognitive_payload is None:
        return None
    return {
        "mode": metacognitive_payload.get("mode"),
        "model_facing": metacognitive_payload.get("model_facing"),
        "trace_id": metacognitive_payload.get("trace_id"),
        "summary": metacognitive_payload.get("summary"),
        "selected": metacognitive_payload.get("selected"),
        "near_miss": metacognitive_payload.get("near_miss"),
        "suggested_next_actions": metacognitive_payload.get("suggested_next_actions"),
    }


def _compact_provider_messages(llm_messages: list[Any]) -> list[dict[str, Any]]:
    recent = llm_messages[-_GPT_BRIDGE_PROVIDER_MESSAGE_LIMIT:]
    return [
        _compact_provider_message(message.model_dump(mode="json"))
        for message in recent
    ]


def _compact_provider_message(message: dict[str, Any]) -> dict[str, Any]:
    content = message.get("content")
    compact_blocks: list[dict[str, Any]] = []
    if isinstance(content, str):
        compact_blocks.append(
            {
                "type": "text",
                "text": _truncate_text(
                    content,
                    limit=_GPT_BRIDGE_PROVIDER_MESSAGE_TEXT_LIMIT,
                ),
            }
        )
    elif isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            block_type = block.get("type")
            if block_type == "text":
                compact_blocks.append(
                    {
                        "type": "text",
                        "text": _truncate_text(
                            str(block.get("text", "")),
                            limit=_GPT_BRIDGE_PROVIDER_MESSAGE_TEXT_LIMIT,
                        ),
                    }
                )
            elif block_type == "tool_use":
                compact_blocks.append(
                    {
                        "type": "tool_use",
                        "name": block.get("name"),
                        "id": block.get("id"),
                    }
                )
            elif block_type == "tool_result":
                compact_blocks.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.get("tool_use_id"),
                        "is_error": block.get("is_error"),
                    }
                )
            elif block_type == "thinking":
                compact_blocks.append(
                    {
                        "type": "thinking",
                        "summary": "thinking block present in provider history; full content is kept in backend trace/history.",
                    }
                )
            else:
                compact_blocks.append({"type": block_type})

    return {
        "role": message.get("role"),
        "content": compact_blocks,
    }


def _truncate_text(text: str, *, limit: int) -> str:
    if len(text) <= limit:
        return text
    omitted = len(text) - limit
    return f"{text[:limit]}... [truncated {omitted} chars]"


def _require_bridge_auth(
    settings: Settings,
    *,
    authorization: str | None,
    x_gpt_bridge_key: str | None,
    query_key: str | None = None,
) -> None:
    expected = settings.gpt_bridge_api_key
    if not expected:
        if settings.environment == "local":
            return
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "gpt_bridge.auth_not_configured",
                "message": "GPT bridge key is not configured.",
                "recoverable": False,
            },
        )
    supplied = x_gpt_bridge_key
    if not supplied and authorization:
        prefix = "bearer "
        lowered = authorization.casefold()
        if lowered.startswith(prefix):
            supplied = authorization[len(prefix) :].strip()
    if not supplied:
        supplied = query_key
    if supplied != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "gpt_bridge.unauthorized",
                "message": "Invalid GPT bridge key.",
                "recoverable": True,
            },
        )


def _get_or_create_bridge_session(
    db: Session,
    request: GPTBridgeBootstrapRequest,
) -> ChatSession:
    if request.session_id is not None:
        return _require_session(db, request.session_id)
    metadata = {
        "source": "gpt_bridge",
        "bridge": "chatgpt_gpt_actions",
        **request.metadata,
    }
    return repositories.create_chat_session(
        db,
        title=request.title or "GPT Bridge Chat",
        metadata=metadata,
    )


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


def _require_turn(db: Session, turn_id: str, *, session_id: str) -> Turn:
    turn = db.get(Turn, turn_id)
    if turn is None or turn.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "turn.not_found",
                "message": f"Turn {turn_id} was not found for session {session_id}.",
                "recoverable": True,
            },
        )
    return turn


def _require_active_turn(db: Session, session_id: str, turn_id: str) -> Turn:
    _require_session(db, session_id)
    turn = _require_turn(db, turn_id, session_id=session_id)
    if turn.status != "started":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "gpt_bridge.turn_not_active",
                "message": f"Turn {turn_id} is already {turn.status}.",
                "recoverable": False,
            },
        )
    return turn


def _resolve_system_prompt(
    settings: Settings,
    db: Session,
    session_id: str,
    turn_id: str,
) -> dict[str, str | None]:
    try:
        system_prompt = resolve_agent_system_prompt(settings)
    except AgentSystemPromptError as exc:
        repositories.add_trace(
            db,
            session_id=session_id,
            turn_id=turn_id,
            kind="llm.error",
            payload={
                "code": "agent.system_prompt_error",
                "message": str(exc),
                "entrypoint": "gpt.bootstrap",
            },
        )
        repositories.complete_turn(
            db,
            turn_id=turn_id,
            status="failed",
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
    return {
        "content": system_prompt.content,
        "source": system_prompt.source,
        "path": system_prompt.path,
    }


def _request_trace(db: Session, *, turn_id: str) -> Trace:
    for trace in repositories.list_traces_for_turn(db, turn_id=turn_id):
        if trace.kind == "llm.request":
            return trace
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "gpt_bridge.bootstrap_missing",
            "message": f"Turn {turn_id} has no bootstrap llm.request trace.",
            "recoverable": False,
        },
    )


def _update_provider_history_from_bootstrap(
    db: Session,
    *,
    session_id: str,
    turn_id: str,
    assistant_text: str,
) -> None:
    request_trace = _request_trace(db, turn_id=turn_id)
    provider_messages = _valid_provider_history(
        request_trace.payload_json.get("provider_messages")
    )
    provider_messages.append(
        {
            "role": "assistant",
            "content": [{"type": "text", "text": assistant_text}],
        }
    )
    repositories.update_chat_session_provider_history(
        db,
        session_id=session_id,
        provider_history=provider_messages,
    )


def _tool_call_summaries(db: Session, *, turn_id: str) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for trace in repositories.list_traces_for_turn(db, turn_id=turn_id):
        if trace.kind != "mind.tool_call":
            continue
        payload = trace.payload_json
        summaries.append(
            {
                "trace_id": trace.id,
                "tool_call_id": payload.get("tool_call_id"),
                "tool_name": payload.get("tool_name"),
                "arguments": payload.get("arguments"),
                "status": payload.get("status"),
                "latency_ms": payload.get("latency_ms"),
            }
        )
    return summaries
