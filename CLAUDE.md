# CLAUDE.md — <PROJECT NAME> (fill at Gate 3; keep under 150 lines)

## Pitch
<one line: who, pain, our twist>

## Commands
```
bash scripts/dev.sh                 # backend :8787 + frontend :3000
cd backend && uv run pytest -q && uv run ruff check .
cd frontend && npm run build && npm run lint
bash scripts/smoke_demo.sh          # MUST pass before every commit; paste raw output
bash scripts/vllm-up.sh coding|vision|omni|stop   # Tier 3 local model (one at a time)
```

## Architecture map
- `backend/app/main.py` — FastAPI routes; envelope `{success, data, error}` on every response
- `backend/app/services/llm.py` — **the only place model calls happen** (3-tier router)
- `backend/app/services/trace.py` — per-run events -> SSE `GET /runs/{id}/events`
- `backend/app/agents/graph.py` — LangGraph (spec: `agents/graph.md`)
- `backend/app/agents/crew.py` — optional CrewAI crew (`uv sync --extra crew`)
- `backend/app/seed.py` — sample cases for "Load sample case"
- `frontend/src/app/page.tsx` — main screen; `frontend/src/components/TracePanel.tsx`
- `openapi.yaml` — frozen API contract (Prism mock: `npx @stoplight/prism-cli mock openapi.yaml -p 4010`)

## Pinned models (do not change without asking)
| Tier | Model | Notes |
|---|---|---|
| 1 Groq | `openai/gpt-oss-120b` (fast: `openai/gpt-oss-20b`) | 3 s timeout |
| 1 Groq vision | `qwen/qwen3.8-27b` | Preview — image input only |
| 2 Gemini | `gemini-3.5-flash-lite` | fallback, 500 req/day free |
| 2 Gemini hero | `gemini-3.8-flash` | ONE wow call only, 20 req/day free |
| 3 local | `nvidia/Qwen3-14B-NVFP4` @ `http://localhost:8001/v1` | vision: Qwen2.5-VL-7B-NVFP4; omni: Phi-4-mm-NVFP4 |
| Embeddings | `gemini-embedding-2` @768 dims, or local `BAAI/bge-m3` | |
| STT | Groq `whisper-large-v3` | |

Router rule: Groq -> (429/timeout) Gemini Flash-Lite -> (no network / Privacy Mode) local vLLM.
VRAM rule: one vLLM model at a time; swap between slices, never during the demo.

## Frozen scope
MUST: <each tagged to a rubric line>
WON'T: <banned until MUST is demoable>

## Do-not-touch
`openapi.yaml` (contract), pinned model IDs, `.env*`, `main` branch pushes.

## Rules
- Vertical slices only (storage -> API/agent -> UI). One slice per session; `/clear` after commit.
- Use context7 for any library API you are not certain of.
- Fix fails twice -> stop, `/rewind`, re-prompt with `/triage`.
