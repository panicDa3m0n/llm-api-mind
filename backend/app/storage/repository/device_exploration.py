"""Persistence boundary for append-only device exploration evidence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, func
from sqlmodel import Session, select

from app.storage.models import DeviceObservation


def add_device_observation(
    db: Session,
    *,
    client_event_id: str,
    run_id: str,
    device_id: str,
    probe: str,
    event_type: str,
    observed_at: datetime,
    source: str = "capacitor",
    app_state: str | None = None,
    payload: dict[str, Any] | None = None,
    normalized: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> tuple[DeviceObservation, bool]:
    existing = db.exec(
        select(DeviceObservation).where(
            DeviceObservation.client_event_id == client_event_id
        )
    ).first()
    if existing is not None:
        return existing, False

    observation = DeviceObservation(
        client_event_id=client_event_id,
        run_id=run_id,
        device_id=device_id,
        probe=probe,
        event_type=event_type,
        source=source,
        app_state=app_state,
        observed_at=_storage_utc(observed_at),
        payload_json=payload or {},
        normalized_json=normalized or {},
        metadata_json=metadata or {},
    )
    db.add(observation)
    db.commit()
    db.refresh(observation)
    return observation, True


def list_device_observations(
    db: Session,
    *,
    device_id: str | None = None,
    run_id: str | None = None,
    probe: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[DeviceObservation]:
    statement = select(DeviceObservation)
    if device_id is not None:
        statement = statement.where(DeviceObservation.device_id == device_id)
    if run_id is not None:
        statement = statement.where(DeviceObservation.run_id == run_id)
    if probe is not None:
        statement = statement.where(DeviceObservation.probe == probe)
    statement = (
        statement.order_by(
            desc(DeviceObservation.observed_at),
            desc(DeviceObservation.received_at),
            desc(DeviceObservation.id),
        )
        .offset(offset)
        .limit(limit)
    )
    return list(db.exec(statement).all())


def count_device_observations(
    db: Session,
    *,
    device_id: str | None = None,
    run_id: str | None = None,
    probe: str | None = None,
) -> int:
    statement = select(func.count()).select_from(DeviceObservation)
    if device_id is not None:
        statement = statement.where(DeviceObservation.device_id == device_id)
    if run_id is not None:
        statement = statement.where(DeviceObservation.run_id == run_id)
    if probe is not None:
        statement = statement.where(DeviceObservation.probe == probe)
    return int(db.exec(statement).one())


def device_probe_counts(
    db: Session,
    *,
    device_id: str | None = None,
    run_id: str | None = None,
) -> dict[str, int]:
    statement = select(
        DeviceObservation.probe,
        func.count(DeviceObservation.id),
    )
    if device_id is not None:
        statement = statement.where(DeviceObservation.device_id == device_id)
    if run_id is not None:
        statement = statement.where(DeviceObservation.run_id == run_id)
    statement = statement.group_by(DeviceObservation.probe)
    return {str(probe): int(count) for probe, count in db.exec(statement).all()}


def _storage_utc(value: datetime) -> datetime:
    """Store one unambiguous UTC wall time despite SQLite dropping offsets."""

    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)
