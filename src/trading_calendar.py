"""Alpaca trading calendar — read-only scheduling safeguards."""

import json
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
CONFIG = Path("/root/.config/iwm-overnight-reversal/paper.env")


def credentials():
    result = {}
    for line in CONFIG.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def next_session(now=None):
    now = now or datetime.now(ET)
    today = now.date()

    query = urllib.parse.urlencode({
        "start": today.isoformat(),
        "end": (today + timedelta(days=10)).isoformat(),
    })

    keys = credentials()
    request = urllib.request.Request(
        "https://paper-api.alpaca.markets/v2/calendar?" + query,
        headers={
            "APCA-API-KEY-ID": keys["APCA_API_KEY_ID"],
            "APCA-API-SECRET-KEY": keys["APCA_API_SECRET_KEY"],
        },
    )

    with urllib.request.urlopen(request, timeout=15) as response:
        sessions = json.load(response)

    for session in sessions:
        session_date = datetime.fromisoformat(session["date"]).date()
        closing = datetime.combine(
            session_date,
            datetime.strptime(session["close"], "%H:%M").time(),
            ET,
        )

        if closing > now:
            return session

    raise RuntimeError("No upcoming trading session found")


if __name__ == "__main__":
    session = next_session()
    print("NEXT TRADING SESSION:", session["date"])
    print("MARKET OPEN:", session["open"], "ET")
    print("MARKET CLOSE:", session["close"], "ET")
    print("ORDERS SUBMITTED: 0")
