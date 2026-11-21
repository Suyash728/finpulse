"""Drift nudges vs pro-rated budget, plus recurring alerts. Essentials are informational, never 'cut'."""

from __future__ import annotations

import calendar

from app.engines.categorize import ESSENTIAL


def compute_nudges(month: str | None = None) -> list[dict]:
    from app.engines.ledger import all_transactions, get_profile
    from app.engines.recurring import detect_recurring

    tx = all_transactions()
    if not tx:
        return []
    month = month if month and any(t["date"].startswith(month) for t in tx) else max(t["date"] for t in tx)[:7]
    in_month = [t for t in tx if t["date"].startswith(month) and t["direction"] == "dr"]
    as_of = max((t["date"] for t in in_month), default=f"{month}-01")
    day = int(as_of[8:10])
    dim = calendar.monthrange(int(month[:4]), int(month[5:7]))[1]
    budgets = get_profile().get("budgets") or {}
    out = []
    for cat, budget in budgets.items():
        budget = float(budget or 0)
        if budget <= 0:
            continue
        spent = round(sum(t["amount"] for t in in_month if t["category"] == cat), 2)
        expected = budget * day / dim
        pct = round(spent / budget * 100)
        if (spent >= 0.75 * budget and day < 20) or (expected and spent / expected > 1.25 and spent > 0.3 * budget):
            msg = (f"{cat} is above its usual level: ₹{spent:,.0f} of ₹{budget:,.0f} by day {day}."
                   if cat in ESSENTIAL else
                   f"{cat} at {pct}% of budget on day {day} (₹{spent:,.0f} of ₹{budget:,.0f}).")
            out.append({"id": f"drift-{month}-{cat}", "kind": "drift", "category": cat, "message": msg,
                        "severity": "alert" if pct >= 100 else "warn", "month": month})
    for r in detect_recurring(tx):
        if r["status"] == "changed":
            out.append({"id": f"price-{r['id']}", "kind": "price_change", "category": r["category"],
                        "message": f"{r['merchant_norm'].title()}: {r['note']}", "severity": "warn", "month": month})
        elif r["status"] == "unused":
            out.append({"id": f"unused-{r['id']}", "kind": "unused", "category": r["category"],
                        "message": f"{r['merchant_norm'].title()} ₹{r['amount']:,.0f}/mo: {r['note']}",
                        "severity": "info", "month": month})
    return out
