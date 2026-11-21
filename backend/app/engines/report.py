"""Monthly review: deterministic stats + chart series + rule-based insights. All math in Python."""

from __future__ import annotations

import calendar
from datetime import date

from app.engines.simulate import NOT_SPEND


def _prev_month(m: str) -> str:
    y, mo = map(int, m.split("-"))
    return f"{y - (mo == 1)}-{12 if mo == 1 else mo - 1:02d}"


def _spend_by_cat(rows: list[dict]) -> dict[str, float]:
    out: dict[str, float] = {}
    for t in rows:
        if t["direction"] == "dr" and t["category"] not in NOT_SPEND:
            out[t["category"]] = round(out.get(t["category"], 0) + t["amount"], 2)
    return out


FIXED = {"Rent", "EMI", "Insurance", "Education", "Utilities", "Subscriptions"}  # paid once, not per day


def _pct(new: float, old: float) -> float | None:
    return round((new - old) / old * 100, 1) if old else None


def _insights(cats: list[dict], changes: list[dict], rate: float, savings: float,
              projection: dict) -> list[dict]:
    """Rule-based insight cards; every number comes from the computed stats above."""
    out: list[dict] = []
    cats = [c for c in cats if c["category"] != "Other"]  # unlabelled rows aren't insight material
    moved = [c for c in cats if c["change_pct"] is not None and abs(c["change_pct"]) >= 10]
    for c in sorted(moved, key=lambda c: -abs(c["change_pct"]))[:2]:
        up = c["change_pct"] > 0
        out.append({"text": f"{c['category']} spending is {'up' if up else 'down'} {abs(round(c['change_pct']))}% "
                            f"vs last month (₹{c['prev_amount']:,.0f} → ₹{c['amount']:,.0f}).",
                    "category": c["category"], "delta_pct": c["change_pct"], "tone": "bad" if up else "good"})
    over = [c for c in cats if c["budget"] and c["amount"] > c["budget"]]
    if over:
        c = max(over, key=lambda c: c["amount"] / c["budget"])
        pct = round((c["amount"] / c["budget"] - 1) * 100)
        out.append({"text": f"{c['category']} is {pct}% over its ₹{c['budget']:,.0f} budget.",
                    "category": c["category"], "delta_pct": float(pct), "tone": "bad"})
    for ch in changes[:1]:
        pct = _pct(ch["to"], ch["from"])
        out.append({"text": f"{ch['merchant_norm'].title()} went from ₹{ch['from']:,.0f} to ₹{ch['to']:,.0f} a month. "
                            "Worth a review.", "category": "Subscriptions", "delta_pct": pct, "tone": "bad"})
    if projection["budget_total"]:
        ok = projection["on_track"]
        done = projection["days_left"] == 0
        verb = "You spent" if done else "On pace to spend"
        out.append({"text": (f"{verb} ₹{projection['projected']:,.0f} this month, "
                             f"{'within' if ok else 'above'} your ₹{projection['budget_total']:,.0f} budget."),
                    "category": None, "delta_pct": None, "tone": "good" if ok else "bad"})
    out.append({"text": f"You kept {round(rate * 100)}% of income (₹{savings:,.0f}) this month.",
                "category": "Savings", "delta_pct": None, "tone": "good" if rate >= 0.2 else "bad"})
    return out


def monthly_report(month: str) -> dict:
    from app.engines.ledger import (
        all_transactions,
        available_months,
        get_goals,
        get_profile,
        latest_month,
    )

    if month == "latest":
        month = latest_month()
    from app.engines.recurring import detect_recurring
    from app.engines.simulate import simulate

    tx = all_transactions()
    rows = [t for t in tx if t["date"].startswith(month)]
    prev_m = _prev_month(month)
    prof = get_profile()
    credits = round(sum(t["amount"] for t in rows if t["direction"] == "cr" and t["category"] == "Income"), 2)
    income = credits or prof["monthly_income"]
    by_cat = _spend_by_cat(rows)
    prev_cat = _spend_by_cat([t for t in tx if t["date"].startswith(prev_m)])
    spend = round(sum(by_cat.values()), 2)
    savings = round(income - spend, 2)
    rate = round(savings / income, 4) if income else 0.0
    budgets = {k: float(v) for k, v in (prof.get("budgets") or {}).items() if v}
    cats = [{"category": c, "amount": a, "budget": budgets.get(c), "prev_amount": prev_cat.get(c, 0.0),
             "change_pct": _pct(a, prev_cat.get(c, 0.0))}
            for c, a in sorted(by_cat.items(), key=lambda x: -x[1])]

    # daily spend + cumulative + projection (as_of = latest transaction in the month)
    y, mo = map(int, month.split("-"))
    dim = calendar.monthrange(y, mo)[1]
    per_day, var_day = [0.0] * dim, [0.0] * dim
    for t in rows:
        if t["direction"] == "dr" and t["category"] not in NOT_SPEND:
            per_day[int(t["date"][8:10]) - 1] += t["amount"]
            if t["category"] not in FIXED:
                var_day[int(t["date"][8:10]) - 1] += t["amount"]
    per_day = [round(v, 2) for v in per_day]
    as_of_day = max((int(t["date"][8:10]) for t in rows), default=dim)
    full_month = date(y, mo, dim) < date.today() and as_of_day >= dim - 1
    if full_month:
        as_of_day = dim
    cum, run = [], 0.0
    for d in range(dim):
        run += per_day[d]
        cum.append({"day": d + 1, "actual": round(run, 2) if d < as_of_day else None})
    spent_so_far = round(sum(per_day[:as_of_day]), 2)
    avg = round(spent_so_far / as_of_day, 2) if as_of_day else 0.0
    # Only variable spending continues per day; fixed bills (rent, EMI...) are already paid.
    var_avg = round(sum(var_day[:as_of_day]) / as_of_day, 2) if as_of_day else 0.0
    projected = spent_so_far if full_month else round(spent_so_far + var_avg * (dim - as_of_day), 2)
    budget_total = round(sum(v for k, v in budgets.items() if k not in NOT_SPEND), 2)
    for i, c in enumerate(cum):
        c["projected"] = round(spent_so_far + var_avg * (i + 1 - as_of_day), 2) if i + 1 >= as_of_day else None
    projection = {"as_of_day": as_of_day, "days_in_month": dim, "days_left": dim - as_of_day,
                  "spent_so_far": spent_so_far, "avg_per_day": avg, "variable_avg_per_day": var_avg, "projected": projected,
                  "budget_total": budget_total, "on_track": bool(budget_total and projected <= budget_total),
                  "cumulative": cum}

    changes = [{"merchant_norm": r["merchant_norm"], "from": r["prev_amount"], "to": r["amount"]}
               for r in detect_recurring(tx) if r["status"] == "changed"]
    sim = {g["goal_id"]: g for g in simulate([])["goal_dates"]}
    goals = [{"goal_id": g["id"], "name": g["name"],
              "pct": round(g["saved_amount"] / g["target_amount"], 4) if g["target_amount"] else 0,
              "on_track": sim.get(g["id"], {}).get("on_track", False)} for g in get_goals()["items"]]
    insights = _insights(cats, changes, rate, savings, projection)
    return {"month": month, "available_months": available_months(), "prev_month": prev_m, "income": income, "spend": spend, "savings": savings,
            "savings_rate": rate, "prev_spend": round(sum(prev_cat.values()), 2),
            "by_category": cats, "daily": [{"date": f"{month}-{d + 1:02d}", "amount": per_day[d]} for d in range(dim)],
            "projection": projection, "recurring_changes": changes, "goal_progress": goals,
            "highlights": [i["text"] for i in insights], "insights": insights}
