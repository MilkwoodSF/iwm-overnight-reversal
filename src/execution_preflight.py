"""Read-only IWM execution preflight. Never submits orders."""

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from session_deadlines import moc_allowed, moc_deadline
from iwm_signal import THRESHOLD, load_config
from order_identity import order_id
from position_sizing import calculate_shares

ET = ZoneInfo("America/New_York")
PAPER = "https://paper-api.alpaca.markets"
DATA = "https://data.alpaca.markets"


def get(url, headers):
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)


def main():
    print("IWM V1 — READ-ONLY EXECUTION PREFLIGHT")
    print("ORDERS SUBMITTED: 0")

    try:
        config = load_config()
        headers = {
            "APCA-API-KEY-ID": config["APCA_API_KEY_ID"],
            "APCA-API-SECRET-KEY": config["APCA_API_SECRET_KEY"],
        }

        now = datetime.now(ET)
        today = now.date()

        calendar = get(
            PAPER + "/v2/calendar?" + urllib.parse.urlencode({
                "start": (today - timedelta(days=15)).isoformat(),
                "end": (today + timedelta(days=10)).isoformat(),
            }),
            headers,
        )

        sessions = sorted(
            (s for s in calendar if s["date"] >= today.isoformat()),
            key=lambda s: s["date"],
        )

        # Skip sessions whose internal MOC submission window has expired.
        eligible_sessions = [
            s for s in sessions if now < moc_deadline(s)
        ]
        if not eligible_sessions:
            raise RuntimeError("No upcoming session before its MOC deadline")

        session = eligible_sessions[0]
        session_date = datetime.fromisoformat(session["date"]).date()

        print("NEXT CALENDAR SESSION:", session_date)
        print("SESSION HOURS:", session["open"], "-", session["close"])

        entry_allowed = session_date == today and moc_allowed(session, now)
        print("MOC INTERNAL DEADLINE:", moc_deadline(session))
        print("AUCTION SAFETY:", "PASS" if entry_allowed else "BLOCKED")

        account = get(PAPER + "/v2/account", headers)
        positions = get(PAPER + "/v2/positions", headers)
        orders = get(PAPER + "/v2/orders?status=open&limit=500", headers)

        if account.get("trading_blocked") or account.get("account_blocked"):
            raise RuntimeError("Account blocked")

        if any(p["symbol"] == "IWM" for p in positions):
            raise RuntimeError("Existing IWM position")

        if any(o["symbol"] == "IWM" for o in orders):
            raise RuntimeError("Outstanding IWM order")

        print("ACCOUNT SAFETY: PASS")

        # Diagnostics may continue outside the entry window.
        # Execution eligibility remains independently blocked.
        client_id = order_id("BUY_MOC", session_date)
        url = PAPER + "/v2/orders:by_client_order_id?" + (
            urllib.parse.urlencode({"client_order_id": client_id})
        )

        try:
            existing = get(url, headers)
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise
        else:
            raise RuntimeError(
                "Order identifier already exists: "
                + existing.get("status", "unknown")
            )

        bars = get(
            DATA + "/v2/stocks/bars?" + urllib.parse.urlencode({
                "symbols": "IWM",
                "timeframe": "1Day",
                "start": (today - timedelta(days=15)).isoformat(),
                "end": today.isoformat(),
                "limit": 20,
                "adjustment": "raw",
                "feed": "sip",
            }),
            headers,
        )["bars"]["IWM"]

        previous_sessions = sorted(
            s["date"] for s in calendar
            if s["date"] < session_date.isoformat()
        )
        if len(previous_sessions) < 2:
            raise RuntimeError("Insufficient preceding calendar sessions")

        expected_dates = previous_sessions[-2:]
        bars_by_date = {
            b["t"][:10]: b for b in bars
            if b["t"][:10] < session_date.isoformat()
        }

        missing = [d for d in expected_dates if d not in bars_by_date]
        if missing:
            raise RuntimeError(
                "Missing required trading-session bars: " + str(missing)
            )

        previous, latest = [bars_by_date[d] for d in expected_dates]
        print("SIGNAL BAR DATES:", expected_dates)
        print("SESSION ALIGNMENT: PASS")

        # For future-session diagnostics, this is provisional:
        # tomorrow's final preceding close may not exist yet.
        if session_date != today:
            print("SIGNAL STATUS: PROVISIONAL — future session")
        prior_return = latest["c"] / previous["c"] - 1

        print("PRIOR SESSION RETURN:", f"{prior_return:.6%}")
        print("FROZEN THRESHOLD:", f"{THRESHOLD:.6%}")

        if prior_return > THRESHOLD:
            print("SIGNAL: NO TRADE")
            print("ENTRY: BLOCKED — no qualifying signal")
            return

        sizing = calculate_shares(
            account["cash"],
            account["equity"],
            latest["c"],
        )
        print("SIZING RESULT:", sizing)
        if sizing["shares"] < 1:
            raise RuntimeError("Insufficient cash for one whole share")

        print("SIGNAL: BUY")
        if not entry_allowed:
            print("ENTRY: BLOCKED — outside today's permitted MOC window")
        else:
            print("ENTRY: ELIGIBLE IN DRY RUN ONLY")
        print("NO ORDER SUBMISSION IMPLEMENTED")

    except Exception as exc:
        print("PREFLIGHT: BLOCKED")
        print("REASON:", type(exc).__name__, str(exc))
    finally:
        print("ORDERS SUBMITTED: 0")


if __name__ == "__main__":
    main()
