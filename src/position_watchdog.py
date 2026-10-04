"""Read-only IWM position watchdog. No order submission."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from sell_preflight import PAPER, get, find_order
from iwm_signal import load_config
from order_identity import order_id

ET = ZoneInfo("America/New_York")


def main():
    print("IWM V1 — POSITION WATCHDOG")

    try:
        config = load_config()
        headers = {
            "APCA-API-KEY-ID": config["APCA_API_KEY_ID"],
            "APCA-API-SECRET-KEY": config["APCA_API_SECRET_KEY"],
        }

        positions = get(PAPER + "/v2/positions", headers)
        iwm = [p for p in positions if p["symbol"] == "IWM"]

        if not iwm:
            print("POSITION: FLAT")
            print("RECOVERY REQUIRED: NO")
            return

        print("POSITION: OPEN")
        print("HELD SHARES:", iwm[0]["qty"])

        orders = get(
            PAPER + "/v2/orders?status=all&limit=500",
            headers,
        )

        buys = [
            o for o in orders
            if o.get("symbol") == "IWM"
            and o.get("side") == "buy"
            and o.get("client_order_id", "").startswith(
                "IWM-V1-BUY_MOC-"
            )
        ]

        if not buys:
            raise RuntimeError(
                "IWM position exists without identifiable strategy buy"
            )

        buys.sort(
            key=lambda o: o.get("created_at") or "",
            reverse=True,
        )
        buy = buys[0]

        print("ORIGINATING BUY:", buy["client_order_id"])
        print("BUY STATUS:", buy["status"])
        print("FILLED SHARES:", buy.get("filled_qty"))

        # An open position always requires active exit reconciliation.
        # Never infer that a missing sell order is safe.
        print("EXIT RECONCILIATION: REQUIRED")
        print("AUTOMATIC RECOVERY: DISABLED")

    except Exception as exc:
        print("WATCHDOG: EXCEPTION")
        print("REASON:", type(exc).__name__, str(exc))
        print("MANUAL REVIEW: REQUIRED")

    finally:
        print("ORDERS SUBMITTED: 0")


if __name__ == "__main__":
    main()
