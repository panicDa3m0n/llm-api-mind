"""Public response models and event payload projections for chat transports."""

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.api.chat_provider_history import valid_content_blocks
from app.llm.provider import LLMTextResult
from app.runtime.events import event_payload
from app.storage.models import ChatSession, CognitiveEvent, Message, Trace


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


def ndjson(event_type: str, data: dict[str, Any]) -> str:
    return json.dumps({"type": event_type, "data": data}, ensure_ascii=True) + "\n"


def response_event_messages(result: LLMTextResult) -> list[dict[str, Any]]:
    if result.raw_provider_messages:
        return result.raw_provider_messages

    raw_content = valid_content_blocks(result.raw_content)
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


def incomplete_result_details(result: LLMTextResult) -> dict[str, Any]:
    raw_types = [
        block.get("type")
        for block in valid_content_blocks(result.raw_content)
        if isinstance(block.get("type"), str)
    ]
    return {
        "reason": "empty_terminal_result",
        "stop_reason": result.stop_reason,
        "provider_message_id": result.provider_message_id,
        "raw_content_types": raw_types,
        "tool_call_count": len(result.tool_calls),
        "completion_recovery": result.completion_recovery,
    }


def session_response(chat_session: ChatSession) -> ChatSessionResponse:
    return ChatSessionResponse(
        id=chat_session.id,
        title=chat_session.title,
        created_at=chat_session.created_at,
        updated_at=chat_session.updated_at,
        metadata=chat_session.metadata_json,
    )


def message_response(message: Message) -> ChatMessageResponse:
    return ChatMessageResponse(
        id=message.id,
        session_id=message.session_id,
        turn_id=message.turn_id,
        role=message.role,
        content=message.content,
        created_at=message.created_at,
        metadata=message.metadata_json,
    )


def trace_response(trace: Trace) -> TraceResponse:
    return TraceResponse(
        id=trace.id,
        session_id=trace.session_id,
        turn_id=trace.turn_id,
        kind=trace.kind,
        payload=trace.payload_json,
        created_at=trace.created_at,
    )


def event_response(event: CognitiveEvent) -> EventResponse:
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


def event_stream_payload(event: CognitiveEvent) -> dict[str, Any]:
    return event_response(event).model_dump(mode="json")


def memory_context_event_payload(memory_context: dict[str, Any]) -> dict[str, Any]:
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


def metacognitive_context_event_payload(
    metacognitive_context: dict[str, Any],
) -> dict[str, Any]:
    return {
        "operation": metacognitive_context.get("operation"),
        "trace_id": metacognitive_context.get("trace_id"),
        "schema_version": metacognitive_context.get("schema_version"),
        "mode": metacognitive_context.get("mode"),
        "model_facing": metacognitive_context.get("model_facing"),
        "selection": metacognitive_context.get("selection", {}),
        "triggers": metacognitive_context.get("triggers", []),
        "lessons": metacognitive_context.get("lessons", []),
        "runtime_inputs": metacognitive_context.get("runtime_inputs", {}),
        "policy": metacognitive_context.get("policy", {}),
    }


def runtime_context_event_payload(runtime_context: dict[str, Any]) -> dict[str, Any]:
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
