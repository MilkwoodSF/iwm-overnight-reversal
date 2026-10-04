"""IWM Prior Decline V1 — observation-only signal calculator."""

import json
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

CONFIG = Path("/root/.config/iwm-overnight-reversal/paper.env")
THRESHOLD = -0.0066555
ET = ZoneInfo("America/New_York")


def load_config():
    settings = {}
    for line in CONFIG.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        settings[key.strip().removeprefix("export ").strip()] = (
            value.strip().strip('"').strip("'")
        )
    return settings


def main():
    now = datetime.now(timezone.utc).astimezone(ET)

    # Before the close, exclude today's unfinished daily bar.
    # After the close, still exclude today: today's return is
    # not eligible to determine today's closing-auction entry.
    cutoff = now.date()

    params = urllib.parse.urlencode({
        "symbols": "IWM",
        "timeframe": "1Day",
        "start": (cutoff - timedelta(days=15)).isoformat(),
        "end": cutoff.isoformat(),
        "limit": 20,
        "adjustment": "raw",
        "feed": "sip",
    })

    settings = load_config()
    request = urllib.request.Request(
        "https://data.alpaca.markets/v2/stocks/bars?" + params,
        headers={
            "APCA-API-KEY-ID": settings["APCA_API_KEY_ID"],
            "APCA-API-SECRET-KEY": settings["APCA_API_SECRET_KEY"],
        },
    )

    with urllib.request.urlopen(request, timeout=15) as response:
        bars = json.load(response).get("bars", {}).get("IWM", [])

    completed = [
        bar for bar in bars
        if bar["t"][:10] < cutoff.isoformat()
    ]

    if len(completed) < 2:
        raise RuntimeError("Insufficient completed sessions")

    previous, latest = completed[-2:]
    prior_return = latest["c"] / previous["c"] - 1
    decision = "BUY" if prior_return <= THRESHOLD else "NO TRADE"

    print("IWM PRIOR DECLINE V1 — OBSERVATION ONLY")
    print("Decision date:", cutoff)
    print("Reference dates:", previous["t"][:10], latest["t"][:10])
    print("Reference closes:", previous["c"], latest["c"])
    print("Previous-session return:", f"{prior_return:+.6%}")
    print("Frozen threshold:", f"{THRESHOLD:+.6%}")
    print("Decision:", decision)
    print("ORDERS SUBMITTED: 0")


if __name__ == "__main__":
    main()
