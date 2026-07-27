"""Isolated API for non-cognitive Android capability experiments."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.storage import repositories
from app.storage.models import DeviceObservation
from app.config import Settings
from app.runtime.device_perception_adapter import admit_device_observation


class DeviceObservationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_event_id: str = Field(min_length=1, max_length=120)
    schema_version: str = Field(
        default="device-observation-v1",
        pattern="^device-observation-v1$",
    )
    run_id: str = Field(min_length=1, max_length=120)
    device_id: str = Field(min_length=1, max_length=180)
    probe: str = Field(min_length=1, max_length=80)
    event_type: str = Field(min_length=1, max_length=120)
    source: str = Field(default="capacitor", min_length=1, max_length=80)
    app_state: str | None = Field(default=None, max_length=40)
    observed_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)
    normalized: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DeviceObservationBatchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observations: list[DeviceObservationInput] = Field(min_length=1, max_length=100)


class DeviceObservationResponse(BaseModel):
    id: str
    client_event_id: str
    schema_version: str
    run_id: str
    device_id: str
    probe: str
    event_type: str
    source: str
    app_state: str | None
    observed_at: datetime
    received_at: datetime
    payload: dict[str, Any]
    normalized: dict[str, Any]
    metadata: dict[str, Any]


class DeviceObservationBatchResponse(BaseModel):
    accepted: int
    deduplicated: int
    observations: list[DeviceObservationResponse]
    cognitive_admission: list[dict[str, Any]] = Field(default_factory=list)


class DeviceObservationListResponse(BaseModel):
    total: int
    returned: int
    observations: list[DeviceObservationResponse]


class DeviceExplorationSummaryResponse(BaseModel):
    schema_version: str = "device-exploration-summary-v1"
    total: int
    device_id: str | None
    run_id: str | None
    probe_counts: dict[str, int]
    latest_observation_at: datetime | None
    model_context_delivery: bool = False
    cognitive_persistence: bool = False
    cognitive_admission_mode: str = "off"


def build_device_exploration_router(
    engine: Engine,
    settings: Settings,
) -> APIRouter:
    router = APIRouter(
        prefix="/api/device-exploration",
        tags=["device-exploration"],
    )

    @router.post(
        "/observations/batch",
        response_model=DeviceObservationBatchResponse,
    )
    def append_observations(
        request: DeviceObservationBatchInput,
    ) -> DeviceObservationBatchResponse:
        accepted = 0
        deduplicated = 0
        stored: list[DeviceObservationResponse] = []
        cognitive_admission: list[dict[str, Any]] = []
        with Session(engine) as db:
            for item in request.observations:
                observation, created = repositories.add_device_observation(
                    db,
                    client_event_id=item.client_event_id,
                    run_id=item.run_id,
                    device_id=item.device_id,
                    probe=item.probe,
                    event_type=item.event_type,
                    observed_at=item.observed_at,
                    source=item.source,
                    app_state=item.app_state,
                    payload=item.payload,
                    normalized=item.normalized,
                    metadata={
                        **item.metadata,
                        "input_schema_version": item.schema_version,
                        "device_observed_at": item.observed_at.isoformat(),
                    },
                )
                stored.append(_response(observation))
                if created:
                    accepted += 1
                    cognitive_admission.append(
                        admit_device_observation(
                            db,
                            settings=settings,
                            profile_id=settings.user_profile_id,
                            observation=observation,
                        )
                    )
                else:
                    deduplicated += 1
        return DeviceObservationBatchResponse(
            accepted=accepted,
            deduplicated=deduplicated,
            observations=stored,
            cognitive_admission=cognitive_admission,
        )

    @router.get(
        "/observations",
        response_model=DeviceObservationListResponse,
    )
    def list_observations(
        device_id: str | None = Query(default=None, max_length=180),
        run_id: str | None = Query(default=None, max_length=120),
        probe: str | None = Query(default=None, max_length=80),
        limit: int = Query(default=200, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ) -> DeviceObservationListResponse:
        with Session(engine) as db:
            total = repositories.count_device_observations(
                db,
                device_id=device_id,
                run_id=run_id,
                probe=probe,
            )
            observations = repositories.list_device_observations(
                db,
                device_id=device_id,
                run_id=run_id,
                probe=probe,
                limit=limit,
                offset=offset,
            )
        return DeviceObservationListResponse(
            total=total,
            returned=len(observations),
            observations=[_response(item) for item in observations],
        )

    @router.get(
        "/summary",
        response_model=DeviceExplorationSummaryResponse,
    )
    def get_summary(
        device_id: str | None = Query(default=None, max_length=180),
        run_id: str | None = Query(default=None, max_length=120),
    ) -> DeviceExplorationSummaryResponse:
        with Session(engine) as db:
            total = repositories.count_device_observations(
                db,
                device_id=device_id,
                run_id=run_id,
            )
            probe_counts = repositories.device_probe_counts(
                db,
                device_id=device_id,
                run_id=run_id,
            )
            latest = repositories.list_device_observations(
                db,
                device_id=device_id,
                run_id=run_id,
                limit=1,
            )
        return DeviceExplorationSummaryResponse(
            total=total,
            device_id=device_id,
            run_id=run_id,
            probe_counts=probe_counts,
            latest_observation_at=_api_utc(latest[0].observed_at) if latest else None,
            cognitive_persistence=(
                settings.device_perception_admission_mode == "active"
            ),
            cognitive_admission_mode=settings.device_perception_admission_mode,
        )

    return router


def _response(observation: DeviceObservation) -> DeviceObservationResponse:
    return DeviceObservationResponse(
        id=observation.id,
        client_event_id=observation.client_event_id,
        schema_version=observation.schema_version,
        run_id=observation.run_id,
        device_id=observation.device_id,
        probe=observation.probe,
        event_type=observation.event_type,
        source=observation.source,
        app_state=observation.app_state,
        observed_at=_api_utc(observation.observed_at),
        received_at=_api_utc(observation.received_at),
        payload=observation.payload_json,
        normalized=observation.normalized_json,
        metadata=observation.metadata_json,
    )


def _api_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
