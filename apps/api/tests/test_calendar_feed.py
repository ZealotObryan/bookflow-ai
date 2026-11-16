import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.modules.calendar.router import _escape_ics, _utc_stamp, render_calendar


def test_ics_escapes_calendar_text() -> None:
    assert _escape_ics("Studio, Inc.; room\\north\nnext") == "Studio\\, Inc.\\; room\\\\north\\nnext"


def test_ics_uses_utc_and_stable_booking_uid() -> None:
    booking_id = uuid.uuid4()
    start = datetime(2027, 1, 12, 9, 0, tzinfo=UTC)
    booking = SimpleNamespace(id=booking_id, starts_at=start, ends_at=start + timedelta(minutes=45))
    business = SimpleNamespace(name="Lilongwe Studio")

    calendar = render_calendar(business, [(booking, None, ["Hair consultation"])])

    assert "BEGIN:VCALENDAR" in calendar
    assert f"UID:{booking_id}@bookflow.ai" in calendar
    assert "DTSTART:20270112T090000Z" in calendar
    assert "DTEND:20270112T094500Z" in calendar
    assert "SUMMARY:Appointment · Hair consultation" in calendar
    assert "END:VCALENDAR" in calendar


def test_ics_rejects_naive_timestamps() -> None:
    try:
        _utc_stamp(datetime(2027, 1, 12, 9, 0))
    except ValueError as exc:
        assert "timezone-aware" in str(exc)
    else:
        raise AssertionError("Naive datetimes must not be accepted")
