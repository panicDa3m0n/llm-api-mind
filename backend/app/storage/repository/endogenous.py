"""Persistence for adaptive endogenous cognition windows."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.storage.models import EndogenousCognitiveWindow, utc_now


def latest_endogenous_window(
    db: Session,
    *,
    profile_id: str,
) -> EndogenousCognitiveWindow | None:
    return db.exec(
        select(EndogenousCognitiveWindow)
        .where(EndogenousCognitiveWindow.profile_id == profile_id)
        .order_by(
            EndogenousCognitiveWindow.opened_at.desc(),
            EndogenousCognitiveWindow.id.desc(),
        )
        .limit(1)
    ).first()


def list_endogenous_windows(
    db: Session,
    *,
    profile_id: str,
    limit: int = 30,
) -> list[EndogenousCognitiveWindow]:
    return list(
        db.exec(
            select(EndogenousCognitiveWindow)
            .where(EndogenousCognitiveWindow.profile_id == profile_id)
            .order_by(
                EndogenousCognitiveWindow.opened_at.desc(),
                EndogenousCognitiveWindow.id.desc(),
            )
            .limit(limit)
        ).all()
    )


def get_endogenous_window_by_schedule_key(
    db: Session,
    *,
    schedule_key: str,
) -> EndogenousCognitiveWindow | None:
    return db.exec(
        select(EndogenousCognitiveWindow).where(
            EndogenousCognitiveWindow.schedule_key == schedule_key
        )
    ).first()


def create_endogenous_window(
    db: Session,
    *,
    schedule_key: str,
    profile_id: str,
    opened_at: datetime,
    cadence_seconds: int,
    next_window_at: datetime,
    consecutive_empty_windows: int,
    substrate: list[dict[str, Any]],
    source_refs: list[str],
) -> tuple[EndogenousCognitiveWindow, bool]:
    window = EndogenousCognitiveWindow(
        schedule_key=schedule_key,
        profile_id=profile_id,
        opened_at=opened_at,
        cadence_seconds=cadence_seconds,
        next_window_at=next_window_at,
        consecutive_empty_windows=consecutive_empty_windows,
        substrate_json=substrate,
        source_refs_json=source_refs,
    )
    db.add(window)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = get_endogenous_window_by_schedule_key(
            db,
            schedule_key=schedule_key,
        )
        if existing is None:
            raise
        return existing, False
    db.refresh(window)
    return window, True


def complete_endogenous_window(
    db: Session,
    *,
    window_id: str,
    status: str,
    cadence_seconds: int,
    next_window_at: datetime,
    consecutive_empty_windows: int,
    candidate_ids: list[str],
    trace_id: str | None,
    outcome: dict[str, Any],
) -> EndogenousCognitiveWindow:
    window = db.get(EndogenousCognitiveWindow, window_id)
    if window is None:
        raise ValueError(f"Endogenous cognitive window not found: {window_id}")
    window.status = status
    window.closed_at = utc_now()
    window.cadence_seconds = cadence_seconds
    window.next_window_at = next_window_at
    window.consecutive_empty_windows = consecutive_empty_windows
    window.candidate_ids_json = candidate_ids
    window.trace_id = trace_id
    window.outcome_json = outcome
    window.updated_at = utc_now()
    db.add(window)
    db.commit()
    db.refresh(window)
    return window


def link_endogenous_activation(
    db: Session,
    *,
    window_id: str,
    activation_id: str,
) -> EndogenousCognitiveWindow:
    window = db.get(EndogenousCognitiveWindow, window_id)
    if window is None:
        raise ValueError(f"Endogenous cognitive window not found: {window_id}")
    window.activation_id = activation_id
    window.updated_at = utc_now()
    db.add(window)
    db.commit()
    db.refresh(window)
    return window


def record_endogenous_activation_outcome(
    db: Session,
    *,
    window_id: str,
    activation_id: str,
    outcome: dict[str, Any],
) -> EndogenousCognitiveWindow:
    window = db.get(EndogenousCognitiveWindow, window_id)
    if window is None:
        raise ValueError(f"Endogenous cognitive window not found: {window_id}")
    window.activation_id = activation_id
    window.outcome_json = {
        **window.outcome_json,
        "activation_outcome": outcome,
    }
    window.updated_at = utc_now()
    db.add(window)
    db.commit()
    db.refresh(window)
    return window
