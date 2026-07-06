from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.config import Settings
from app.main import create_app
from app.storage import repositories
from app.storage.models import utc_now


def make_client(db_engine: Engine) -> TestClient:
    settings = Settings(
        app_name="Test Maintenance API",
        environment="test",
        minimax_api_key="test-key",
        maintenance_enabled=False,
    )
    return TestClient(create_app(settings, db_engine=db_engine))


def test_maintenance_memory_proposals_are_paged_and_archived(db_engine: Engine) -> None:
    client = make_client(db_engine)
    session = client.post("/api/chat/sessions", json={"title": "Proposal queue"}).json()
    with Session(db_engine) as db:
        first, _ = repositories.upsert_memory_proposal(
            db,
            idempotency_key="memory_proposal:test_maintenance_api:first",
            source="maintenance.memory_review",
            proposed_action="review_similar",
            action_confidence=0.75,
            risk="medium",
            candidate_type="user_preference",
            candidate_scope="user",
            content="The user prefers concise answers when tired.",
            reason_for_storage="Useful preference candidate.",
            source_session_id=session["id"],
            tags=["communication"],
            similar_memory_ids=["mem_existing"],
            decision={"proposed_action": "review_similar"},
        )
        repositories.upsert_memory_proposal(
            db,
            idempotency_key="memory_proposal:test_maintenance_api:second",
            source="maintenance.memory_review",
            proposed_action="create_new",
            action_confidence=0.82,
            risk="low",
            candidate_type="project_fact",
            candidate_scope="project",
            content="The project keeps proposal review outside the Mind API.",
            reason_for_storage="Architecture candidate.",
            source_session_id=session["id"],
            tags=["architecture"],
            decision={"proposed_action": "create_new"},
        )
        first_id = first.id

    list_response = client.get(
        "/api/maintenance/memory/proposals",
        params={"status": "pending", "limit": 1, "offset": 0},
    )

    assert list_response.status_code == 200
    body = list_response.json()
    assert body["operation"] == "maintenance.memory.proposals.list"
    assert body["returned"] == 1
    assert body["has_more"] is True
    assert body["next_offset"] == 1
    assert body["proposals"][0]["status"] == "pending"
    assert body["proposals"][0]["candidate"]["content"]

    archive_response = client.post(
        f"/api/maintenance/memory/proposals/{first_id}/archive",
        json={"reason": "Reviewed by maintenance evaluator."},
    )

    assert archive_response.status_code == 200
    archived = archive_response.json()["proposal"]
    assert archived["status"] == "archived_manual"
    assert archived["result"]["reason"] == "Reviewed by maintenance evaluator."
    assert archived["applied_at"] is not None

    resolved_response = client.get(
        "/api/maintenance/memory/proposals",
        params={
            "status": "resolved",
            "resolved_from": "2000-01-01T00:00:00",
            "resolved_to": "2999-01-01T00:00:00",
            "limit": 10,
            "offset": 0,
        },
    )
    resolved_ids = [
        proposal["id"] for proposal in resolved_response.json()["proposals"]
    ]
    assert first_id in resolved_ids
    assert resolved_response.json()["statuses"]

    pending_response = client.get(
        "/api/maintenance/memory/proposals",
        params={"status": "pending", "limit": 10, "offset": 0},
    )
    pending_ids = [proposal["id"] for proposal in pending_response.json()["proposals"]]
    assert first_id not in pending_ids


def test_maintenance_memory_proposal_archive_returns_404_for_missing_id(
    db_engine: Engine,
) -> None:
    client = make_client(db_engine)

    response = client.post(
        "/api/maintenance/memory/proposals/prop_missing/archive",
        json={"reason": "No such proposal."},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "memory_proposal.not_found"


def test_maintenance_overview_and_jobs_expose_lab_state(db_engine: Engine) -> None:
    client = make_client(db_engine)
    session = client.post("/api/chat/sessions", json={"title": "Maintenance lab"}).json()
    with Session(db_engine) as db:
        turn = repositories.create_turn(
            db,
            session_id=session["id"],
            model="MiniMax-M3",
        )
        job, _ = repositories.schedule_session_maintenance_job(
            db,
            kind="session.idle_maintenance",
            session_id=session["id"],
            trigger_turn_id=turn.id,
            trigger_event_id=None,
            due_at=utc_now() + timedelta(minutes=15),
            input_payload={"trigger": "test"},
        )
        repositories.upsert_memory_proposal(
            db,
            idempotency_key="memory_proposal:test_maintenance_api:overview",
            source="maintenance.memory_review",
            proposed_action="create_new",
            action_confidence=0.9,
            risk="low",
            candidate_type="user_preference",
            candidate_scope="user",
            content="The user likes maintenance dashboards.",
            reason_for_storage="Useful lab preference candidate.",
            source_session_id=session["id"],
            maintenance_job_id=job.id,
            tags=["maintenance"],
            decision={"proposed_action": "create_new"},
        )
        job_id = job.id

    overview_response = client.get("/api/maintenance/overview")

    assert overview_response.status_code == 200
    overview = overview_response.json()
    assert overview["operation"] == "maintenance.overview"
    assert overview["settings"]["enabled"] is False
    assert overview["jobs"]["counts_by_status"]["pending"] == 1
    assert overview["memory_proposals"]["counts_by_status"]["pending"] == 1
    assert overview["memory_proposals"]["counts_by_action"]["create_new"] == 1
    assert overview["jobs"]["recent"][0]["id"] == job_id

    jobs_response = client.get(
        "/api/maintenance/jobs",
        params={"status": "pending", "limit": 10},
    )

    assert jobs_response.status_code == 200
    jobs = jobs_response.json()
    assert jobs["operation"] == "maintenance.jobs.list"
    assert jobs["returned"] == 1
    assert jobs["jobs"][0]["id"] == job_id
    assert jobs["jobs"][0]["session_id"] == session["id"]


def test_maintenance_job_run_returns_404_for_missing_id(db_engine: Engine) -> None:
    client = make_client(db_engine)

    response = client.post("/api/maintenance/jobs/mnt_missing/run")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "maintenance_job.not_found"
