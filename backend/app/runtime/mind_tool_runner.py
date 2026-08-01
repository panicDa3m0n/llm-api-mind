"""Shared provider-tool runner for every native Scarlet model turn.

The HTTP adapter and autonomous cognition use the same model-facing
``mind_shell`` contract.  This module owns the provider-tool receipt path so
both callers persist identical tool calls, traces, and lifecycle events.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.config import Settings
from app.llm.provider import LLMExecutedToolCall, LLMProvider, LLMToolUse
from app.mind.dispatcher import (
    MindAPIContext,
    MindAPIError,
    MindAPIRequest,
    MindAPIResponse,
)
from app.mind.schema import MIND_SHELL_TOOL_SCHEMA
from app.mind.shell import MindShellRequest, dispatch_mind_shell
from app.runtime.events import record_tool_call_completed, record_tool_call_started
from app.storage import repositories
from app.storage.models import CognitiveEvent


ProviderFactory = Callable[[Settings], LLMProvider]


def build_mind_tool_runner(
    engine: Engine,
    *,
    settings: Settings,
    provider_factory: ProviderFactory,
    session_id: str,
    turn_id: str,
    source_message_id: str,
    trace_ids: list[str],
    runtime_trigger: str = "human_message",
    event_sink: list[CognitiveEvent] | None = None,
) -> Callable[[LLMToolUse], LLMExecutedToolCall]:
    """Create the single executable ``mind_shell`` path for one model turn."""

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
                runtime_trigger=runtime_trigger,
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
                arguments=(
                    mind_request.model_dump(mode="json")
                    if mind_request is not None
                    else {"raw_input": tool_use.input}
                ),
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
                    "arguments": (
                        mind_request.model_dump(mode="json")
                        if mind_request is not None
                        else {"raw_input": tool_use.input}
                    ),
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
            arguments=(
                mind_request.model_dump(mode="json")
                if mind_request is not None
                else {"raw_input": tool_use.input}
            ),
            result=result_payload,
            status=tool_call_status,
            latency_ms=latency_ms,
            tool_call_id=tool_call_id,
            trace_id=trace_id,
            provider_content_parts=mind_response.provider_content_parts,
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
