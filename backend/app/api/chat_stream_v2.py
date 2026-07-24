"""Provider-independent streaming and replay contract for API Mind clients."""

from __future__ import annotations

import json
import time
from collections.abc import Iterable, Iterator
from copy import deepcopy
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.api.chat_serialization import message_response
from app.storage import repositories
from app.storage.models import CognitiveEvent


SCARLET_STREAM_SCHEMA_VERSION: Literal["scarlet-stream-v2"] = "scarlet-stream-v2"
TERMINAL_EVENT_TYPES = {"turn.completed", "turn.failed"}
COMMON_CLIENT_PAYLOAD_FIELDS = {
    "operation",
    "model",
    "entrypoint",
    "schema_version",
    "block_count",
    "block_index",
    "searched",
    "selected_count",
    "candidate_count",
    "negative_evidence",
    "mode",
    "model_facing",
    "model_step",
    "index",
    "text",
    "has_text",
    "provider_message_id",
    "stop_reason",
    "answer_disposition",
    "provider_tool_use_id",
    "tool_name",
    "arguments",
    "result_summary",
    "latency_ms",
    "code",
    "message",
    "details",
    "trace_ids",
    "usage",
    "tool_call_count",
    "completion_recovery",
    "stream",
    "reason",
    "status",
    "provider_attempt",
    "next_provider_attempt",
    "provider_attempt_limit",
}


class StreamEventLinks(BaseModel):
    parent_event_id: str | None = None
    trace_id: str | None = None
    tool_call_id: str | None = None
    message_id: str | None = None


class ScarletStreamEvent(BaseModel):
    schema_version: Literal["scarlet-stream-v2"] = SCARLET_STREAM_SCHEMA_VERSION
    event_id: str
    seq: int = Field(ge=1)
    session_id: str
    turn_id: str | None
    event_type: str
    phase: Literal[
        "created", "streaming", "executing", "completed", "persisted", "failed"
    ]
    timestamp: datetime
    visibility: Literal["public", "debug", "private"]
    links: StreamEventLinks = Field(default_factory=StreamEventLinks)
    payload: dict[str, Any] = Field(default_factory=dict)


class StreamReplayCursor(BaseModel):
    requested_after_seq: int = Field(ge=0)
    next_after_seq: int = Field(ge=0)
    latest_seq: int = Field(ge=0)
    has_more: bool


class StreamReplayResponse(BaseModel):
    schema_version: Literal["scarlet-stream-v2"] = SCARLET_STREAM_SCHEMA_VERSION
    session_id: str
    events: list[ScarletStreamEvent]
    cursor: StreamReplayCursor


def project_stream_event(
    db: Session,
    event: CognitiveEvent,
) -> ScarletStreamEvent:
    """Project one persisted runtime event into the stable client contract."""

    payload = _client_payload(event)
    if event.message_id:
        message = repositories.get_message(db, event.message_id)
        if message is not None:
            payload["message"] = message_response(message).model_dump(mode="json")
    if event.type in TERMINAL_EVENT_TYPES and event.turn_id:
        turn = repositories.get_turn(db, event.turn_id)
        if turn is not None:
            payload["turn"] = {
                "id": turn.id,
                "status": turn.status,
                "started_at": turn.started_at.isoformat(),
                "completed_at": (
                    turn.completed_at.isoformat() if turn.completed_at else None
                ),
                "latency_ms": turn.latency_ms,
                "error": turn.error_json,
            }
    return ScarletStreamEvent(
        event_id=event.id,
        seq=event.seq,
        session_id=event.session_id,
        turn_id=event.turn_id,
        event_type=event.type,
        phase=event_phase(event),
        timestamp=event.created_at,
        visibility=event.visibility,
        links={
            "parent_event_id": event.parent_event_id,
            "trace_id": event.trace_id,
            "tool_call_id": event.tool_call_id,
            "message_id": event.message_id,
        },
        payload=payload,
    )


def _client_payload(event: CognitiveEvent) -> dict[str, Any]:
    source = event.payload_json or {}
    payload = {
        key: deepcopy(value)
        for key, value in source.items()
        if key in COMMON_CLIENT_PAYLOAD_FIELDS
    }
    if event.type == "memory.context.built":
        for key in ("selected", "near_miss", "conflicts"):
            value = source.get(key)
            if isinstance(value, list):
                payload[key] = deepcopy(value)
    elif event.type.startswith("metacognitive.context."):
        lessons = source.get("lessons")
        if isinstance(lessons, list):
            payload["lessons"] = deepcopy(lessons)
    return payload


def replay_session_events(
    db: Session,
    *,
    session_id: str,
    after_seq: int,
    limit: int,
) -> StreamReplayResponse:
    """Return one ordered replay page after a durable session cursor."""

    fetched = repositories.list_events_for_session_after_seq(
        db,
        session_id=session_id,
        after_seq=after_seq,
        limit=limit + 1,
    )
    page = fetched[:limit]
    latest_seq = repositories.latest_event_seq(db, session_id=session_id)
    next_after_seq = page[-1].seq if page else after_seq
    return StreamReplayResponse(
        session_id=session_id,
        events=[project_stream_event(db, event) for event in page],
        cursor=StreamReplayCursor(
            requested_after_seq=after_seq,
            next_after_seq=next_after_seq,
            latest_seq=latest_seq,
            has_more=len(fetched) > limit or next_after_seq < latest_seq,
        ),
    )


def stream_v2_from_native_lines(
    lines: Iterable[str],
    *,
    engine: Engine,
) -> Iterator[str]:
    """Expose only persisted canonical events from the legacy live generator."""

    emitted_ids: set[str] = set()
    for line in lines:
        envelope = json.loads(line)
        if envelope.get("type") != "runtime_event":
            continue
        data = envelope.get("data")
        raw_event = data.get("event") if isinstance(data, dict) else None
        event_id = raw_event.get("id") if isinstance(raw_event, dict) else None
        if not isinstance(event_id, str) or event_id in emitted_ids:
            continue
        with Session(engine) as db:
            event = repositories.get_event(db, event_id)
            if event is None:
                continue
            projected = project_stream_event(db, event)
        emitted_ids.add(event_id)
        yield json.dumps(projected.model_dump(mode="json"), ensure_ascii=True) + "\n"


def stream_persisted_turn_events(
    *,
    engine: Engine,
    session_id: str,
    turn_id: str,
    after_seq: int = 0,
    poll_interval_seconds: float = 0.1,
) -> Iterator[str]:
    """Follow one turn from durable events and allow cursor-based reconnection."""

    cursor = after_seq
    while True:
        with Session(engine) as db:
            events = [
                event
                for event in repositories.list_events_for_turn(db, turn_id=turn_id)
                if event.session_id == session_id and event.seq > cursor
            ]
            projected = [project_stream_event(db, event) for event in events]
            turn = repositories.get_turn(db, turn_id)
        for event in projected:
            cursor = max(cursor, event.seq)
            yield json.dumps(event.model_dump(mode="json"), ensure_ascii=True) + "\n"
            if event.event_type in TERMINAL_EVENT_TYPES:
                return
        if turn is None or turn.status in {"completed", "failed"}:
            return
        time.sleep(poll_interval_seconds)


def reduce_stream_events(
    events: Iterable[ScarletStreamEvent | dict[str, Any]],
    *,
    cursor_seq: int = 0,
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Reference idempotent reducer for session-global stream events.

    Events beyond a sequence gap remain pending. Replaying from the last
    applied cursor fills the gap without duplicating already seen event ids.
    """

    if state is not None:
        cursor_seq = int(state.get("cursor_seq", cursor_seq))
    turns = deepcopy(state.get("turns", {})) if state is not None else {}
    applied_event_ids = (
        list(state.get("applied_event_ids", [])) if state is not None else []
    )
    fingerprints = (
        dict(state.get("event_fingerprints", {})) if state is not None else {}
    )
    conflicting_event_ids = (
        list(state.get("conflicting_event_ids", [])) if state is not None else []
    )
    sequence_conflicts = (
        list(state.get("sequence_conflicts", [])) if state is not None else []
    )
    by_id: dict[str, ScarletStreamEvent] = {}
    if state is not None:
        for item in state.get("pending_events", []):
            pending_event = ScarletStreamEvent.model_validate(item)
            by_id[pending_event.event_id] = pending_event

    for item in events:
        event = (
            item
            if isinstance(item, ScarletStreamEvent)
            else ScarletStreamEvent.model_validate(item)
        )
        fingerprint = _event_fingerprint(event)
        existing_fingerprint = fingerprints.get(event.event_id)
        if existing_fingerprint is not None:
            if existing_fingerprint != fingerprint:
                conflicting_event_ids.append(event.event_id)
            continue
        fingerprints[event.event_id] = fingerprint
        existing = by_id.setdefault(event.event_id, event)
        if existing.model_dump(mode="json") != event.model_dump(mode="json"):
            conflicting_event_ids.append(event.event_id)

    ordered = sorted(by_id.values(), key=lambda item: (item.seq, item.event_id))
    expected_seq = cursor_seq + 1
    pending: list[ScarletStreamEvent] = []
    newly_applied: list[ScarletStreamEvent] = []

    for event in ordered:
        if event.seq < expected_seq:
            sequence_conflicts.append(event.seq)
            continue
        if event.seq > expected_seq:
            pending.append(event)
            continue
        newly_applied.append(event)
        applied_event_ids.append(event.event_id)
        expected_seq += 1
        _apply_turn_event(turns, event)

    missing_ranges = _missing_ranges(
        start=expected_seq,
        observed=sorted({event.seq for event in pending}),
    )
    return {
        "schema_version": SCARLET_STREAM_SCHEMA_VERSION,
        "cursor_seq": newly_applied[-1].seq if newly_applied else cursor_seq,
        "next_expected_seq": expected_seq,
        "applied_event_ids": applied_event_ids,
        "pending_event_ids": [event.event_id for event in pending],
        "pending_events": [event.model_dump(mode="json") for event in pending],
        "missing_seq_ranges": missing_ranges,
        "conflicting_event_ids": sorted(set(conflicting_event_ids)),
        "sequence_conflicts": sorted(set(sequence_conflicts)),
        "event_fingerprints": fingerprints,
        "turns": turns,
    }


def event_phase(
    event: CognitiveEvent,
) -> Literal["created", "streaming", "executing", "completed", "persisted", "failed"]:
    if event.type == "turn.started":
        return "created"
    if event.type.endswith(".failed") or event.status == "failed":
        return "failed"
    if event.type.endswith(".persisted"):
        return "persisted"
    if event.type.endswith(".started") or event.status == "active":
        if event.type.startswith("mind.tool_call"):
            return "executing"
        return "streaming"
    return "completed"


def _apply_turn_event(
    turns: dict[str, dict[str, Any]],
    event: ScarletStreamEvent,
) -> None:
    if event.turn_id is None:
        return
    state = turns.setdefault(
        event.turn_id,
        {
            "status": "active",
            "terminal": False,
            "user_message": None,
            "assistant_message": None,
            "notes": [],
            "answer": None,
            "tools": {},
            "error": None,
            "event_ids": [],
        },
    )
    state["event_ids"].append(event.event_id)
    message = event.payload.get("message")
    if event.event_type == "message.user.persisted" and isinstance(message, dict):
        state["user_message"] = message
    elif event.event_type == "message.assistant.persisted" and isinstance(
        message, dict
    ):
        state["assistant_message"] = message
    elif event.event_type == "assistant.note.emitted":
        state["notes"].append(
            {"event_id": event.event_id, "text": event.payload.get("text", "")}
        )
    elif event.event_type == "assistant.answer.completed":
        state["answer"] = event.payload.get("text")
    elif event.event_type.startswith("mind.tool_call."):
        tool_key = str(
            event.payload.get("provider_tool_use_id")
            or event.payload.get("tool_call_id")
            or event.event_id
        )
        tool_state = state["tools"].setdefault(tool_key, {})
        tool_state.update(event.payload)
        tool_state["event_id"] = event.event_id
        tool_state["phase"] = event.phase
    elif event.event_type == "turn.failed":
        state["status"] = "failed"
        state["terminal"] = True
        state["error"] = {
            "code": event.payload.get("code"),
            "message": event.payload.get("message"),
            "details": event.payload.get("details"),
        }
    elif event.event_type == "turn.completed":
        state["status"] = "completed"
        state["terminal"] = True


def _missing_ranges(*, start: int, observed: list[int]) -> list[dict[str, int]]:
    if not observed or observed[0] <= start:
        return []
    return [{"start": start, "end": observed[0] - 1}]


def _event_fingerprint(event: ScarletStreamEvent) -> str:
    return json.dumps(
        event.model_dump(mode="json"),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
