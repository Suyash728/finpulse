"""Coach agent: plain function calling (spec: agents/graph.md). Owner: Suyash.

Flow: intent_guard -> up to MAX_STEPS tool rounds -> answer -> essentials post-check.
Each step emits trace.emit(run_id, node, status, tier_used, ms, args=..., result_summary=...).
All model calls go through app.services.llm.chat(); every rupee figure comes from a tool result.

Guardrails live here (not in engines/) so the backend owner stays on ingest; move them to
engines/guardrails.py later if both agree.
"""

from __future__ import annotations

import inspect
import json
import re
import time
from collections.abc import Callable
from datetime import date

from app.engines.categorize import CATEGORIES, ESSENTIAL
from app.examples import EXAMPLES
from app.services import llm, trace

MAX_STEPS = 4
FAST_MODEL = "openai/gpt-oss-20b"

TOOL_NAMES = ("query_transactions", "get_profile", "update_profile", "set_goal",
              "get_recurring", "simulate", "get_nudges")

# ----------------------------------------------------------------- guardrails
_SEC_NOUN = (r"stocks?|shares?|equit(?:y|ies)|mutual\s*funds?|\bmf\b|etfs?|index\s*funds?|crypto\w*|"
             r"bitcoin|btc|ethereum|\beth\b|dogecoin|nfts?|ipos?|smallcap|midcap|largecap|"
             r"small[-\s]cap|mid[-\s]cap|large[-\s]cap|f&o|options?\s+trading|futures|sensex|nifty")
_SEC_VERB = r"buy|sell|hold|invest(?:ing)?\s+in|put\s+(?:my\s+)?money\s+in|pick|recommend|suggest|best|top|which|good"
_STRONG = [
    re.compile(rf"\b(?:{_SEC_VERB})\b[^.?!]{{0,40}}\b(?:{_SEC_NOUN})", re.IGNORECASE),
    re.compile(rf"\b(?:{_SEC_NOUN})\b[^.?!]{{0,25}}\b(?:to\s+buy|to\s+pick|should\s+i|worth\s+buying|good\s+buy|good\s+investment)",
               re.IGNORECASE),
    re.compile(r"\bsip\s+in\s+\w+", re.IGNORECASE),
    re.compile(r"\b(?:buy|sell)\b[^.?!]{0,15}\b[A-Z]{2,10}\b"),  # ticker-like ALLCAPS: "buy TCS"
]
# "Should I buy Reliance?": a capitalised name after buy/sell/invest is ambiguous -> ask the LLM.
_AMBIGUOUS = re.compile(r"\b(?:buy|sell|invest|hold)\b[^.?!]{0,20}\b[A-Z][a-zA-Z]{2,}")

SECURITIES_REFUSAL = (
    "I can't recommend specific stocks, funds or crypto. That needs a SEBI-registered advisor who "
    "knows your full situation. Here's how people usually think about it:\n"
    "- **Emergency fund first:** 3–6 months of expenses in a savings account or liquid fund.\n"
    "- **Then clear high-interest debt** (credit cards, personal loans).\n"
    "- **Then long-term, diversified investing:** low-cost index funds spread risk across many "
    "companies; match the risk to how many years until you need the money.\n"
    "Want me to work out how much you could set aside each month for investing?"
)


def is_securities_request(text: str) -> bool | None:
    """True = clearly asks for a security pick; None = ambiguous (ask the LLM); False = no."""
    if any(p.search(text) for p in _STRONG):
        return True
    if _AMBIGUOUS.search(text):
        return None
    return False


_CUT = r"cut|cutting|reduce|reducing|lower|lowering|skip|skipping|stop|stopping|trim|trimming|slash|less\s+on|spend\s+less|drop|eliminate"
_ESS = "|".join(sorted((re.escape(c) for c in ESSENTIAL), key=len, reverse=True))
_ESS_NEAR = [
    re.compile(rf"\b(?:{_CUT})\b(?:\W+\w+){{0,6}}?\W+({_ESS})\b", re.IGNORECASE),
    re.compile(rf"\b({_ESS})\b(?:\W+\w+){{0,6}}?\W+(?:{_CUT})\b", re.IGNORECASE),
]
_NEGATION = re.compile(r"\b(?:don'?t|do not|never|not|isn'?t|aren'?t|avoid|without)\b", re.IGNORECASE)


def mentions_cutting_essentials(reply: str) -> list[str]:
    """Essential category names that appear within ~6 words of a cut verb (negated sentences ignored)."""
    found: set[str] = set()
    for sentence in re.split(r"(?<=[.!?\n])\s+", reply):
        if _NEGATION.search(sentence):
            continue
        for pat in _ESS_NEAR:
            for m in pat.finditer(sentence):
                found.add(next(c for c in ESSENTIAL if c.lower() == m.group(1).lower()))
    return sorted(found)


def _strip_essential_cuts(reply: str) -> str:
    keep = [s for s in re.split(r"(?<=[.!?\n])\s+", reply) if not mentions_cutting_essentials(s)]
    return " ".join(keep).strip()


_RUPEE = re.compile(r"(?:₹|rs\.?|inr)\s?(\d[\d,]*(?:\.\d+)?)", re.IGNORECASE)
_NUM = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def _numbers_in(obj: object, acc: set[float]) -> set[float]:
    """Every number found in tool results (values and digits inside strings)."""
    if isinstance(obj, bool):
        return acc
    if isinstance(obj, int | float):
        acc.add(round(abs(float(obj)), 2))
    elif isinstance(obj, str):
        for m in _NUM.findall(obj):
            try:
                acc.add(round(abs(float(m.replace(",", ""))), 2))
            except ValueError:
                pass
    elif isinstance(obj, dict):
        for v in obj.values():
            _numbers_in(v, acc)
    elif isinstance(obj, list | tuple):
        for v in obj:
            _numbers_in(v, acc)
    return acc


def unsupported_amounts(reply: str, sources: list[object]) -> list[str]:
    """₹ amounts in the reply that no tool result (or the user) provided, i.e. LLM arithmetic."""
    known: set[float] = set()
    for src in sources:
        _numbers_in(src, known)
    bad = []
    for raw in _RUPEE.findall(reply):
        val = round(float(raw.replace(",", "")), 2)
        if val not in known:
            bad.append(raw)
    return bad


def _strip_unsupported(reply: str, sources: list[object]) -> str:
    keep = [s for s in re.split(r"(?<=[.!?\n])\s+", reply) if not unsupported_amounts(s, sources)]
    return " ".join(keep).strip()


def intent_guard(message: str) -> dict:
    """Regex first; LLM yes/no only when ambiguous. Returns {intent, tier_used, ms}."""
    t0 = time.perf_counter()
    hit = is_securities_request(message)
    if hit is not None:
        return {"intent": "securities" if hit else "planning", "tier_used": None,
                "ms": int((time.perf_counter() - t0) * 1000)}
    prompt = [
        {"role": "system", "content": "Classify the user's message. Answer with exactly one word: "
         "'securities' if it asks whether to buy, sell or hold a specific stock, company share, fund, "
         "ETF, crypto or IPO; otherwise 'planning'."},
        {"role": "user", "content": message},
    ]
    try:
        try:
            r = llm.chat(prompt, tiers=("groq",), model=FAST_MODEL, temperature=0, max_tokens=200)
        except llm.AllTiersFailed:
            r = llm.chat(prompt, temperature=0, max_tokens=200)
        intent = "securities" if "securities" in r.text.lower() else "planning"
        return {"intent": intent, "tier_used": r.tier, "ms": int((time.perf_counter() - t0) * 1000)}
    except llm.AllTiersFailed:
        return {"intent": "planning", "tier_used": None, "ms": int((time.perf_counter() - t0) * 1000)}


# ----------------------------------------------------------------- tools
def _db():
    from app.db import get_client

    return get_client()


def _fallback(fn: Callable[[], object], example: object) -> tuple[object, bool]:
    """Run the real engine; fall back to the contract example until that slice lands."""
    try:
        return fn(), False
    except NotImplementedError:
        return example, True


def tool_query_transactions(month: str | None = None, category: str | None = None,
                            merchant: str | None = None, limit: int = 30) -> dict:
    def real():
        q = _db().table("transactions").select(
            "date,amount,direction,merchant_norm,category,cat_source")
        if month:
            q = q.gte("date", f"{month}-01").lte("date", f"{month}-31")
        if category:
            q = q.eq("category", category)
        if merchant:
            q = q.ilike("merchant_norm", f"%{merchant.lower()}%")
        rows = q.order("date", desc=True).limit(500).execute().data
        totals: dict[str, float] = {}
        for r in rows:
            if r["direction"] == "dr":
                totals[r["category"]] = round(totals.get(r["category"], 0) + float(r["amount"]), 2)
        return {"count": len(rows), "debit_totals_by_category": totals,
                "items": rows[: max(1, min(int(limit), 50))]}

    try:
        return real()
    except Exception:  # noqa: BLE001 - no DB / not ingested yet -> contract example
        ex = EXAMPLES["transactions"]
        return {"count": ex["total"], "debit_totals_by_category": {}, "items": ex["items"],
                "note": "example data"}


def tool_get_profile() -> dict:
    """DB profile once seeded (income > 0); otherwise the demo seed profile."""
    from app.seed import PROFILE

    seed = {k: v for k, v in PROFILE.items() if k != "email"}
    try:
        rows = _db().table("profile").select(
            "monthly_income,fixed_costs,emergency_fund,budgets").eq("id", 1).execute().data
    except Exception:  # noqa: BLE001 - no DB configured -> seed profile
        return seed
    return rows[0] if rows and float(rows[0].get("monthly_income") or 0) > 0 else seed


def tool_update_profile(**fields) -> dict:
    allowed = {k: v for k, v in fields.items()
               if k in {"monthly_income", "fixed_costs", "emergency_fund", "budgets"} and v is not None}
    if not allowed:
        return {"error": "nothing to update"}
    _db().table("profile").update(allowed).eq("id", 1).execute()
    return tool_get_profile()


def tool_set_goal(name: str, target_amount: float, target_date: str, saved_amount: float = 0) -> dict:
    date.fromisoformat(target_date)  # validate
    row = {"name": name, "target_amount": target_amount, "target_date": target_date,
           "saved_amount": saved_amount}
    return _db().table("goals").insert(row).execute().data[0]


def tool_get_recurring() -> dict:
    from app.engines.recurring import detect_recurring

    def real():
        try:
            rows = _db().table("transactions").select("*").execute().data
        except Exception:  # noqa: BLE001 - no DB -> engine sees no rows
            rows = []
        return {"items": detect_recurring(rows)}

    out, _ = _fallback(real, EXAMPLES["recurring"])
    return out  # type: ignore[return-value]


def tool_simulate(adjustments: list[dict] | None = None) -> dict:
    from app.engines.simulate import simulate

    adj, blocked = [], []
    for a in adjustments or []:
        if a.get("category") not in CATEGORIES:
            continue
        change = a.get("pct_change") if a.get("pct_change") is not None else a.get("abs_change")
        if a["category"] in ESSENTIAL and a["category"] != "Income" and (change or 0) < 0:
            blocked.append(a["category"])  # essentials may be modelled rising, never cut
            continue
        adj.append(a)
    out, _ = _fallback(lambda: simulate(adj), EXAMPLES["simulate"])
    out = dict(out)  # type: ignore[arg-type]
    if blocked:
        out["not_modelled"] = f"Cuts to essential categories are not modelled: {', '.join(sorted(set(blocked)))}"
    try:  # deltas computed here (Python), so the model can quote them instead of subtracting
        b, sc = out["baseline"], out["scenario"]
        out["delta_monthly_savings"] = round(sc["monthly_savings"] - b["monthly_savings"], 2)
        out["delta_monthly_spend"] = round(sc["monthly_spend"] - b["monthly_spend"], 2)
    except (KeyError, TypeError):
        pass
    return out


def tool_get_nudges(month: str | None = None) -> dict:
    from app.engines.nudges import compute_nudges

    m = month or date.today().strftime("%Y-%m")
    out, _ = _fallback(lambda: {"items": compute_nudges(m)}, EXAMPLES["nudges"])
    return out  # type: ignore[return-value]


TOOLS: dict[str, Callable[..., dict]] = {
    "query_transactions": tool_query_transactions,
    "get_profile": tool_get_profile,
    "update_profile": tool_update_profile,
    "set_goal": tool_set_goal,
    "get_recurring": tool_get_recurring,
    "simulate": tool_simulate,
    "get_nudges": tool_get_nudges,
}


def _fn(name: str, desc: str, props: dict, required: list[str] | None = None) -> dict:
    return {"type": "function", "function": {
        "name": name, "description": desc,
        "parameters": {"type": "object", "properties": props, "required": required or []}}}


_CAT = {"type": "string", "enum": list(CATEGORIES)}


def tool_schemas() -> list[dict]:
    """OpenAI-format tool definitions for TOOL_NAMES."""
    return [
        _fn("query_transactions", "List the user's transactions and debit totals per category.",
            {"month": {"type": "string", "description": "YYYY-MM"}, "category": _CAT,
             "merchant": {"type": "string"}, "limit": {"type": "integer", "maximum": 50}}),
        _fn("get_profile", "Monthly income, fixed costs, emergency fund and category budgets.", {}),
        _fn("update_profile", "Update income, fixed costs or emergency fund when the user states new values.",
            {"monthly_income": {"type": "number"}, "fixed_costs": {"type": "number"},
             "emergency_fund": {"type": "number"}}),
        _fn("set_goal", "Create a savings goal.",
            {"name": {"type": "string"}, "target_amount": {"type": "number"},
             "target_date": {"type": "string", "description": "YYYY-MM-DD"},
             "saved_amount": {"type": "number"}}, ["name", "target_amount", "target_date"]),
        _fn("get_recurring", "Recurring payments and subscriptions, with status active/changed/unused.", {}),
        _fn("simulate", "What-if: apply spending/income changes and get baseline vs scenario savings "
            "and projected goal dates. Use for ANY what-if or 'can I afford' question.",
            {"adjustments": {"type": "array", "items": {
                "type": "object", "required": ["category"],
                "properties": {"category": _CAT,
                               "pct_change": {"type": "number", "description": "-30 = cut 30%"},
                               "abs_change": {"type": "number", "description": "rupees per month"}}}}},
            ["adjustments"]),
        _fn("get_nudges", "Current alerts: budget drift, price changes, unused subscriptions.",
            {"month": {"type": "string", "description": "YYYY-MM"}}),
    ]


def _summary(name: str, result: dict) -> str:
    try:
        if name == "simulate":
            b, s = result["baseline"], result["scenario"]
            dates = "; ".join(f"{g['name']} {g['baseline_date'][:7]}→{g['scenario_date'][:7]}"
                              for g in result.get("goal_dates", [])[:2])
            return f"savings {b['monthly_savings']:,.0f}→{s['monthly_savings']:,.0f}/mo; {dates}"[:80]
        if name == "get_recurring":
            items = result.get("items", [])
            flagged = [i["merchant_norm"] for i in items if i.get("status") != "active"]
            return f"{len(items)} recurring; flagged: {', '.join(flagged) or 'none'}"[:80]
        if name == "get_profile":
            return f"income {float(result.get('monthly_income', 0)):,.0f}/mo"
        if name == "query_transactions":
            return f"{result.get('count', 0)} txns"
        if name == "get_nudges":
            return f"{len(result.get('items', []))} nudges"
        if name == "set_goal":
            return f"goal '{result.get('name')}' saved"
    except (KeyError, TypeError, ValueError):
        pass
    return "ok"


# ----------------------------------------------------------------- loop
ESSENTIAL_LIST = ", ".join(sorted(ESSENTIAL))
SYSTEM_PROMPT = f"""You are FinPulse, a friendly personal-finance coach for one salaried user in India.
You explain, model scenarios with tools and educate. Today is {{today}}.

Hard rules:
1. Never recommend specific stocks, funds, ETFs, crypto or IPOs.
2. Never suggest cutting or reducing essential categories: {ESSENTIAL_LIST}. You MAY model them
   rising (e.g. rent goes up) with the simulate tool. If essentials exceed income (simulate warnings),
   say so plainly and point to raising income or talking to a human advisor.
3. Never calculate. Every rupee figure, percentage or date in your answer must appear verbatim in a
   tool result: no differences, totals or "about ₹X" of your own. simulate returns
   delta_monthly_savings / delta_monthly_spend for changes. Write rupees as ₹ with Indian digit
   grouping (₹1,00,000) and dates as month + year (Feb 2027).
4. The user's goals (e.g. Emergency fund, Goa trip) are already saved: simulate returns each goal's
   projected date, so never ask for goal targets. For any what-if, "can I afford" or "by <month>"
   question, call simulate. Merchants map to categories: Zomato/Swiggy = Food Delivery,
   restaurants = Dining, Netflix/Spotify/gym = Subscriptions, Amazon/Myntra = Shopping.
5. At most {MAX_STEPS} tool calls. Ask a clarifying question only if the request names no category.

Style: lead with the answer, under 120 words, then at most 3 short bullet actions. Only suggest cuts in
discretionary categories (Dining, Food Delivery, Shopping, Entertainment, Travel, Subscriptions)."""

CORRECTIVE = ("Your previous draft suggested cutting essential spending ({cats}). Rewrite it: do not "
              "suggest reducing any essential category; focus on discretionary categories or income.")


# Gemini 3 rejects function calls in history without a thought_signature (calls made by Groq have
# none). Keep Gemini's real one; otherwise send Google's documented placeholder. Groq ignores it.
_SIG_PLACEHOLDER = {"google": {"thought_signature": "skip_thought_signature_validator"}}


def _assistant_msg(msg) -> dict:
    out: dict = {"role": "assistant", "content": getattr(msg, "content", None) or ""}
    calls = getattr(msg, "tool_calls", None) or []
    if calls:
        out["tool_calls"] = []
        for c in calls:
            extra = (getattr(c, "model_extra", None) or {}).get("extra_content") or _SIG_PLACEHOLDER
            out["tool_calls"].append({"id": c.id, "type": "function", "extra_content": extra,
                                      "function": {"name": c.function.name,
                                                   "arguments": c.function.arguments or "{}"}})
    return out


def _clean_args(fn: Callable[..., dict], args: object) -> dict:
    """Drop keys the tool doesn't accept (models sometimes send {"": {}})."""
    if not isinstance(args, dict):
        return {}
    params = inspect.signature(fn).parameters
    if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values()):
        return {k: v for k, v in args.items() if k}
    return {k: v for k, v in args.items() if k in params}


def run(run_id: str, message: str, history: list[dict]) -> dict:
    """Execute guard -> tool loop -> answer, emitting trace events. Returns {answer, refused}."""
    g = intent_guard(message)
    if g["intent"] == "securities":
        trace.emit(run_id, "intent_guard", "refused", g["tier_used"], g["ms"], args={},
                   result_summary="blocked: securities pick request")
        trace.emit(run_id, "answer", "finished", None, 0, args={}, result_summary="refusal + education")
        return {"answer": SECURITIES_REFUSAL, "refused": True}
    trace.emit(run_id, "intent_guard", "ok", g["tier_used"], g["ms"], args={},
               result_summary=f"intent={g['intent']}")

    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT.format(today=date.today().isoformat())}]
    messages += [{"role": h["role"], "content": h["content"]} for h in history[-8:]
                 if h.get("role") in ("user", "assistant")]
    messages.append({"role": "user", "content": message})

    answer, tier, t_answer = "", None, time.perf_counter()
    sources: list[object] = [message, *[h.get("content", "") for h in history]]
    for _step in range(MAX_STEPS):
        t0 = time.perf_counter()
        r = llm.chat(messages, tools=tool_schemas(), tool_choice="auto", temperature=0.2, max_tokens=700)
        tier = r.tier
        calls = getattr(r.message, "tool_calls", None) or []
        if not calls:
            answer = r.text
            t_answer = t0
            break
        messages.append(_assistant_msg(r.message))
        for c in calls:
            name = c.function.name
            try:
                args = json.loads(c.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            ts = time.perf_counter()
            try:
                if name not in TOOLS:
                    raise ValueError(f"unknown tool {name}")
                args = _clean_args(TOOLS[name], args)
                result = TOOLS[name](**args)
                status, summary = "ok", _summary(name, result)
            except Exception as exc:  # noqa: BLE001 - surface tool errors to the model + trace
                result, status, summary = {"error": str(exc)[:200]}, "error", str(exc)[:80]
            sources.append(result)
            trace.emit(run_id, name, status, tier, int((time.perf_counter() - ts) * 1000),
                       args=args, result_summary=summary)
            messages.append({"role": "tool", "tool_call_id": c.id, "content": json.dumps(result, default=str)})
    else:
        t_answer = time.perf_counter()
        r = llm.chat(messages + [{"role": "user", "content": "Answer now using the tool results above."}],
                     temperature=0.2)
        answer, tier = r.text, r.tier

    bad = mentions_cutting_essentials(answer)
    if bad:
        r = llm.chat(messages + [{"role": "assistant", "content": answer},
                                 {"role": "system", "content": CORRECTIVE.format(cats=", ".join(bad))}],
                     temperature=0.2)
        answer = r.text if not mentions_cutting_essentials(r.text) else _strip_essential_cuts(r.text)
        trace.emit(run_id, "essentials_guard", "ok", r.tier, 0, args={"flagged": bad},
                   result_summary="rewrote reply: essentials cut removed")

    bad_nums = unsupported_amounts(answer, sources)
    if bad_nums:
        fix = ("These rupee amounts are not in any tool result: " + ", ".join(f"₹{b}" for b in bad_nums)
               + ". Rewrite the answer using only figures that appear in the tool results; do not add, "
               "subtract or estimate amounts.")
        try:
            r = llm.chat(messages + [{"role": "assistant", "content": answer},
                                     {"role": "user", "content": fix}], temperature=0, max_tokens=700)
            answer, tier = r.text, r.tier
        except llm.AllTiersFailed:
            pass
        if unsupported_amounts(answer, sources):
            answer = _strip_unsupported(answer, sources)
        trace.emit(run_id, "numbers_guard", "ok", tier, 0, args={"unsupported": bad_nums},
                   result_summary=f"removed LLM-made amounts: {', '.join(bad_nums)}"[:80])

    trace.emit(run_id, "answer", "finished", tier, int((time.perf_counter() - t_answer) * 1000),
               args={}, result_summary=answer[:80])
    return {"answer": answer, "refused": False}
