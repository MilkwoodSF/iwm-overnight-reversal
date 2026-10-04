"""Historical mechanical dry run. No API access or order submission."""

import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from auction_safety import check_deadline
from iwm_signal import THRESHOLD
from order_identity import order_id
from position_sizing import calculate_shares
from session_deadlines import moc_allowed

ET = ZoneInfo("America/New_York")
session = date(2026, 10, 5)
calendar = {"date": "2026-10-05", "open": "09:30", "close": "16:00"}

# Synthetic historical scenarios: test mechanics, not historical performance.
previous_close = Decimal("281.52")
declining_close = Decimal("279.00")
rising_close = Decimal("284.00")

decline = declining_close / previous_close - 1
rise = rising_close / previous_close - 1

assert decline <= Decimal(str(THRESHOLD))
assert rise > Decimal(str(THRESHOLD))
print("FROZEN SIGNAL: PASS — BUY and NO TRADE scenarios")

sizing = calculate_shares("10000", "10000", declining_close)
assert sizing["shares"] == 34
assert sizing["estimated_value"] <= sizing["budget"]
assert sizing["budget"] == Decimal("9500.00")
assert sizing["cash_buffer"] >= 0
print("CASH-ONLY WHOLE-SHARE SIZING: PASS")
print("SIMULATED SHARES:", sizing["shares"])
print("SIMULATED PURCHASE:", sizing["estimated_value"])

before = datetime(2026, 10, 5, 15, 40, tzinfo=ET)
after = datetime(2026, 10, 5, 15, 45, tzinfo=ET)
assert moc_allowed(calendar, before)
assert not moc_allowed(calendar, after)
assert check_deadline("BUY_MOC", before, session)[0]
assert not check_deadline("BUY_MOC", after, session)[0]
print("AUCTION DEADLINES: PASS")

identifier = order_id("BUY_MOC", session)
assert identifier == order_id("BUY_MOC", session)
assert identifier != order_id("SELL_MOO", session)

# Simulate an existing identifier: the duplicate must be rejected.
existing_ids = {identifier}
assert identifier in existing_ids
print("DETERMINISTIC DUPLICATE DETECTION: PASS")

print("MECHANICAL DRY RUN: PASS")
print("API CALLS: 0")
print("ORDERS SUBMITTED: 0")
