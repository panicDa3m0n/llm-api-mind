from __future__ import annotations

from datetime import timedelta

from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.ops.park_legacy_workspace_candidates import (
    legacy_candidate_ids,
    reconcile_legacy_candidates,
)
from app.runtime.events import record_event
from app.storage import repositories
from app.storage.db import init_db
from app.storage.models import utc_now


def test_legacy_reconciliation_only_parks_the_exact_retired_retry_path(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    now = utc_now()
    with Session(db_engine) as db:
        session = repositories.get_or_create_autonomous_session(
            db,
            profile_id="local-user",
        )
        legacy, _ = repositories.create_candidate(
            db,
            profile_id="local-user",
            candidate_kind="continuity_question",
            context_family="session_continuity",
            claim="The old fallback should be parked.",
            why_now="Fixture.",
            cognitive_question="Should this loop re-enter automatically?",
            expected_transformation="Stop the blind retry.",
            uncertainty="medium",
            exact_fingerprint="legacy-retry-path",
            sources=[
                {
                    "source_kind": "event",
                    "source_id": "evt_legacy",
                    "observed_at": now,
                }
            ],
        )
        unrelated, _ = repositories.create_candidate(
            db,
            profile_id="local-user",
            candidate_kind="future_review",
            context_family="session_continuity",
            claim="A genuine explicit deferral stays suspended.",
            why_now="Fixture.",
            cognitive_question="Is a later review still scheduled?",
            expected_transformation="Keep its legitimate lifecycle.",
            uncertainty="medium",
            exact_fingerprint="unrelated-suspension",
            sources=[
                {
                    "source_kind": "event",
                    "source_id": "evt_unrelated",
                    "observed_at": now,
                }
            ],
        )
        repositories.update_candidate(
            db,
            candidate_id=legacy.id,
            status="suspended",
            deferred_until=now + timedelta(minutes=10),
        )
        repositories.update_candidate(
            db,
            candidate_id=unrelated.id,
            status="suspended",
            deferred_until=now + timedelta(hours=1),
        )
        record_event(
            db,
            session_id=session.id,
            event_type="cognition.candidate.suspended",
            payload={
                "candidate_id": legacy.id,
                "reason": "no_explicit_episode_or_volition_decision",
            },
            source="cognitive_workspace",
            actor="backend",
            visibility="private",
        )

        ids = legacy_candidate_ids(db, profile_id="local-user")
        reconciled = reconcile_legacy_candidates(
            db,
            profile_id="local-user",
            candidate_ids=ids,
        )
        stored_legacy = repositories.get_candidate(db, legacy.id)
        stored_unrelated = repositories.get_candidate(db, unrelated.id)

    assert reconciled == [legacy.id]
    assert stored_legacy is not None
    assert stored_legacy.status == "parked"
    assert stored_legacy.deferred_until is None
    assert stored_unrelated is not None
    assert stored_unrelated.status == "suspended"
