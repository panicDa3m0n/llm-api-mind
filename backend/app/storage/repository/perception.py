"""Append-only perception ledger and per-session consumption cursors."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import and_, func, or_
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.storage.models import (
    PerceptionChannelState,
    PerceptionCursor,
    PerceptionEvent,
    utc_now,
)


def add_perception_event(
    db: Session,
    *,
    profile_id: str,
    channel: str,
    event_type: str,
    source: str,
    source_event_key: str,
    observed_at: datetime,
    payload: dict[str, Any],
    navigation: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> tuple[PerceptionEvent, bool]:
    existing = db.exec(
        select(PerceptionEvent).where(
            PerceptionEvent.source_event_key == source_event_key
        )
    ).first()
    if existing is not None:
        return existing, False
    event = PerceptionEvent(
        profile_id=profile_id,
        channel=channel,
        event_type=event_type,
        source=source,
        source_event_key=source_event_key,
        observed_at=observed_at,
        payload_json=payload,
        navigation_json=navigation or {},
        metadata_json=metadata or {},
    )
    db.add(event)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.exec(
            select(PerceptionEvent).where(
                PerceptionEvent.source_event_key == source_event_key
            )
        ).first()
        if existing is None:
            raise
        return existing, False
    db.refresh(event)
    _refresh_channel_state(db, event)
    return event, True


def list_perception_events(
    db: Session,
    *,
    profile_id: str,
    channel: str | None = None,
    since: datetime | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[PerceptionEvent]:
    statement = select(PerceptionEvent).where(
        PerceptionEvent.profile_id == profile_id
    )
    if channel is not None:
        statement = statement.where(PerceptionEvent.channel == channel)
    if since is not None:
        statement = statement.where(PerceptionEvent.observed_at > since)
    statement = (
        statement.order_by(
            PerceptionEvent.observed_at.desc(),
            PerceptionEvent.received_at.desc(),
            PerceptionEvent.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    )
    return list(db.exec(statement).all())


def get_perception_event(
    db: Session,
    event_id: str,
) -> PerceptionEvent | None:
    return db.get(PerceptionEvent, event_id)


def perception_availability_index(
    db: Session,
    *,
    profile_id: str,
    session_id: str | None,
) -> list[dict[str, Any]]:
    states = list(
        db.exec(
            select(PerceptionChannelState)
            .where(PerceptionChannelState.profile_id == profile_id)
            .order_by(PerceptionChannelState.channel)
        ).all()
    )
    cursors: dict[str, PerceptionCursor] = {}
    if session_id is not None:
        cursors = {
            item.channel: item
            for item in db.exec(
                select(PerceptionCursor).where(
                    PerceptionCursor.session_id == session_id
                )
            ).all()
        }
    index: list[dict[str, Any]] = []
    for state in states:
        cursor = cursors.get(state.channel)
        unseen = _count_unseen(
            db,
            profile_id=profile_id,
            channel=state.channel,
            last_received_at=cursor.last_received_at if cursor else None,
            last_event_id=cursor.last_event_id if cursor else None,
        )
        index.append(
            {
                "channel": state.channel,
                "status": state.status,
                "event_count": state.event_count,
                "unseen_count": unseen,
                "latest_event_id": state.latest_event_id,
                "latest_observed_at": (
                    state.latest_observed_at.isoformat()
                    if state.latest_observed_at
                    else None
                ),
                "last_opened_event_id": cursor.last_event_id if cursor else None,
                "open_command": f"perception open {state.channel} --limit 10",
            }
        )
    return index


def open_perception_channel(
    db: Session,
    *,
    profile_id: str,
    session_id: str,
    channel: str,
    limit: int,
) -> list[PerceptionEvent]:
    cursor = db.exec(
        select(PerceptionCursor)
        .where(PerceptionCursor.session_id == session_id)
        .where(PerceptionCursor.channel == channel)
    ).first()
    statement = (
        select(PerceptionEvent)
        .where(PerceptionEvent.profile_id == profile_id)
        .where(PerceptionEvent.channel == channel)
    )
    if cursor is not None and cursor.last_received_at is not None:
        statement = statement.where(
            or_(
                PerceptionEvent.received_at > cursor.last_received_at,
                and_(
                    PerceptionEvent.received_at == cursor.last_received_at,
                    PerceptionEvent.id > (cursor.last_event_id or ""),
                ),
            )
        )
    statement = statement.order_by(
        PerceptionEvent.received_at,
        PerceptionEvent.id,
    ).limit(limit)
    events = list(db.exec(statement).all())
    if not events:
        return []
    latest = events[-1]
    if cursor is None:
        cursor = PerceptionCursor(
            profile_id=profile_id,
            session_id=session_id,
            channel=channel,
        )
    cursor.last_event_id = latest.id
    cursor.last_observed_at = latest.observed_at
    cursor.last_received_at = latest.received_at
    cursor.opened_count += len(events)
    cursor.updated_at = utc_now()
    db.add(cursor)
    db.commit()
    return events


def _refresh_channel_state(db: Session, event: PerceptionEvent) -> None:
    state = db.exec(
        select(PerceptionChannelState)
        .where(PerceptionChannelState.profile_id == event.profile_id)
        .where(PerceptionChannelState.channel == event.channel)
    ).first()
    count = db.exec(
        select(func.count(PerceptionEvent.id))
        .where(PerceptionEvent.profile_id == event.profile_id)
        .where(PerceptionEvent.channel == event.channel)
    ).one()
    if state is None:
        state = PerceptionChannelState(
            profile_id=event.profile_id,
            channel=event.channel,
        )
    previous_latest = (
        db.get(PerceptionEvent, state.latest_event_id)
        if state.latest_event_id
        else None
    )
    if previous_latest is None or _observed_order(event) > _observed_order(
        previous_latest
    ):
        state.latest_event_id = event.id
        state.latest_observed_at = event.observed_at
    state.event_count = int(count or 0)
    state.updated_at = utc_now()
    db.add(state)
    db.commit()


def _count_unseen(
    db: Session,
    *,
    profile_id: str,
    channel: str,
    last_received_at: datetime | None,
    last_event_id: str | None,
) -> int:
    statement = (
        select(func.count(PerceptionEvent.id))
        .where(PerceptionEvent.profile_id == profile_id)
        .where(PerceptionEvent.channel == channel)
    )
    if last_received_at is not None:
        statement = statement.where(
            or_(
                PerceptionEvent.received_at > last_received_at,
                and_(
                    PerceptionEvent.received_at == last_received_at,
                    PerceptionEvent.id > (last_event_id or ""),
                ),
            )
        )
    return int(db.exec(statement).one() or 0)


def _observed_order(event: PerceptionEvent) -> tuple[datetime, datetime, str]:
    return (event.observed_at, event.received_at, event.id)
