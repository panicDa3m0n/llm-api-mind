from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine, inspect

from app.storage.db import init_db
from app.storage.repositories import (
    add_memory,
    add_message,
    add_trace,
    complete_turn,
    create_chat_session,
    create_turn,
    list_memories,
    list_messages,
    list_traces_for_turn,
    mark_memory_used,
)


def make_test_engine():
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def test_init_db_creates_core_tables() -> None:
    engine = make_test_engine()

    init_db(engine)

    table_names = set(inspect(engine).get_table_names())
    assert {
        "sessions",
        "messages",
        "turns",
        "traces",
        "tool_calls",
        "memories",
    }.issubset(table_names)


def test_session_message_turn_and_trace_round_trip() -> None:
    engine = make_test_engine()
    init_db(engine)

    with Session(engine) as db:
        chat_session = create_chat_session(
            db,
            title="Trace experiment",
            metadata={"source": "test"},
        )
        turn = create_turn(db, session_id=chat_session.id, model="MiniMax-M2.7")
        user_message = add_message(
            db,
            session_id=chat_session.id,
            turn_id=turn.id,
            role="user",
            content="hello",
        )
        assistant_message = add_message(
            db,
            session_id=chat_session.id,
            turn_id=turn.id,
            role="assistant",
            content="hi",
            raw_content={"blocks": [{"type": "text", "text": "hi"}]},
        )
        trace = add_trace(
            db,
            session_id=chat_session.id,
            turn_id=turn.id,
            kind="llm.request",
            payload={"model": "MiniMax-M2.7", "input_tokens": 12},
        )
        completed_turn = complete_turn(db, turn_id=turn.id, latency_ms=123)

        messages = list_messages(db, session_id=chat_session.id)
        traces = list_traces_for_turn(db, turn_id=turn.id)

    assert chat_session.id.startswith("ses_")
    assert turn.id.startswith("turn_")
    assert user_message.id.startswith("msg_")
    assert assistant_message.raw_content_json == {
        "blocks": [{"type": "text", "text": "hi"}]
    }
    assert completed_turn.status == "completed"
    assert completed_turn.latency_ms == 123
    assert trace.payload_json["input_tokens"] == 12
    assert [message.role for message in messages] == ["user", "assistant"]
    assert [item.kind for item in traces] == ["llm.request"]


def test_memory_record_round_trip() -> None:
    engine = make_test_engine()
    init_db(engine)

    with Session(engine) as db:
        chat_session = create_chat_session(db, title="Memory test")
        turn = create_turn(db, session_id=chat_session.id, model="MiniMax-M2.7")
        memory = add_memory(
            db,
            memory_type="user_preference",
            scope="project",
            content="The project owner prefers SAL updates with risks and next steps.",
            reason_for_storage="Stable project communication preference.",
            expected_future_use="Shape future status updates.",
            confidence=0.9,
            salience=0.8,
            source_session_id=chat_session.id,
            source_turn_id=turn.id,
            tags=["sal", "communication"],
        )
        memories = list_memories(
            db,
            memory_types=["user_preference"],
            scope="project",
        )
        used = mark_memory_used(db, memory_id=memory.id)

    assert memory.id.startswith("mem_")
    assert [item.id for item in memories] == [memory.id]
    assert memories[0].tags_json == ["sal", "communication"]
    assert used is not None
    assert used.usage_count == 1
    assert used.last_used_at is not None
