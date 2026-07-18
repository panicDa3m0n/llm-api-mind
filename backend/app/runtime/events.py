from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.llm.provider import LLMExecutedToolCall, LLMStreamEvent
from app.storage import repositories
from app.storage.models import CognitiveEvent


STREAM_EVENT_TYPE_MAP = {
    "model_request": "llm.request.started",
    "thinking_start": "llm.thinking.started",
    "thinking_captured": "llm.thinking.captured",
    "tool_use_start": "mind.tool_use.started",
    "tool_call": "mind.tool_call.requested",
    "tool_result": "mind.tool_call.result_returned",
    "text_start": "llm.text.started",
    "assistant_note": "assistant.note.emitted",
    "assistant_answer": "assistant.answer.completed",
    "model_stop": "llm.request.stopped",
    "completion_recovery": "llm.completion.recovery.started",
}

DELTA_STREAM_EVENTS = {
    "thinking_delta",
    "tool_input_delta",
    "text_delta",
}


def record_event(
    db: Session,
    *,
    session_id: str,
    event_type: str,
    payload: dict[str, Any] | None = None,
    turn_id: str | None = None,
    source: str = "runtime",
    actor: str = "backend",
    visibility: str = "debug",
    status: str = "completed",
    parent_event_id: str | None = None,
    trace_id: str | None = None,
    tool_call_id: str | None = None,
    message_id: str | None = None,
) -> CognitiveEvent:
    return repositories.add_event(
        db,
        session_id=session_id,
        turn_id=turn_id,
        event_type=event_type,
        payload=payload or {},
        source=source,
        actor=actor,
        visibility=visibility,
        status=status,
        parent_event_id=parent_event_id,
        trace_id=trace_id,
        tool_call_id=tool_call_id,
        message_id=message_id,
    )


def record_event_with_engine(
    engine: Engine,
    *,
    session_id: str,
    event_type: str,
    payload: dict[str, Any] | None = None,
    turn_id: str | None = None,
    source: str = "runtime",
    actor: str = "backend",
    visibility: str = "debug",
    status: str = "completed",
    parent_event_id: str | None = None,
    trace_id: str | None = None,
    tool_call_id: str | None = None,
    message_id: str | None = None,
) -> CognitiveEvent:
    with Session(engine) as db:
        return record_event(
            db,
            session_id=session_id,
            turn_id=turn_id,
            event_type=event_type,
            payload=payload,
            source=source,
            actor=actor,
            visibility=visibility,
            status=status,
            parent_event_id=parent_event_id,
            trace_id=trace_id,
            tool_call_id=tool_call_id,
            message_id=message_id,
        )


def record_provider_stream_event(
    engine: Engine,
    *,
    session_id: str,
    turn_id: str,
    stream_event: LLMStreamEvent,
) -> CognitiveEvent | None:
    if stream_event.type in DELTA_STREAM_EVENTS:
        return None
    event_type = STREAM_EVENT_TYPE_MAP.get(stream_event.type)
    if event_type is None:
        return None
    payload = dict(stream_event.data)
    payload["provider_stream_event"] = stream_event.type
    source, actor, visibility = _stream_event_identity(stream_event)
    return record_event_with_engine(
        engine,
        session_id=session_id,
        turn_id=turn_id,
        event_type=event_type,
        payload=payload,
        source=source,
        actor=actor,
        visibility=visibility,
        status=_status_for_stream_event(stream_event),
        tool_call_id=_string(payload.get("tool_call_id")),
        trace_id=_string(payload.get("trace_id")),
    )


def record_tool_call_started(
    db: Session,
    *,
    session_id: str,
    turn_id: str,
    provider_tool_use_id: str,
    tool_name: str,
    arguments: dict[str, Any],
) -> CognitiveEvent:
    return record_event(
        db,
        session_id=session_id,
        turn_id=turn_id,
        event_type="mind.tool_call.started",
        payload={
            "provider_tool_use_id": provider_tool_use_id,
            "tool_name": tool_name,
            "arguments": arguments,
            "operation": _mind_operation(arguments),
        },
        source=tool_name or "mind_api",
        actor="scarlet",
        visibility="debug",
        status="active",
    )


def record_tool_call_completed(
    db: Session,
    *,
    session_id: str,
    turn_id: str,
    started_event_id: str | None,
    executed: LLMExecutedToolCall,
) -> CognitiveEvent:
    return record_event(
        db,
        session_id=session_id,
        turn_id=turn_id,
        event_type="mind.tool_call.completed"
        if executed.status == "completed"
        else "mind.tool_call.failed",
        payload={
            "provider_tool_use_id": executed.provider_tool_use_id,
            "tool_name": executed.tool_name,
            "operation": _mind_operation(executed.arguments),
            "arguments": executed.arguments,
            "result_summary": _mind_result_summary(executed.result),
            "latency_ms": executed.latency_ms,
        },
        source=executed.tool_name or "mind_api",
        actor="backend",
        visibility="debug",
        status=executed.status,
        parent_event_id=started_event_id,
        trace_id=executed.trace_id,
        tool_call_id=executed.tool_call_id,
    )


def record_response_content_events(
    db: Session,
    *,
    session_id: str,
    turn_id: str,
    raw_provider_messages: list[dict[str, Any]],
    response_trace_id: str,
    assistant_message_id: str,
) -> list[CognitiveEvent]:
    events: list[CognitiveEvent] = []
    for model_step, provider_message in enumerate(raw_provider_messages, start=1):
        content = provider_message.get("content")
        if not isinstance(content, list):
            continue
        has_tool_use = any(
            isinstance(block, dict) and block.get("type") == "tool_use"
            for block in content
        )
        for index, block in enumerate(content):
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text" and isinstance(block.get("text"), str):
                text = block["text"].strip()
                if not text:
                    continue
                events.append(
                    record_event(
                        db,
                        session_id=session_id,
                        turn_id=turn_id,
                        event_type="assistant.note.emitted"
                        if has_tool_use
                        else "assistant.answer.completed",
                        payload={
                            "text": text,
                            "model_step": model_step,
                            "index": index,
                            "provider_message_id": provider_message.get("id"),
                            "stop_reason": provider_message.get("stop_reason"),
                        },
                        source="assistant",
                        actor="scarlet",
                        visibility="public",
                        status="completed",
                        trace_id=response_trace_id,
                        message_id=assistant_message_id,
                    )
                )
            elif block.get("type") == "thinking":
                thinking_text = block.get("thinking")
                events.append(
                    record_event(
                        db,
                        session_id=session_id,
                        turn_id=turn_id,
                        event_type="llm.thinking.captured",
                        payload={
                            "text": thinking_text
                            if isinstance(thinking_text, str)
                            else "",
                            "model_step": model_step,
                            "index": index,
                            "provider_message_id": provider_message.get("id"),
                            "stop_reason": provider_message.get("stop_reason"),
                            "has_text": isinstance(thinking_text, str)
                            and bool(thinking_text),
                        },
                        source="provider",
                        actor="llm",
                        visibility="private",
                        status="completed",
                        trace_id=response_trace_id,
                    )
                )
    return events


def event_payload(event: CognitiveEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "session_id": event.session_id,
        "turn_id": event.turn_id,
        "seq": event.seq,
        "type": event.type,
        "source": event.source,
        "actor": event.actor,
        "visibility": event.visibility,
        "status": event.status,
        "parent_event_id": event.parent_event_id,
        "trace_id": event.trace_id,
        "tool_call_id": event.tool_call_id,
        "message_id": event.message_id,
        "payload": event.payload_json,
        "created_at": event.created_at.isoformat(),
    }


def compact_event_for_context(event: CognitiveEvent) -> dict[str, Any]:
    payload = event.payload_json or {}
    summary: dict[str, Any] = {
        "type": event.type,
        "source": event.source,
        "actor": event.actor,
        "status": event.status,
        "visibility": event.visibility,
        "created_at": event.created_at.isoformat(),
    }
    for key in (
        "operation",
        "path",
        "method",
        "result_summary",
        "selected_count",
        "candidate_count",
        "negative_evidence",
        "error",
    ):
        if key in payload:
            summary[key] = payload[key]
    return summary


def _status_for_stream_event(stream_event: LLMStreamEvent) -> str:
    if stream_event.type in {
        "model_request",
        "thinking_start",
        "tool_use_start",
        "completion_recovery",
    }:
        return "active"
    status = stream_event.data.get("status")
    return status if isinstance(status, str) else "completed"


def _stream_event_identity(stream_event: LLMStreamEvent) -> tuple[str, str, str]:
    if stream_event.type in {"assistant_note", "assistant_answer"}:
        return ("assistant", "scarlet", "public")
    if stream_event.type == "thinking_captured":
        return ("provider", "llm", "debug")
    return ("provider", "llm", "debug")


def _mind_operation(arguments: dict[str, Any]) -> dict[str, Any]:
    if "command" in arguments:
        return {
            "command": arguments.get("command"),
            "intent": arguments.get("intent"),
        }
    return {
        "method": arguments.get("method"),
        "path": arguments.get("path"),
        "intent": arguments.get("intent"),
    }


def _mind_result_summary(result: dict[str, Any]) -> dict[str, Any]:
    envelope = result if isinstance(result, dict) else {}
    operation_result = envelope.get("result")
    if not isinstance(operation_result, dict):
        operation_result = {}
    error = envelope.get("error")
    summary: dict[str, Any] = {
        "ok": envelope.get("ok"),
        "operation": operation_result.get("operation"),
        "confidence": envelope.get("confidence"),
    }
    if "command" in operation_result:
        summary["command"] = operation_result.get("command")
    if "target" in operation_result:
        summary["target"] = operation_result.get("target")
    for key in (
        "stored",
        "policy_decision",
        "memory_id",
        "count",
        "up_to_date",
        "json_repair_applied",
    ):
        if key in operation_result:
            summary[key] = operation_result[key]
    if isinstance(error, dict):
        summary["error"] = {
            "code": error.get("code"),
            "message": error.get("message"),
            "recoverable": error.get("recoverable"),
        }
    return summary


def _string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None
