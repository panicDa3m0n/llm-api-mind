import json

from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from app.config import Settings
from app.llm.provider import LLMTextResult
from app.mind.memory import (
    MindAPIContext,
    create_memory_proposal_from_review_candidate,
)
from app.runtime.maintenance import (
    run_due_maintenance_jobs,
    schedule_session_idle_maintenance,
)
from app.storage import repositories
from app.storage.db import init_db
from app.storage.models import utc_now


class FakeMaintenanceProvider:
    calls: list[dict[str, str | None]] = []
    memory_review_candidates: list[dict] | None = None
    resolver_decisions: list[dict] | None = None

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
        elif system and "resolve Scarlet memory maintenance proposals" in system:
            decisions = self.__class__.resolver_decisions or [
                {
                    "proposal_id": "prop_missing",
                    "outcome": "keep_pending",
                    "reason": "Default fake resolver decision.",
                    "confidence": 0.0,
                }
            ]
            if any(item.get("proposal_id") == "__first__" for item in decisions):
                prompt_payload = json.loads(prompt)
                first_id = prompt_payload["proposals"][0]["id"]
                decisions = [
                    {
                        **item,
                        "proposal_id": first_id
                        if item.get("proposal_id") == "__first__"
                        else item.get("proposal_id"),
                    }
                    for item in decisions
                ]
            text = json.dumps(
                {
                    "summary": "Resolver kept the candidate pending.",
                    "decisions": decisions,
                }
            )
            provider_message_id = "resolver_msg"
        else:
            candidates = self.__class__.memory_review_candidates
            if candidates is None:
                candidates = [
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
                ]
            text = json.dumps(
                {
                    "summary": "One possible semantic memory was missed.",
                    "candidate_count": len(candidates),
                    "candidates": candidates,
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
    FakeMaintenanceProvider.memory_review_candidates = None
    FakeMaintenanceProvider.resolver_decisions = None

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
        proposals = repositories.list_memory_proposals(
            db,
            source_session_id=session_id,
            status="pending_review",
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
    trace_kinds = [trace.kind for trace in traces]
    assert "maintenance.memory_review" in trace_kinds
    assert "maintenance.memory_proposal_resolution" in trace_kinds
    assert "mind.sessions.summarize" in trace_kinds
    event_types = [event.type for event in events]
    assert "maintenance.job.started" in event_types
    assert "maintenance.memory_review.completed" in event_types
    assert event_types[-1] == "maintenance.job.completed"
    review_trace = next(trace for trace in traces if trace.kind == "maintenance.memory_review")
    assert review_trace.payload_json["mode"] == "proposal_pipeline"
    assert (
        review_trace.payload_json["review"]["candidates"][0]["content"]
        == "The user likes chocolate but feels bad if they eat too much."
    )
    assert len(proposals) == 1
    assert proposals[0].content == "The user likes chocolate but feels bad if they eat too much."
    assert proposals[0].proposed_action == "create_new"
    assert proposals[0].status == "pending_review"
    assert proposals[0].result_json["resolution"]["outcome"] == "keep_pending"
    completed_event = next(
        event for event in events if event.type == "maintenance.memory_review.completed"
    )
    assert completed_event.payload_json["proposal_count"] == 1
    assert completed_event.payload_json["proposal_created_count"] == 1
    assert completed_event.payload_json["resolution"]["resolver_called"] is True
    assert len(FakeMaintenanceProvider.calls) == 3


def test_idle_maintenance_safely_applies_high_confidence_create_candidate() -> None:
    engine = make_test_engine()
    init_db(engine)
    settings = make_settings()
    FakeMaintenanceProvider.calls = []
    FakeMaintenanceProvider.memory_review_candidates = [
        {
            "type": "user_preference",
            "scope": "user",
            "content": "The user prefers mint tea during late work sessions.",
            "reason_for_storage": "Useful future drink preference.",
            "expected_future_use": "Suggest non-caffeinated drinks during late work.",
            "confidence": 0.98,
            "salience": 0.95,
            "tags": ["personal-fact", "drink-preference"],
            "evidence": "User stated this preference directly.",
            "write_recommended": True,
        }
    ]
    FakeMaintenanceProvider.resolver_decisions = None

    with Session(engine) as db:
        chat_session = repositories.create_chat_session(db, title="Safe apply")
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
            content="Durante le sessioni serali preferisco il te alla menta.",
        )
        repositories.add_message(
            db,
            session_id=chat_session.id,
            turn_id=turn.id,
            role="assistant",
            content="Ricevuto.",
        )
        repositories.complete_turn(db, turn_id=turn.id)
        job, _ = schedule_session_idle_maintenance(
            db,
            settings=settings,
            session_id=chat_session.id,
            trigger_turn_id=turn.id,
            trigger_event_id=None,
        )
        session_id = chat_session.id
        job_id = job.id

    run_due_maintenance_jobs(
        engine,
        settings=settings,
        provider_factory=FakeMaintenanceProvider,
        now=utc_now(),
    )

    with Session(engine) as db:
        proposals = repositories.list_memory_proposals(
            db,
            source_session_id=session_id,
            status="applied_create",
        )
        memories = repositories.list_memories_for_session(db, session_id=session_id)
        completed_job = repositories.get_maintenance_job(db, job_id)

    assert completed_job is not None
    assert completed_job.status == "completed"
    assert len(proposals) == 1
    assert proposals[0].result_json["resolution"]["resolver"] == "deterministic_preflight"
    assert proposals[0].result_json["memory_result"]["memory_id"] == memories[0].id
    assert memories[0].created_by == "maintenance"
    assert memories[0].content == "The user prefers mint tea during late work sessions."
    assert len(FakeMaintenanceProvider.calls) == 2


def test_idle_maintenance_archives_exact_duplicate_without_resolver_call() -> None:
    engine = make_test_engine()
    init_db(engine)
    settings = make_settings()
    FakeMaintenanceProvider.calls = []
    FakeMaintenanceProvider.memory_review_candidates = [
        {
            "type": "user_preference",
            "scope": "user",
            "content": "The user likes chocolate but feels bad if they eat too much.",
            "reason_for_storage": "Future food recommendations.",
            "expected_future_use": "Avoid over-recommending chocolate.",
            "confidence": 0.9,
            "salience": 0.8,
            "tags": ["personal-fact", "food-preference"],
            "evidence": "User stated this fact directly.",
            "write_recommended": True,
        }
    ]
    FakeMaintenanceProvider.resolver_decisions = None

    with Session(engine) as db:
        chat_session = repositories.create_chat_session(db, title="Duplicate idle")
        turn = repositories.create_turn(
            db,
            session_id=chat_session.id,
            model=settings.minimax_model,
        )
        existing = repositories.add_memory(
            db,
            memory_type="user_preference",
            scope="user",
            content="The user likes chocolate but feels bad if they eat too much.",
            reason_for_storage="Future food recommendations.",
            expected_future_use="Avoid over-recommending chocolate.",
            confidence=0.9,
            salience=0.8,
            source_session_id=chat_session.id,
            source_turn_id=turn.id,
            tags=["personal-fact", "food-preference"],
        )
        repositories.add_message(
            db,
            session_id=chat_session.id,
            turn_id=turn.id,
            role="user",
            content="Ti ricordo che amo il cioccolato ma troppo mi fa stare male.",
        )
        repositories.complete_turn(db, turn_id=turn.id)
        schedule_session_idle_maintenance(
            db,
            settings=settings,
            session_id=chat_session.id,
            trigger_turn_id=turn.id,
            trigger_event_id=None,
        )
        session_id = chat_session.id
        existing_id = existing.id

    run_due_maintenance_jobs(
        engine,
        settings=settings,
        provider_factory=FakeMaintenanceProvider,
        now=utc_now(),
    )

    with Session(engine) as db:
        proposals = repositories.list_memory_proposals(
            db,
            source_session_id=session_id,
            status="archived_noop_duplicate",
        )
        memories = repositories.list_memories_for_session(db, session_id=session_id)

    assert len(proposals) == 1
    assert proposals[0].similar_memory_ids_json[0] == existing_id
    assert proposals[0].result_json["resolution"]["outcome"] == "noop_duplicate"
    assert [memory.id for memory in memories] == [existing_id]
    assert len(FakeMaintenanceProvider.calls) == 2


def test_idle_maintenance_llm_resolver_can_apply_cautious_create_candidate() -> None:
    engine = make_test_engine()
    init_db(engine)
    settings = make_settings()
    FakeMaintenanceProvider.calls = []
    FakeMaintenanceProvider.memory_review_candidates = [
        {
            "type": "task_context",
            "scope": "project",
            "content": "The project owner wants Dream review kept as a future evolution.",
            "reason_for_storage": "Useful project direction.",
            "expected_future_use": "Avoid implementing Dream during current maintenance work.",
            "confidence": 0.9,
            "salience": 0.8,
            "tags": ["memory-maintenance", "dream"],
            "evidence": "Owner explicitly scoped Dream out of the current slice.",
            "write_recommended": True,
        }
    ]
    FakeMaintenanceProvider.resolver_decisions = [
        {
            "proposal_id": "__first__",
            "outcome": "apply_create",
            "reason": "The candidate is explicitly source-supported and not similar to active memories.",
            "confidence": 0.91,
        }
    ]

    with Session(engine) as db:
        chat_session = repositories.create_chat_session(db, title="Resolver apply")
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
            content="Teniamo Dream fuori da questa implementazione.",
        )
        repositories.complete_turn(db, turn_id=turn.id)
        schedule_session_idle_maintenance(
            db,
            settings=settings,
            session_id=chat_session.id,
            trigger_turn_id=turn.id,
            trigger_event_id=None,
        )
        session_id = chat_session.id

    run_due_maintenance_jobs(
        engine,
        settings=settings,
        provider_factory=FakeMaintenanceProvider,
        now=utc_now(),
    )

    with Session(engine) as db:
        proposals = repositories.list_memory_proposals(
            db,
            source_session_id=session_id,
            status="applied_create",
        )
        memories = repositories.list_memories_for_session(db, session_id=session_id)
        traces = repositories.list_traces_for_session(
            db,
            session_id=session_id,
            kinds=["maintenance.memory_proposal_resolution"],
            limit=10,
        )

    assert len(proposals) == 1
    assert proposals[0].result_json["resolution"]["resolver"] == "llm_proposal_resolution"
    assert proposals[0].result_json["memory_result"]["memory_id"] == memories[0].id
    assert memories[0].content == "The project owner wants Dream review kept as a future evolution."
    assert len(traces) == 1
    assert len(FakeMaintenanceProvider.calls) == 3


def test_memory_review_proposal_detects_exact_duplicate() -> None:
    engine = make_test_engine()
    init_db(engine)
    settings = make_settings()

    with Session(engine) as db:
        chat_session = repositories.create_chat_session(db, title="Duplicate review")
        turn = repositories.create_turn(
            db,
            session_id=chat_session.id,
            model=settings.minimax_model,
        )
        existing = repositories.add_memory(
            db,
            memory_type="user_preference",
            scope="user",
            content="The user likes chocolate but feels bad if they eat too much.",
            reason_for_storage="Future food recommendations.",
            expected_future_use="Avoid over-recommending chocolate.",
            confidence=0.9,
            salience=0.8,
            source_session_id=chat_session.id,
            source_turn_id=turn.id,
            tags=["personal-fact", "food-preference"],
        )
        existing_id = existing.id
        trace = repositories.add_trace(
            db,
            session_id=chat_session.id,
            turn_id=turn.id,
            kind="maintenance.memory_review",
            payload={"operation": "maintenance.memory_review"},
        )
        proposal, created = create_memory_proposal_from_review_candidate(
            db,
            candidate={
                "type": "user_preference",
                "scope": "user",
                "content": (
                    "The user likes chocolate but feels bad if they eat too much."
                ),
                "reason_for_storage": "Future food recommendations.",
                "expected_future_use": "Avoid over-recommending chocolate.",
                "confidence": 0.9,
                "salience": 0.8,
                "tags": ["personal-fact", "food-preference"],
                "evidence": "User stated the fact directly.",
                "write_recommended": True,
            },
            context=MindAPIContext(
                engine=engine,
                session_id=chat_session.id,
                turn_id=turn.id,
                settings=settings,
            ),
            source_trace_id=trace.id,
            maintenance_job_id=None,
            candidate_index=0,
        )

    assert created is True
    assert proposal.proposed_action == "noop_duplicate"
    assert proposal.similar_memory_ids_json[0] == existing_id
    assert proposal.decision_json["reason"].startswith("equivalent active memory")
    assessment = proposal.decision_json["maintenance_assessment"]
    assert assessment["policy_version"] == "maintenance_preflight_assessment_v1"
    assert assessment["lane"] == "deterministic_archive"
    assert "duplicate_memory" in assessment["review_focus"]
    assert assessment["counts"]["similar_memories"] >= 1


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
