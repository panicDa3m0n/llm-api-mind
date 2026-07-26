"""Hybrid live delivery for transient provider frames and durable V2 events."""

from __future__ import annotations

import json
import queue
import threading
from collections.abc import Iterator
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.api.chat_stream_v2 import (
    TERMINAL_EVENT_TYPES,
    ScarletStreamEvent,
    project_stream_event,
)
from app.storage import repositories


SCARLET_LIVE_SCHEMA_VERSION: Literal["scarlet-live-v1"] = "scarlet-live-v1"
TRANSIENT_FRAME_TYPES = {"thinking_delta", "text_delta", "tool_input_delta"}


class ScarletLiveFrame(BaseModel):
    frame_id: str
    frame_type: Literal["thinking_delta", "text_delta", "tool_input_delta"]
    turn_id: str
    model_step: int = Field(ge=1)
    index: int = Field(ge=0)
    payload: dict[str, Any] = Field(default_factory=dict)


class ScarletLiveItem(BaseModel):
    schema_version: Literal["scarlet-live-v1"] = SCARLET_LIVE_SCHEMA_VERSION
    kind: Literal["event", "frame"]
    event: ScarletStreamEvent | None = None
    frame: ScarletLiveFrame | None = None


class LiveTurnFeed:
    """Connection-local feed that never owns or cancels the native turn."""

    def __init__(self) -> None:
        self._active = threading.Event()
        self._active.set()
        self._items: queue.SimpleQueue[str | None] = queue.SimpleQueue()

    def publish(self, line: str) -> None:
        if self._active.is_set():
            self._items.put(line)

    def finish(self) -> None:
        if self._active.is_set():
            self._items.put(None)

    def detach(self) -> None:
        self._active.clear()

    def next_line(self, *, timeout: float) -> str | None:
        return self._items.get(timeout=timeout)


def stream_live_turn_items(
    *,
    feed: LiveTurnFeed,
    engine: Engine,
    session_id: str,
    turn_id: str,
    poll_interval_seconds: float = 0.1,
) -> Iterator[str]:
    """Project one native execution into durable events plus transient frames."""

    emitted_event_ids: set[str] = set()
    cursor = 0
    runner_finished = False
    try:
        while True:
            line: str | None = None
            if not runner_finished:
                try:
                    line = feed.next_line(timeout=poll_interval_seconds)
                except queue.Empty:
                    line = ""
                if line is None:
                    runner_finished = True

            transient_item: ScarletLiveItem | None = None
            if line:
                transient_item = live_item_from_native_line(
                    line,
                    engine=engine,
                    emitted_event_ids=emitted_event_ids,
                )

            target_seq = (
                transient_item.event.seq
                if transient_item is not None
                and transient_item.kind == "event"
                and transient_item.event is not None
                else None
            )
            should_poll = line == "" or runner_finished or target_seq is not None
            turn = None
            if should_poll:
                with Session(engine) as db:
                    persisted = [
                        event
                        for event in repositories.list_events_for_turn(
                            db,
                            turn_id=turn_id,
                        )
                        if event.session_id == session_id
                        and event.seq > cursor
                        and (target_seq is None or event.seq <= target_seq)
                    ]
                    projected = [
                        project_stream_event(db, event) for event in persisted
                    ]
                    turn = repositories.get_turn(db, turn_id)
                for event in projected:
                    cursor = max(cursor, event.seq)
                    emitted_event_ids.add(event.event_id)
                    item = ScarletLiveItem(kind="event", event=event)
                    yield (
                        json.dumps(item.model_dump(mode="json"), ensure_ascii=True)
                        + "\n"
                    )
                    if event.event_type in TERMINAL_EVENT_TYPES:
                        return

            if transient_item is not None and transient_item.kind == "frame":
                yield (
                    json.dumps(
                        transient_item.model_dump(mode="json"),
                        ensure_ascii=True,
                    )
                    + "\n"
                )

            if runner_finished and (
                turn is None or turn.status in {"completed", "failed"}
            ):
                return
    finally:
        feed.detach()


def live_item_from_native_line(
    line: str,
    *,
    engine: Engine,
    emitted_event_ids: set[str] | None = None,
) -> ScarletLiveItem | None:
    """Convert one internal native line without opening full trace payloads."""

    envelope = json.loads(line)
    event_type = envelope.get("type")
    data = envelope.get("data")
    if not isinstance(data, dict):
        return None

    if event_type == "runtime_event":
        raw_event = data.get("event")
        event_id = raw_event.get("id") if isinstance(raw_event, dict) else None
        if not isinstance(event_id, str):
            return None
        if emitted_event_ids is not None:
            if event_id in emitted_event_ids:
                return None
            emitted_event_ids.add(event_id)
        with Session(engine) as db:
            event = repositories.get_event(db, event_id)
            if event is None:
                return None
            projected = project_stream_event(db, event)
        return ScarletLiveItem(kind="event", event=projected)

    if event_type not in TRANSIENT_FRAME_TYPES:
        return None
    turn_id = data.get("turn_id")
    model_step = data.get("model_step")
    index = data.get("index")
    if (
        not isinstance(turn_id, str)
        or not isinstance(model_step, int)
        or model_step < 1
        or not isinstance(index, int)
        or index < 0
    ):
        return None
    payload_key = "partial_json" if event_type == "tool_input_delta" else "text"
    payload_value = data.get(payload_key)
    if not isinstance(payload_value, str) or not payload_value:
        return None
    prefix = {
        "thinking_delta": "thinking",
        "text_delta": "content",
        "tool_input_delta": "tool-input",
    }[event_type]
    return ScarletLiveItem(
        kind="frame",
        frame=ScarletLiveFrame(
            frame_id=f"{prefix}-{turn_id}-{model_step}-{index}",
            frame_type=event_type,
            turn_id=turn_id,
            model_step=model_step,
            index=index,
            payload={payload_key: payload_value},
        ),
    )
