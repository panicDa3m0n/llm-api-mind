"""Single user-time boundary for model-facing dynamic context."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.runtime.time import SOCIAL_DAY_BOUNDARY, aware_utc


def user_timezone(timezone_id: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_id)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def render_user_time(value: datetime | str, *, timezone_id: str) -> str:
    if isinstance(value, str):
        normalized = value.strip().replace("Z", "+00:00")
        value = datetime.fromisoformat(normalized)
    return aware_utc(value).astimezone(user_timezone(timezone_id)).isoformat()


def timezone_packet(now: datetime, *, timezone_id: str) -> dict[str, str]:
    localized = now.astimezone(user_timezone(timezone_id))
    offset = localized.strftime("%z")
    return {
        "id": timezone_id,
        "name": localized.tzname() or timezone_id,
        "utc_offset": f"{offset[:3]}:{offset[3:]}" if offset else "+00:00",
        "social_day_boundary": SOCIAL_DAY_BOUNDARY.strftime("%H:%M"),
    }
