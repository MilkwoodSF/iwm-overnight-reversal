"""Independent Telegram notifications for IWM paper trading."""

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

CONFIG = Path("/root/.config/iwm-overnight-reversal/paper.env")


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


def send_message(message):
    settings = load_config()
    token = settings["TELEGRAM_BOT_TOKEN"]
    chat_id = settings["TELEGRAM_CHAT_ID"]

    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": message,
        }).encode(),
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            result = json.load(response)
        return result.get("ok") is True
    except Exception:
        return False


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] != "--test":
        sys.exit("Usage: python3 src/telegram_notifier.py --test")

    message = (
        "IWM OVERNIGHT REVERSAL V1\n"
        "TELEGRAM CONNECTION TEST\n\n"
        "Dedicated Alpaca paper account\n"
        "No orders submitted\n"
        "Trade notifications: BUY / SELL fills only"
    )

    success = send_message(message)
    print("TELEGRAM TEST:", "PASS" if success else "FAIL")
    sys.exit(0 if success else 1)
