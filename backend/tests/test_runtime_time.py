from datetime import datetime, timezone

from app.api.chat_serialization import ChatMessageResponse
from app.mind.context_time import render_user_time
from app.mind.time_filters import TimeFilter, resolve_interval
from app.runtime.time import social_date, utc_isoformat


def test_user_time_preserves_historical_dst_offset() -> None:
    july = render_user_time(
        datetime(2026, 7, 12, 13, 30, tzinfo=timezone.utc),
        timezone_id="Europe/Rome",
    )
    december = render_user_time(
        datetime(2026, 12, 12, 14, 30, tzinfo=timezone.utc),
        timezone_id="Europe/Rome",
    )

    assert july == "2026-07-12T15:30:00+02:00"
    assert december == "2026-12-12T15:30:00+01:00"


def test_social_day_uses_previous_evening_before_five() -> None:
    local_night = datetime.fromisoformat("2026-07-27T00:05:00+02:00")
    local_morning = datetime.fromisoformat("2026-07-27T05:00:00+02:00")

    assert social_date(local_night).isoformat() == "2026-07-26"
    assert social_date(local_morning).isoformat() == "2026-07-27"


def test_transport_timestamps_are_unambiguous_utc() -> None:
    naive_storage_time = datetime(2026, 7, 27, 13, 8)
    response = ChatMessageResponse(
        id="msg_test",
        session_id="ses_test",
        turn_id=None,
        role="user",
        content="Test",
        created_at=naive_storage_time,
        metadata={},
    )

    assert utc_isoformat(naive_storage_time) == "2026-07-27T13:08:00Z"
    assert response.model_dump(mode="json")["created_at"] == (
        "2026-07-27T13:08:00Z"
    )


def test_time_filter_resolves_days_in_configured_timezone_across_dst() -> None:
    july = resolve_interval(
        TimeFilter(preset="today"),
        now=datetime(2026, 7, 12, 13, 30, tzinfo=timezone.utc),
        timezone_name="Europe/Rome",
    )
    december = resolve_interval(
        TimeFilter(preset="today"),
        now=datetime(2026, 12, 12, 14, 30, tzinfo=timezone.utc),
        timezone_name="Europe/Rome",
    )

    assert july == {
        "preset": "today",
        "from": "2026-07-11T22:00:00+00:00",
        "to": "2026-07-12T22:00:00+00:00",
        "timezone": "Europe/Rome",
        "timezone_name": "CEST",
        "utc_offset": "+0200",
    }
    assert december == {
        "preset": "today",
        "from": "2026-12-11T23:00:00+00:00",
        "to": "2026-12-12T23:00:00+00:00",
        "timezone": "Europe/Rome",
        "timezone_name": "CET",
        "utc_offset": "+0100",
    }
