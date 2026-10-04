"""Frozen IWM V1 paper-trading position sizing.

Cash-only execution. Maximum allocation: 95% of available cash or equity.
No orders are submitted by this module.
"""

from decimal import Decimal, ROUND_FLOOR


def calculate_shares(cash, equity, reference_price):
    cash = Decimal(str(cash))
    equity = Decimal(str(equity))
    price = Decimal(str(reference_price))

    if cash <= 0 or equity <= 0 or price <= 0:
        raise ValueError("Cash, equity and price must be positive")

    budget = min(cash, equity) * Decimal("0.95")
    shares = int(
        (budget / price).to_integral_value(rounding=ROUND_FLOOR)
    )

    return {
        "shares": shares,
        "budget": budget,
        "estimated_value": price * shares,
        "cash_buffer": cash - price * shares,
    }


if __name__ == "__main__":
    result = calculate_shares(
        cash="10000",
        equity="10000",
        reference_price="281.52",
    )

    print("IWM POSITION SIZING — TEST ONLY")
    print("Shares:", result["shares"])
    print("Maximum budget: $", result["budget"])
    print("Estimated purchase: $", result["estimated_value"])
    print("Remaining cash: $", result["cash_buffer"])
    print("ORDERS SUBMITTED: 0")
