"""Canonical timestamp conversion at model and transport boundaries."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone


SOCIAL_DAY_BOUNDARY = time(hour=5)


def aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def utc_isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    return aware_utc(value).isoformat().replace("+00:00", "Z")


def social_date(value: datetime) -> date:
    """Return the conversational day associated with a local timestamp."""

    if value.tzinfo is None:
        raise ValueError("social_date requires a timezone-aware local timestamp")
    if value.timetz().replace(tzinfo=None) < SOCIAL_DAY_BOUNDARY:
        return (value - timedelta(days=1)).date()
    return value.date()
