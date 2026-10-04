"""Offline sell-safety tests. No API calls or order submissions."""

import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sell_preflight import validate_sell

ET = ZoneInfo("America/New_York")
exit_date = date(2026, 10, 5)
now = datetime(2026, 10, 5, 9, 15, tzinfo=ET)

buy = {
    "symbol": "IWM",
    "side": "buy",
    "status": "filled",
    "filled_at": "2026-10-02T20:00:00Z",
    "filled_qty": "33",
}
position = {"symbol": "IWM", "qty": "33"}

assert validate_sell(buy, position, None, exit_date, now) == 33
print("CONFIRMED FILL AND MATCHING POSITION: PASS")

for label, test_buy, test_position, test_sell, test_now in [
    ("MISSING BUY", None, position, None, now),
    ("UNFILLED BUY", {**buy, "status": "accepted"}, position, None, now),
    ("QUANTITY MISMATCH", buy, {"symbol": "IWM", "qty": "32"}, None, now),
    ("DUPLICATE SELL", buy, position, {"status": "accepted"}, now),
    ("MISSED DEADLINE", buy, position, None,
     datetime(2026, 10, 5, 9, 20, tzinfo=ET)),
]:
    try:
        validate_sell(test_buy, test_position, test_sell, exit_date, test_now)
    except RuntimeError:
        print(label + ": CORRECTLY BLOCKED")
    else:
        raise AssertionError(label + " was incorrectly permitted")

print("SELL SAFETY TESTS: PASS")
print("API CALLS: 0")
print("ORDERS SUBMITTED: 0")
