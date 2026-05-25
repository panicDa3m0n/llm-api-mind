from datetime import timedelta

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine, inspect

from app.storage.db import init_db
from app.storage.repositories import (
    add_event,
    add_memory,
    add_memory_fact,
    add_message,
    add_trace,
    complete_turn,
    create_chat_session,
    create_turn,
    get_session_summary,
    list_memory_facts,
    list_memories,
    list_messages,
    list_events_for_turn,
    list_due_maintenance_jobs,
    list_traces_for_turn,
    mark_memory_used,
    schedule_session_maintenance_job,
    start_maintenance_job,
    complete_maintenance_job,
    upsert_session_summary,
)
from app.storage.models import utc_now


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
        "events",
        "tool_calls",
        "memories",
        "memory_facts",
        "session_summaries",
        "maintenance_jobs",
        "search_documents_fts",
    }.issubset(table_names)
    session_columns = {
        column["name"] for column in inspect(engine).get_columns("sessions")
    }
    assert "provider_history_json" in session_columns


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
        event = add_event(
            db,
            session_id=chat_session.id,
            turn_id=turn.id,
            event_type="llm.request.created",
            payload={"trace_id": trace.id, "model": "MiniMax-M2.7"},
            trace_id=trace.id,
        )
        completed_turn = complete_turn(db, turn_id=turn.id, latency_ms=123)

        messages = list_messages(db, session_id=chat_session.id)
        traces = list_traces_for_turn(db, turn_id=turn.id)
        events = list_events_for_turn(db, turn_id=turn.id)

    assert chat_session.id.startswith("ses_")
    assert chat_session.provider_history_json == []
    assert turn.id.startswith("turn_")
    assert user_message.id.startswith("msg_")
    assert assistant_message.raw_content_json == {
        "blocks": [{"type": "text", "text": "hi"}]
    }
    assert completed_turn.status == "completed"
    assert completed_turn.latency_ms == 123
    assert trace.payload_json["input_tokens"] == 12
    assert event.id.startswith("evt_")
    assert [message.role for message in messages] == ["user", "assistant"]
    assert [item.kind for item in traces] == ["llm.request"]
    assert [item.type for item in events] == ["llm.request.created"]
    assert events[0].seq == 1
    assert events[0].trace_id == trace.id


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


def test_memory_fact_round_trip() -> None:
    engine = make_test_engine()
    init_db(engine)

    with Session(engine) as db:
        chat_session = create_chat_session(db, title="Memory fact test")
        turn = create_turn(db, session_id=chat_session.id, model="MiniMax-M2.7")
        memory = add_memory(
            db,
            memory_type="user_preference",
            scope="project",
            content="Protocollo Zero-Luce uses Contesto, Evidenza, Rischio.",
            reason_for_storage="Stable response format.",
            source_session_id=chat_session.id,
            source_turn_id=turn.id,
        )
        fact = add_memory_fact(
            db,
            memory_id=memory.id,
            entity="protocollo-zero-luce",
            predicate="response_format",
            value={"kind": "ordered_blocks", "blocks": ["Contesto", "Evidenza"]},
            source_session_id=chat_session.id,
            source_turn_id=turn.id,
            confidence=0.9,
            salience=0.8,
            metadata={"aliases": ["zero light protocol"]},
        )
        facts = list_memory_facts(
            db,
            entity="protocollo-zero-luce",
            predicate="response_format",
        )

    assert fact.id.startswith("fact_")
    assert [item.id for item in facts] == [fact.id]
    assert facts[0].metadata_json["aliases"] == ["zero light protocol"]


def test_session_summary_round_trip() -> None:
    engine = make_test_engine()
    init_db(engine)

    with Session(engine) as db:
        chat_session = create_chat_session(db, title="Episodic test")
        turn = create_turn(db, session_id=chat_session.id, model="MiniMax-M2.7")
        first = add_message(
            db,
            session_id=chat_session.id,
            turn_id=turn.id,
            role="user",
            content="We discussed episodic recall.",
        )
        second = add_message(
            db,
            session_id=chat_session.id,
            turn_id=turn.id,
            role="assistant",
            content="I will preserve the session summary as navigation.",
        )
        session_summary = upsert_session_summary(
            db,
            session_id=chat_session.id,
            summary="Discussion about episodic recall and session summaries.",
            topics=["episodic recall"],
            decisions=["Keep summaries separate from semantic memory."],
            open_questions=["How often should summaries refresh?"],
            memory_ids=["mem_example"],
            message_count=2,
            source_turn_count=1,
            last_message_id=second.id,
            metadata={"summary_source": "test"},
        )
        first_id = first.id
        second_id = second.id
        session_summary_id = session_summary.id
        fetched = get_session_summary(db, session_id=chat_session.id)
        assert fetched is not None
        fetched_summary = fetched.summary
        fetched_topics = fetched.topics_json
        fetched_decisions = fetched.decisions_json
        fetched_open_questions = fetched.open_questions_json
        fetched_memory_ids = fetched.memory_ids_json
        fetched_last_message_id = fetched.last_message_id
        fetched_metadata = fetched.metadata_json

    assert first_id.startswith("msg_")
    assert session_summary_id.startswith("ses_sum_")
    assert fetched_summary == "Discussion about episodic recall and session summaries."
    assert fetched_topics == ["episodic recall"]
    assert fetched_decisions == ["Keep summaries separate from semantic memory."]
    assert fetched_open_questions == ["How often should summaries refresh?"]
    assert fetched_memory_ids == ["mem_example"]
    assert fetched_last_message_id == second_id
    assert fetched_metadata["summary_source"] == "test"


def test_maintenance_job_round_trip_and_supersede() -> None:
    engine = make_test_engine()
    init_db(engine)

    with Session(engine) as db:
        chat_session = create_chat_session(db, title="Maintenance test")
        first_turn = create_turn(db, session_id=chat_session.id, model="MiniMax-M2.7")
        first_job, first_superseded = schedule_session_maintenance_job(
            db,
            kind="session.idle_maintenance",
            session_id=chat_session.id,
            trigger_turn_id=first_turn.id,
            trigger_event_id=None,
            due_at=utc_now() + timedelta(seconds=60),
            input_payload={"idle_seconds": 60},
        )
        second_turn = create_turn(db, session_id=chat_session.id, model="MiniMax-M2.7")
        second_job, superseded = schedule_session_maintenance_job(
            db,
            kind="session.idle_maintenance",
            session_id=chat_session.id,
            trigger_turn_id=second_turn.id,
            trigger_event_id=None,
            due_at=utc_now() - timedelta(seconds=1),
            input_payload={"idle_seconds": 60},
        )
        due_jobs = list_due_maintenance_jobs(db, now=utc_now(), limit=10)
        started = start_maintenance_job(db, job_id=second_job.id)
        assert started is not None
        started_status = started.status
        completed = complete_maintenance_job(
            db,
            job_id=second_job.id,
            status="completed",
            result={"ok": True},
        )
        first_job_id = first_job.id
        second_job_id = second_job.id
        superseded_ids = [job.id for job in superseded]
        superseded_statuses = [job.status for job in superseded]
        superseded_replacements = [job.superseded_by_job_id for job in superseded]
        due_job_ids = [job.id for job in due_jobs]
        completed_status = completed.status
        completed_result = completed.result_json

    assert first_superseded == []
    assert first_job_id.startswith("mnt_")
    assert superseded_ids == [first_job_id]
    assert superseded_statuses == ["superseded"]
    assert superseded_replacements == [second_job_id]
    assert due_job_ids == [second_job_id]
    assert started_status == "running"
    assert completed_status == "completed"
    assert completed_result == {"ok": True}
