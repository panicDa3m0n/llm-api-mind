from app.api.chat_stream_v2 import ScarletStreamEvent, reduce_stream_events


def _event(
    seq: int,
    event_type: str,
    *,
    event_id: str | None = None,
    payload: dict | None = None,
) -> ScarletStreamEvent:
    return ScarletStreamEvent(
        event_id=event_id or f"evt_{seq}",
        seq=seq,
        session_id="ses_stream",
        turn_id="turn_stream",
        event_type=event_type,
        phase="completed",
        timestamp="2026-07-19T12:00:00+00:00",
        visibility="public",
        links={},
        payload=payload or {},
    )


def test_reference_reducer_is_order_independent_and_idempotent() -> None:
    started = _event(1, "turn.started")
    user = _event(
        2,
        "message.user.persisted",
        payload={"message": {"id": "msg_user", "content": "Ciao"}},
    )
    note = _event(3, "assistant.note.emitted", payload={"text": "Controllo."})
    tool_started = _event(
        4,
        "mind.tool_call.started",
        payload={"provider_tool_use_id": "toolu_1", "command": "help"},
    )
    tool_completed = _event(
        5,
        "mind.tool_call.completed",
        payload={"provider_tool_use_id": "toolu_1", "result_summary": {"ok": True}},
    )
    answer = _event(6, "assistant.answer.completed", payload={"text": "Fatto."})
    assistant = _event(
        7,
        "message.assistant.persisted",
        payload={"message": {"id": "msg_assistant", "content": "Fatto."}},
    )
    completed = _event(8, "turn.completed")

    result = reduce_stream_events(
        [completed, tool_completed, note, started, answer, user, tool_started, assistant, note]
    )

    assert result["cursor_seq"] == 8
    assert result["pending_event_ids"] == []
    assert result["missing_seq_ranges"] == []
    assert result["conflicting_event_ids"] == []
    state = result["turns"]["turn_stream"]
    assert state["status"] == "completed"
    assert state["terminal"] is True
    assert state["user_message"]["content"] == "Ciao"
    assert state["assistant_message"]["content"] == "Fatto."
    assert state["notes"] == [{"event_id": "evt_3", "text": "Controllo."}]
    assert state["answer"] == "Fatto."
    assert state["tools"]["toolu_1"]["phase"] == "completed"


def test_reference_reducer_holds_events_after_a_gap_for_replay() -> None:
    result = reduce_stream_events(
        [_event(11, "turn.started"), _event(13, "turn.completed")],
        cursor_seq=10,
    )

    assert result["cursor_seq"] == 11
    assert result["next_expected_seq"] == 12
    assert result["pending_event_ids"] == ["evt_13"]
    assert result["missing_seq_ranges"] == [{"start": 12, "end": 12}]
    assert result["turns"]["turn_stream"]["terminal"] is False

    replayed = reduce_stream_events(
        [_event(12, "assistant.answer.completed", payload={"text": "Ok"})],
        state=result,
    )
    assert replayed["cursor_seq"] == 13
    assert replayed["missing_seq_ranges"] == []
    assert replayed["turns"]["turn_stream"]["terminal"] is True

    duplicate_replay = reduce_stream_events(
        [_event(12, "assistant.answer.completed", payload={"text": "Ok"})],
        state=replayed,
    )
    assert duplicate_replay["cursor_seq"] == 13
    assert duplicate_replay["turns"] == replayed["turns"]


def test_reference_reducer_reports_conflicting_duplicate_ids() -> None:
    original = _event(1, "turn.started", event_id="evt_same")
    conflicting = _event(1, "turn.failed", event_id="evt_same")

    result = reduce_stream_events([original, conflicting])

    assert result["conflicting_event_ids"] == ["evt_same"]
    assert result["cursor_seq"] == 1
