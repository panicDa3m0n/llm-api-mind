import json
import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.config import Settings
from app.llm.factory import active_provider_max_tokens
from app.llm.provider import LLMConfigurationError, LLMProvider, LLMRequestError
from app.mind.episodic import handle_session_summarize
from app.mind.memory import MindAPIContext
from app.runtime.events import record_event
from app.storage import repositories
from app.storage.models import MaintenanceJob, utc_now


SESSION_IDLE_MAINTENANCE_KIND = "session.idle_maintenance"
logger = logging.getLogger(__name__)

MEMORY_REVIEW_SYSTEM_PROMPT = """You review a completed chat session for Scarlet's memory maintenance.

You are not speaking to the user. Return only one JSON object.

Goal: detect semantic memories that appear to be missing from persistent memory.
Do not write memory yourself. Do not invent facts. Prefer "no candidate" over
storing noisy, unsupported, private, or one-off details.

Required JSON shape:

{
  "summary": "short maintenance finding",
  "candidate_count": 0,
  "candidates": [
    {
      "type": "user_preference|project_fact|decision|correction|task_context|behavioral_pattern|episodic",
      "scope": "user|project|session",
      "content": "compact sourceable semantic memory candidate",
      "reason_for_storage": "why this may help future Scarlet",
      "expected_future_use": "when this may matter later",
      "confidence": 0.0,
      "salience": 0.0,
      "tags": ["tag"],
      "evidence": "short transcript-grounded evidence",
      "write_recommended": true
    }
  ],
  "skipped_reason": null
}
"""


ProviderFactory = Callable[[Settings], LLMProvider]


@dataclass(frozen=True)
class MaintenanceJobRef:
    id: str
    kind: str
    session_id: str
    trigger_turn_id: str | None
    trigger_event_id: str | None


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
        if job_ref.kind != SESSION_IDLE_MAINTENANCE_KIND:
            result = {"reason": f"Unknown maintenance job kind: {job_ref.kind}"}
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


def _verify_session_still_idle(
    engine: Engine,
    job: MaintenanceJobRef,
) -> dict[str, Any]:
    with Session(engine) as db:
        latest_turn = repositories.latest_turn_for_session(db, session_id=job.session_id)
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


def _run_idle_summary(
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


def _run_memory_review(
    engine: Engine,
    *,
    settings: Settings,
    provider_factory: ProviderFactory,
    job: MaintenanceJobRef,
) -> dict[str, Any]:
    with Session(engine) as db:
        messages = repositories.list_messages(db, session_id=job.session_id)
        memories = repositories.list_memories_for_session(db, session_id=job.session_id)
        memory_write_traces = repositories.list_traces_for_session(
            db,
            session_id=job.session_id,
            kinds=["mind.memory.write"],
            limit=200,
        )
        prompt = _build_memory_review_prompt(
            messages=messages,
            memories=memories,
            memory_write_trace_count=len(memory_write_traces),
        )

    try:
        provider = provider_factory(settings)
        result = provider.generate_text(
            prompt=prompt,
            system=MEMORY_REVIEW_SYSTEM_PROMPT,
            max_tokens=active_provider_max_tokens(settings),
        )
    except LLMConfigurationError as exc:
        return {
            "ok": False,
            "error_code": "maintenance.memory_review.provider_unavailable",
            "error_message": str(exc),
        }
    except LLMRequestError as exc:
        return {
            "ok": False,
            "error_code": "maintenance.memory_review.provider_error",
            "error_message": str(exc),
        }

    parsed = _parse_json_object(result.text)
    if parsed is None:
        parsed = {
            "summary": "Memory review did not return valid JSON.",
            "candidate_count": 0,
            "candidates": [],
            "skipped_reason": "invalid_json",
            "raw_text": result.text,
        }
        ok = False
    else:
        parsed = _normalize_memory_review(parsed)
        ok = True

    with Session(engine) as db:
        trace = repositories.add_trace(
            db,
            session_id=job.session_id,
            turn_id=job.trigger_turn_id,
            kind="maintenance.memory_review",
            payload={
                "operation": "maintenance.memory_review",
                "job_id": job.id,
                "review": parsed,
                "provider": {
                    "model": result.model,
                    "usage": result.usage,
                    "provider_message_id": result.provider_message_id,
                    "stop_reason": result.stop_reason,
                },
                "mode": "report_only",
            },
        )
        event = record_event(
            db,
            session_id=job.session_id,
            turn_id=job.trigger_turn_id,
            event_type="maintenance.memory_review.completed",
            payload={
                "job_id": job.id,
                "trace_id": trace.id,
                "candidate_count": parsed.get("candidate_count", 0),
                "write_recommended_count": sum(
                    1
                    for item in parsed.get("candidates", [])
                    if isinstance(item, dict) and item.get("write_recommended")
                ),
                "mode": "report_only",
            },
            source="maintenance",
            actor="backend",
            visibility="debug",
            status="completed" if ok else "failed",
            trace_id=trace.id,
        )
        trace_id = trace.id
        event_id = event.id

    return {
        "ok": ok,
        "review": parsed,
        "trace_id": trace_id,
        "event_id": event_id,
    }


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


def _build_memory_review_prompt(
    *,
    messages: list[Any],
    memories: list[Any],
    memory_write_trace_count: int,
) -> str:
    conversation = [
        {
            "role": message.role,
            "content": message.content,
            "message_id": message.id,
            "turn_id": message.turn_id,
        }
        for message in messages
        if message.role in {"user", "assistant"}
    ]
    existing_memories = [
        {
            "id": memory.id,
            "type": memory.memory_type,
            "scope": memory.scope,
            "status": memory.status,
            "content": memory.content,
            "tags": memory.tags_json,
        }
        for memory in memories
    ]
    return json.dumps(
        {
            "task": "Detect sourceable semantic memory candidates missed during this idle session.",
            "mode": "report_only",
            "memory_write_trace_count": memory_write_trace_count,
            "conversation": conversation,
            "existing_memories_from_session": existing_memories,
            "rules": [
                "Do not duplicate existing memories.",
                "Prefer compact reusable semantic facts, preferences, decisions, corrections, or checkpoints.",
                "Do not include secrets or unsupported guesses.",
                "Return only the required JSON object.",
            ],
        },
        ensure_ascii=True,
        indent=2,
    )


def _parse_json_object(text: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None


def _normalize_memory_review(parsed: dict[str, Any]) -> dict[str, Any]:
    candidates = parsed.get("candidates")
    normalized_candidates: list[dict[str, Any]] = []
    if isinstance(candidates, list):
        for candidate in candidates[:20]:
            if not isinstance(candidate, dict):
                continue
            content = _string(candidate.get("content"))
            if not content:
                continue
            normalized_candidates.append(
                {
                    "type": _string(candidate.get("type")) or "task_context",
                    "scope": _string(candidate.get("scope")) or "session",
                    "content": content[:2000],
                    "reason_for_storage": _string(candidate.get("reason_for_storage"))
                    or "Idle memory review identified this as future-useful.",
                    "expected_future_use": _string(candidate.get("expected_future_use")),
                    "confidence": _score(candidate.get("confidence"), default=0.7),
                    "salience": _score(candidate.get("salience"), default=0.7),
                    "tags": _list_of_strings(candidate.get("tags"))[:12],
                    "evidence": _string(candidate.get("evidence")),
                    "write_recommended": bool(candidate.get("write_recommended")),
                }
            )
    return {
        "summary": _string(parsed.get("summary")) or "Memory review completed.",
        "candidate_count": len(normalized_candidates),
        "candidates": normalized_candidates,
        "skipped_reason": _string(parsed.get("skipped_reason")),
    }


def _string(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _score(value: Any, *, default: float) -> float:
    if isinstance(value, (float, int)):
        return max(0.0, min(1.0, float(value)))
    return default


def _list_of_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]
