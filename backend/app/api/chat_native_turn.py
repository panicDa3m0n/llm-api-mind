"""Shared native-turn preparation, completion, and transport-neutral state."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.api.chat_provider_history import provider_messages_for_turn
from app.api.chat_serialization import (
    ChatMessageResponse,
    ChatTurnResponse,
    event_stream_payload,
    message_response,
    metacognitive_context_event_payload,
    ndjson,
    session_response,
)
from app.config import Settings
from app.llm.factory import (
    active_provider_max_tokens,
    active_provider_model,
)
from app.llm.provider import (
    LLMConfigurationError,
    LLMIncompleteResponseError,
    LLMMessage,
    LLMProvider,
    LLMRequestError,
    LLMTextResult,
)
from app.mind.context import MemoryContextBuild
from app.mind.contracts import LivePerceptionCapture
from app.mind.schema import MIND_SHELL_TOOL_SCHEMA
from app.prompts.system import AgentSystemPromptError, resolve_agent_system_prompt
from app.runtime.events import record_event, record_provider_stream_event
from app.runtime.mind_tool_runner import build_mind_tool_runner
from app.runtime.turn_kernel import (
    ModelTurnPreparation,
    complete_model_turn,
    prepare_model_turn,
    record_failed_model_turn,
    require_terminal_response,
)
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
    """Native transport additions over one shared model-turn preparation."""

    kernel: ModelTurnPreparation
    user_message: ChatMessageResponse
    execution_messages: list[LLMMessage]
    live_perception_capture: LivePerceptionCapture | None = None

    @property
    def session_id(self) -> str:
        return self.kernel.session_id

    @property
    def turn_id(self) -> str:
        return self.kernel.turn_id

    @property
    def trace_ids(self) -> list[str]:
        return self.kernel.trace_ids

    @property
    def effective_system(self) -> str:
        return self.kernel.effective_system

    @property
    def max_tokens(self) -> int:
        return self.kernel.max_tokens

    @property
    def memory_context(self) -> MemoryContextBuild:
        return self.kernel.memory_context

    @property
    def stream(self) -> bool:
        return self.kernel.stream


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
    transient_user_content_parts: list[dict[str, Any]] | None = None,
    request_metadata: dict[str, Any] | None = None,
    live_perception_capture: LivePerceptionCapture | None = None,
) -> NativeTurnPreparation:
    """Persist the human adapter boundary, then use the shared turn kernel."""

    started = time.perf_counter()
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
        if chat_session.kind != "human_dialogue":
            raise NativeTurnFailure(
                status_code=409,
                detail={
                    "code": "session.not_human_dialogue",
                    "message": (
                        "The requested session is reserved for Scarlet's "
                        "internal autonomous cognition."
                    ),
                    "recoverable": False,
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

        kernel_prepared = prepare_model_turn(
            db,
            settings=settings,
            chat_session=chat_session,
            turn_id=turn_id,
            source_message=stored_user_message,
            history=history,
            canonical_messages=canonical_messages,
            provider_history_source=provider_history_source,
            base_system=system_prompt.content,
            system_source=system_prompt.source,
            system_path=system_prompt.path,
            model=model,
            max_tokens=max_tokens,
            started=started,
            stream=stream,
            entrypoint=entrypoint,
            accounting_transport=accounting_transport,
            request_metadata=request_metadata,
        )

    execution_messages = _execution_messages_with_transient_content(
        kernel_prepared.model_messages,
        transient_user_content_parts or [],
    )

    return NativeTurnPreparation(
        kernel=kernel_prepared,
        user_message=user_message,
        execution_messages=execution_messages,
        live_perception_capture=live_perception_capture,
    )

def complete_native_turn(
    *,
    settings: Settings,
    engine: Engine,
    prepared: NativeTurnPreparation,
    result: LLMTextResult,
    semantic_content_event_seen: bool = False,
) -> NativeTurnCompletion:
    """Project a shared model-turn completion onto the native HTTP response."""

    completion = complete_model_turn(
        settings=settings,
        engine=engine,
        prepared=prepared.kernel,
        result=result,
        # Synchronous native requests do not emit provider content events before
        # completion, while streaming requests may already have done so.
        semantic_content_event_seen=(
            semantic_content_event_seen if prepared.stream else False
        ),
    )
    with Session(engine) as db:
        chat_session = repositories.get_chat_session(db, prepared.session_id)
        assistant_message = repositories.get_message(
            db,
            completion.assistant_message_id,
        )
        completed_turn = repositories.get_turn(db, completion.completed_turn_id)
        if (
            chat_session is None
            or assistant_message is None
            or completed_turn is None
        ):
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
            live_perception_capture=prepared.live_perception_capture,
            model=result.model,
            latency_ms=completion.latency_ms,
            usage=result.usage,
        )
    return NativeTurnCompletion(
        response=response,
        runtime_events=completion.runtime_events,
    )

def record_failed_native_turn(
    engine: Engine,
    *,
    prepared: NativeTurnPreparation,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> CognitiveEvent:
    return record_failed_model_turn(
        engine,
        prepared=prepared.kernel,
        code=code,
        message=message,
        details=details,
    )


def execute_native_turn(
    *,
    settings: Settings,
    engine: Engine,
    provider_factory: ProviderFactory,
    prepared: NativeTurnPreparation,
) -> ChatTurnResponse:
    try:
        provider = provider_factory(settings)
        tool_runner = build_mind_tool_runner(
            engine,
            settings=settings,
            provider_factory=provider_factory,
            session_id=prepared.session_id,
            turn_id=prepared.turn_id,
            source_message_id=prepared.user_message.id,
            trace_ids=prepared.trace_ids,
        )
        result = provider.generate_chat_with_tools(
            messages=prepared.execution_messages,
            system=prepared.effective_system,
            max_tokens=prepared.max_tokens,
            tools=[MIND_SHELL_TOOL_SCHEMA],
            tool_runner=tool_runner,
            max_tool_calls=None,
        )
        result = require_terminal_response(result)
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

    return complete_native_turn(
        settings=settings,
        engine=engine,
        prepared=prepared,
        result=result,
    ).response



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
    llm_messages = prepared.execution_messages
    system = prepared.effective_system
    max_tokens = prepared.max_tokens
    memory_context = prepared.memory_context.payload
    metacognitive_context = prepared.memory_context.metacognitive_payload
    runtime_context = prepared.memory_context.runtime_payload
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
    semantic_content_event_seen = False
    try:
        provider = provider_factory(settings)
        tool_runner = build_mind_tool_runner(
            engine,
            settings=settings,
            provider_factory=provider_factory,
            session_id=session_id,
            turn_id=turn_id,
            source_message_id=user_message_response.id,
            trace_ids=trace_ids,
            event_sink=pending_runtime_events,
            live_perception_capture=prepared.live_perception_capture,
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
            result = require_terminal_response(result)
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

    completion = complete_native_turn(
        settings=settings,
        engine=engine,
        prepared=prepared,
        result=result,
        semantic_content_event_seen=semantic_content_event_seen,
    )
    for event in completion.runtime_events:
        yield emit("runtime_event", {"event": event})
    yield emit("turn_complete", completion.response.model_dump(mode="json"))


def _execution_messages_with_transient_content(
    messages: list[LLMMessage],
    transient_parts: list[dict[str, Any]],
) -> list[LLMMessage]:
    """Attach media to the current user message without changing history."""

    if not transient_parts:
        return messages
    execution_messages = [message.model_copy(deep=True) for message in messages]
    for index in range(len(execution_messages) - 1, -1, -1):
        message = execution_messages[index]
        if message.role != "user":
            continue
        text = _message_text(message.content)
        message.content = [
            {"type": "input_text", "text": text},
            *transient_parts,
        ]
        return execution_messages
    raise ValueError("Transient media requires a current user message.")


def _message_text(content: str | list[dict[str, Any]]) -> str:
    if isinstance(content, str):
        return content
    return "\n".join(
        str(block.get("text"))
        for block in content
        if block.get("type") in {"text", "input_text"}
        and isinstance(block.get("text"), str)
    ).strip()
