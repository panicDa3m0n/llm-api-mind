"""Inspection and lab controls for Scarlet's autonomous cognition."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.config import Settings
from app.llm.factory import build_llm_provider
from app.runtime.autonomy import run_autonomous_activation
from app.runtime.events import event_payload
from app.runtime.time import utc_isoformat
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
        return {
            "operation": "autonomy.overview",
            "enabled": settings.autonomous_activation_enabled,
            "interval_seconds": settings.autonomous_activation_interval_seconds,
            "worker_interval_seconds": (
                settings.autonomous_activation_worker_interval_seconds
            ),
            "session": _session_payload(session),
            "next_activation": _activation_payload(next_activation),
            "recent_activations": [
                _activation_payload(item) for item in recent
            ],
            "perception_channels": channels,
        }

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
            activation = repositories.schedule_autonomous_activation(
                db,
                profile_id=settings.user_profile_id,
                session_id=session.id,
                scheduled_at=now,
                trigger_kind="manual_lab",
                schedule_key=(
                    f"manual_lab:{settings.user_profile_id}:{uuid4().hex}"
                ),
            )
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
        "trigger_kind": activation.trigger_kind,
        "status": activation.status,
        "active_mode": activation.active_mode,
        "scheduled_at": utc_isoformat(activation.scheduled_at),
        "started_at": utc_isoformat(activation.started_at),
        "completed_at": utc_isoformat(activation.completed_at),
        "attempt_count": activation.attempt_count,
        "outcome": activation.outcome_json,
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
