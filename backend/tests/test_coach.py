"""Coach agent: guardrails + function-calling loop with a fake LLM (no network)."""

import json
from types import SimpleNamespace

import pytest

from app.agents import coach
from app.services import llm, trace


@pytest.fixture(autouse=True)
def _no_db(monkeypatch):
    """Coach tests never touch Supabase; tools fall back to seed/example data."""
    def boom():
        raise RuntimeError("no db in tests")

    monkeypatch.setattr(coach, "_db", boom)


PICKS = [
    "Which stock should I buy?",
    "Should I buy Infosys shares?",
    "Is bitcoin a good buy right now?",
    "Recommend a mutual fund for me",
    "Best crypto to invest in 2027?",
    "Should I sell my TCS shares?",
    "Which ETF gives the best returns?",
    "Should I put my money in Nifty 50 index funds?",
    "Is the Swiggy IPO worth buying?",
    "Should I buy HDFC or ICICI?",
]
NORMAL = [
    "Can I afford a Goa trip in March?",
    "What if my rent goes up by 3000?",
    "How big should my emergency fund be?",
    "Which subscriptions should I review?",
    "Should I buy a new phone this month?",
    "What is an index fund?",
    "How do I spend less on Swiggy?",
    "Help me plan for my emergency fund by June",
    "Why did my Netflix bill go up?",
    "Am I on track for my goals?",
]


@pytest.mark.parametrize("q", PICKS)
def test_security_picks_flagged(q):
    assert coach.is_securities_request(q) is True


@pytest.mark.parametrize("q", NORMAL)
def test_normal_questions_not_flagged(q):
    assert coach.is_securities_request(q) is False


def test_company_name_is_ambiguous_and_goes_to_llm():
    assert coach.is_securities_request("Should I buy Reliance?") is None


@pytest.mark.parametrize("text,expected", [
    ("You could cut your rent by moving somewhere cheaper.", ["Rent"]),
    ("Try to reduce Groceries spending a little.", ["Groceries"]),
    ("Lower your EMI by prepaying the loan.", ["EMI"]),
    ("Don't cut rent or groceries; they are essentials.", []),
    ("Cut Food Delivery by 30% to free up money.", []),
    ("Rent rising by 3,000 delays your goal by two months.", []),
])
def test_essentials_detector(text, expected):
    assert coach.mentions_cutting_essentials(text) == expected


def _msg(content="", calls=None):
    return SimpleNamespace(content=content, tool_calls=calls)


def _call(cid, name, args):
    return SimpleNamespace(id=cid, function=SimpleNamespace(name=name, arguments=json.dumps(args)))


def _fake_chat(script):
    calls = []

    def chat(messages, **kw):
        calls.append({"messages": messages, **kw})
        m = script[len(calls) - 1]
        return llm.LLMResult(m.content or "", "groq", "x", 5, m)

    return chat, calls


def test_refusal_skips_agent(monkeypatch):
    chat, calls = _fake_chat([])
    monkeypatch.setattr(llm, "chat", chat)
    trace.open_run("r1")
    out = coach.run("r1", "Which stock should I buy?", [])
    assert out["refused"] and "SEBI" in out["answer"] and calls == []
    assert trace.events("r1")[0]["status"] == "refused"


def test_loop_calls_simulate_and_answers(monkeypatch):
    chat, calls = _fake_chat([
        _msg(calls=[_call("c1", "simulate", {"adjustments": [{"category": "Food Delivery", "pct_change": -30}]})]),
        _msg("Yes: you'd save ₹22,700/mo and reach the emergency fund by Mar 2027."),
    ])
    monkeypatch.setattr(llm, "chat", chat)
    trace.open_run("r2")
    out = coach.run("r2", "Can I hit my emergency fund by June if I cut Zomato 30%?", [])
    nodes = [e["node"] for e in trace.events("r2")]
    assert nodes == ["intent_guard", "simulate", "answer"]
    sim = trace.events("r2")[1]
    assert sim["status"] == "ok" and sim["args"]["adjustments"][0]["pct_change"] == -30
    assert "savings" in sim["result_summary"]
    assert calls[1]["messages"][-1]["role"] == "tool" and not out["refused"]


def test_essentials_answer_is_rewritten(monkeypatch):
    chat, _ = _fake_chat([
        _msg("You should cut your rent and dining."),
        _msg("Trim Dining by 20% and keep rent as is."),
    ])
    monkeypatch.setattr(llm, "chat", chat)
    trace.open_run("r3")
    out = coach.run("r3", "Should I spend less on rent?", [])
    assert "essentials_guard" in [e["node"] for e in trace.events("r3")]
    assert coach.mentions_cutting_essentials(out["answer"]) == []


def test_bad_tool_args_are_dropped():
    assert coach._clean_args(coach.tool_get_recurring, {"": {}}) == {}
    assert coach._clean_args(coach.tool_simulate, {"adjustments": [], "x": 1}) == {"adjustments": []}


def test_tool_calls_carry_gemini_signature():
    m = coach._assistant_msg(_msg(calls=[_call("c1", "get_profile", {})]))
    assert m["tool_calls"][0]["extra_content"]["google"]["thought_signature"]


def test_simulate_tool_adds_python_deltas():
    out = coach.tool_simulate([{"category": "Rent", "abs_change": 3000}])
    assert out["delta_monthly_savings"] == round(
        out["scenario"]["monthly_savings"] - out["baseline"]["monthly_savings"], 2)


def test_numbers_guard_flags_llm_arithmetic():
    tool = {"items": [{"amount": 649, "prev_amount": 499}, {"amount": 1499}]}
    assert coach.unsupported_amounts("Netflix went ₹499 → ₹649; gym ₹1,499.", [tool]) == []
    assert coach.unsupported_amounts("Together they cost ₹2,148 a month.", [tool]) == ["2,148"]
    assert coach.unsupported_amounts("Rent up ₹3,000", ["What if rent goes up ₹3,000?"]) == []


def test_simulate_tool_blocks_essential_cuts():
    out = coach.tool_simulate([{"category": "Rent", "abs_change": -2000}])
    assert "Rent" in out["not_modelled"]
    assert "not_modelled" not in coach.tool_simulate([{"category": "Rent", "abs_change": 3000}])


def test_answer_with_made_up_amount_is_rewritten(monkeypatch):
    chat, _ = _fake_chat([
        _msg(calls=[_call("c1", "get_recurring", {})]),
        _msg("Netflix and the gym together cost ₹2,148 a month."),
        _msg("Netflix rose from ₹499 to ₹649 and cult.fit costs ₹1,499."),
    ])
    monkeypatch.setattr(llm, "chat", chat)
    trace.open_run("r4")
    out = coach.run("r4", "Which subscriptions should I review?", [])
    assert "2,148" not in out["answer"] and "numbers_guard" in [e["node"] for e in trace.events("r4")]
