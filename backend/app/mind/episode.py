"""Scarlet-owned cognitive episode lifecycle over the shared Mind shell."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any

from sqlmodel import Session

from app.mind.contracts import MindAPIContext, MemoryOperationResult
from app.runtime.events import record_event
from app.storage import repositories
from app.storage.models import ChatSession


FINAL_EPISODE_STATUSES = {"resolved", "abandoned", "invalidated"}


def handle_episode(
    body: dict[str, Any],
    context: MindAPIContext | None,
    *,
    intent: str,
) -> MemoryOperationResult:
    if context is None or context.session_id is None:
        return _error(
            "episode.context_required",
            "Episode operations require an active Scarlet session.",
        )
    action = str(body.get("action") or "list").strip().casefold().replace("-", "_")
    with Session(context.engine) as db:
        chat_session = db.get(ChatSession, context.session_id)
        if chat_session is None:
            return _error("episode.session_not_found", "Active session was not found.")
        profile_id = chat_session.profile_id
        try:
            if action == "list":
                episodes = repositories.list_episodes(
                    db,
                    profile_id=profile_id,
                    status=_text(body, "status"),
                    limit=_limit(body),
                )
                return _ok(
                    "episode.list",
                    {"episodes": [_episode_payload(db, item) for item in episodes]},
                    "Episodes are bounded inquiries, not a second memory or focus store.",
                )
            if action in {"read", "open"} and body.get("episode_id"):
                episode = _owned_episode(db, profile_id, _required(body, "episode_id"))
                return _ok(
                    "episode.read",
                    {"episode": _episode_payload(db, episode)},
                    "Inspect source references before treating an episode claim as fact.",
                )
            if action == "open":
                candidate_ids = _strings(body.get("candidate_ids"))
                if not candidate_ids:
                    return _error(
                        "episode.candidate_required",
                        "Opening an episode requires at least one source-backed candidate.",
                    )
                candidates = []
                for candidate_id in candidate_ids:
                    candidate = repositories.get_candidate(db, candidate_id)
                    if candidate is None or candidate.profile_id != profile_id:
                        return _error(
                            "episode.candidate_not_found",
                            f"Candidate not found for this profile: {candidate_id}",
                        )
                    candidates.append(candidate)
                question = _text(body, "question") or candidates[0].cognitive_question
                transformation = (
                    _text(body, "expected_transformation")
                    or candidates[0].expected_transformation
                )
                episode = repositories.create_episode(
                    db,
                    profile_id=profile_id,
                    question=question,
                    expected_transformation=transformation,
                    candidate_ids=candidate_ids,
                    source_session_id=context.session_id,
                    source_turn_id=context.turn_id,
                    started_by="scarlet",
                    metadata={"intent": intent, "runtime_trigger": context.runtime_trigger},
                )
                _episode_event(
                    db,
                    context=context,
                    event_type="cognition.episode.opened",
                    episode_id=episode.id,
                    payload={"candidate_ids": candidate_ids, "question": question},
                )
                return _ok(
                    "episode.open",
                    {"episode": _episode_payload(db, episode)},
                    "The episode is now Scarlet's bounded inquiry.",
                )
            if action == "checkpoint":
                episode = _owned_episode(db, profile_id, _required(body, "episode_id"))
                progress = _required(body, "progress")
                activation = (
                    repositories.get_autonomous_activation_by_turn(
                        db,
                        turn_id=context.turn_id,
                    )
                    if context.turn_id is not None
                    else None
                )
                step = repositories.add_episode_step(
                    db,
                    episode_id=episode.id,
                    activation_id=activation.id if activation is not None else None,
                    turn_id=context.turn_id,
                    progress_summary=progress,
                    next_step=_text(body, "next_step"),
                    state_deltas=_dicts(body.get("state_deltas")),
                    source_refs=_strings(body.get("source_refs")),
                    no_progress=bool(body.get("no_progress", False)),
                )
                _episode_event(
                    db,
                    context=context,
                    event_type="cognition.episode.checkpointed",
                    episode_id=episode.id,
                    payload={"step_id": step.id, "no_progress": step.no_progress},
                )
                return _ok(
                    "episode.checkpoint",
                    {"episode": _episode_payload(db, episode), "step_id": step.id},
                    "A checkpoint records change or explicit non-progress without inventing importance.",
                )
            if action in {"suspend", "resume", "resolve", "abandon"}:
                episode = _owned_episode(db, profile_id, _required(body, "episode_id"))
                if action == "resume":
                    updated = repositories.update_episode(
                        db,
                        episode_id=episode.id,
                        status="active",
                        suspended_until=None,
                        resume_condition="resumed by Scarlet",
                    )
                elif action == "suspend":
                    resume_at = _optional_datetime(body.get("resume_at"))
                    resume_event = _text(body, "resume_event")
                    reason = _required(body, "reason")
                    updated = repositories.update_episode(
                        db,
                        episode_id=episode.id,
                        status="suspended",
                        suspended_until=resume_at,
                        resume_condition=resume_event or reason,
                        stop_reason=reason,
                    )
                    if resume_at is not None:
                        _create_condition(
                            db,
                            profile_id=profile_id,
                            episode_id=episode.id,
                            kind="at_time",
                            predicate={"at": resume_at.isoformat()},
                            not_before=resume_at,
                        )
                    if resume_event is not None:
                        _create_condition(
                            db,
                            profile_id=profile_id,
                            episode_id=episode.id,
                            kind="on_event",
                            predicate={"event_type": resume_event},
                        )
                else:
                    resolution = _required(body, "resolution")
                    updated = repositories.update_episode(
                        db,
                        episode_id=episode.id,
                        status="resolved" if action == "resolve" else "abandoned",
                        resolution=resolution,
                        stop_reason=_text(body, "reason") or resolution,
                    )
                    for link in repositories.list_episode_candidates(
                        db,
                        episode_id=episode.id,
                    ):
                        repositories.update_candidate(
                            db,
                            candidate_id=link.candidate_id,
                            status="resolved" if action == "resolve" else "rejected",
                            resolution=resolution,
                        )
                lifecycle_event = {
                    "suspend": "cognition.episode.suspended",
                    "resume": "cognition.episode.resumed",
                    "resolve": "cognition.episode.resolved",
                    "abandon": "cognition.episode.abandoned",
                }[action]
                _episode_event(
                    db,
                    context=context,
                    event_type=lifecycle_event,
                    episode_id=episode.id,
                    payload={"status": updated.status},
                )
                return _ok(
                    f"episode.{action}",
                    {"episode": _episode_payload(db, updated)},
                    "Episode lifecycle changed with a traceable Scarlet decision.",
                )
            if action == "reject":
                candidate_id = _required(body, "candidate_id")
                candidate = repositories.get_candidate(db, candidate_id)
                if candidate is None or candidate.profile_id != profile_id:
                    return _error(
                        "episode.candidate_not_found",
                        f"Candidate not found for this profile: {candidate_id}",
                    )
                updated_candidate = repositories.update_candidate(
                    db,
                    candidate_id=candidate.id,
                    status="rejected",
                    resolution=_required(body, "reason"),
                )
                _episode_event(
                    db,
                    context=context,
                    event_type="cognition.candidate.rejected",
                    episode_id=None,
                    payload={
                        "candidate_id": updated_candidate.id,
                        "reason": updated_candidate.resolution,
                    },
                )
                return _ok(
                    "episode.reject",
                    {"candidate": _candidate_payload(db, updated_candidate)},
                    "The provisional candidate was rejected by Scarlet, not by the appraiser.",
                )
            if action == "expectation_add":
                episode = _owned_episode(db, profile_id, _required(body, "episode_id"))
                expectation = repositories.create_expectation(
                    db,
                    episode_id=episode.id,
                    claim=_required(body, "claim"),
                    observable_outcome=_required(body, "observable_outcome"),
                    due_at=_optional_datetime(body.get("due_at")),
                )
                return _ok(
                    "episode.expectation_add",
                    {"expectation": _expectation_payload(expectation)},
                    "The prediction is explicit and can be checked against future evidence.",
                )
            if action == "expectation_resolve":
                expectation = repositories.resolve_expectation(
                    db,
                    expectation_id=_required(body, "expectation_id"),
                    status=_text(body, "status") or "resolved",
                    evaluation=_required(body, "evaluation"),
                    outcome_refs=_strings(body.get("outcome_refs")),
                )
                return _ok(
                    "episode.expectation_resolve",
                    {"expectation": _expectation_payload(expectation)},
                    "The prediction outcome remains linked to its evidence references.",
                )
            if action == "wake_list":
                conditions = repositories.list_pending_wake_conditions(
                    db,
                    profile_id=profile_id,
                    limit=_limit(body),
                )
                return _ok(
                    "episode.wake_list",
                    {"wake_conditions": [_condition_payload(item) for item in conditions]},
                    "Only explicit pending wake contracts are listed.",
                )
            if action == "wake_add":
                episode_id = _text(body, "episode_id")
                if episode_id is not None:
                    _owned_episode(db, profile_id, episode_id)
                at = _optional_datetime(body.get("at"))
                event_type = _text(body, "event_type")
                if at is None and event_type is None:
                    return _error(
                        "episode.wake_contract_required",
                        "wake-add requires --at or an exact --event-type.",
                    )
                kind = "at_time" if at is not None else "on_event"
                predicate = (
                    {"at": at.isoformat()}
                    if at is not None
                    else {"event_type": event_type}
                )
                condition = _create_condition(
                    db,
                    profile_id=profile_id,
                    episode_id=episode_id,
                    kind=kind,
                    predicate=predicate,
                    not_before=at,
                )
                return _ok(
                    "episode.wake_add",
                    {"wake_condition": _condition_payload(condition)},
                    "The wake condition is deterministic and inspectable.",
                )
            if action == "wake_cancel":
                condition = repositories.get_wake_condition(
                    db,
                    _required(body, "condition_id"),
                )
                if condition is None or condition.profile_id != profile_id:
                    return _error(
                        "episode.wake_condition_not_found",
                        "Wake condition was not found for this profile.",
                    )
                updated_condition = repositories.update_wake_condition(
                    db,
                    condition_id=condition.id,
                    status="cancelled",
                )
                return _ok(
                    "episode.wake_cancel",
                    {"wake_condition": _condition_payload(updated_condition)},
                    "The wake contract was cancelled without deleting its history.",
                )
        except ValueError as exc:
            return _error("episode.invalid_request", str(exc))
    return _error(
        "episode.action_not_supported",
        f"Unsupported episode action: {action}",
    )


def _owned_episode(db: Session, profile_id: str, episode_id: str) -> Any:
    episode = repositories.get_episode(db, episode_id)
    if episode is None or episode.profile_id != profile_id:
        raise ValueError(f"Episode not found for this profile: {episode_id}")
    return episode


def _create_condition(
    db: Session,
    *,
    profile_id: str,
    episode_id: str | None,
    kind: str,
    predicate: dict[str, Any],
    not_before: datetime | None = None,
) -> Any:
    digest = hashlib.sha256(
        json.dumps(
            {
                "profile_id": profile_id,
                "episode_id": episode_id,
                "kind": kind,
                "predicate": predicate,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    condition, _ = repositories.create_wake_condition(
        db,
        profile_id=profile_id,
        episode_id=episode_id,
        kind=kind,
        condition_key=f"wake:{digest}",
        predicate=predicate,
        not_before=not_before,
    )
    return condition


def _episode_event(
    db: Session,
    *,
    context: MindAPIContext,
    event_type: str,
    episode_id: str | None,
    payload: dict[str, Any],
) -> None:
    record_event(
        db,
        session_id=context.session_id or "",
        turn_id=context.turn_id,
        event_type=event_type,
        payload={"episode_id": episode_id, **payload},
        source="mind.episode",
        actor="scarlet",
        visibility="private",
    )


def _episode_payload(db: Session, episode: Any) -> dict[str, Any]:
    candidate_links = repositories.list_episode_candidates(db, episode_id=episode.id)
    steps = repositories.list_episode_steps(db, episode_id=episode.id, limit=20)
    expectations = repositories.list_expectations(db, episode_id=episode.id)
    return {
        "id": episode.id,
        "status": episode.status,
        "question": episode.question,
        "expected_transformation": episode.expected_transformation,
        "candidate_ids": [item.candidate_id for item in candidate_links],
        "source_session_id": episode.source_session_id,
        "source_turn_id": episode.source_turn_id,
        "last_progress_at": _iso(episode.last_progress_at),
        "suspended_until": _iso(episode.suspended_until),
        "resume_condition": episode.resume_condition,
        "resolution": episode.resolution,
        "stop_reason": episode.stop_reason,
        "created_at": episode.created_at.isoformat(),
        "updated_at": episode.updated_at.isoformat(),
        "steps": [
            {
                "id": item.id,
                "progress": item.progress_summary,
                "next_step": item.next_step,
                "source_refs": item.source_refs_json,
                "no_progress": item.no_progress,
                "created_at": item.created_at.isoformat(),
            }
            for item in steps
        ],
        "expectations": [_expectation_payload(item) for item in expectations],
    }


def _candidate_payload(db: Session, candidate: Any) -> dict[str, Any]:
    return {
        "id": candidate.id,
        "status": candidate.status,
        "kind": candidate.candidate_kind,
        "claim": candidate.claim,
        "cognitive_question": candidate.cognitive_question,
        "expected_transformation": candidate.expected_transformation,
        "source_refs": [
            f"{item.source_kind}:{item.source_id}"
            for item in repositories.list_candidate_sources(
                db,
                candidate_id=candidate.id,
            )
        ],
    }


def _expectation_payload(expectation: Any) -> dict[str, Any]:
    return {
        "id": expectation.id,
        "status": expectation.status,
        "claim": expectation.claim,
        "observable_outcome": expectation.observable_outcome,
        "due_at": _iso(expectation.due_at),
        "evaluation": expectation.evaluation,
        "outcome_refs": expectation.outcome_refs_json,
    }


def _condition_payload(condition: Any) -> dict[str, Any]:
    return {
        "id": condition.id,
        "status": condition.status,
        "kind": condition.kind,
        "episode_id": condition.episode_id,
        "candidate_id": condition.candidate_id,
        "predicate": condition.predicate_json,
        "not_before": _iso(condition.not_before),
        "deadline": _iso(condition.deadline),
        "matched_at": _iso(condition.matched_at),
    }


def _required(body: dict[str, Any], key: str) -> str:
    value = _text(body, key)
    if value is None:
        raise ValueError(f"{key} is required")
    return value


def _text(body: dict[str, Any], key: str) -> str | None:
    value = body.get(key)
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _limit(body: dict[str, Any]) -> int:
    value = body.get("limit", 20)
    return max(1, min(int(value) if isinstance(value, int) else 20, 100))


def _optional_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValueError("datetime values must be ISO-8601 strings")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _ok(
    operation: str,
    payload: dict[str, Any],
    hint: str,
) -> MemoryOperationResult:
    return MemoryOperationResult(
        ok=True,
        result={"operation": operation, **payload},
        cognitive_hint=hint,
        confidence=1.0,
    )


def _error(code: str, message: str) -> MemoryOperationResult:
    return MemoryOperationResult(
        ok=False,
        result={"operation": "episode"},
        cognitive_hint="Inspect help episode and retry with a complete command.",
        suggested_next_actions=["Use help episode"],
        error_code=code,
        error_message=message,
        confidence=1.0,
    )
