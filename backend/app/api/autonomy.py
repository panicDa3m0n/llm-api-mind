"""Inspection and lab controls for Scarlet's autonomous cognition."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.config import Settings
from app.llm.factory import build_llm_provider
from app.runtime.autonomy import run_autonomous_activation
from app.runtime.autonomy_schedule import coalesce_autonomous_activation
from app.runtime.cognitive_workspace import run_cognitive_workspace_tick
from app.runtime.events import event_payload
from app.runtime.time import aware_utc, utc_isoformat
from app.storage import repositories
from app.storage.models import AutonomousActivation, PerceptionEvent, utc_now


class PerceptionEventInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: str = Field(min_length=1, max_length=80)
    event_type: str = Field(min_length=1, max_length=120)
    source: str = Field(min_length=1, max_length=120)
    source_event_key: str = Field(min_length=1, max_length=240)
    observed_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)
    navigation: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PerceptionBatchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[PerceptionEventInput] = Field(min_length=1, max_length=200)


def build_autonomy_router(
    engine: Engine,
    settings: Settings,
    provider_factory=build_llm_provider,
) -> APIRouter:
    router = APIRouter(prefix="/api/autonomy", tags=["autonomy"])

    @router.get("/overview")
    def overview() -> dict[str, Any]:
        with Session(engine) as db:
            session = repositories.get_or_create_autonomous_session(
                db,
                profile_id=settings.user_profile_id,
            )
            if settings.cognitive_workspace_mode == "active":
                pending = repositories.list_autonomous_activations(
                    db,
                    profile_id=settings.user_profile_id,
                    session_id=session.id,
                    status="pending",
                    limit=1,
                )
                next_activation = pending[0] if pending else None
            else:
                next_activation = repositories.ensure_next_periodic_activation(
                    db,
                    profile_id=settings.user_profile_id,
                    session_id=session.id,
                    interval_seconds=settings.autonomous_activation_interval_seconds,
                )
            recent = repositories.list_autonomous_activations(
                db,
                profile_id=settings.user_profile_id,
                session_id=session.id,
                limit=5,
            )
            channels = repositories.perception_availability_index(
                db,
                profile_id=settings.user_profile_id,
                session_id=session.id,
            )
            endogenous_window = repositories.latest_endogenous_window(
                db,
                profile_id=settings.user_profile_id,
            )
        return {
            "operation": "autonomy.overview",
            "enabled": settings.autonomous_activation_enabled,
            "legacy_periodic_interval_seconds": (
                settings.autonomous_activation_interval_seconds
            ),
            "m3_min_gap_seconds": settings.autonomous_activation_min_gap_seconds,
            "m3_max_silence_seconds": (
                settings.autonomous_activation_max_silence_seconds
            ),
            "worker_interval_seconds": (
                settings.autonomous_activation_worker_interval_seconds
            ),
            "workspace_mode": settings.cognitive_workspace_mode,
            "scarlet_model": settings.minimax_model,
            "auxiliary_model": settings.auxiliary_minimax_model,
            "session": _session_payload(session),
            "next_activation": (
                _activation_payload(next_activation)
                if next_activation is not None
                else None
            ),
            "recent_activations": [
                _activation_payload(item) for item in recent
            ],
            "perception_channels": channels,
            "endogenous_cognition": {
                "enabled": settings.endogenous_cognition_enabled,
                "minimum_interval_seconds": (
                    settings.endogenous_cognition_min_interval_seconds
                ),
                "base_interval_seconds": (
                    settings.endogenous_cognition_base_interval_seconds
                ),
                "maximum_interval_seconds": (
                    settings.endogenous_cognition_max_interval_seconds
                ),
                "latest_window": (
                    _endogenous_window_payload(endogenous_window)
                    if endogenous_window is not None
                    else None
                ),
            },
        }

    @router.get("/workspace")
    def workspace(
        limit: int = Query(default=30, ge=1, le=100),
    ) -> dict[str, Any]:
        with Session(engine) as db:
            candidates = repositories.list_candidates(
                db,
                profile_id=settings.user_profile_id,
                limit=limit,
            )
            episodes = repositories.list_episodes(
                db,
                profile_id=settings.user_profile_id,
                limit=limit,
            )
            conditions = repositories.list_wake_conditions(
                db,
                profile_id=settings.user_profile_id,
                limit=limit,
            )
            receipts = repositories.list_signal_receipts(
                db,
                profile_id=settings.user_profile_id,
                limit=limit,
            )
            arbitrations = repositories.list_arbitrations(
                db,
                profile_id=settings.user_profile_id,
                limit=limit,
            )
            endogenous_windows = repositories.list_endogenous_windows(
                db,
                profile_id=settings.user_profile_id,
                limit=limit,
            )
            return {
                "operation": "autonomy.workspace",
                "mode": settings.cognitive_workspace_mode,
                "scarlet_model": settings.minimax_model,
                "auxiliary_model": settings.auxiliary_minimax_model,
                "candidates": [
                    _workspace_candidate_payload(db, item) for item in candidates
                ],
                "episodes": [
                    _workspace_episode_payload(db, item) for item in episodes
                ],
                "wake_conditions": [
                    _wake_condition_payload(item) for item in conditions
                ],
                "signal_receipts": [
                    _signal_receipt_payload(item) for item in receipts
                ],
                "arbitrations": [
                    {
                        "id": item.id,
                        "mode": item.mode,
                        "status": item.status,
                        "authority": item.authority,
                        "model": item.model,
                        "candidate_ids": item.candidate_ids_json,
                        "selected_ids": item.selected_ids_json,
                        "decision": item.decision_json,
                        "trace_id": item.trace_id,
                        "created_at": utc_isoformat(item.created_at),
                    }
                    for item in arbitrations
                ],
                "endogenous_windows": [
                    _endogenous_window_payload(item)
                    for item in endogenous_windows
                ],
            }

    @router.post("/workspace/tick")
    def workspace_tick() -> dict[str, Any]:
        return run_cognitive_workspace_tick(
            engine,
            settings=settings,
            provider_factory=provider_factory,
        )

    @router.get("/history")
    def history(
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        with Session(engine) as db:
            session = repositories.get_or_create_autonomous_session(
                db,
                profile_id=settings.user_profile_id,
            )
            activations = repositories.list_autonomous_activations(
                db,
                profile_id=settings.user_profile_id,
                session_id=session.id,
                limit=limit + 1,
                offset=offset,
            )
            has_more = len(activations) > limit
            visible = activations[:limit]
            cycles = [
                _cycle_payload(db, activation)
                for activation in visible
            ]
        return {
            "operation": "autonomy.history",
            "session": _session_payload(session),
            "limit": limit,
            "offset": offset,
            "returned": len(cycles),
            "has_more": has_more,
            "next_offset": offset + limit if has_more else None,
            "cycles": cycles,
        }

    @router.post("/run-now")
    def run_now() -> dict[str, Any]:
        now = utc_now()
        with Session(engine) as db:
            session = repositories.get_or_create_autonomous_session(
                db,
                profile_id=settings.user_profile_id,
            )
            scheduled = coalesce_autonomous_activation(
                db,
                profile_id=settings.user_profile_id,
                session_id=session.id,
                trigger_kind="manual_lab",
                workspace={
                    "schema_version": "scarlet-cognitive-workspace-v1",
                    "authority": "manual_lab_request",
                    "selected_candidates": [],
                    "instruction": (
                        "A manual internal-cycle request is pending. Inspect the "
                        "available continuity and do not manufacture activity."
                    ),
                },
                min_gap_seconds=settings.autonomous_activation_min_gap_seconds,
                now=now,
            )
            activation = scheduled.activation
        if aware_utc(activation.scheduled_at) > aware_utc(now):
            return {
                "activation_id": activation.id,
                "status": "scheduled",
                "eligible_at": aware_utc(activation.scheduled_at).isoformat(),
            }
        return run_autonomous_activation(
            engine,
            settings=settings,
            provider_factory=provider_factory,
            activation_id=activation.id,
            now=now,
        )

    @router.post("/perception/events/batch")
    def ingest_perception_events(
        body: PerceptionBatchInput,
    ) -> dict[str, Any]:
        stored: list[dict[str, Any]] = []
        duplicates: list[str] = []
        with Session(engine) as db:
            for item in body.events:
                event, created = repositories.add_perception_event(
                    db,
                    profile_id=settings.user_profile_id,
                    channel=item.channel,
                    event_type=item.event_type,
                    source=item.source,
                    source_event_key=item.source_event_key,
                    observed_at=item.observed_at,
                    payload=item.payload,
                    navigation=item.navigation,
                    metadata=item.metadata,
                )
                stored.append(_perception_payload(event))
                if not created:
                    duplicates.append(event.id)
        return {
            "operation": "perception.events.ingest",
            "received": len(body.events),
            "stored_or_existing": len(stored),
            "duplicate_event_ids": duplicates,
            "events": stored,
        }

    return router


def _cycle_payload(
    db: Session,
    activation: AutonomousActivation,
) -> dict[str, Any]:
    messages = (
        repositories.list_messages_for_turn(db, turn_id=activation.turn_id)
        if activation.turn_id
        else []
    )
    events = (
        repositories.list_events_for_turn(db, turn_id=activation.turn_id)
        if activation.turn_id
        else []
    )
    tool_calls = (
        repositories.list_tool_calls_for_turn(db, turn_id=activation.turn_id)
        if activation.turn_id
        else []
    )
    return {
        "activation": _activation_payload(activation),
        "messages": [
            {
                "id": item.id,
                "role": item.role,
                "content": item.content,
                "created_at": utc_isoformat(item.created_at),
                "metadata": item.metadata_json,
            }
            for item in messages
        ],
        "events": [event_payload(item) for item in events],
        "tool_calls": [
            {
                "id": item.id,
                "tool_name": item.tool_name,
                "arguments": item.arguments_json,
                "result": item.result_json,
                "status": item.status,
                "latency_ms": item.latency_ms,
                "created_at": utc_isoformat(item.created_at),
            }
            for item in tool_calls
        ],
    }


def _activation_payload(activation: AutonomousActivation) -> dict[str, Any]:
    return {
        "id": activation.id,
        "profile_id": activation.profile_id,
        "session_id": activation.session_id,
        "turn_id": activation.turn_id,
        "candidate_id": activation.candidate_id,
        "episode_id": activation.episode_id,
        "wake_condition_id": activation.wake_condition_id,
        "trigger_kind": activation.trigger_kind,
        "status": activation.status,
        "active_mode": activation.active_mode,
        "scheduled_at": utc_isoformat(activation.scheduled_at),
        "started_at": utc_isoformat(activation.started_at),
        "completed_at": utc_isoformat(activation.completed_at),
        "attempt_count": activation.attempt_count,
        "outcome": activation.outcome_json,
        "workspace": activation.workspace_json,
        "error": activation.error_json,
    }


def _session_payload(session: Any) -> dict[str, Any]:
    return {
        "id": session.id,
        "title": session.title,
        "kind": session.kind,
        "profile_id": session.profile_id,
        "created_at": utc_isoformat(session.created_at),
        "updated_at": utc_isoformat(session.updated_at),
    }


def _perception_payload(event: PerceptionEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "channel": event.channel,
        "event_type": event.event_type,
        "source": event.source,
        "observed_at": utc_isoformat(event.observed_at),
        "received_at": utc_isoformat(event.received_at),
    }


def _workspace_candidate_payload(db: Session, candidate: Any) -> dict[str, Any]:
    return {
        "id": candidate.id,
        "status": candidate.status,
        "kind": candidate.candidate_kind,
        "context_family": candidate.context_family,
        "claim": candidate.claim,
        "why_now": candidate.why_now,
        "cognitive_question": candidate.cognitive_question,
        "expected_transformation": candidate.expected_transformation,
        "uncertainty": candidate.uncertainty,
        "deferral_count": candidate.deferral_count,
        "deferred_until": utc_isoformat(candidate.deferred_until),
        "selected_episode_id": candidate.selected_episode_id,
        "source_refs": [
            f"{item.source_kind}:{item.source_id}"
            for item in repositories.list_candidate_sources(
                db,
                candidate_id=candidate.id,
            )
        ],
        "appraisal_model": candidate.appraisal_model,
        "appraisal_trace_id": candidate.appraisal_trace_id,
        "created_at": utc_isoformat(candidate.created_at),
        "updated_at": utc_isoformat(candidate.updated_at),
    }


def _workspace_episode_payload(db: Session, episode: Any) -> dict[str, Any]:
    return {
        "id": episode.id,
        "status": episode.status,
        "question": episode.question,
        "expected_transformation": episode.expected_transformation,
        "candidate_ids": [
            item.candidate_id
            for item in repositories.list_episode_candidates(
                db,
                episode_id=episode.id,
            )
        ],
        "last_progress_at": utc_isoformat(episode.last_progress_at),
        "suspended_until": utc_isoformat(episode.suspended_until),
        "resume_condition": episode.resume_condition,
        "resolution": episode.resolution,
        "stop_reason": episode.stop_reason,
        "created_at": utc_isoformat(episode.created_at),
        "updated_at": utc_isoformat(episode.updated_at),
    }


def _wake_condition_payload(condition: Any) -> dict[str, Any]:
    return {
        "id": condition.id,
        "status": condition.status,
        "kind": condition.kind,
        "episode_id": condition.episode_id,
        "candidate_id": condition.candidate_id,
        "predicate": condition.predicate_json,
        "not_before": utc_isoformat(condition.not_before),
        "deadline": utc_isoformat(condition.deadline),
        "matched_event_id": condition.matched_event_id,
        "matched_at": utc_isoformat(condition.matched_at),
    }


def _signal_receipt_payload(receipt: Any) -> dict[str, Any]:
    return {
        "id": receipt.id,
        "source_kind": receipt.source_kind,
        "source_key": receipt.source_key,
        "source_type": receipt.source_type,
        "policy": receipt.policy,
        "disposition": receipt.disposition,
        "candidate_id": receipt.candidate_id,
        "episode_id": receipt.episode_id,
        "registry_version": receipt.registry_version,
        "observed_at": utc_isoformat(receipt.observed_at),
        "processed_at": utc_isoformat(receipt.processed_at),
    }


def _endogenous_window_payload(window: Any) -> dict[str, Any]:
    return {
        "id": window.id,
        "schedule_key": window.schedule_key,
        "profile_id": window.profile_id,
        "status": window.status,
        "opened_at": utc_isoformat(window.opened_at),
        "closed_at": utc_isoformat(window.closed_at),
        "cadence_seconds": window.cadence_seconds,
        "next_window_at": utc_isoformat(window.next_window_at),
        "consecutive_empty_windows": window.consecutive_empty_windows,
        "source_refs": window.source_refs_json,
        "candidate_ids": window.candidate_ids_json,
        "activation_id": window.activation_id,
        "trace_id": window.trace_id,
        "outcome": window.outcome_json,
    }
