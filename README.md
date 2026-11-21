# <Project name>

> <one-line pitch>

```mermaid
flowchart LR
  UI[Next.js 14 UI<br/>trace panel] -->|REST + SSE| API[FastAPI]
  API --> G[LangGraph agent]
  G --> R{llm.py router}
  R -->|1| Groq[Groq gpt-oss-120b]
  R -->|2 on 429/timeout| Gem[Gemini Flash-Lite]
  R -->|3 offline / Privacy Mode| V[vLLM local GPU]
  API --> DB[(Supabase Postgres + pgvector)]
```

## Quickstart
```bash
cp .env.example .env              # fill keys
cd backend && uv sync && cd ..
cd frontend && npm ci && cd ..
bash scripts/dev.sh               # API :8787, UI :3000
bash scripts/smoke_demo.sh
```

## Env vars
`GROQ_API_KEY`, `GEMINI_API_KEY`, `VLLM_BASE_URL`, `VLLM_MODEL`, `PRIVACY_MODE`,
`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `NEXT_PUBLIC_API_URL`, `CORS_ORIGINS`

## Rubric alignment
| Criterion | Where to see it |
|---|---|
| <criterion> | <screen / demo second> |

## Works offline
Toggle **Privacy Mode**: every model call goes to a local vLLM server on the presenter's GPU.

## AI disclosure
See [AI_DISCLOSURE.md](AI_DISCLOSURE.md).
