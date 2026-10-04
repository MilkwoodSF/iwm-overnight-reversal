"""Deterministic order identifiers for IWM paper trading."""

from datetime import date


def order_id(action: str, session: date) -> str:
    if action not in ("BUY_MOC", "SELL_MOO"):
        raise ValueError("Unsupported action")

    if not isinstance(session, date):
        raise TypeError("Session must be a date")

    return f"IWM-V1-{action}-{session:%Y%m%d}"


if __name__ == "__main__":
    session = date(2026, 10, 5)

    buy = order_id("BUY_MOC", session)
    sell = order_id("SELL_MOO", session)

    assert buy == "IWM-V1-BUY_MOC-20261005"
    assert sell == "IWM-V1-SELL_MOO-20261005"
    assert buy == order_id("BUY_MOC", session)
    assert buy != sell

    print("BUY IDENTIFIER:", buy)
    print("SELL IDENTIFIER:", sell)
    print("DETERMINISTIC IDENTIFIERS: PASS")
    print("ORDERS SUBMITTED: 0")
