"""Read-only IWM sell-side reconciliation. Never submits orders."""

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from iwm_signal import load_config
from order_identity import order_id
from trading_calendar import next_session

ET = ZoneInfo("America/New_York")
PAPER = "https://paper-api.alpaca.markets"


def get(url, headers):
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)


def find_order(client_id, headers):
    url = PAPER + "/v2/orders:by_client_order_id?" + (
        urllib.parse.urlencode({"client_order_id": client_id})
    )

    try:
        return get(url, headers)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def validate_sell(
    buy, position, existing_sell, sell_date, now, buy_date=None
):
    """Pure safety checks; returns quantity only when all pass."""
    if buy is None:
        raise RuntimeError("No confirmed buy order")

    if buy.get("symbol") != "IWM":
        raise RuntimeError("Buy order symbol mismatch")

    if buy.get("side") != "buy":
        raise RuntimeError("Expected a buy order")

    if buy_date is not None:
        if buy.get("client_order_id") != order_id("BUY_MOC", buy_date):
            raise RuntimeError("Buy identifier does not match entry session")

        timestamp = buy.get("filled_at")
        if not timestamp:
            raise RuntimeError("Buy fill timestamp unavailable")

        filled_date = datetime.fromisoformat(
            timestamp.replace("Z", "+00:00")
        ).astimezone(ET).date()

        if filled_date != buy_date:
            raise RuntimeError("Buy fill occurred on unexpected date")

    status = buy.get("status")

    if status == "partially_filled":
        raise RuntimeError(
            "Buy remains partially filled; further fills are possible"
        )

    if status not in ("filled", "canceled", "expired"):
        raise RuntimeError("Buy order has unresolved status")

    from decimal import Decimal

    filled = Decimal(str(buy.get("filled_qty") or "0"))
    if filled <= 0 or filled != filled.to_integral_value():
        raise RuntimeError("Invalid confirmed fill quantity")

    if status == "filled" and buy.get("filled_at") is None:
        raise RuntimeError("Missing confirmed fill timestamp")

    quantity = int(filled)

    if quantity < 1:
        raise RuntimeError("Invalid filled quantity")

    if position is None or position.get("symbol") != "IWM":
        raise RuntimeError("IWM position missing")

    if int(position["qty"]) != quantity:
        raise RuntimeError("Position and buy fill quantities disagree")

    if existing_sell is not None:
        raise RuntimeError("Sell order identifier already exists")

    local = now.astimezone(ET)

    if local.date() != sell_date:
        raise RuntimeError("Not the scheduled exit session")

    if not time(4, 0) <= local.time() < time(9, 20):
        raise RuntimeError("Outside conservative MOO window")

    return quantity


def main():
    print("IWM V1 — READ-ONLY SELL PREFLIGHT")

    try:
        config = load_config()
        headers = {
            "APCA-API-KEY-ID": config["APCA_API_KEY_ID"],
            "APCA-API-SECRET-KEY": config["APCA_API_SECRET_KEY"],
        }

        now = datetime.now(ET)
        session = next_session(now)

        if session is None:
            raise RuntimeError("No upcoming trading session")

        sell_date = date.fromisoformat(session["date"])
        print("CANDIDATE EXIT SESSION:", sell_date)

        # Find the preceding trading session through Alpaca's calendar.
        calendar_url = PAPER + "/v2/calendar?" + urllib.parse.urlencode({
            "start": (sell_date - timedelta(days=10)).isoformat(),
            "end": sell_date.isoformat(),
        })
        calendar = get(calendar_url, headers)
        previous = sorted(
            date.fromisoformat(s["date"])
            for s in calendar
            if s["date"] < sell_date.isoformat()
        )

        if not previous:
            raise RuntimeError("Previous trading session unavailable")

        buy_date = previous[-1]
        print("EXPECTED BUY SESSION:", buy_date)

        buy = find_order(order_id("BUY_MOC", buy_date), headers)
        sell = find_order(order_id("SELL_MOO", sell_date), headers)

        positions = get(PAPER + "/v2/positions", headers)
        position = next(
            (p for p in positions if p["symbol"] == "IWM"),
            None,
        )

        quantity = validate_sell(
            buy, position, sell, sell_date, now, buy_date
        )

        print("CONFIRMED POSITION:", quantity, "shares")
        print("SELL: ELIGIBLE IN DRY RUN ONLY")

    except Exception as exc:
        print("SELL: BLOCKED")
        print("REASON:", type(exc).__name__, str(exc))

    finally:
        print("ORDERS SUBMITTED: 0")


if __name__ == "__main__":
    main()
