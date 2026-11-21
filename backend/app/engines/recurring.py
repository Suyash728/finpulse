"""Recurring payment / subscription detection (pure Python over transactions)."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

VARIABLE = {"Transfers", "Income", "Shopping", "Fuel", "Other", "Groceries", "Dining", "Food Delivery",
            "Travel", "Entertainment", "Medical"}  # one-off-ish spending, not bills
PRICE_CATEGORIES = {"Subscriptions", "Insurance"}  # bills like electricity vary naturally
SUBSCRIPTION_NAMES = ("netflix", "spotify", "cultfit", "prime", "hotstar", "youtube", "icloud", "tata play")
FITNESS = ("cultfit", "gym", "fitness")


def detect_recurring(transactions: list[dict]) -> list[dict]:
    """Debits from the same merchant once a month in >= 2 months.

    changed: latest amount differs from previous by > 5% (subscription-like categories)
    unused:  fitness subscription with no other fitness-related spending
    """
    by_merchant: dict[str, list[dict]] = defaultdict(list)
    for t in transactions:
        is_sub = any(k in t["merchant_norm"] for k in SUBSCRIPTION_NAMES)
        if t["direction"] == "dr" and (is_sub or t["category"] not in VARIABLE):
            by_merchant[t["merchant_norm"]].append(t)
    names = " ".join(by_merchant)
    items = []
    for m, rows in by_merchant.items():
        months: dict[str, list[dict]] = defaultdict(list)
        for r in rows:
            months[r["date"][:7]].append(r)
        if len(months) < 2 or max(len(v) for v in months.values()) > 1:
            continue  # not monthly (e.g. Swiggy several times a month)
        ordered = sorted(rows, key=lambda r: r["date"])
        last, prev = ordered[-1], ordered[-2]
        amt, prev_amt = float(last["amount"]), float(prev["amount"])
        change = (amt - prev_amt) / prev_amt if prev_amt else 0
        status, note = "active", f"Monthly, last paid {last['date']}"
        if abs(change) > 0.05 and (last["category"] in PRICE_CATEGORIES or any(k in m for k in SUBSCRIPTION_NAMES)):
            status = "changed"
            note = f"Price {'up' if change > 0 else 'down'} {abs(round(change * 100))}% (₹{prev_amt:,.0f} → ₹{amt:,.0f})"
        elif any(k in m for k in FITNESS) and not any(k in n for n in names.split() for k in ("decathlon", "sports")):
            status, note = "unused", "No related fitness activity found while you keep paying"
        next_due = (date.fromisoformat(last["date"]) + timedelta(days=30)).isoformat()
        items.append({"id": m, "merchant_norm": m, "category": last["category"], "amount": amt, "next_due": next_due,
                      "prev_amount": prev_amt, "cadence": "monthly", "last_seen": last["date"],
                      "status": status, "note": note})
    order = {"changed": 0, "unused": 1, "active": 2}
    return sorted(items, key=lambda i: (order[i["status"]], -i["amount"]))
