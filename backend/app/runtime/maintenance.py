import json
import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.config import Settings
from app.llm.factory import active_provider_max_tokens
from app.llm.provider import LLMConfigurationError, LLMProvider, LLMRequestError
from app.mind.episodic import handle_session_summarize
from app.mind.memory import (
    MindAPIContext,
    apply_create_memory_proposal,
    create_memory_proposal_from_review_candidate,
    memory_proposal_payload,
)
from app.runtime.events import record_event
from app.storage import repositories
from app.storage.models import MaintenanceJob, utc_now


SESSION_IDLE_MAINTENANCE_KIND = "session.idle_maintenance"
SESSION_SUMMARY_REPAIR_KIND = "session.summary_repair"
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
      "tags": ["tag"],
      "evidence": "short transcript-grounded evidence",
      "source_message_ids": ["msg_..."],
      "write_recommended": true
    }
  ],
  "skipped_reason": null
}
"""

PROPOSAL_RESOLUTION_SYSTEM_PROMPT = """You resolve Scarlet memory maintenance proposals.

You are not speaking to the user. Return only one JSON object.

Goal: decide only the ambiguous proposal items provided by backend maintenance.
Be conservative. Do not invent facts. Prefer keep_pending when evidence is
insufficient, similar memories may need merge/update/deprecation, or the
proposal contains sensitive or unsupported content.

Allowed outcomes:
- apply_create: create a new active memory only when the proposal is directly
  source-supported, not a duplicate, and safe to store.
- reject: archive as not useful/noisy/unsupported.
- noop_duplicate: archive because an equivalent memory already exists.
- keep_pending: leave for future Dream/human review.

Required JSON shape:

{
  "summary": "short resolver finding",
  "decisions": [
    {
      "proposal_id": "prop_...",
      "outcome": "apply_create|reject|noop_duplicate|keep_pending",
      "reason": "short source-grounded reason",
      "confidence": 0.0
    }
  ]
}
"""

SAFE_AUTO_CREATE_MIN_ACTION_CONFIDENCE = 0.8
LLM_APPLY_CREATE_MIN_CONFIDENCE = 0.85


ProviderFactory = Callable[[Settings], LLMProvider]


@dataclass(frozen=True)
class MaintenanceJobRef:
    id: str
    kind: str
    session_id: str
    trigger_turn_id: str | None
    trigger_event_id: str | None
    input_payload: dict[str, Any]


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
        if any(job.status in {"pending", "running", "completed"} for job in matching_jobs):
            continue
        attempt = len(matching_jobs) + 1
        if attempt > settings.summary_reconcile_max_attempts:
            continue
        delay = 0
        if attempt > 1:
            delay = settings.summary_reconcile_retry_backoff_seconds * (2 ** (attempt - 2))
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
        if classification in {"missing", "stale"} and state.latest_turn_status != "completed":
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


def memory_provenance_audit(
    db: Session,
    *,
    apply: bool = False,
    limit: int | None = None,
) -> dict[str, Any]:
    """Classify and optionally repair source-message hooks without guessing."""

    memories = repositories.list_all_memories(db, include_low_confidence=True)
    items: list[dict[str, Any]] = []
    repaired = 0
    for memory in memories:
        if limit is not None and len(items) >= limit:
            break
        classification = "complete"
        candidate_message_id: str | None = None
        evidence = "source session and message are already present"
        old_source_message_id = memory.source_message_id
        if memory.source_session_id is None or memory.source_turn_id is None:
            classification = "unresolved_missing_session_or_turn"
            evidence = "memory lacks a persisted source session or turn hook"
        elif memory.source_message_id is not None:
            source_message = repositories.get_message(db, memory.source_message_id)
            if (
                source_message is None
                or source_message.session_id != memory.source_session_id
                or source_message.turn_id != memory.source_turn_id
            ):
                classification = "unresolved_invalid_source_message"
                evidence = "stored source message does not resolve inside the source turn"
        else:
            user_messages = [
                message
                for message in repositories.list_messages_for_turn(
                    db,
                    turn_id=memory.source_turn_id,
                )
                if message.role == "user"
                and message.session_id == memory.source_session_id
            ]
            if len(user_messages) == 1:
                classification = "repairable_single_user_message"
                candidate_message_id = user_messages[0].id
                evidence = "exactly one persisted user message exists in the source turn"
            else:
                classification = "unresolved_ambiguous_source_turn"
                evidence = f"source turn contains {len(user_messages)} matching user messages"
        if apply and candidate_message_id is not None:
            repositories.update_memory_source_message(
                db,
                memory_id=memory.id,
                source_message_id=candidate_message_id,
            )
            classification = "repaired"
            repaired += 1
        items.append(
            {
                "memory_id": memory.id,
                "scope": memory.scope,
                "status": memory.status,
                "classification": classification,
                "source_session_id": memory.source_session_id,
                "source_turn_id": memory.source_turn_id,
                "old_source_message_id": old_source_message_id,
                "proposed_source_message_id": candidate_message_id,
                "evidence": evidence,
            }
        )
    counts: dict[str, int] = {}
    counts_by_scope: dict[str, dict[str, int]] = {}
    for item in items:
        key = str(item["classification"])
        counts[key] = counts.get(key, 0) + 1
        scope = str(item["scope"])
        scope_counts = counts_by_scope.setdefault(scope, {})
        scope_counts[key] = scope_counts.get(key, 0) + 1
    return {
        "apply": apply,
        "checked": len(items),
        "repaired": repaired,
        "counts": counts,
        "counts_by_scope": counts_by_scope,
        "items": items,
    }


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


def _run_summary_repair(
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
    result = _run_idle_summary(
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
        valid_message_ids = {
            message.id
            for message in messages
            if message.role in {"user", "assistant"}
        }
        parsed = _normalize_memory_review(
            parsed,
            valid_message_ids=valid_message_ids,
        )
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
                "mode": "proposal_pipeline",
            },
        )
        proposal_payloads: list[dict[str, Any]] = []
        proposal_created_count = 0
        if ok:
            proposal_context = MindAPIContext(
                engine=engine,
                session_id=job.session_id,
                turn_id=job.trigger_turn_id,
                settings=settings,
                provider_factory=provider_factory,
            )
            for index, candidate in enumerate(parsed.get("candidates", [])):
                if not isinstance(candidate, dict) or not candidate.get(
                    "write_recommended"
                ):
                    continue
                proposal, created = create_memory_proposal_from_review_candidate(
                    db,
                    candidate=candidate,
                    context=proposal_context,
                    source_trace_id=trace.id,
                    maintenance_job_id=job.id,
                    candidate_index=index,
                )
                proposal_payloads.append(
                    {
                        "id": proposal.id,
                        "status": proposal.status,
                        "proposed_action": proposal.proposed_action,
                        "risk": proposal.risk,
                        "created": created,
                    }
                )
                if created:
                    proposal_created_count += 1
        trace_id = trace.id

    resolution = (
        _resolve_memory_review_proposals(
            engine,
            settings=settings,
            provider=provider,
            job=job,
            proposal_ids=[item["id"] for item in proposal_payloads],
            source_trace_id=trace_id,
        )
        if ok
        else _empty_resolution_result()
    )

    with Session(engine) as db:
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
                "mode": "proposal_pipeline",
                "proposal_count": len(proposal_payloads),
                "proposal_created_count": proposal_created_count,
                "proposal_ids": [item["id"] for item in proposal_payloads],
                "resolution": resolution,
            },
            source="maintenance",
            actor="backend",
            visibility="debug",
            status="completed" if ok else "failed",
            trace_id=trace_id,
        )
        event_id = event.id

    return {
        "ok": ok,
        "review": parsed,
        "proposals": proposal_payloads,
        "resolution": resolution,
        "trace_id": trace_id,
        "event_id": event_id,
    }


def _empty_resolution_result() -> dict[str, Any]:
    return {
        "auto_archived_count": 0,
        "auto_applied_count": 0,
        "llm_reviewed_count": 0,
        "llm_applied_count": 0,
        "pending_review_count": 0,
        "resolver_called": False,
        "decisions": [],
    }


def _resolve_memory_review_proposals(
    engine: Engine,
    *,
    settings: Settings,
    provider: LLMProvider,
    job: MaintenanceJobRef,
    proposal_ids: list[str],
    source_trace_id: str,
) -> dict[str, Any]:
    result = _empty_resolution_result()
    if not proposal_ids:
        return result

    ambiguous_ids: list[str] = []
    decisions: list[dict[str, Any]] = []
    with Session(engine) as db:
        for proposal_id in proposal_ids:
            proposal = repositories.get_memory_proposal(db, proposal_id)
            if proposal is None or proposal.status != "pending":
                continue
            if proposal.proposed_action == "reject_candidate":
                resolved = _resolve_proposal_without_memory(
                    db,
                    proposal=proposal,
                    status="archived_rejected",
                    resolver="deterministic_preflight",
                    outcome="reject",
                    reason=proposal.decision_json.get("reason")
                    or "preflight rejected the candidate",
                )
                if resolved is not None:
                    result["auto_archived_count"] += 1
                    decisions.append(_proposal_decision_payload(resolved))
                continue
            if proposal.proposed_action == "noop_duplicate":
                resolved = _resolve_proposal_without_memory(
                    db,
                    proposal=proposal,
                    status="archived_noop_duplicate",
                    resolver="deterministic_preflight",
                    outcome="noop_duplicate",
                    reason=proposal.decision_json.get("reason")
                    or "preflight found an equivalent active memory or fact",
                )
                if resolved is not None:
                    result["auto_archived_count"] += 1
                    decisions.append(_proposal_decision_payload(resolved))
                continue
            if _safe_auto_create(proposal):
                _, resolved = apply_create_memory_proposal(
                    db,
                    proposal=proposal,
                    resolver="deterministic_preflight",
                    reason="high-confidence create_new proposal passed conservative auto-apply gates",
                )
                result["auto_applied_count"] += 1
                decisions.append(_proposal_decision_payload(resolved))
                continue
            ambiguous_ids.append(proposal.id)

    if not ambiguous_ids:
        result["decisions"] = decisions
        return result

    try:
        prompt = _build_proposal_resolution_prompt(engine, proposal_ids=ambiguous_ids)
        llm_result = provider.generate_text(
            prompt=prompt,
            system=PROPOSAL_RESOLUTION_SYSTEM_PROMPT,
            max_tokens=active_provider_max_tokens(settings),
        )
        parsed = _parse_json_object(llm_result.text)
        if parsed is None:
            raise ValueError("proposal resolver did not return valid JSON")
        resolver_payload = _normalize_proposal_resolution(parsed, ambiguous_ids)
        resolver_error = None
    except Exception as exc:  # keep maintenance useful if optional resolution fails
        resolver_payload = {
            "summary": "Proposal resolver failed; ambiguous proposals remain pending review.",
            "decisions": [
                {
                    "proposal_id": proposal_id,
                    "outcome": "keep_pending",
                    "reason": str(exc),
                    "confidence": 0.0,
                }
                for proposal_id in ambiguous_ids
            ],
        }
        resolver_error = str(exc)
        llm_result = None

    with Session(engine) as db:
        trace = repositories.add_trace(
            db,
            session_id=job.session_id,
            turn_id=job.trigger_turn_id,
            kind="maintenance.memory_proposal_resolution",
            payload={
                "operation": "maintenance.memory_proposal_resolution",
                "job_id": job.id,
                "source_trace_id": source_trace_id,
                "proposal_ids": ambiguous_ids,
                "resolver": resolver_payload,
                "provider": {
                    "model": llm_result.model if llm_result is not None else None,
                    "usage": llm_result.usage if llm_result is not None else None,
                    "provider_message_id": (
                        llm_result.provider_message_id
                        if llm_result is not None
                        else None
                    ),
                    "stop_reason": (
                        llm_result.stop_reason if llm_result is not None else None
                    ),
                },
                "error": resolver_error,
            },
        )
        result["resolver_called"] = True
        result["llm_reviewed_count"] = len(ambiguous_ids)
        for decision in resolver_payload["decisions"]:
            proposal = repositories.get_memory_proposal(
                db,
                str(decision["proposal_id"]),
            )
            if proposal is None or proposal.status != "pending":
                continue
            resolved = _apply_resolver_decision(
                db,
                proposal=proposal,
                decision=decision,
                resolver_trace_id=trace.id,
            )
            if resolved is None:
                continue
            if resolved.status == "applied_create":
                result["llm_applied_count"] += 1
            if resolved.status == "pending_review":
                result["pending_review_count"] += 1
            decisions.append(_proposal_decision_payload(resolved))

    result["decisions"] = decisions
    return result


def _safe_auto_create(proposal: Any) -> bool:
    decision = proposal.decision_json or {}
    return (
        proposal.proposed_action == "create_new"
        and proposal.action_confidence >= SAFE_AUTO_CREATE_MIN_ACTION_CONFIDENCE
        and bool(proposal.evidence)
        and not proposal.similar_memory_ids_json
        and not decision.get("conflicting_fact_ids")
        and not decision.get("matching_fact_ids")
    )


def _build_proposal_resolution_prompt(
    engine: Engine,
    *,
    proposal_ids: list[str],
) -> str:
    with Session(engine) as db:
        proposals = [
            proposal
            for proposal_id in proposal_ids
            if (proposal := repositories.get_memory_proposal(db, proposal_id))
            is not None
        ]
        source_session_ids = sorted(
            {proposal.source_session_id for proposal in proposals if proposal.source_session_id}
        )
        transcripts = {}
        for session_id in source_session_ids:
            transcripts[session_id] = [
                {
                    "id": message.id,
                    "role": message.role,
                    "content": message.content,
                    "turn_id": message.turn_id,
                }
                for message in repositories.list_messages(db, session_id=session_id)
                if message.role in {"user", "assistant"}
            ]
        payload = {
            "task": "Resolve ambiguous memory proposals produced by idle maintenance.",
            "rules": [
                "Use apply_create only for directly source-supported new memories.",
                "Use keep_pending for possible merge, update, deprecation, stale-memory, or uncertain cases.",
                "Use reject for unsupported, noisy, too private, or one-off candidates.",
                "Use noop_duplicate only when an equivalent active memory is already present.",
            ],
            "proposals": [memory_proposal_payload(proposal) for proposal in proposals],
            "source_transcripts": transcripts,
        }
    return json.dumps(payload, ensure_ascii=True, indent=2)


def _normalize_proposal_resolution(
    parsed: dict[str, Any],
    proposal_ids: list[str],
) -> dict[str, Any]:
    allowed_ids = set(proposal_ids)
    allowed_outcomes = {"apply_create", "reject", "noop_duplicate", "keep_pending"}
    decisions: list[dict[str, Any]] = []
    raw_decisions = parsed.get("decisions")
    if isinstance(raw_decisions, list):
        for item in raw_decisions[: len(proposal_ids)]:
            if not isinstance(item, dict):
                continue
            proposal_id = _string(item.get("proposal_id"))
            if proposal_id not in allowed_ids:
                continue
            outcome = _string(item.get("outcome")) or "keep_pending"
            if outcome not in allowed_outcomes:
                outcome = "keep_pending"
            decisions.append(
                {
                    "proposal_id": proposal_id,
                    "outcome": outcome,
                    "reason": _string(item.get("reason")) or "No reason provided.",
                    "confidence": _score(item.get("confidence"), default=0.0),
                }
            )
    covered = {item["proposal_id"] for item in decisions}
    for proposal_id in proposal_ids:
        if proposal_id not in covered:
            decisions.append(
                {
                    "proposal_id": proposal_id,
                    "outcome": "keep_pending",
                    "reason": "Resolver omitted this proposal.",
                    "confidence": 0.0,
                }
            )
    return {
        "summary": _string(parsed.get("summary"))
        or "Proposal resolver completed.",
        "decisions": decisions,
    }


def _apply_resolver_decision(
    db: Session,
    *,
    proposal: Any,
    decision: dict[str, Any],
    resolver_trace_id: str,
) -> Any | None:
    outcome = decision["outcome"]
    confidence = float(decision.get("confidence") or 0.0)
    reason = str(decision.get("reason") or "No reason provided.")
    if outcome == "apply_create" and _llm_can_apply_create(proposal, confidence):
        _, resolved = apply_create_memory_proposal(
            db,
            proposal=proposal,
            resolver="llm_proposal_resolution",
            reason=reason,
            decision={**decision, "resolver_trace_id": resolver_trace_id},
        )
        return resolved
    if outcome == "noop_duplicate":
        return _resolve_proposal_without_memory(
            db,
            proposal=proposal,
            status="archived_noop_duplicate",
            resolver="llm_proposal_resolution",
            outcome="noop_duplicate",
            reason=reason,
            decision={**decision, "resolver_trace_id": resolver_trace_id},
        )
    if outcome == "reject":
        return _resolve_proposal_without_memory(
            db,
            proposal=proposal,
            status="archived_rejected",
            resolver="llm_proposal_resolution",
            outcome="reject",
            reason=reason,
            decision={**decision, "resolver_trace_id": resolver_trace_id},
        )
    keep_reason = (
        reason
        if outcome == "keep_pending"
        else f"{reason} Auto-apply gates rejected outcome {outcome}."
    )
    return _resolve_proposal_without_memory(
        db,
        proposal=proposal,
        status="pending_review",
        resolver="llm_proposal_resolution",
        outcome="keep_pending",
        reason=keep_reason,
        decision={**decision, "resolver_trace_id": resolver_trace_id},
    )


def _llm_can_apply_create(proposal: Any, confidence: float) -> bool:
    decision = proposal.decision_json or {}
    return (
        confidence >= LLM_APPLY_CREATE_MIN_CONFIDENCE
        and proposal.proposed_action == "create_new"
        and not proposal.similar_memory_ids_json
        and not decision.get("conflicting_fact_ids")
        and not decision.get("matching_fact_ids")
    )


def _resolve_proposal_without_memory(
    db: Session,
    *,
    proposal: Any,
    status: str,
    resolver: str,
    outcome: str,
    reason: str,
    decision: dict[str, Any] | None = None,
) -> Any | None:
    return repositories.resolve_memory_proposal(
        db,
        proposal_id=proposal.id,
        status=status,
        result={
            "resolution": {
                "resolver": resolver,
                "outcome": outcome,
                "reason": reason,
                "decision": decision or {},
                "decided_at": _isoformat(utc_now()),
            },
            "preflight_snapshot": proposal.decision_json,
            "dream_review_candidate": True,
        },
    )


def _proposal_decision_payload(proposal: Any) -> dict[str, Any]:
    resolution = proposal.result_json.get("resolution", {})
    return {
        "proposal_id": proposal.id,
        "status": proposal.status,
        "outcome": resolution.get("outcome"),
        "resolver": resolution.get("resolver"),
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


def _normalize_memory_review(
    parsed: dict[str, Any],
    *,
    valid_message_ids: set[str],
) -> dict[str, Any]:
    candidates = parsed.get("candidates")
    normalized_candidates: list[dict[str, Any]] = []
    if isinstance(candidates, list):
        for candidate in candidates[:20]:
            if not isinstance(candidate, dict):
                continue
            content = _string(candidate.get("content"))
            if not content:
                continue
            source_message_ids = [
                message_id
                for message_id in _list_of_strings(
                    candidate.get("source_message_ids")
                )
                if message_id in valid_message_ids
            ]
            normalized_candidates.append(
                {
                    "type": _string(candidate.get("type")) or "task_context",
                    "scope": _string(candidate.get("scope")) or "session",
                    "content": content[:2000],
                    "reason_for_storage": _string(candidate.get("reason_for_storage"))
                    or "Idle memory review identified this as future-useful.",
                    "expected_future_use": _string(candidate.get("expected_future_use")),
                    "tags": _list_of_strings(candidate.get("tags"))[:12],
                    "evidence": _string(candidate.get("evidence")),
                    "source_message_ids": source_message_ids,
                    "write_recommended": bool(candidate.get("write_recommended"))
                    and bool(source_message_ids),
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


def _isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _list_of_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]
