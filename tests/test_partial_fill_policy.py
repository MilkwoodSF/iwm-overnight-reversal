"""Offline partial-fill recovery policy tests. No trading operations."""

from decimal import Decimal


def reconcile_fill(buy, position):
    if buy is None:
        return "BLOCKED", 0, "Missing buy order"

    if buy.get("symbol") != "IWM" or buy.get("side") != "buy":
        return "BLOCKED", 0, "Unexpected order"

    filled = Decimal(str(buy.get("filled_qty") or "0"))

    if filled <= 0 or filled != filled.to_integral_value():
        return "BLOCKED", 0, "Invalid filled quantity"

    if position is None or position.get("symbol") != "IWM":
        return "BLOCKED", 0, "Position unavailable"

    held = Decimal(str(position["qty"]))

    if held != filled:
        return "BLOCKED", 0, "Position mismatch"

    if buy.get("status") == "filled":
        return "READY", int(held), "Confirmed complete fill"

    if buy.get("status") in ("partially_filled", "canceled", "expired"):
        return "RECOVERY", int(held), "Confirmed shares require reconciliation"

    return "BLOCKED", 0, "Unresolved order status"


def scenario(label, buy, position, expected):
    result = reconcile_fill(buy, position)
    assert result[:2] == expected, (label, result)
    print(label + ":", result)


base = {"symbol": "IWM", "side": "buy"}

scenario(
    "COMPLETE FILL",
    {**base, "status": "filled", "filled_qty": "33"},
    {"symbol": "IWM", "qty": "33"},
    ("READY", 33),
)

scenario(
    "PARTIAL FILL",
    {**base, "status": "partially_filled", "filled_qty": "12"},
    {"symbol": "IWM", "qty": "12"},
    ("RECOVERY", 12),
)

scenario(
    "CANCELED AFTER PARTIAL FILL",
    {**base, "status": "canceled", "filled_qty": "7"},
    {"symbol": "IWM", "qty": "7"},
    ("RECOVERY", 7),
)

scenario(
    "POSITION MISMATCH",
    {**base, "status": "filled", "filled_qty": "33"},
    {"symbol": "IWM", "qty": "32"},
    ("BLOCKED", 0),
)

scenario(
    "ZERO FILL",
    {**base, "status": "canceled", "filled_qty": "0"},
    None,
    ("BLOCKED", 0),
)

print("PARTIAL-FILL POLICY TESTS: PASS")
print("API CALLS: 0")
print("ORDERS SUBMITTED: 0")
