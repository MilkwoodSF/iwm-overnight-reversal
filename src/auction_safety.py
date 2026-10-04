"""IWM V1 auction deadlines. Pure validation; never submits orders."""

from datetime import datetime, time
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

# Conservative internal cutoffs, earlier than Alpaca's auction deadlines.
DEADLINES = {
    "BUY_MOC": time(15, 45),
    "SELL_MOO": time(9, 20),
}


def check_deadline(action, now, session_date):
    if action not in DEADLINES:
        raise ValueError("Unknown auction action")

    if now.tzinfo is None:
        raise ValueError("Timezone-aware datetime required")

    local = now.astimezone(ET)

    if local.date() != session_date:
        return False, "BLOCKED: Wrong trading date"

    if local.time() >= DEADLINES[action]:
        return False, "BLOCKED: Internal auction deadline passed"

    if action == "BUY_MOC" and local.time() < time(9, 30):
        return False, "BLOCKED: MOC submission window not started"

    if action == "SELL_MOO" and local.time() < time(4, 0):
        return False, "BLOCKED: MOO submission window not started"

    return True, "DEADLINE CHECK PASSED"


if __name__ == "__main__":
    from datetime import date

    session = date(2026, 10, 5)

    tests = [
        ("BUY_MOC", "2026-10-05T15:40:00-04:00", True),
        ("BUY_MOC", "2026-10-05T15:45:00-04:00", False),
        ("BUY_MOC", "2026-10-05T15:50:00-04:00", False),
        ("SELL_MOO", "2026-10-05T09:15:00-04:00", True),
        ("SELL_MOO", "2026-10-05T09:20:00-04:00", False),
        ("SELL_MOO", "2026-10-05T09:28:00-04:00", False),
        ("BUY_MOC", "2026-10-04T15:40:00-04:00", False),
    ]

    for action, timestamp, expected in tests:
        allowed, reason = check_deadline(
            action,
            datetime.fromisoformat(timestamp),
            session,
        )
        assert allowed == expected, (action, timestamp, reason)
        print(action, timestamp, reason)

    print("ALL DEADLINE TESTS PASSED")
    print("ORDERS SUBMITTED: 0")
