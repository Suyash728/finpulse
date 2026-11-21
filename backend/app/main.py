"""FastAPI app. Every response uses the envelope {success, data, error}. Contract: openapi.yaml.

Slice 0: every route below is a STUB returning its openapi example (app/examples.py).
Owner of routes + engines: Vaishnavi. Coach (app/agents/coach.py): Suyash.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from typing import Literal

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

load_dotenv()

from app.services import trace

log = logging.getLogger("finpulse")

app = FastAPI(title="FinPulse API")
app.add_middleware(CORSMiddleware, allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
                   allow_methods=["*"], allow_headers=["*"])


def ok(data=None):
    return {"success": True, "data": data, "error": None}


def fail(msg: str):
    return {"success": False, "data": None, "error": msg}


def _safe(fn):
    """Run an engine call; any failure becomes the envelope error (and is logged)."""
    try:
        return ok(fn())
    except ValueError as exc:
        return fail(str(exc))
    except Exception as exc:
        log.exception("route failed")
        return fail(f"{type(exc).__name__}: {str(exc)[:200]}")


# ---------- request models (mirror openapi.yaml) ----------
class CorrectIn(BaseModel):
    category: str


class RuleApplyIn(BaseModel):
    rule_id: str
    transaction_ids: list[str]


class ProfileIn(BaseModel):
    monthly_income: float | None = None
    fixed_costs: float | None = None
    emergency_fund: float | None = None
    email: str | None = None
    budgets: dict[str, float] | None = None


class GoalIn(BaseModel):
    name: str
    target_amount: float
    saved_amount: float = 0
    target_date: str


class Adjustment(BaseModel):
    category: str
    pct_change: float | None = None
    abs_change: float | None = None


class SimulateIn(BaseModel):
    adjustments: list[Adjustment]


class EmailIn(BaseModel):
    kind: Literal["nudges", "report"]
    month: str | None = None


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class CoachIn(BaseModel):
    message: str
    history: list[ChatTurn] = []


# ---------- routes ----------
@app.get("/health")
def health():
    return ok({"status": "up"})


@app.post("/admin/reset-demo")
def reset_demo():
    """Demo helper (not in the public contract): wipe data, re-seed profile + goals."""
    from app.engines import ledger

    return _safe(lambda: (ledger.reset_demo(), {"reset": True})[1])


@app.post("/ingest")
async def ingest(request: Request):
    """multipart `file` (pdf/csv/txt) OR JSON {kind:"sms", text}. TODO(slice 1): engines.parse ->
    normalize -> categorize -> insert uploads + transactions."""
    from app.engines import ledger

    if request.headers.get("content-type", "").startswith("multipart/"):
        async with request.form() as form:  # closes the spooled upload
            f = form.get("file")
            if f is None or isinstance(f, str):
                return fail("missing file")
            data, name = await f.read(), f.filename
        return _safe(lambda: ledger.ingest("file", name, data=data))
    body = await request.json()
    if body.get("kind") != "sms" or not body.get("text"):
        return fail("expected {kind:'sms', text}")
    return _safe(lambda: ledger.ingest("sms", "Pasted SMS", text=body["text"]))


@app.get("/transactions")
def list_transactions(month: str | None = None, category: str | None = None,
                      needs_review: bool | None = None):
    from app.engines import ledger

    return _safe(lambda: ledger.list_transactions(month, category, needs_review))


@app.post("/transactions/{tx_id}/correct")
def correct_transaction(tx_id: str, body: CorrectIn):
    from app.engines.categorize import learn_rule

    try:
        rule, similar_ids = learn_rule(tx_id, body.category)
        return ok({"rule": rule, "similar_ids": similar_ids})
    except ValueError as exc:
        return fail(str(exc))
    except Exception:
        log.exception("correct failed")
        return fail("Could not save transaction correction")


@app.post("/rules/apply")
def rules_apply(body: RuleApplyIn):
    from app.engines.categorize import apply_rule

    try:
        updated = apply_rule(body.rule_id, body.transaction_ids)
        return ok({"updated": updated})
    except ValueError as exc:
        return fail(str(exc))
    except Exception:
        log.exception("apply failed")
        return fail("Could not apply category rule")


@app.get("/profile")
def get_profile():
    from app.engines import ledger

    return _safe(ledger.get_profile)


@app.put("/profile")
def put_profile(body: ProfileIn):
    from app.engines import ledger

    return _safe(lambda: ledger.put_profile(body.model_dump()))


@app.get("/goals")
def get_goals():
    from app.engines import ledger

    return _safe(ledger.get_goals)


@app.post("/goals")
def post_goal(body: GoalIn):
    from app.engines import ledger

    return _safe(lambda: ledger.add_goal(body.model_dump()))


@app.get("/recurring")
def get_recurring():
    from app.engines import ledger
    from app.engines.recurring import detect_recurring

    return _safe(lambda: {"items": detect_recurring(ledger.all_transactions())})


@app.post("/simulate")
def post_simulate(body: SimulateIn):
    from app.engines.simulate import simulate

    return _safe(lambda: simulate([a.model_dump() for a in body.adjustments]))


@app.get("/nudges")
def get_nudges():
    from app.engines.nudges import compute_nudges

    return _safe(lambda: {"items": compute_nudges()})


@app.get("/report/{month}")
def get_report(month: str):
    from app.engines.report import monthly_report

    return _safe(lambda: monthly_report(month))


@app.post("/email/send")
def email_send(body: EmailIn):
    from app.engines.emailer import send

    return _safe(lambda: send(body.kind, body.month))


@app.get("/stats/auto-rate")
def auto_rate():
    from app.engines import ledger

    return _safe(ledger.auto_rate_series)


# ---------- coach (SSE trace pattern kept from the template) ----------
_answers: dict[str, dict] = {}


def _run_coach(run_id: str, message: str, history: list[dict]) -> None:
    """Coach agent (owner: Suyash). Spec: agents/graph.md."""
    from app.agents import coach as coach_agent

    try:
        _answers[run_id] = coach_agent.run(run_id, message, history)
    except Exception as exc:  # noqa: BLE001 - surface any agent failure in the trace panel
        trace.emit(run_id, "answer", "error", None, 0, args={}, result_summary=str(exc)[:80])
        _answers[run_id] = {"answer": "Sorry, the coach couldn't answer right now. Please try again.",
                            "refused": False}
    finally:
        trace.close(run_id)


@app.post("/coach")
def coach(body: CoachIn, bg: BackgroundTasks):
    run_id = uuid.uuid4().hex[:12]
    trace.open_run(run_id)
    bg.add_task(_run_coach, run_id, body.message, [h.model_dump() for h in body.history])
    return ok({"run_id": run_id})


@app.get("/coach/{run_id}")
def coach_result(run_id: str):
    res = _answers.get(run_id, {})
    return ok({"events": trace.events(run_id), "answer": res.get("answer"),
               "refused": res.get("refused", False)})


@app.get("/coach/{run_id}/events")
async def coach_events(run_id: str):
    async def stream():
        while True:
            ev = await asyncio.to_thread(trace.next_event, run_id)
            if ev is None:
                yield ": keepalive\n\n"
            elif trace.is_done(ev):
                yield "event: end\ndata: {}\n\n"
                return
            else:
                yield f"data: {json.dumps(ev)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")
