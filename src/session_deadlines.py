"""Calendar-aware IWM auction deadlines. No trading operations."""

from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")


def moc_deadline(session):
    """Earlier of 3:45 p.m. ET or 15 minutes before session close."""
    session_date = datetime.fromisoformat(session["date"]).date()
    hour, minute = map(int, session["close"].split(":"))

    closing = datetime.combine(
        session_date, time(hour, minute), tzinfo=ET
    )

    standard_limit = datetime.combine(
        session_date, time(15, 45), tzinfo=ET
    )

    return min(standard_limit, closing - timedelta(minutes=15))


def moc_allowed(session, now):
    if now.tzinfo is None:
        raise ValueError("Timezone-aware datetime required")

    local = now.astimezone(ET)
    session_date = datetime.fromisoformat(session["date"]).date()

    opening_hour, opening_minute = map(
        int, session["open"].split(":")
    )
    opening = datetime.combine(
        session_date,
        time(opening_hour, opening_minute),
        tzinfo=ET,
    )

    return opening <= local < moc_deadline(session)


if __name__ == "__main__":
    regular = {
        "date": "2026-10-05",
        "open": "09:30",
        "close": "16:00",
    }

    early = {
        "date": "2026-10-05",
        "open": "09:30",
        "close": "13:00",
    }

    assert moc_deadline(regular).strftime("%H:%M") == "15:45"
    assert moc_deadline(early).strftime("%H:%M") == "12:45"

    for session, clock, expected in [
        (regular, "15:40", True),
        (regular, "15:45", False),
        (early, "12:40", True),
        (early, "12:45", False),
        (early, "15:00", False),
    ]:
        hour, minute = map(int, clock.split(":"))
        now = datetime(
            2026, 10, 5, hour, minute, tzinfo=ET
        )
        result = moc_allowed(session, now)
        assert result == expected, (clock, result)
        print(session["close"], clock, "ALLOWED" if result else "BLOCKED")

    print("CALENDAR-AWARE DEADLINE TESTS: PASS")
    print("ORDERS SUBMITTED: 0")
