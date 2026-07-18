from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.config import Settings
from app.main import create_app
from app.mind.search import sync_memory_retrieval_artifacts
from app.runtime.memory_provenance import memory_provenance_audit
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


def test_summary_reconcile_returns_scheduled_ids_after_session_closes(
    db_engine: Engine,
) -> None:
    settings = Settings(
        app_name="Test Summary Reconcile",
        environment="test",
        minimax_api_key="test-key",
        maintenance_enabled=True,
        summary_reconcile_enabled=True,
    )
    client = TestClient(create_app(settings, db_engine=db_engine))
    with Session(db_engine) as db:
        chat_session = repositories.create_chat_session(db, title="Missing summary")
        turn = repositories.create_turn(
            db,
            session_id=chat_session.id,
            model="MiniMax-M3",
        )
        repositories.add_message(
            db,
            session_id=chat_session.id,
            turn_id=turn.id,
            role="user",
            content="A completed source conversation.",
        )
        repositories.add_message(
            db,
            session_id=chat_session.id,
            turn_id=turn.id,
            role="assistant",
            content="A completed answer.",
        )
        repositories.complete_turn(db, turn_id=turn.id)

    response = client.post(
        "/api/maintenance/summary/reconcile",
        params={"dry_run": False, "limit": 2},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["scheduled_job_ids"]) == 1
    assert body["scheduled_job_ids"][0].startswith("mnt_")


def test_provenance_fixture_deprecation_is_explicit_guarded_and_auditable(
    db_engine: Engine,
) -> None:
    client = make_client(db_engine)
    with Session(db_engine) as db:
        source_session = repositories.create_chat_session(
            db,
            title="Codex Test Seed - guarded fixture",
        )
        fixture = repositories.add_memory(
            db,
            memory_type="project_fact",
            scope="project",
            content="Controlled fixture content.",
            reason_for_storage="Fixture for provenance maintenance.",
            source_session_id=source_session.id,
            tags=["codex-test", "codex-dirty-memory-v1"],
            metadata={
                "codex_test_dataset_version": "dirty-memory-v1",
                "codex_test_key": "guarded-fixture",
                "codex_test_lane": "project",
            },
        )
        fact = repositories.add_memory_fact(
            db,
            memory_id=fixture.id,
            entity="fixture",
            predicate="is_controlled",
            value={"value": True},
            source_session_id=source_session.id,
        )
        sync_memory_retrieval_artifacts(
            db,
            [fixture],
            facts_by_memory={fixture.id: [fact]},
        )
        db.refresh(source_session)
        original_session_updated_at = source_session.updated_at
        fixture_id = fixture.id
        source_session_id = source_session.id

    audit_response = client.get("/api/maintenance/memory/provenance")
    assert audit_response.status_code == 200
    audit = audit_response.json()
    assert audit["read_only"] is True
    assert audit["record_counts"]["explicit_test_fixture"] == 1
    candidate = audit["candidate_sets"]["explicit_test_fixture_deprecation"]
    assert candidate["memory_ids"] == [fixture_id]

    legacy_apply_query = client.get(
        "/api/maintenance/memory/provenance",
        params={"apply": "true"},
    )
    assert legacy_apply_query.status_code == 200
    assert legacy_apply_query.json()["read_only"] is True
    with Session(db_engine) as db:
        unchanged = repositories.get_memory(db, fixture_id)
        assert unchanged is not None
        assert unchanged.status == "active"

    dry_run = client.post(
        "/api/maintenance/memory/provenance/deprecate-explicit-test-fixtures",
        json={"dry_run": True, "reason": "Confirmed test-only fixture."},
    )
    assert dry_run.status_code == 200
    assert dry_run.json()["applied_count"] == 0

    missing_approval = client.post(
        "/api/maintenance/memory/provenance/deprecate-explicit-test-fixtures",
        json={
            "dry_run": False,
            "reason": "Confirmed test-only fixture.",
            "expected_candidate_digest": candidate["digest_sha256"],
            "backup_reference": "test-backup",
        },
    )
    assert missing_approval.status_code == 422

    drifted = client.post(
        "/api/maintenance/memory/provenance/deprecate-explicit-test-fixtures",
        json={
            "dry_run": False,
            "reason": "Confirmed test-only fixture.",
            "expected_candidate_digest": "0" * 64,
            "backup_reference": "test-backup",
            "approval": "deprecate-explicit-codex-test-fixtures",
        },
    )
    assert drifted.status_code == 409
    assert drifted.json()["detail"]["code"] == (
        "memory_provenance.mutation_guard_failed"
    )

    applied = client.post(
        "/api/maintenance/memory/provenance/deprecate-explicit-test-fixtures",
        json={
            "dry_run": False,
            "reason": "Confirmed test-only fixture.",
            "expected_candidate_digest": candidate["digest_sha256"],
            "backup_reference": "test-backup",
            "approval": "deprecate-explicit-codex-test-fixtures",
        },
    )
    assert applied.status_code == 200
    body = applied.json()
    assert body["applied_count"] == 1
    assert len(body["activity_ids"]) == 1
    assert body["residual_audit"]["candidate_sets"][
        "explicit_test_fixture_deprecation"
    ]["count"] == 0

    with Session(db_engine) as db:
        stored = repositories.get_memory(db, fixture_id)
        assert stored is not None
        assert stored.status == "deprecated"
        assert stored.metadata_json["lifecycle"]["last_event"]["backup_reference"] == (
            "test-backup"
        )
        stored_fact = repositories.list_memory_facts(
            db,
            memory_id=fixture_id,
            include_inactive=True,
        )[0]
        assert stored_fact.status == "deprecated"
        surfaces = repositories.list_memory_surfaces(
            db,
            target_type="memory",
            target_id=fixture_id,
        )
        assert surfaces
        assert {surface.status for surface in surfaces} == {"deprecated"}
        activities = repositories.list_memory_activities(db, memory_id=fixture_id)
        assert activities[0].eligible_for_recent is False
        source_session = repositories.get_chat_session(db, source_session_id)
        assert source_session is not None
        assert source_session.updated_at == original_session_updated_at


def test_provenance_audit_does_not_infer_fixture_or_redundancy_from_similarity(
    db_engine: Engine,
) -> None:
    make_client(db_engine)
    with Session(db_engine) as db:
        source_session = repositories.create_chat_session(db, title="Real conversation")
        first = repositories.add_memory(
            db,
            memory_type="project_fact",
            scope="project",
            content="The phrase codex-test can be discussed in real project work.",
            reason_for_storage="Real discussion, not a fixture.",
            source_session_id=source_session.id,
            tags=["codex-test"],
            metadata={},
        )
        second = repositories.add_memory(
            db,
            memory_type="project_fact",
            scope="project",
            content="The phrase codex-test can be discussed in real project work.",
            reason_for_storage="Exact duplicate for review only.",
            source_session_id=source_session.id,
            tags=["codex-test"],
            metadata={},
        )
        audit = memory_provenance_audit(db)
        first_id = first.id
        second_id = second.id

    by_id = {item["memory_id"]: item for item in audit["items"]}
    for memory_id in (first_id, second_id):
        assert by_id[memory_id]["record_class"] == "exact_duplicate_review_candidate"
        assert by_id[memory_id]["recommended_action"] == "review_only"
        assert by_id[memory_id]["fixture_evidence"]["confirmed"] is False
