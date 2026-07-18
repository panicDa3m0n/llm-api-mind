import logging
import threading
from collections.abc import Callable
from datetime import timedelta
from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.config import Settings
from app.runtime.events import record_event
from app.runtime.maintenance_history import (
    run_history_compaction as _run_history_compaction,
    run_idle_summary as _run_idle_summary,
    run_summary_repair as _run_summary_repair,
    verify_session_still_idle as _verify_session_still_idle,
)
from app.runtime.maintenance_memory import run_memory_review as _run_memory_review
from app.runtime.maintenance_shared import (
    SESSION_HISTORY_COMPACTION_KIND,
    SESSION_IDLE_MAINTENANCE_KIND,
    SESSION_SUMMARY_REPAIR_KIND,
    MaintenanceJobRef,
    ProviderFactory,
)
from app.storage import repositories
from app.storage.models import MaintenanceJob, utc_now


logger = logging.getLogger(__name__)


def schedule_session_idle_maintenance(
    db: Session,
    *,
    settings: Settings,
    session_id: str,
    trigger_turn_id: str,
    trigger_event_id: str | None,
) -> tuple[MaintenanceJob, Any]:
    due_at = utc_now() + timedelta(seconds=settings.maintenance_idle_seconds)
    job, superseded = repositories.schedule_session_maintenance_job(
        db,
        kind=SESSION_IDLE_MAINTENANCE_KIND,
        session_id=session_id,
        trigger_turn_id=trigger_turn_id,
        trigger_event_id=trigger_event_id,
        due_at=due_at,
        input_payload={
            "idle_seconds": settings.maintenance_idle_seconds,
            "trigger": "turn.completed",
            "steps": ["sessions.summarize", "memory.missed_save_review"],
        },
    )
    event = record_event(
        db,
        session_id=session_id,
        turn_id=trigger_turn_id,
        event_type="maintenance.job.scheduled",
        payload={
            "job_id": job.id,
            "kind": job.kind,
            "due_at": job.due_at.isoformat(),
            "idle_seconds": settings.maintenance_idle_seconds,
            "superseded_job_ids": [item.id for item in superseded],
        },
        source="maintenance",
        actor="backend",
        visibility="debug",
        status=job.status,
        parent_event_id=trigger_event_id,
    )
    return job, event


def schedule_history_compaction(
    db: Session,
    *,
    settings: Settings,
    session_id: str,
    trigger_turn_id: str,
    trigger_event_id: str | None,
    source_map: dict[str, Any],
    external_context_tokens: int,
    chars_per_token: float,
    model_history_tokens: int | None = None,
) -> tuple[MaintenanceJob, Any] | None:
    if settings.history_compaction_mode != "active":
        return None
    source_history_sha256 = source_map.get("canonical_history_sha256")
    canonical_history_tokens = int(source_map.get("canonical_estimated_tokens") or 0)
    active_history_tokens = (
        int(model_history_tokens)
        if model_history_tokens is not None
        else canonical_history_tokens
    )
    total_estimated_tokens = active_history_tokens + external_context_tokens
    if (
        source_map.get("status") != "complete"
        or not source_history_sha256
        or total_estimated_tokens < settings.context_compaction_trigger_tokens
    ):
        return None

    job, superseded = repositories.schedule_session_maintenance_job(
        db,
        kind=SESSION_HISTORY_COMPACTION_KIND,
        session_id=session_id,
        trigger_turn_id=trigger_turn_id,
        trigger_event_id=trigger_event_id,
        due_at=utc_now(),
        input_payload={
            "source_history_sha256": source_history_sha256,
            "canonical_history_estimated_tokens": canonical_history_tokens,
            "model_history_estimated_tokens": active_history_tokens,
            "external_context_estimated_tokens": external_context_tokens,
            "total_estimated_tokens": total_estimated_tokens,
            "chars_per_token": chars_per_token,
            "trigger_tokens": settings.context_compaction_trigger_tokens,
        },
        idempotency_key=(
            f"{SESSION_HISTORY_COMPACTION_KIND}:{session_id}:{source_history_sha256}"
        ),
    )
    event = record_event(
        db,
        session_id=session_id,
        turn_id=trigger_turn_id,
        event_type="history.compaction.scheduled",
        payload={
            "job_id": job.id,
            "source_history_sha256": source_history_sha256,
            "total_estimated_tokens": total_estimated_tokens,
            "canonical_history_estimated_tokens": canonical_history_tokens,
            "model_history_estimated_tokens": active_history_tokens,
            "trigger_tokens": settings.context_compaction_trigger_tokens,
            "superseded_job_ids": [item.id for item in superseded],
            "canonical_history_mutation": "none",
        },
        source="maintenance",
        actor="backend",
        visibility="debug",
        status=job.status,
        parent_event_id=trigger_event_id,
    )
    return job, event


def schedule_summary_repairs(
    db: Session,
    *,
    settings: Settings,
    limit: int | None = None,
    exclude_session_id: str | None = None,
) -> list[MaintenanceJob]:
    if not settings.maintenance_enabled or not settings.summary_reconcile_enabled:
        return []

    scheduled: list[MaintenanceJob] = []
    batch_limit = limit or settings.summary_reconcile_batch_size
    for state in repositories.list_session_summary_states(
        db,
        exclude_session_id=exclude_session_id,
    ):
        if len(scheduled) >= batch_limit:
            break
        if state.summary_state not in {"missing", "stale"}:
            continue
        if state.latest_turn_status != "completed" or state.last_message_id is None:
            continue

        prior_jobs = repositories.list_maintenance_jobs(
            db,
            kind=SESSION_SUMMARY_REPAIR_KIND,
            session_id=state.chat_session.id,
            limit=100,
        )
        matching_jobs = [
            job
            for job in prior_jobs
            if job.input_json.get("target_last_message_id") == state.last_message_id
        ]
        if any(
            job.status in {"pending", "running", "completed"} for job in matching_jobs
        ):
            continue
        attempt = len(matching_jobs) + 1
        if attempt > settings.summary_reconcile_max_attempts:
            continue
        delay = 0
        if attempt > 1:
            delay = settings.summary_reconcile_retry_backoff_seconds * (
                2 ** (attempt - 2)
            )
        due_at = utc_now() + timedelta(seconds=delay)
        idempotency_key = (
            f"{SESSION_SUMMARY_REPAIR_KIND}:{state.chat_session.id}:"
            f"{state.last_message_id}:attempt:{attempt}"
        )
        job, _ = repositories.schedule_session_maintenance_job(
            db,
            kind=SESSION_SUMMARY_REPAIR_KIND,
            session_id=state.chat_session.id,
            trigger_turn_id=state.latest_turn_id,
            trigger_event_id=None,
            due_at=due_at,
            input_payload={
                "target_last_message_id": state.last_message_id,
                "summary_state": state.summary_state,
                "attempt": attempt,
                "max_attempts": settings.summary_reconcile_max_attempts,
                "source": "summary_reconciler",
            },
            idempotency_key=idempotency_key,
        )
        scheduled.append(job)
    for job in scheduled:
        db.refresh(job)
    return scheduled


def run_due_maintenance_jobs(
    engine: Engine,
    *,
    settings: Settings,
    provider_factory: ProviderFactory,
    now: Any | None = None,
) -> list[dict[str, Any]]:
    if not settings.maintenance_enabled:
        return []

    with Session(engine) as db:
        schedule_summary_repairs(db, settings=settings)
        due_jobs = repositories.list_due_maintenance_jobs(
            db,
            now=now,
            limit=settings.maintenance_job_batch_size,
        )

    results: list[dict[str, Any]] = []
    for due_job in due_jobs:
        results.append(
            run_maintenance_job(
                engine,
                settings=settings,
                provider_factory=provider_factory,
                job_id=due_job.id,
            )
        )
    return results


def run_maintenance_job(
    engine: Engine,
    *,
    settings: Settings,
    provider_factory: ProviderFactory,
    job_id: str,
) -> dict[str, Any]:
    with Session(engine) as db:
        job = repositories.start_maintenance_job(db, job_id=job_id)
        if job is None:
            return {"job_id": job_id, "status": "not_pending"}
        job_ref = MaintenanceJobRef(
            id=job.id,
            kind=job.kind,
            session_id=job.session_id,
            trigger_turn_id=job.trigger_turn_id,
            trigger_event_id=job.trigger_event_id,
            input_payload=job.input_json,
        )
        record_event(
            db,
            session_id=job_ref.session_id,
            turn_id=job_ref.trigger_turn_id,
            event_type="maintenance.job.started",
            payload={"job_id": job_ref.id, "kind": job_ref.kind},
            source="maintenance",
            actor="backend",
            visibility="debug",
            status="running",
            parent_event_id=job_ref.trigger_event_id,
        )

    try:
        if job_ref.kind == SESSION_HISTORY_COMPACTION_KIND:
            compaction_result = _run_history_compaction(
                engine,
                settings=settings,
                provider_factory=provider_factory,
                job=job_ref,
            )
            status = "completed" if compaction_result.get("ok") else "failed"
            return _finish_job(
                engine,
                job_id=job_ref.id,
                session_id=job_ref.session_id,
                turn_id=job_ref.trigger_turn_id,
                trigger_event_id=job_ref.trigger_event_id,
                status=status,
                result=compaction_result,
                error=None if status == "completed" else compaction_result,
            )

        if job_ref.kind == SESSION_SUMMARY_REPAIR_KIND:
            repair_result = _run_summary_repair(
                engine,
                settings=settings,
                provider_factory=provider_factory,
                job=job_ref,
            )
            status = "completed" if repair_result.get("ok") else "failed"
            return _finish_job(
                engine,
                job_id=job_ref.id,
                session_id=job_ref.session_id,
                turn_id=job_ref.trigger_turn_id,
                trigger_event_id=job_ref.trigger_event_id,
                status=status,
                result=repair_result,
                error=None if status == "completed" else repair_result,
            )

        if job_ref.kind != SESSION_IDLE_MAINTENANCE_KIND:
            result: dict[str, Any] = {
                "reason": f"Unknown maintenance job kind: {job_ref.kind}"
            }
            return _finish_job(
                engine,
                job_id=job_ref.id,
                session_id=job_ref.session_id,
                turn_id=job_ref.trigger_turn_id,
                trigger_event_id=job_ref.trigger_event_id,
                status="skipped",
                result=result,
            )

        idle_status = _verify_session_still_idle(engine, job_ref)
        if not idle_status["idle"]:
            return _finish_job(
                engine,
                job_id=job_ref.id,
                session_id=job_ref.session_id,
                turn_id=job_ref.trigger_turn_id,
                trigger_event_id=job_ref.trigger_event_id,
                status="skipped",
                result=idle_status,
            )

        summary_result = _run_idle_summary(
            engine,
            settings=settings,
            provider_factory=provider_factory,
            job=job_ref,
        )
        memory_review_result = _run_memory_review(
            engine,
            settings=settings,
            provider_factory=provider_factory,
            job=job_ref,
        )
        status = (
            "completed"
            if summary_result.get("ok") and memory_review_result.get("ok")
            else "failed"
        )
        result = {
            "idle": True,
            "summary": summary_result,
            "memory_review": memory_review_result,
        }
        error = None if status == "completed" else result
        return _finish_job(
            engine,
            job_id=job_ref.id,
            session_id=job_ref.session_id,
            turn_id=job_ref.trigger_turn_id,
            trigger_event_id=job_ref.trigger_event_id,
            status=status,
            result=result,
            error=error,
        )
    except Exception as exc:
        result = {"error": type(exc).__name__, "message": str(exc)}
        return _finish_job(
            engine,
            job_id=job_ref.id,
            session_id=job_ref.session_id,
            turn_id=job_ref.trigger_turn_id,
            trigger_event_id=job_ref.trigger_event_id,
            status="failed",
            result=result,
            error=result,
        )


def start_maintenance_worker(
    engine: Engine,
    *,
    settings: Settings,
    provider_factory: ProviderFactory,
) -> Callable[[], None]:
    if not settings.maintenance_enabled:
        return lambda: None

    stop_event = threading.Event()

    def loop() -> None:
        while not stop_event.wait(settings.maintenance_worker_interval_seconds):
            try:
                run_due_maintenance_jobs(
                    engine,
                    settings=settings,
                    provider_factory=provider_factory,
                )
            except Exception:
                logger.exception("Maintenance worker batch failed.")

    thread = threading.Thread(
        target=loop,
        name="api-mind-maintenance",
        daemon=True,
    )
    thread.start()

    def stop() -> None:
        stop_event.set()
        thread.join(timeout=2)

    return stop


def _finish_job(
    engine: Engine,
    *,
    job_id: str,
    session_id: str,
    turn_id: str | None,
    trigger_event_id: str | None,
    status: str,
    result: dict[str, Any],
    error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    with Session(engine) as db:
        completed = repositories.complete_maintenance_job(
            db,
            job_id=job_id,
            result=result,
            status=status,
            error=error,
        )
        record_event(
            db,
            session_id=session_id,
            turn_id=turn_id,
            event_type=f"maintenance.job.{status}",
            payload={
                "job_id": completed.id,
                "kind": completed.kind,
                "result": result,
            },
            source="maintenance",
            actor="backend",
            visibility="debug",
            status=status,
            parent_event_id=trigger_event_id,
        )
    return {"job_id": job_id, "status": status, "result": result}
