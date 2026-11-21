"""FastAPI app. Every response uses the envelope {success, data, error}. Contract: openapi.yaml.

Slice 0: every route below is a STUB returning its openapi example (app/examples.py).
Owner of routes + engines: Vaishnavi. Coach (app/agents/coach.py): Suyash.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from typing import Literal

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

load_dotenv()

from app.examples import EXAMPLES  # imported after load_dotenv()
from app.services import trace

app = FastAPI(title="FinPulse API")
app.add_middleware(CORSMiddleware, allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
                   allow_methods=["*"], allow_headers=["*"])


def ok(data=None):
    return {"success": True, "data": data, "error": None}


def fail(msg: str):
    return {"success": False, "data": None, "error": msg}


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


@app.post("/ingest")
async def ingest(request: Request):
    """multipart `file` (pdf/csv/txt) OR JSON {kind:"sms", text}. TODO(slice 1): engines.parse ->
    normalize -> categorize -> insert uploads + transactions."""
    if request.headers.get("content-type", "").startswith("multipart/"):
        async with request.form() as form:  # closes the spooled upload
            if "file" not in form:
                return fail("missing file")
    else:
        body = await request.json()
        if body.get("kind") != "sms" or not body.get("text"):
            return fail("expected {kind:'sms', text}")
    return ok(EXAMPLES["ingest"])


@app.get("/transactions")
def list_transactions(month: str | None = None, category: str | None = None,
                      needs_review: bool | None = None):
    """TODO(slice 2)"""
    return ok(EXAMPLES["transactions"])


@app.post("/transactions/{tx_id}/correct")
def correct_transaction(tx_id: str, body: CorrectIn):
    from app.engines.categorize import learn_rule

    try:
        rule, similar_ids = learn_rule(tx_id, body.category)
        return ok({"rule": rule, "similar_ids": similar_ids})
    except ValueError as exc:
        return fail(str(exc))
    except Exception:
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
        return fail("Could not apply category rule")


@app.get("/profile")
def get_profile():
    """TODO(slice 5)"""
    return ok(EXAMPLES["profile"])


@app.put("/profile")
def put_profile(body: ProfileIn):
    """TODO(slice 5)"""
    return ok(EXAMPLES["profile_put"])


@app.get("/goals")
def get_goals():
    """TODO(slice 5)"""
    return ok(EXAMPLES["goals"])


@app.post("/goals")
def post_goal(body: GoalIn):
    """TODO(slice 5)"""
    return ok(EXAMPLES["goal_post"])


@app.get("/recurring")
def get_recurring():
    """TODO(slice 4): engines.recurring.detect_recurring"""
    return ok(EXAMPLES["recurring"])


@app.post("/simulate")
def post_simulate(body: SimulateIn):
    """TODO(slice 6): engines.simulate.simulate"""
    return ok(EXAMPLES["simulate"])


@app.get("/nudges")
def get_nudges():
    """TODO(slice 7): engines.nudges.compute_nudges"""
    return ok(EXAMPLES["nudges"])


@app.get("/report/{month}")
def get_report(month: str):
    """TODO(slice 8): engines.report.monthly_report"""
    return ok(EXAMPLES["report"])


@app.post("/email/send")
def email_send(body: EmailIn):
    """TODO(slice 9): engines.emailer.send"""
    return ok(EXAMPLES["email"])


@app.get("/stats/auto-rate")
def auto_rate():
    """TODO(slice 2)"""
    return ok(EXAMPLES["auto_rate"])


# ---------- coach (SSE trace pattern kept from the template) ----------
_answers: dict[str, dict] = {}


def _stub_coach(run_id: str, message: str) -> None:
    """TODO(slice 10): replace with app.agents.coach.run(run_id, message, history)."""
    for ev in EXAMPLES["coach_events"]:
        trace.emit(run_id, **ev)
    _answers[run_id] = {"answer": EXAMPLES["coach_answer"], "refused": False}
    trace.emit(run_id, "answer", "finished")
    trace.close(run_id)


@app.post("/coach")
def coach(body: CoachIn, bg: BackgroundTasks):
    run_id = uuid.uuid4().hex[:12]
    trace.open_run(run_id)
    bg.add_task(_stub_coach, run_id, body.message)
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
