---
name: newslice
description: Build one vertical slice (DB to API to agent to UI) from the frozen scope in CLAUDE.md
argument-hint: [slice-number]
disable-model-invocation: true
---
Enter Plan Mode. Read CLAUDE.md, openapi.yaml and agents/graph.md. Build slice $ARGUMENTS only.
1. Migration or seed rows for this slice (backend/app/seed.py or Supabase migration).
2. FastAPI route matching openapi.yaml; all model calls through backend/app/services/llm.py.
3. Agent logic: plain function call unless agents/graph.md names a LangGraph node. Emit a trace event per step.
4. UI component wired to the real route, with a "Load sample case" path.
5. Run `bash scripts/smoke_demo.sh` and paste the raw output. Also `cd backend && uv run pytest -q`.
Use context7 for any library API you are unsure of.
Stop. List files changed and propose one commit message. Do not start the next slice.
