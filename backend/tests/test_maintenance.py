import json

from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from app.config import Settings
from app.llm.provider import LLMTextResult
from app.runtime.maintenance import (
    run_due_maintenance_jobs,
    schedule_session_idle_maintenance,
)
from app.storage import repositories
from app.storage.db import init_db
from app.storage.models import utc_now


class FakeMaintenanceProvider:
    calls: list[dict[str, str | None]] = []

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate_text(
        self,
        *,
        prompt: str,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMTextResult:
        self.__class__.calls.append({"prompt": prompt, "system": system})
        if system and "episodic memory" in system:
            text = json.dumps(
                {
                    "summary": "The session discussed a durable food preference.",
                    "topics": ["memory", "personal preference"],
                    "decisions": [],
                    "open_questions": [],
                    "notable_context": [
                        "The user said they like chocolate but feel bad if they eat too much."
                    ],
                }
            )
            provider_message_id = "summary_msg"
        else:
            text = json.dumps(
                {
                    "summary": "One possible semantic memory was missed.",
                    "candidate_count": 1,
                    "candidates": [
                        {
                            "type": "user_preference",
                            "scope": "user",
                            "content": (
                                "The user likes chocolate but feels bad if they "
                                "eat too much."
                            ),
                            "reason_for_storage": "Future food recommendations.",
                            "expected_future_use": "Avoid over-recommending chocolate.",
                            "confidence": 0.9,
                            "salience": 0.8,
                            "tags": [
                                "personal-fact",
                                "food-preference",
                                "health-constraint",
                            ],
                            "evidence": "User stated the fact directly.",
                            "write_recommended": True,
                        }
                    ],
                    "skipped_reason": None,
                }
            )
            provider_message_id = "review_msg"
        return LLMTextResult(
            model=self.settings.minimax_model,
            text=text,
            usage={"input_tokens": 10, "output_tokens": 20},
            provider_message_id=provider_message_id,
            stop_reason="end_turn",
        )


def make_test_engine() -> Engine:
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def make_settings() -> Settings:
    return Settings(
        environment="test",
        minimax_api_key="test-key",
        minimax_model="MiniMax-M2.7",
        minimax_max_tokens=4096,
        maintenance_idle_seconds=0,
        maintenance_worker_interval_seconds=0.01,
    )


def test_due_idle_maintenance_summarizes_and_reviews_memory_candidates() -> None:
    engine = make_test_engine()
    init_db(engine)
    settings = make_settings()
    FakeMaintenanceProvider.calls = []

    with Session(engine) as db:
        chat_session = repositories.create_chat_session(db, title="Idle maintenance")
        turn = repositories.create_turn(
            db,
            session_id=chat_session.id,
            model=settings.minimax_model,
        )
        repositories.add_message(
            db,
            session_id=chat_session.id,
            turn_id=turn.id,
            role="user",
            content="Mi piace il cioccolato, ma se ne mangio troppo sto male.",
        )
        repositories.add_message(
            db,
            session_id=chat_session.id,
            turn_id=turn.id,
            role="assistant",
            content="Lo terrò presente quando parliamo di dolci.",
        )
        completed = repositories.complete_turn(db, turn_id=turn.id)
        turn_event = repositories.add_event(
            db,
            session_id=chat_session.id,
            turn_id=turn.id,
            event_type="turn.completed",
            status=completed.status,
        )
        job, scheduled_event = schedule_session_idle_maintenance(
            db,
            settings=settings,
            session_id=chat_session.id,
            trigger_turn_id=turn.id,
            trigger_event_id=turn_event.id,
        )
        session_id = chat_session.id
        turn_id = turn.id
        job_id = job.id
        scheduled_event_type = scheduled_event.type

    results = run_due_maintenance_jobs(
        engine,
        settings=settings,
        provider_factory=FakeMaintenanceProvider,
        now=utc_now(),
    )

    with Session(engine) as db:
        summary = repositories.get_session_summary(db, session_id=session_id)
        traces = repositories.list_traces_for_session(
            db,
            session_id=session_id,
            limit=20,
        )
        events = repositories.list_events_for_turn(db, turn_id=turn_id)
        completed_job = repositories.get_maintenance_job(db, job_id)

    assert scheduled_event_type == "maintenance.job.scheduled"
    assert len(results) == 1
    assert results[0]["status"] == "completed"
    assert completed_job is not None
    assert completed_job.status == "completed"
    assert summary is not None
    assert summary.summary == "The session discussed a durable food preference."
    assert [trace.kind for trace in traces] == [
        "maintenance.memory_review",
        "mind.sessions.summarize",
    ]
    event_types = [event.type for event in events]
    assert "maintenance.job.started" in event_types
    assert "maintenance.memory_review.completed" in event_types
    assert event_types[-1] == "maintenance.job.completed"
    review_trace = traces[0]
    assert review_trace.payload_json["mode"] == "report_only"
    assert (
        review_trace.payload_json["review"]["candidates"][0]["content"]
        == "The user likes chocolate but feels bad if they eat too much."
    )
    assert len(FakeMaintenanceProvider.calls) == 2


def test_idle_maintenance_skips_when_a_newer_turn_exists() -> None:
    engine = make_test_engine()
    init_db(engine)
    settings = make_settings()
    FakeMaintenanceProvider.calls = []

    with Session(engine) as db:
        chat_session = repositories.create_chat_session(db, title="Skip maintenance")
        first_turn = repositories.create_turn(
            db,
            session_id=chat_session.id,
            model=settings.minimax_model,
        )
        repositories.complete_turn(db, turn_id=first_turn.id)
        job, _ = schedule_session_idle_maintenance(
            db,
            settings=settings,
            session_id=chat_session.id,
            trigger_turn_id=first_turn.id,
            trigger_event_id=None,
        )
        first_turn_id = first_turn.id
        job_id = job.id
        second_turn = repositories.create_turn(
            db,
            session_id=chat_session.id,
            model=settings.minimax_model,
        )
        repositories.complete_turn(db, turn_id=second_turn.id)

    results = run_due_maintenance_jobs(
        engine,
        settings=settings,
        provider_factory=FakeMaintenanceProvider,
        now=utc_now(),
    )

    with Session(engine) as db:
        skipped_job = repositories.get_maintenance_job(db, job_id)
        events = repositories.list_events_for_turn(db, turn_id=first_turn_id)

    assert len(results) == 1
    assert results[0]["status"] == "skipped"
    assert results[0]["result"]["reason"] == "newer_turn_exists"
    assert skipped_job is not None
    assert skipped_job.status == "skipped"
    assert [event.type for event in events][-1] == "maintenance.job.skipped"
    assert FakeMaintenanceProvider.calls == []
