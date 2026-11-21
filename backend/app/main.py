"""FastAPI app. Every response uses the envelope {success, data, error}."""

from __future__ import annotations

import asyncio
import json
import os
import uuid

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

load_dotenv()

from app.agents import graph  # imported after load_dotenv()
from app.seed import SAMPLES
from app.services import trace

app = FastAPI(title="hackathon-starter")
app.add_middleware(CORSMiddleware, allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
                   allow_methods=["*"], allow_headers=["*"])


def ok(data=None):
    return {"success": True, "data": data, "error": None}


def fail(msg: str):
    return {"success": False, "data": None, "error": msg}


class RunIn(BaseModel):
    input: str
    privacy_mode: bool = False


class ResumeIn(BaseModel):
    approve: bool


_results: dict[str, dict] = {}


@app.get("/health")
def health():
    return ok({"status": "up"})


@app.get("/samples")
def samples():
    return ok(SAMPLES)


def _run(run_id: str, fn, *args):
    try:
        out = fn(*args)
        _results[run_id] = out
        if "__interrupt__" in out:
            trace.emit(run_id, "approval", "waiting")
            trace.emit(run_id, "graph", "interrupted")
        else:
            trace.emit(run_id, "graph", "finished", result=out.get("result"))
            trace.close(run_id)
    except Exception as exc:  # noqa: BLE001 - surface any graph failure in the trace panel
        trace.emit(run_id, "graph", "error", error=str(exc)[:300])
        trace.close(run_id)


@app.post("/runs")
def create_run(body: RunIn, bg: BackgroundTasks):
    run_id = uuid.uuid4().hex[:12]
    trace.open_run(run_id)
    bg.add_task(_run, run_id, graph.start, run_id, body.input, body.privacy_mode)
    return ok({"run_id": run_id})


@app.post("/runs/{run_id}/resume")
def resume_run(run_id: str, body: ResumeIn, bg: BackgroundTasks):
    if run_id not in _results:
        return fail("unknown or still-running run")
    bg.add_task(_run, run_id, graph.resume, run_id, body.approve)
    return ok({"run_id": run_id})


@app.get("/runs/{run_id}")
def get_run(run_id: str):
    out = _results.get(run_id)
    return ok({"events": trace.events(run_id),
               "state": {k: v for k, v in (out or {}).items() if k != "__interrupt__"}})


@app.get("/runs/{run_id}/events")
async def run_events(run_id: str):
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
