import time
from typing import Any

from fastapi import APIRouter, Header, HTTPException, status
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
from app.llm.provider import LLMConfigurationError, LLMExecutedToolCall
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
from app.runtime.context_accounting import build_external_context_accounting_preflight
from app.runtime.answer_obligations import (
    AnswerObligationManifest,
    AnswerValidationResult,
    augment_with_tool_evidence,
    compile_answer_obligations,
    gpt_action_policy,
    validate_answer_semantics,
)
from app.runtime.maintenance import (
    schedule_session_idle_maintenance,
    schedule_summary_repairs,
)
from app.runtime.preferences import load_runtime_preferences
from app.storage import repositories
from app.storage.models import ChatSession, Trace, Turn, new_id

ProviderFactory = Any

_GPT_BRIDGE_PROVIDER_MESSAGE_LIMIT = 8
_GPT_BRIDGE_PROVIDER_MESSAGE_TEXT_LIMIT = 1200


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
    action_policy: dict[str, Any]
    required_actions: list[dict[str, Any]] = Field(default_factory=list)
    recommended_actions: list[dict[str, Any]] = Field(default_factory=list)


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
    ) -> GPTBridgeBootstrapResponse:
        _require_bridge_auth(
            settings,
            authorization=authorization,
            x_gpt_bridge_key=x_gpt_bridge_key,
        )
        started = time.perf_counter()
        trace_ids: list[str] = []

        with Session(engine) as db:
            chat_session = _get_or_create_bridge_session(db, request, settings=settings)
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
            effective_system = _compose_system_with_runtime_context(
                system_prompt["content"],
                memory_context.runtime_context,
            )
            bootstrap_context = _gpt_bootstrap_context_payload(
                runtime_context=memory_context.runtime_context,
                metacognitive_payload=memory_context.metacognitive_payload,
                llm_messages=llm_messages,
                provider_history_source=provider_history_source,
                provider_message_stats=provider_message_stats,
                trace_ids=trace_ids,
            )
            answer_manifest = compile_answer_obligations(
                transport="gpt_bridge",
                memory_context=memory_context.payload,
                metacognitive_context=memory_context.metacognitive_payload,
            )
            answer_manifest_trace_id: str | None = None
            if settings.answer_obligations_mode != "off":
                answer_manifest_trace_id = _record_gpt_answer_manifest(
                    db,
                    session_id=session_id,
                    turn_id=turn_id,
                    manifest=answer_manifest,
                    mode=settings.answer_obligations_mode,
                    phase="bootstrap",
                )
                trace_ids.append(answer_manifest_trace_id)
            action_policy, required_actions, recommended_actions = gpt_action_policy(
                answer_manifest
            )
            action_policy["mode"] = settings.answer_obligations_mode
            bootstrap_context["answer_obligations"] = answer_manifest.model_dump(
                mode="json"
            )
            accounting_payload = build_external_context_accounting_preflight(
                session_id=session_id,
                turn_id=turn_id,
                transport="gpt_bridge_bootstrap",
                payload=bootstrap_context,
                settings=settings,
            )
            accounting_trace = repositories.add_trace(
                db,
                session_id=session_id,
                turn_id=turn_id,
                kind="context.accounting.preflight",
                payload=accounting_payload,
            )
            trace_ids.append(accounting_trace.id)
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
                    "model_context_profile": memory_context.model_context_profile,
                    "model_context_trace_id": memory_context.model_context_trace_id,
                    "context_accounting_trace_id": accounting_trace.id,
                    "context_accounting": {
                        "schema_version": accounting_payload["schema_version"],
                        "measurement_boundary": accounting_payload[
                            "measurement_boundary"
                        ],
                        "total": accounting_payload["total"],
                    },
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
                    "answer_obligations_trace_id": answer_manifest_trace_id,
                    "answer_obligations": answer_manifest.model_dump(mode="json"),
                    "latency_ms": int((time.perf_counter() - started) * 1000),
                },
            )
            trace_ids.append(request_trace.id)
            bootstrap_context["full_diagnostics"]["available_in_trace_ids"] = list(
                trace_ids
            )
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
                context=bootstrap_context,
                required_next_steps=[
                    "Use this returned context as Scarlet's active turn context.",
                    "Call POST /gpt/action for every mind_shell command you need.",
                    "Call POST /gpt/finalize with the exact final answer before showing it to the user.",
                ],
                action_policy=action_policy,
                required_actions=required_actions,
                recommended_actions=recommended_actions,
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
    ) -> GPTBridgeActionResponse:
        _require_bridge_auth(
            settings,
            authorization=authorization,
            x_gpt_bridge_key=x_gpt_bridge_key,
        )
        started = time.perf_counter()
        source_message_id: str | None = None
        with Session(engine) as db:
            _require_active_turn(db, request.session_id, request.turn_id)
            source_message = repositories.latest_message_for_turn(
                db,
                turn_id=request.turn_id,
                role="user",
            )
            source_message_id = source_message.id if source_message is not None else None
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
                source_message_id=source_message_id,
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
            answer_manifest = augment_with_tool_evidence(
                _answer_manifest_for_turn(db, turn_id=request.turn_id),
                _executed_tool_calls_for_turn(db, turn_id=request.turn_id),
            )
            manifest_trace_id: str | None = None
            if settings.answer_obligations_mode != "off":
                manifest_trace_id = _record_gpt_answer_manifest(
                    db,
                    session_id=request.session_id,
                    turn_id=request.turn_id,
                    manifest=answer_manifest,
                    mode=settings.answer_obligations_mode,
                    phase="after_action",
                )
            action_policy, required_actions, recommended_actions = gpt_action_policy(
                answer_manifest
            )
            action_policy.update(
                {
                    "mode": settings.answer_obligations_mode,
                    "manifest_trace_id": manifest_trace_id,
                }
            )
            return GPTBridgeActionResponse(
                ok=mind_response.ok,
                session_id=request.session_id,
                turn_id=request.turn_id,
                tool_call_id=tool_call.id,
                trace_id=trace.id,
                response=mind_response,
                action_policy=action_policy,
                required_actions=required_actions,
                recommended_actions=recommended_actions,
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
    ) -> GPTBridgeFinalizeResponse:
        _require_bridge_auth(
            settings,
            authorization=authorization,
            x_gpt_bridge_key=x_gpt_bridge_key,
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

            answer_manifest = augment_with_tool_evidence(
                _answer_manifest_for_turn(db, turn_id=request.turn_id),
                _executed_tool_calls_for_turn(db, turn_id=request.turn_id),
            )
            semantic_validation = None
            if (
                settings.answer_obligations_mode in {"shadow", "active"}
                and answer_manifest.semantic
            ):
                try:
                    provider = provider_factory(settings)
                except LLMConfigurationError as exc:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail={
                            "code": "gpt_bridge.answer_validation_unavailable",
                            "message": str(exc),
                            "recoverable": True,
                        },
                    ) from exc
                semantic_validation = validate_answer_semantics(
                    provider=provider,
                    manifest=answer_manifest,
                    answer=request.answer,
                    max_tokens=settings.answer_validation_max_tokens,
                )
            accepted = semantic_validation is None or semantic_validation.accepted
            validation_trace_id = _record_gpt_answer_validation(
                db,
                session_id=request.session_id,
                turn_id=request.turn_id,
                manifest=answer_manifest,
                answer=request.answer,
                validation=semantic_validation,
                accepted=accepted,
                mode=settings.answer_obligations_mode,
            )
            trace_ids.append(validation_trace_id)
            if (
                settings.answer_obligations_mode == "active"
                and semantic_validation is not None
                and semantic_validation.validator_status == "failed"
            ):
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={
                        "code": "gpt_bridge.answer_validation_unavailable",
                        "message": (
                            "The answer validator could not establish whether the "
                            "draft satisfies the current hard obligations."
                        ),
                        "recoverable": True,
                        "answer_validation_trace_id": validation_trace_id,
                        "validator_error": semantic_validation.validator_error,
                    },
                )
            if (
                settings.answer_obligations_mode == "active"
                and semantic_validation is not None
                and not semantic_validation.accepted
            ):
                prior_rejections = _gpt_answer_rejection_count(
                    db,
                    turn_id=request.turn_id,
                    exclude_trace_id=validation_trace_id,
                )
                detail = {
                    "code": "gpt_bridge.answer_obligation_failed",
                    "message": (
                        "The final draft did not satisfy the current hard answer "
                        "obligations. Correct it before finalizing."
                    ),
                    "recoverable": prior_rejections == 0,
                    "answer_validation_trace_id": validation_trace_id,
                    "hard_failure_ids": semantic_validation.hard_failure_ids,
                    "findings": [
                        item.model_dump(mode="json")
                        for item in semantic_validation.findings
                    ],
                    "required_next_steps": [
                        "Use any still-required GPT Action.",
                        "Correct the answer using the validation findings.",
                        "Call finalizeScarletBeforeAnswer again with the corrected exact draft.",
                    ],
                }
                if prior_rejections > 0:
                    repositories.complete_turn(
                        db,
                        turn_id=request.turn_id,
                        status="failed",
                        latency_ms=int((time.perf_counter() - started) * 1000),
                        error=detail,
                    )
                    record_event(
                        db,
                        session_id=request.session_id,
                        turn_id=request.turn_id,
                        event_type="turn.failed",
                        payload=detail,
                        source="answer_control",
                        actor="backend",
                        visibility="debug",
                        status="failed",
                        trace_id=validation_trace_id,
                    )
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail=detail,
                    )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=detail,
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
                    "answer_validation_trace_id": validation_trace_id,
                    "answer_obligations": answer_manifest.model_dump(mode="json"),
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

    return router



def _gpt_bootstrap_context_payload(
    *,
    runtime_context: str,
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

    payload = {
        "profile": "gpt-bootstrap-compact-v1",
        "runtime_context": runtime_context,
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
    return payload


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
    *,
    settings: Settings,
) -> ChatSession:
    if request.session_id is not None:
        return _require_session(db, request.session_id)
    metadata = {
        "source": "gpt_bridge",
        "bridge": "chatgpt_gpt_actions",
        **request.metadata,
    }
    chat_session = repositories.create_chat_session(
        db,
        title=request.title or "GPT Bridge Chat",
        metadata=metadata,
    )
    schedule_summary_repairs(
        db,
        settings=settings,
        limit=1,
        exclude_session_id=chat_session.id,
    )
    return chat_session


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


def _record_gpt_answer_manifest(
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


def _answer_manifest_for_turn(
    db: Session,
    *,
    turn_id: str,
) -> AnswerObligationManifest:
    traces = repositories.list_traces_for_turn(db, turn_id=turn_id)
    for trace in reversed(traces):
        if trace.kind != "answer.obligations":
            continue
        raw_manifest = trace.payload_json.get("manifest")
        if not isinstance(raw_manifest, dict):
            continue
        return AnswerObligationManifest.model_validate(raw_manifest)
    return AnswerObligationManifest(transport="gpt_bridge")


def _executed_tool_calls_for_turn(
    db: Session,
    *,
    turn_id: str,
) -> list[LLMExecutedToolCall]:
    executed: list[LLMExecutedToolCall] = []
    for trace in repositories.list_traces_for_turn(db, turn_id=turn_id):
        if trace.kind != "mind.tool_call":
            continue
        payload = trace.payload_json
        provider_tool_use_id = payload.get("provider_tool_use_id")
        if not isinstance(provider_tool_use_id, str) or not provider_tool_use_id:
            continue
        executed.append(
            LLMExecutedToolCall(
                provider_tool_use_id=provider_tool_use_id,
                tool_name=str(payload.get("tool_name") or "mind_shell"),
                arguments=payload.get("arguments")
                if isinstance(payload.get("arguments"), dict)
                else {},
                result=payload.get("result")
                if isinstance(payload.get("result"), dict)
                else {},
                status=str(payload.get("status") or "error"),
                latency_ms=payload.get("latency_ms")
                if isinstance(payload.get("latency_ms"), int)
                else None,
                tool_call_id=str(payload.get("tool_call_id"))
                if payload.get("tool_call_id")
                else None,
                trace_id=trace.id,
            )
        )
    return executed


def _record_gpt_answer_validation(
    db: Session,
    *,
    session_id: str,
    turn_id: str,
    manifest: AnswerObligationManifest,
    answer: str,
    validation: AnswerValidationResult | None,
    accepted: bool,
    mode: str,
) -> str:
    runtime_accepted = mode != "active" or accepted
    trace = repositories.add_trace(
        db,
        session_id=session_id,
        turn_id=turn_id,
        kind="answer.validation",
        payload={
            "transport": "gpt_bridge",
            "mode": mode,
            "accepted": runtime_accepted,
            "semantic_passed": accepted,
            "manifest": manifest.model_dump(mode="json"),
            "semantic": validation.model_dump(mode="json")
            if validation is not None
            else None,
            "draft": {"chars": len(answer), "text": answer},
        },
    )
    trace_id = trace.id
    record_event(
        db,
        session_id=session_id,
        turn_id=turn_id,
        event_type="answer.validation.accepted"
        if runtime_accepted
        else "answer.validation.rejected",
        payload={
            "transport": "gpt_bridge",
            "mode": mode,
            "semantic_passed": accepted,
            "hard_failure_ids": validation.hard_failure_ids
            if validation is not None
            else [],
        },
        source="answer_control",
        actor="backend",
        visibility="debug",
        status="completed" if runtime_accepted else "error",
        trace_id=trace_id,
    )
    return trace_id


def _gpt_answer_rejection_count(
    db: Session,
    *,
    turn_id: str,
    exclude_trace_id: str,
) -> int:
    return sum(
        1
        for trace in repositories.list_traces_for_turn(db, turn_id=turn_id)
        if trace.kind == "answer.validation"
        and trace.id != exclude_trace_id
        and trace.payload_json.get("transport") == "gpt_bridge"
        and trace.payload_json.get("accepted") is False
    )
