"""Monthly review: deterministic stats only (cut-list item 4: no LLM narrative)."""

from __future__ import annotations

from app.engines.simulate import NOT_SPEND


def monthly_report(month: str) -> dict:
    from app.engines.ledger import all_transactions, get_goals, get_profile
    from app.engines.recurring import detect_recurring
    from app.engines.simulate import simulate

    tx = all_transactions()
    rows = [t for t in tx if t["date"].startswith(month)]
    prof = get_profile()
    credits = round(sum(t["amount"] for t in rows if t["direction"] == "cr" and t["category"] == "Income"), 2)
    income = credits or prof["monthly_income"]
    by_cat: dict[str, float] = {}
    for t in rows:
        if t["direction"] == "dr" and t["category"] not in NOT_SPEND:
            by_cat[t["category"]] = round(by_cat.get(t["category"], 0) + t["amount"], 2)
    spend = round(sum(by_cat.values()), 2)
    savings = round(income - spend, 2)
    rate = round(savings / income, 4) if income else 0.0
    budgets = prof.get("budgets") or {}
    cats = [{"category": c, "amount": a, "budget": float(budgets[c]) if budgets.get(c) else None}
            for c, a in sorted(by_cat.items(), key=lambda x: -x[1])]
    changes = [{"merchant_norm": r["merchant_norm"], "from": r["prev_amount"], "to": r["amount"]}
               for r in detect_recurring(tx) if r["status"] == "changed"]
    sim = {g["goal_id"]: g for g in simulate([])["goal_dates"]}
    goals = [{"goal_id": g["id"], "name": g["name"],
              "pct": round(g["saved_amount"] / g["target_amount"], 4) if g["target_amount"] else 0,
              "on_track": sim.get(g["id"], {}).get("on_track", False)} for g in get_goals()["items"]]
    highlights = [f"Savings rate {round(rate * 100)}% (₹{savings:,.0f} saved)"]
    over = [c for c in cats if c["budget"] and c["amount"] > c["budget"]]
    for c in over[:2]:
        highlights.append(f"{c['category']} {round((c['amount'] / c['budget'] - 1) * 100)}% over budget "
                          f"(₹{c['amount']:,.0f} vs ₹{c['budget']:,.0f})")
    for ch in changes[:1]:
        highlights.append(f"{ch['merchant_norm'].title()} price changed ₹{ch['from']:,.0f} → ₹{ch['to']:,.0f}")
    return {"month": month, "income": income, "spend": spend, "savings": savings, "savings_rate": rate,
            "by_category": cats, "recurring_changes": changes, "goal_progress": goals, "highlights": highlights}
