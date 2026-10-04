"""Offline integration test of the actual IWM paper service."""
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import iwm_paper_service as svc

ET = ZoneInfo("America/New_York")
orders = []
positions = []
notifications = []
state = {"notified": [], "alerts": []}
posts = []

sessions = [
    {"date": "2026-10-01", "open": "09:30", "close": "16:00"},
    {"date": "2026-10-02", "open": "09:30", "close": "16:00"},
    {"date": "2026-10-05", "open": "09:30", "close": "16:00"},
    {"date": "2026-10-06", "open": "09:30", "close": "16:00"},
]

def fake_api(base, endpoint, headers, method="GET", payload=None):
    if method == "POST":
        assert base == svc.PAPER
        assert endpoint == "/v2/orders"
        assert payload["symbol"] == "IWM"
        assert payload["time_in_force"] in ("cls", "opg")
        assert not any(o["client_order_id"] == payload["client_order_id"]
                       for o in orders)
        order = {
            **payload,
            "id": f"simulated-{len(orders) + 1}",
            "status": "new",
            "filled_qty": "0",
            "filled_at": None,
            "filled_avg_price": None,
            "created_at": "2026-10-05T19:35:00Z",
        }
        orders.append(order)
        posts.append(payload)
        return order

    if endpoint.startswith("/v2/calendar?"):
        return sessions
    if endpoint == "/v2/account":
        return {
            "cash": "10000", "equity": "10000",
            "buying_power": "40000",
            "trading_blocked": False, "account_blocked": False,
        }
    if endpoint == "/v2/positions":
        return positions
    if endpoint.startswith("/v2/orders:by_client_order_id?"):
        cid = parse_qs(endpoint.split("?", 1)[1])["client_order_id"][0]
        return next((o for o in orders if o["client_order_id"] == cid), None)
    if endpoint.startswith("/v2/orders?"):
        if "status=open" in endpoint:
            return [o for o in orders if o["status"] in
                    ("new", "accepted", "pending_new")]
        return orders
    if endpoint.startswith("/v2/stocks/bars?"):
        return {"bars": {"IWM": [
            {"t": "2026-10-01T04:00:00Z", "c": 281.52},
            {"t": "2026-10-02T04:00:00Z", "c": 278.00},
            {"t": "2026-10-05T04:00:00Z", "c": 279.00},
        ]}}
    raise AssertionError(f"Unexpected API request: {method} {endpoint}")

def fake_notify(state, category, key, message, enabled):
    assert enabled
    if key not in state[category]:
        notifications.append(message)
        state[category].append(key)

def clock(day, hour, minute):
    return datetime.fromisoformat(
        f"{day}T{hour:02d}:{minute:02d}:00"
    ).replace(tzinfo=ET)

with patch.object(svc, "api", side_effect=fake_api), \
     patch.object(svc, "notify_once", side_effect=fake_notify):

    # Qualifying prior-session decline: submit one closing-auction buy.
    svc.run({}, state, True, clock("2026-10-05", 15, 35))
    assert len(posts) == 1
    assert posts[0]["side"] == "buy"
    assert posts[0]["time_in_force"] == "cls"
    assert int(posts[0]["qty"]) > 0
    print("MOC BUY SUBMISSION: PASS")

    # Re-running must not create a duplicate.
    svc.run({}, state, True, clock("2026-10-05", 15, 36))
    assert len(posts) == 1
    print("DUPLICATE BUY PREVENTION: PASS")

    # Alpaca confirms the closing-auction fill.
    buy = orders[0]
    buy.update(
        status="filled",
        filled_qty=buy["qty"],
        filled_avg_price="279.00",
        filled_at="2026-10-05T20:00:00Z",
    )
    positions.append({"symbol": "IWM", "qty": buy["qty"]})
    svc.run({}, state, True, clock("2026-10-05", 16, 10))
    assert len(notifications) == 1
    assert "BUY FILLED" in notifications[0]
    assert len(posts) == 1
    print("CONFIRMED BUY FILL AND NOTIFICATION: PASS")

    # Following trading session: submit the opening-auction sell.
    svc.run({}, state, True, clock("2026-10-06", 9, 10))
    assert len(posts) == 2
    assert posts[1]["side"] == "sell"
    assert posts[1]["time_in_force"] == "opg"
    assert posts[1]["qty"] == buy["qty"]
    print("NEXT-SESSION MOO SELL: PASS")

    # Duplicate exit must not be submitted.
    svc.run({}, state, True, clock("2026-10-06", 9, 11))
    assert len(posts) == 2
    print("DUPLICATE SELL PREVENTION: PASS")

    # Alpaca confirms the opening-auction sale.
    sell = orders[1]
    sell.update(
        status="filled",
        filled_qty=sell["qty"],
        filled_avg_price="280.00",
        filled_at="2026-10-06T13:30:00Z",
    )
    positions.clear()
    svc.run({}, state, True, clock("2026-10-06", 9, 40))
    assert len(notifications) == 2
    assert "SELL FILLED" in notifications[1]
    assert "Overnight P&L" in notifications[1]
    assert len(posts) == 2
    print("CONFIRMED SELL FILL AND P&L NOTIFICATION: PASS")

print("INTEGRATED OFFLINE EXECUTION: PASS")
print("REAL API CALLS: 0")
print("REAL ORDERS: 0")
print("REAL TELEGRAM MESSAGES: 0")
