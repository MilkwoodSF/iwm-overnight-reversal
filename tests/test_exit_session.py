"""Validate the next-session exit relationship. Offline tests only."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")


def expected_exit(buy_session, calendar):
    sessions = sorted(
        date.fromisoformat(s["date"]) for s in calendar
    )
    following = [d for d in sessions if d > buy_session]

    if not following:
        raise ValueError("Next trading session unavailable")

    return following[0]


def validate_exit_session(buy_session, sell_session, calendar):
    expected = expected_exit(buy_session, calendar)
    if sell_session != expected:
        raise ValueError(
            f"Incorrect exit: expected {expected}, got {sell_session}"
        )
    return True


calendar = [
    {"date": "2026-09-30"},
    {"date": "2026-10-01"},
    {"date": "2026-10-02"},
    {"date": "2026-10-05"},
    {"date": "2026-10-06"},
]

assert validate_exit_session(
    date(2026, 10, 2), date(2026, 10, 5), calendar
)
print("FRIDAY BUY / MONDAY SELL: PASS")

assert validate_exit_session(
    date(2026, 9, 30), date(2026, 10, 1), calendar
)
print("MONTH-BOUNDARY EXIT: PASS")

for invalid in (date(2026, 10, 2), date(2026, 10, 6)):
    try:
        validate_exit_session(
            date(2026, 10, 2), invalid, calendar
        )
    except ValueError:
        print("INCORRECT EXIT DATE: BLOCKED")
    else:
        raise AssertionError("Incorrect exit accepted")

print("EXIT-SESSION TESTS: PASS")
print("API CALLS: 0")
print("ORDERS SUBMITTED: 0")
