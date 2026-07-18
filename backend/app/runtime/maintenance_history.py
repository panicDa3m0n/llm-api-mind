from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.config import Settings
from app.mind.contracts import MindAPIContext
from app.mind.episodic import handle_session_summarize
from app.runtime.history_runtime import generate_history_compaction
from app.runtime.maintenance_shared import (
    SESSION_SUMMARY_REPAIR_KIND,
    MaintenanceJobRef,
    ProviderFactory,
)
from app.storage import repositories


def session_summary_audit(
    db: Session,
    *,
    exclude_session_id: str | None = None,
) -> dict[str, Any]:
    states = repositories.list_session_summary_states(
        db,
        exclude_session_id=exclude_session_id,
    )
    counts: dict[str, int] = {}
    sessions: list[dict[str, Any]] = []
    for state in states:
        classification = state.summary_state
        if (
            classification in {"missing", "stale"}
            and state.latest_turn_status != "completed"
        ):
            classification = "blocked_active_turn"
        elif classification in {"missing", "stale"}:
            jobs = repositories.list_maintenance_jobs(
                db,
                kind=SESSION_SUMMARY_REPAIR_KIND,
                session_id=state.chat_session.id,
                limit=100,
            )
            matching = [
                job
                for job in jobs
                if job.input_json.get("target_last_message_id") == state.last_message_id
            ]
            if matching and all(job.status == "failed" for job in matching):
                classification = "failed_maintenance"
        counts[classification] = counts.get(classification, 0) + 1
        sessions.append(
            {
                "session_id": state.chat_session.id,
                "title": state.chat_session.title,
                "classification": classification,
                "last_message_id": state.last_message_id,
                "last_message_at": (
                    state.last_message_at.isoformat()
                    if state.last_message_at is not None
                    else None
                ),
                "turn_count": state.turn_count,
                "latest_turn_id": state.latest_turn_id,
                "latest_turn_status": state.latest_turn_status,
                "summary_id": state.summary.id if state.summary is not None else None,
                "summary_last_message_id": (
                    state.summary.last_message_id if state.summary is not None else None
                ),
            }
        )
    return {"counts": counts, "sessions": sessions}


def run_summary_repair(
    engine: Engine,
    *,
    settings: Settings,
    provider_factory: ProviderFactory,
    job: MaintenanceJobRef,
) -> dict[str, Any]:
    with Session(engine) as db:
        state = next(
            (
                item
                for item in repositories.list_session_summary_states(db)
                if item.chat_session.id == job.session_id
            ),
            None,
        )
    if state is None or state.last_message_id is None:
        return {"ok": True, "status": "skipped", "reason": "session_is_empty"}
    if state.latest_turn_status != "completed":
        return {
            "ok": True,
            "status": "skipped",
            "reason": "latest_turn_not_completed",
            "latest_turn_status": state.latest_turn_status,
        }
    target_message_id = job.input_payload.get("target_last_message_id")
    if target_message_id != state.last_message_id:
        return {
            "ok": True,
            "status": "skipped",
            "reason": "summary_target_changed",
            "target_last_message_id": target_message_id,
            "actual_last_message_id": state.last_message_id,
        }
    result = run_idle_summary(
        engine,
        settings=settings,
        provider_factory=provider_factory,
        job=job,
    )
    return {
        **result,
        "status": "completed" if result.get("ok") else "failed",
        "target_last_message_id": target_message_id,
        "attempt": job.input_payload.get("attempt"),
    }


def run_history_compaction(
    engine: Engine,
    *,
    settings: Settings,
    provider_factory: ProviderFactory,
    job: MaintenanceJobRef,
) -> dict[str, Any]:
    return generate_history_compaction(
        engine,
        settings=settings,
        provider_factory=provider_factory,
        session_id=job.session_id,
        trigger_turn_id=job.trigger_turn_id,
        expected_history_sha256=str(
            job.input_payload.get("source_history_sha256") or ""
        ),
        external_context_tokens=int(
            job.input_payload.get("external_context_estimated_tokens") or 0
        ),
        chars_per_token=float(job.input_payload.get("chars_per_token") or 3.5),
    )


def verify_session_still_idle(
    engine: Engine,
    job: MaintenanceJobRef,
) -> dict[str, Any]:
    with Session(engine) as db:
        latest_turn = repositories.latest_turn_for_session(
            db, session_id=job.session_id
        )
        if latest_turn is None:
            return {"idle": False, "reason": "session_has_no_turns"}
        if latest_turn.id != job.trigger_turn_id:
            return {
                "idle": False,
                "reason": "newer_turn_exists",
                "latest_turn_id": latest_turn.id,
                "trigger_turn_id": job.trigger_turn_id,
            }
        if latest_turn.status != "completed":
            return {
                "idle": False,
                "reason": "latest_turn_not_completed",
                "latest_turn_id": latest_turn.id,
                "latest_turn_status": latest_turn.status,
            }
    return {"idle": True, "trigger_turn_id": job.trigger_turn_id}


def run_idle_summary(
    engine: Engine,
    *,
    settings: Settings,
    provider_factory: ProviderFactory,
    job: MaintenanceJobRef,
) -> dict[str, Any]:
    context = MindAPIContext(
        engine=engine,
        session_id=job.session_id,
        turn_id=job.trigger_turn_id,
        settings=settings,
        provider_factory=provider_factory,
    )
    result = handle_session_summarize(
        job.session_id,
        {
            "force": False,
            "focus": "idle session summary for episodic recall and memory review",
        },
        context,
        intent="Refresh episodic summary after the session idle timer.",
    )
    return {
        "ok": result.ok,
        "result": result.result,
        "error_code": result.error_code,
        "error_message": result.error_message,
    }
