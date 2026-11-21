# FinPulse: manual steps (do these by hand)

Tick each box as you go. Times are IST, 21 Nov. Never paste keys into chat, commits or this file.

## 0. Right now (≈10 min): unblocks both of you
- [ ] **Claude Code mode:** press `Shift+Tab` until it shows *bypass permissions*.
- [ ] **Commit slice 0 on a branch** (the guard hook blocks pushes to `main`):
  ```bash
  git switch -c slice-0-bootstrap
  git add -A && git commit        # use the message Claude proposed
  git push -u origin slice-0-bootstrap
  ```
  Open a PR, merge it on GitHub, then both run `git switch main && git pull`.
- [ ] **Tell Vaishnavi:**
  - `cd backend && uv sync`
  - read the engine docstrings in `backend/app/engines/*.py`; `TODO(slice N)` marks what to build
  - stub routes return `app/examples.py` until she replaces them, so the UI can build against them now

## 1. API keys (≈10 min)
| Service | Where | Env var(s) |
|---|---|---|
| Groq | console.groq.com → API Keys | `GROQ_API_KEY` |
| Google AI Studio | aistudio.google.com → Get API key | `GEMINI_API_KEY` |
| Supabase | step 2 | `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` |
| Resend | step 3 | `RESEND_API_KEY`, `EMAIL_FROM`, `DEMO_EMAIL` |

- [ ] `cp .env.example .env` at the repo root and fill it in (the backend's `load_dotenv()` walks up and finds it).
- [ ] Share the filled `.env` with Vaishnavi privately (password manager / DM). **Never commit it.**

## 2. Supabase (≈5 min)
- [ ] supabase.com → New project `finpulse`. Region: *Need a specific region?* → **Singapore (ap-southeast-1)**
      (same as Render). Save the DB password. Data access: ✅ Enable Data API, ✅ **Grant API access to new
      tables automatically**, ✅ Enable RLS on new tables automatically. Postgres type: default.
- [ ] SQL Editor → paste all of `supabase/migrations/0001_init.sql` → Run. Check Table Editor shows 7 tables:
      uploads, transactions, category_rules, profile (1 row), goals, recurring, nudges.
- [ ] Project Settings → API: copy **Project URL** → `SUPABASE_URL` and the **service_role** key → `SUPABASE_SERVICE_KEY`.
      (Use service_role, not anon; it stays server-side only.)
- [ ] RLS is on with no policies: anon key gets nothing, the backend's service_role key bypasses RLS.
      Ignore "RLS enabled, no policies" advisor warnings.

## 3. Resend (≈5 min)
- [ ] resend.com → sign up **with the inbox you'll demo from** → API Keys → create → `RESEND_API_KEY`.
- [ ] `EMAIL_FROM=onboarding@resend.dev` (test sender, no domain setup).
- [ ] `DEMO_EMAIL` = **the same email you signed up to Resend with.** The test sender only delivers to the
      account owner's address; any other recipient fails.

## 4. Local check (≈3 min)
```bash
bash scripts/dev.sh                     # API :8787, UI :3000
bash scripts/smoke_demo.sh              # expect SMOKE PASS
```
- [ ] Open http://localhost:3000 on desktop, then DevTools → device toolbar (iPhone) → bottom tab bar shows.
- [ ] Theme toggle (top right) switches light/dark.
- [ ] Optional mock for frontend work: `npx @stoplight/prism-cli mock openapi.yaml -p 4010`, then run with
      `NEXT_PUBLIC_API_URL=http://localhost:4010`.

## 5. Deploy: do a first deploy EARLY (by ~18:30), redeploy at 22:15
### API on Render
- [ ] render.com → New → **Blueprint** → pick the repo → it reads `render.yaml` (service `finpulse-api`, root `backend`,
      region Singapore).
- [ ] Fill the `sync: false` env vars: GROQ_API_KEY, GEMINI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY,
      RESEND_API_KEY, DEMO_EMAIL, CORS_ORIGINS (set after Vercel; see below).
- [ ] Wait for deploy → open `https://<finpulse-api>.onrender.com/health` → `{"success":true,...}`.
- [ ] Free tier sleeps after ~15 min idle (cold start ~50 s). **Open /health 2 min before the demo.**

### Frontend on Vercel
- [ ] vercel.com → Add New Project → import repo → **Root Directory: `frontend`** (framework auto: Next.js).
- [ ] Env var: `NEXT_PUBLIC_API_URL=https://<finpulse-api>.onrender.com` (no trailing slash) → Deploy.
- [ ] Back on Render: `CORS_ORIGINS=https://<your-app>.vercel.app` (comma-separate if you also want localhost) → redeploy.
- [ ] Smoke the cloud API: `API=https://<finpulse-api>.onrender.com bash scripts/smoke_demo.sh`.

## 6. PWA install check (needs the HTTPS Vercel URL)
- [ ] Android Chrome: menu → *Install app* → opens standalone with the teal icon.
- [ ] iPhone Safari: Share → *Add to Home Screen*.
- [ ] Desktop Chrome: install icon in the address bar.
- [ ] After every redeploy, if the UI looks stale: DevTools → Application → Service Workers → *Update*
      (or bump `CACHE` in `frontend/public/sw.js`).

## 7. Demo data
- [ ] "Load sample case" posts `backend/samples/*` (already generated and committed). To regenerate:
      `cd backend && uv run python ../scripts/make_samples.py`.
- [ ] Story to narrate: Oct SMS+CSV → correct the 5 cryptic merchants (RAZ*PAYU8823 → Groceries, POS 4471 →
      Dining, ksh.store → Medical, PAYTM*QR8812 → Fuel, RMKCLASSES → Education) → load Nov → auto-rate jumps;
      Netflix 499→649 alert; cult.fit unused; Food Delivery drift nudge; Nov PDF reconciles.

## 8. Before submitting (by 23:30)
- [ ] README: fill Live demo / API / Video links; flip the Features-vs-PS4 Status column.
- [ ] `AI_DISCLOSURE.md`: one Contribution-log row per slice (time, area, ours vs Claude Code, reviewer).
- [ ] Record the demo video (≤ the event limit). Show: ingest → correction → Nov auto-rate → recurring →
      what-if → coach trace + **securities refusal** + **essentials not cut** → email → install PWA on a phone.
- [ ] Final `bash scripts/smoke_demo.sh` against the cloud API and paste the output in the submission if asked.
- [ ] Submit the form; check the repo is public (or judges have access).
