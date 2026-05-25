from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


TimePreset = Literal["today", "yesterday", "last_7_days", "this_session"]
MemoryTimeBasis = Literal["source_conversation", "recorded", "valid"]
SessionTimeBasis = Literal["conversation", "created", "updated", "summary"]


class TimeFilter(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    preset: TimePreset | None = None
    from_at: datetime | None = Field(default=None, alias="from")
    to_at: datetime | None = Field(default=None, alias="to")
    basis: str | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_aliases(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        if "from" not in normalized:
            for alias in ("from_at", "start", "since", "after", "date_from"):
                if alias in normalized:
                    normalized["from"] = normalized.pop(alias)
                    break
        if "to" not in normalized:
            for alias in ("to_at", "end", "until", "before", "date_to"):
                if alias in normalized:
                    normalized["to"] = normalized.pop(alias)
                    break
        if "preset" not in normalized:
            for alias in ("range", "period", "when"):
                if alias in normalized:
                    normalized["preset"] = normalized.pop(alias)
                    break
        if "date" in normalized and "from" not in normalized and "to" not in normalized:
            normalized["from"] = normalized.pop("date")
            normalized["to"] = normalized["from"]
        return normalized

    @model_validator(mode="after")
    def validate_bounds(self) -> "TimeFilter":
        if self.preset is None and self.from_at is None and self.to_at is None:
            raise ValueError("time requires preset, from, or to")
        if self.preset == "this_session" and (self.from_at is not None or self.to_at is not None):
            raise ValueError("time.preset=this_session cannot be combined with from/to")
        if self.from_at is not None and self.to_at is not None:
            from_utc = ensure_utc(self.from_at)
            to_utc = ensure_utc(self.to_at)
            if to_utc < from_utc:
                raise ValueError("time.to must be greater than or equal to time.from")
        return self


def parse_time_filter(value: Any) -> tuple[TimeFilter | None, ValidationError | None]:
    if value is None:
        return None, None
    try:
        return TimeFilter.model_validate(value), None
    except ValidationError as exc:
        return None, exc


def resolve_interval(
    time_filter: TimeFilter | None,
    *,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    if time_filter is None:
        return None
    if time_filter.preset == "this_session":
        return {
            "preset": "this_session",
            "from": None,
            "to": None,
            "timezone": _local_now(now).tzname(),
            "utc_offset": _local_now(now).strftime("%z"),
        }

    local_now = _local_now(now)
    start: datetime | None
    end: datetime | None
    if time_filter.preset == "today":
        start = datetime.combine(local_now.date(), time.min, tzinfo=local_now.tzinfo)
        end = start + timedelta(days=1)
    elif time_filter.preset == "yesterday":
        today_start = datetime.combine(local_now.date(), time.min, tzinfo=local_now.tzinfo)
        start = today_start - timedelta(days=1)
        end = today_start
    elif time_filter.preset == "last_7_days":
        start = local_now - timedelta(days=7)
        end = local_now
    else:
        start = _as_local_day_start(time_filter.from_at, local_now) if time_filter.from_at else None
        end = _as_local_day_end(time_filter.to_at, local_now) if time_filter.to_at else None

    return {
        "preset": time_filter.preset,
        "from": ensure_utc(start).isoformat() if start is not None else None,
        "to": ensure_utc(end).isoformat() if end is not None else None,
        "timezone": local_now.tzname(),
        "utc_offset": local_now.strftime("%z"),
    }


def interval_contains(
    value: datetime | None,
    *,
    resolved: dict[str, Any] | None,
) -> bool:
    if resolved is None:
        return True
    if resolved.get("preset") == "this_session":
        return True
    if value is None:
        return False
    instant = ensure_utc(value)
    start = _parse_resolved_datetime(resolved.get("from"))
    end = _parse_resolved_datetime(resolved.get("to"))
    if start is not None and instant < start:
        return False
    if end is not None and instant >= end:
        return False
    return True


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def time_filter_payload(time_filter: TimeFilter | None, resolved: dict[str, Any] | None) -> dict[str, Any] | None:
    if time_filter is None:
        return None
    return {
        "preset": time_filter.preset,
        "from": time_filter.from_at.isoformat() if time_filter.from_at is not None else None,
        "to": time_filter.to_at.isoformat() if time_filter.to_at is not None else None,
        "basis": time_filter.basis,
        "resolved": resolved,
    }


def _local_now(now: datetime | None) -> datetime:
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone()


def _as_local_day_start(value: datetime, local_now: datetime) -> datetime:
    if _date_only_like(value):
        return datetime.combine(value.date(), time.min, tzinfo=local_now.tzinfo)
    if value.tzinfo is None:
        return value.replace(tzinfo=local_now.tzinfo)
    return value.astimezone(local_now.tzinfo)


def _as_local_day_end(value: datetime, local_now: datetime) -> datetime:
    if _date_only_like(value):
        return datetime.combine(value.date(), time.min, tzinfo=local_now.tzinfo) + timedelta(days=1)
    if value.tzinfo is None:
        return value.replace(tzinfo=local_now.tzinfo)
    return value.astimezone(local_now.tzinfo)


def _date_only_like(value: datetime) -> bool:
    return (
        value.hour == 0
        and value.minute == 0
        and value.second == 0
        and value.microsecond == 0
    )


def _parse_resolved_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    return ensure_utc(datetime.fromisoformat(value))
