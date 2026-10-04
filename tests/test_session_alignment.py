"""Verify IWM signal bars align with actual preceding trading sessions."""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def validate_alignment(entry_date, calendar_dates, bars):
    previous_sessions = sorted(
        d for d in calendar_dates if d < entry_date
    )

    if len(previous_sessions) < 2:
        raise ValueError("Insufficient preceding trading sessions")

    expected = previous_sessions[-2:]
    actual = sorted(date.fromisoformat(b["t"][:10]) for b in bars)

    if actual != expected:
        raise ValueError(
            f"Session mismatch: expected {expected}, received {actual}"
        )

    return True


if __name__ == "__main__":
    sessions = [
        date(2026, 9, 30),
        date(2026, 10, 1),
        date(2026, 10, 2),
        date(2026, 10, 5),
    ]

    correct = [
        {"t": "2026-10-01T04:00:00Z"},
        {"t": "2026-10-02T04:00:00Z"},
    ]

    stale = [
        {"t": "2026-09-30T04:00:00Z"},
        {"t": "2026-10-01T04:00:00Z"},
    ]

    assert validate_alignment(date(2026, 10, 5), sessions, correct)

    try:
        validate_alignment(date(2026, 10, 5), sessions, stale)
    except ValueError:
        print("STALE DATA: CORRECTLY REJECTED")
    else:
        raise AssertionError("Stale data was accepted")

    print("SESSION ALIGNMENT: PASS")
    print("API CALLS: 0")
    print("ORDERS SUBMITTED: 0")
