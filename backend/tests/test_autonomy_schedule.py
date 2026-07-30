from __future__ import annotations

from datetime import timedelta

from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.config import Settings
from app.runtime.autonomy import run_autonomous_activation
from app.runtime.autonomy_schedule import (
    activation_min_gap_deadline,
    coalesce_autonomous_activation,
)
from app.runtime.time import aware_utc
from app.storage import repositories
from app.storage.db import init_db
from app.storage.models import utc_now


def _settings() -> Settings:
    return Settings(
        agent_system_prompt="You are Scarlet.",
        maintenance_enabled=False,
        cognitive_workspace_mode="off",
        autonomous_activation_min_gap_seconds=900,
        autonomous_activation_max_silence_seconds=10800,
    )


def _completed_activation(
    db: Session,
    *,
    profile_id: str,
    session_id: str,
):
    activation = repositories.schedule_autonomous_activation(
        db,
        profile_id=profile_id,
        session_id=session_id,
        scheduled_at=utc_now() - timedelta(minutes=1),
        schedule_key="completed-baseline",
    )
    return repositories.complete_autonomous_activation(
        db,
        activation_id=activation.id,
        status="completed",
        turn_id=None,
        active_mode="idle",
    )


def test_scheduler_coalesces_sources_until_the_next_m3_gap(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    with Session(db_engine) as db:
        session = repositories.get_or_create_autonomous_session(
            db,
            profile_id="local-user",
        )
        completed = _completed_activation(
            db,
            profile_id="local-user",
            session_id=session.id,
        )
        assert completed.completed_at is not None
        first_now = completed.completed_at + timedelta(seconds=60)
        first = coalesce_autonomous_activation(
            db,
            profile_id="local-user",
            session_id=session.id,
            trigger_kind="cognitive_workspace",
            candidate_id="cand_one",
            workspace={
                "selected_candidate_ids": ["cand_one"],
                "selected_candidates": [{"id": "cand_one"}],
            },
            min_gap_seconds=900,
            now=first_now,
        )
        second = coalesce_autonomous_activation(
            db,
            profile_id="local-user",
            session_id=session.id,
            trigger_kind="max_silence",
            candidate_id="cand_two",
            workspace={
                "selected_candidate_ids": ["cand_two"],
                "selected_candidates": [{"id": "cand_two"}],
            },
            min_gap_seconds=900,
            now=completed.completed_at + timedelta(seconds=120),
        )

        assert first.disposition == "scheduled"
        assert second.disposition == "coalesced"
        assert second.activation.id == first.activation.id
        expected_eligible_at = aware_utc(completed.completed_at) + timedelta(
            seconds=900
        )
        assert second.eligible_at == expected_eligible_at
        assert aware_utc(second.activation.scheduled_at) == second.eligible_at
        assert second.activation.trigger_kind == "coalesced"
        assert second.activation.workspace_json["selected_candidate_ids"] == [
            "cand_one",
            "cand_two",
        ]
        assert second.activation.workspace_json["coalesced_trigger_kinds"] == [
            "cognitive_workspace",
            "max_silence",
        ]


def test_runner_defers_a_due_activation_until_the_minimum_m3_gap(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    settings = _settings()
    with Session(db_engine) as db:
        session = repositories.get_or_create_autonomous_session(
            db,
            profile_id=settings.user_profile_id,
        )
        completed = _completed_activation(
            db,
            profile_id=settings.user_profile_id,
            session_id=session.id,
        )
        assert completed.completed_at is not None
        attempted_at = completed.completed_at + timedelta(seconds=30)
        activation = repositories.schedule_autonomous_activation(
            db,
            profile_id=settings.user_profile_id,
            session_id=session.id,
            scheduled_at=attempted_at,
            trigger_kind="manual_lab",
            schedule_key="premature-activation",
        )
        deadline = activation_min_gap_deadline(
            db,
            profile_id=settings.user_profile_id,
            min_gap_seconds=settings.autonomous_activation_min_gap_seconds,
            now=attempted_at,
        )

    assert deadline is not None
    result = run_autonomous_activation(
        db_engine,
        settings=settings,
        provider_factory=lambda _settings: None,
        activation_id=activation.id,
        now=attempted_at,
    )

    assert result["status"] == "deferred"
    assert result["reason"] == "minimum_m3_gap_not_elapsed"
    with Session(db_engine) as db:
        stored = db.get(type(activation), activation.id)
        assert stored is not None
        assert stored.status == "deferred"
        pending = repositories.get_pending_autonomous_activation(
            db,
            profile_id=settings.user_profile_id,
        )
        assert pending is not None
        assert aware_utc(pending.scheduled_at) == deadline


def test_scheduler_never_starts_a_second_m3_turn_while_one_is_running(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    now = utc_now()
    with Session(db_engine) as db:
        session = repositories.get_or_create_autonomous_session(
            db,
            profile_id="local-user",
        )
        active = repositories.schedule_autonomous_activation(
            db,
            profile_id="local-user",
            session_id=session.id,
            scheduled_at=now,
            schedule_key="running-activation",
        )
        claimed = repositories.claim_autonomous_activation(
            db,
            activation_id=active.id,
            lease_seconds=900,
            now=now,
        )
        assert claimed is not None

        scheduled = coalesce_autonomous_activation(
            db,
            profile_id="local-user",
            session_id=session.id,
            trigger_kind="cognitive_workspace",
            workspace={"selected_candidate_ids": ["cand_later"]},
            min_gap_seconds=900,
            now=now,
        )

        assert scheduled.activation.id != active.id
        assert scheduled.eligible_at == now + timedelta(seconds=900)
        assert aware_utc(scheduled.activation.scheduled_at) == scheduled.eligible_at
