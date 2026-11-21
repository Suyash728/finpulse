# FinPulse — Build Playbook (Slices 1–4, Deploy, Submit)

Put this file in the repo as `docs/PLAYBOOK.md` and commit it, so both Claude Code sessions can read it.
Claude Code already has the project context from `CLAUDE.md`, `openapi.yaml` and `agents/graph.md`; each prompt below just points at them.

---

## 0. Revised clock (we started slices at 17:45, not 17:00)

| Time (IST) | Phase | Vaishnavi (backend) | Suyash (frontend + agent) |
|---|---|---|---|
| 17:50–19:15 | **Slice 1: Ingest + learn** | parsers, normalize, categorize, `/ingest`, `/transactions`, `/correct`, `/rules/apply` | Transactions page, upload/paste sheet, badges, inline edit, apply-to-similar dialog |
| 19:15–19:30 | **Early deploy** | Render service + env vars | Vercel project + env vars, phone smoke test |
| 19:30–20:30 | **Slice 2: Living model** | recurring, simulate, profile/goals routes | Home dashboard, Plan page, what-if sliders + chart |
| **20:30** | **MUST-core done + scope freeze** | | |
| 20:30–21:30 | **Slice 3: Coach** | guardrail pre-check, tool endpoints wired for the agent | coach loop, chat UI, trace panel |
| 21:30–22:15 | **Slice 4: Nudges, report, email, PWA** | nudges, report, emailer | nudge cards, report page, Email button, PWA install check |
| 22:15–22:35 | **Final deploy + smoke test** | redeploy Render | redeploy Vercel, test on phone |
| 22:35–23:30 | **Submit** | README + AI_DISCLOSURE | demo video + submission |

**Cut list, in this order, if a slice runs over by more than 15 minutes:**
1. PDF ingest. Keep SMS + CSV.
2. Email. Keep in-app nudges.
3. Service worker. Keep the manifest only.
4. Report narrative. Keep the stats only.

## 1. How we work in parallel

- **Branches:** Vaishnavi works on `be/slice-N`, Suyash on `fe/slice-N`. At each slice end: `gh pr create --fill && gh pr merge --squash --delete-branch`, then both run `git pull`.
- **Files:** Vaishnavi owns `backend/app/engines/*`, `backend/app/main.py` and `supabase/`. Suyash owns `frontend/*` and `backend/app/agents/coach.py`. Don't edit each other's files; post in chat instead.
- **Contract:** `openapi.yaml` is the source of truth. If a response shape must change, change `openapi.yaml` first in its own small PR and tell the other person.
- **Until real routes land:** Suyash builds against the stubs, or against `npx @stoplight/prism-cli mock openapi.yaml -p 4010`.
- **AI disclosure:** after every slice, add one row to the contribution log in `AI_DISCLOSURE.md`.
- **Each slice:** run `/clear` before starting it.

---

## 2. Slice 1 — Ingest + learn (the core) · 17:50–19:15

**Done when:** you paste the October SMS, fix one cryptic merchant, and the dialog offers "Apply to N similar". After that, ingesting the November file shows that merchant with a **Learned** badge, and `auto_rate` is higher.

### Vaishnavi — Claude Code prompt

```
Enter Plan Mode. Read CLAUDE.md, openapi.yaml, docs/PLAYBOOK.md (slice 1). Build ONLY the backend of slice 1.
All model calls go through backend/app/services/llm.py. Use context7 for pdfplumber, pandas, supabase-py.

Files in scope: backend/app/engines/{normalize.py, parse.py, categorize.py}, backend/app/db.py,
backend/app/main.py (routes below), backend/tests/test_slice1.py. Nothing in frontend/.

1. normalize.py: merchant_norm(raw) -> str. Lowercase; strip prefixes (upi/, pos, neft, imps, ach, nach,
   ecs, vpa, to, by, ref, txn); cut at '*', '/', '@' and keep the most merchant-like token; drop digit runs
   of 3+, city words (mumbai, bangalore, blr, delhi, pune, navi), extra spaces. Alias map for common
   brands (swiggy, zomato, netflix, amazon, flipkart, uber, ola, cult.fit -> cultfit, jio, airtel, bescom,
   mahadiscom). Unit-test 12 samples taken from backend/samples.
2. parse.py: three parsers returning list[dict(date, raw_text, merchant, amount, type)]:
   - parse_sms(text): regex for HDFC/SBI/ICICI/UPI debit+credit styles (Rs/INR/₹, "debited", "credited",
     "spent", "sent to", "received from", "VPA x@y"). Lines the regex can't read -> one batched LLM call
     (fast model openai/gpt-oss-20b, response_format json) -> validate every field; drop rows missing amount.
   - parse_csv(bytes): pandas; detect columns by fuzzy header (date/txn date/value date;
     narration/description/particulars; debit/withdrawal/dr; credit/deposit/cr; or amount + Dr/Cr column);
     dayfirst dates; strip commas from amounts.
   - parse_pdf(bytes): pdfplumber extract_tables, same column detection; if no tables, text -> LLM JSON.
     Reconcile: if opening and closing balance are found, check opening - debits + credits == closing
     (±1 rupee); return reconciled true/false/null.
3. categorize.py: categorize(rows) applies, in order:
   a) category_rules exact match on merchant_norm -> cat_source='rule', confidence=1
   b) rule pattern contained in merchant_norm -> 'rule', 0.95
   c) one batched LLM call for the rest (fast model, JSON list), prompt includes the fixed category list
      from CLAUDE.md and the user's last 20 corrections as examples -> 'ai', model-reported confidence
      clamped 0–1; any category not in the list -> 'Other', confidence 0.
   Credits whose text contains salary/sal/payroll -> Income, 'rule'.
4. Routes (match openapi.yaml exactly, envelope {success,data,error}):
   - POST /ingest: multipart file (csv/pdf) OR JSON {kind:"sms", text}. Create uploads row, parse,
     normalize, categorize, insert transactions with upload_id. provisional auto_rate = share of rows that
     are 'rule' or ('ai' and confidence >= 0.7). Return {upload_id, rows, auto_rate, reconciled}.
   - GET /transactions?month=YYYY-MM&category=&needs_review=true (needs_review = 'ai' and confidence < 0.7)
   - POST /transactions/{id}/correct {category}: set category, cat_source='user', confidence=1; upsert
     category_rules(merchant_pattern=merchant_norm, category, source='user', hits+1); find similar_ids =
     same merchant_norm, cat_source != 'user', category != new one. Recompute the upload's auto_rate =
     1 - (user-corrected rows in that upload / total rows). Return {rule, similar_ids, auto_rate}.
   - POST /rules/apply {rule_id, transaction_ids}: set category, cat_source='rule', confidence=1.
   - GET /stats/auto-rate: [{upload_id, kind, month, auto_rate}] ordered by created_at.
5. tests/test_slice1.py: normalize samples, a CSV parse, the rule-before-AI order (mock llm.chat),
   and a correct -> rule -> re-ingest -> 'rule' round trip (mock db or use a test schema).

Verify and paste raw output:
cd backend && uv run pytest -q && uv run ruff check .
curl -s -X POST localhost:8787/ingest -H 'content-type: application/json' \
  -d "{\"kind\":\"sms\",\"text\":$(jq -Rs . < samples/sms_oct.txt)}" | jq '.data.auto_rate, (.data.rows|length)'
STOP. List files changed, propose a commit message, add a row to AI_DISCLOSURE.md.
```

### Suyash — Claude Code prompt

```
Enter Plan Mode. Read CLAUDE.md, openapi.yaml, docs/PLAYBOOK.md (slice 1). Build ONLY the frontend of slice 1.
Use context7 for shadcn/ui and Next.js 14 App Router. Fetch through frontend/src/lib/api.ts.
Files in scope: frontend/src/app/transactions/*, frontend/src/components/{IngestSheet, TxnList,
CategoryBadge, ApplySimilarDialog, AutoRateChip}.tsx. Nothing in backend/.

Design rules (whole app): minimal and information-dense. Neutral greys + ONE accent colour; numbers in
tabular-nums; ₹ with Indian digit grouping (Intl.NumberFormat('en-IN')); no decorative illustrations;
44px minimum tap targets; works at 360px width first, then scales to desktop.

1. IngestSheet (shadcn Sheet, opened from a "+ Add" button on Transactions and Home):
   tabs "Paste SMS" (textarea) | "Upload file" (csv/pdf). Plus "Load sample" buttons for Oct SMS,
   Oct CSV, Nov SMS, Nov CSV, Nov PDF (fetch from /samples or bundle in public/samples).
   After ingest: toast "42 transactions · 71% auto-categorised" (+ "reconciled ✓" when true).
2. Transactions page: month selector, filter chips (All · Needs review · by category), list grouped by
   date. Row = merchant (bold), raw text (muted, 1 line, truncated), amount (red debit / green credit),
   CategoryBadge. On mobile the row is a card; on desktop use a table.
3. CategoryBadge: shows the category + a source marker: "You" (user), "Learned" (rule, accent colour),
   "AI 82%" (ai, muted; amber when < 70%). Tap -> Select with the fixed category list -> POST correct.
4. ApplySimilarDialog: opens when similar_ids is non-empty: "Apply 'Food Delivery' to 6 similar
   transactions?" with a preview list and Apply / Skip buttons. Apply -> POST /rules/apply. Show an Undo
   toast for 5 s (undo = re-correct those rows back to their old categories).
5. AutoRateChip in the page header: the latest auto_rate plus a sparkline from GET /stats/auto-rate.
   This is the demo proof, so it must update right after ingest and after every correction.

Verify: cd frontend && npm run build && npm run lint. Then run the click path with the Playwright MCP at
390x844: open /transactions -> Load sample Oct SMS -> fix one "AI" row -> Apply similar -> Load Nov SMS ->
see a "Learned" badge. Paste raw output. STOP. List files, propose a commit message.
```

### Slice 1 merge check (both, 2 minutes)

`bash scripts/smoke_demo.sh`, then do the click path once on the merged `main` against the real backend.

---

## 3. Early deploy · 19:15–19:30 (de-risks the night)

### Suyash — Claude Code prompt

```
Deploy the current main. Backend: Render using render.yaml (service finpulse-api), set env vars
GROQ_API_KEY, GEMINI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY, RESEND_API_KEY, DEMO_EMAIL, CORS_ORIGINS
(= the Vercel URL). Frontend: Vercel, root frontend/, env NEXT_PUBLIC_API_URL = the Render URL.
Use the Vercel MCP for project and env setup if available. Then:
curl -s https://<render-url>/health and open the Vercel URL on a 390px viewport via Playwright: load the
Oct SMS sample and confirm rows render. Paste raw output. Do not change application code.
```

---

## 4. Slice 2 — Living money model · 19:30–20:30

**Done when:** the Home screen shows the Netflix price-rise alert and goal progress. On Plan, dragging "Dining −30%" moves the emergency-fund date earlier, live.

### Vaishnavi — Claude Code prompt

```
Enter Plan Mode. Read CLAUDE.md, openapi.yaml, docs/PLAYBOOK.md (slice 2). Backend of slice 2 only.
Files: backend/app/engines/{recurring.py, simulate.py}, main.py routes, tests/test_slice2.py.

1. recurring.py detect(): debits grouped by merchant_norm with >= 2 occurrences; intervals 25–35 days
   (monthly) or 6–8 (weekly); amounts within 20% of each other. Upsert the recurring table with
   period_days, last_amount, prev_amount, last_seen. status:
   'changed' when |last - prev| / prev > 5% (message "Netflix ₹499 → ₹649 (+30%)");
   'unused' when the user has marked it unused (add PATCH /recurring/{merchant_norm} {unused: bool};
   update openapi.yaml in the same PR and tell Suyash); else 'active'. Run detect() after every /ingest.
   GET /recurring returns items + monthly_total.
2. simulate.py simulate(adjustments): baseline = per-category average monthly debit over the months in
   the data; income from profile. scenario = baseline with adjustments ({category, pct_change} or
   {category, abs_change}). surplus = income - total spend. Goals funded in target_date order from the
   surplus: months_needed = ceil((target - saved_so_far) / surplus); projected_date vs target_date ->
   on_track. Return {baseline:{spend, surplus}, scenario:{spend, surplus}, delta_surplus,
   goals:[{name, target_date, projected_date_baseline, projected_date_scenario, on_track}],
   series:[12 months of cumulative savings, baseline vs scenario], essentials_over_income: bool}.
   Pure Python, no LLM. If surplus <= 0, projected dates = null and on_track = false.
3. GET/PUT /profile, GET/POST /goals, POST /simulate exactly as in openapi.yaml.
4. Tests: Netflix 499 -> 649 flagged 'changed'; a dining −30% cut moves the projected date earlier;
   surplus <= 0 gives null dates.
Verify: uv run pytest -q; curl POST /simulate with a dining -30% adjustment | jq. Paste raw output. STOP.
```

### Suyash — Claude Code prompt

```
Enter Plan Mode. Read CLAUDE.md, openapi.yaml, docs/PLAYBOOK.md (slice 2). Frontend of slice 2 only.
Files: frontend/src/app/page.tsx (Home), frontend/src/app/plan/*, components {KpiStrip, AlertList,
GoalCard, WhatIfPanel, ProjectionChart}.tsx. Use Recharts.

Home (one screen on mobile without much scrolling; information-dense):
- KpiStrip: this month's spend vs budget, savings rate, AutoRateChip (reuse from slice 1). Small type, big numbers.
- AlertList: recurring items with status 'changed' or 'unused' (one line each, with an action:
  "Mark unused" / "Dismiss"), plus a slot for slice-4 nudges.
- GoalCard per goal: progress bar, target date, "on track / 2 months late" from /simulate baseline.
- Category split: a horizontal bar list of the top 6 categories (no pie charts).
Plan page:
- Profile form (income, fixed costs, emergency fund, email) + goals list with an add form.
- WhatIfPanel: sliders for the discretionary categories (Dining, Food Delivery, Shopping, Entertainment,
  Travel, Subscriptions) from −50% to +50%, plus "Rent change ₹" and "Income change ₹" inputs. Debounced
  POST /simulate (300 ms). ProjectionChart: baseline vs scenario savings lines, and the goal dates moving
  (old date struck through → new date).
- Essential categories are NOT offered as cut sliders (the guardrail shows in the UI too), but rent/income
  CHANGES are allowed.
- If essentials_over_income: a calm banner explaining it, pointing to raising income or a human advisor.
Verify: npm run build && npm run lint; Playwright at 390x844: Home shows the Netflix alert -> Plan ->
drag Food Delivery to -30% -> the emergency-fund date changes. Paste raw output. STOP.
```

**20:30 — scope freeze.** From here on, no new features beyond slices 3 and 4. Cut from the list if behind.

---

## 5. Slice 3 — Coach agent · 20:30–21:30

**Done when:** "Can I hit my emergency fund by June if I cut Zomato 30%?" shows `simulate` in the trace and answers with exact numbers. "Should I buy Reliance?" is refused with an educational answer. "Should I spend less on rent?" doesn't get "cut rent" advice.

### Vaishnavi — Claude Code prompt

```
Enter Plan Mode. Read CLAUDE.md, agents/graph.md, docs/PLAYBOOK.md (slice 3). Backend support only.
Files: backend/app/engines/guardrails.py, tests/test_guardrails.py.
1. guardrails.py:
   - is_securities_request(text) -> bool: keyword/regex first (buy, sell, invest in, which stock, share,
     mutual fund, SIP in, ETF, crypto, bitcoin, NFT, IPO, ticker-like ALLCAPS 2–10 letters next to
     buy/sell/invest), then a cheap LLM yes/no via llm.py only when the keywords are ambiguous.
   - SECURITIES_REFUSAL: a short template — we don't pick securities; here is the concept (emergency fund
     first, then high-interest debt, then diversified long-term investing), and an offer to simulate how
     much they could set aside monthly.
   - mentions_cutting_essentials(reply) -> list[str]: essential category names within ~6 words of
     cut/reduce/lower/skip/stop.
2. Tests: 10 pick-requests flagged, 10 normal questions not flagged; the essentials detector on 6 sentences.
Verify: uv run pytest -q tests/test_guardrails.py. Paste raw output. STOP.
```

### Suyash — Claude Code prompt

```
Enter Plan Mode. Read CLAUDE.md, agents/graph.md, openapi.yaml, docs/PLAYBOOK.md (slice 3).
Files: backend/app/agents/coach.py, the /coach routes in main.py (coordinate with Vaishnavi; only add
the coach routes), frontend/src/app/coach/*, TracePanel.tsx (reuse).
1. coach.py, plain function calling through llm.chat(..., tools=...) with openai/gpt-oss-120b:
   - Before the loop: if guardrails.is_securities_request -> return SECURITIES_REFUSAL and emit a trace
     event {node:"guardrail", status:"blocked: securities"}.
   - System prompt: educational coach for an Indian user; every ₹ number must come from a tool result;
     never recommend cutting essentials (list them); may model essentials rising; if
     essentials_over_income, say so plainly and suggest income options or a human advisor; no specific
     securities; short answers (under 120 words) plus at most 3 bullet actions.
   - Tools = Python functions calling the engines directly (not HTTP): query_transactions, get_profile,
     update_profile, set_goal, get_recurring, simulate, get_nudges (stub until slice 4). Max 4 tool rounds.
   - Each tool call -> trace.emit(run_id, tool_name, "ok", tier_used, ms, args=..., result_summary=...).
   - After the final reply: if guardrails.mentions_cutting_essentials(reply) -> regenerate once with a
     corrective system note; emit {node:"guardrail", status:"rewrote: essentials"}.
   - POST /coach {message, history} -> {run_id}; GET /coach/{run_id}/events (SSE, same pattern as the
     template's run events); GET /coach/{run_id} -> {reply, events}.
2. Coach page: chat bubbles; suggested prompts as chips ("What if rent goes up ₹3k?", "Can I reach my
   emergency fund by June?", "Which subscriptions should I review?", "Should I buy Reliance shares?").
   TracePanel collapsible under each assistant message on mobile and as a right column on desktop:
   tool name, args, result summary, ms, tier. When a reply came from a simulate call, render the
   ProjectionChart inline.
Verify: Playwright at 390x844: send the 4 suggested prompts; paste the trace JSON for each.
Expected: simulate called for prompts 1–2, get_recurring for 3, guardrail blocked for 4. STOP.
```

---

## 6. Slice 4 — Nudges, report, email, PWA · 21:30–22:15

**Done when:** the Home screen shows "Food Delivery at 82% of budget on day 14". Tapping **Email me** delivers the nudges and the October report to the demo inbox. The app installs from Chrome on the phone.

### Vaishnavi — Claude Code prompt

```
Enter Plan Mode. Read CLAUDE.md, openapi.yaml, docs/PLAYBOOK.md (slice 4). Backend only.
Files: backend/app/engines/{nudges.py, report.py, emailer.py}, main.py routes, tests/test_slice4.py.
1. nudges.py: as_of = the latest transaction date (demo data is historical). For each category with a
   budget: spent month-to-date, expected = budget * day / days_in_month. Nudge if spent >= 75% of budget
   before day 20, or spent / expected > 1.25. Also add recurring 'changed' items and goals that are off
   track. Wording for essentials is informational only ("Utilities is above its usual level"), never
   "cut". Store new nudges in the nudges table (dedupe by kind + category + month). GET /nudges.
2. report.py: GET /report/{month}: deterministic stats {income, spend, savings_rate, top_categories with
   change vs the previous month, subscriptions_total, goals progress, auto_rate}; then ONE LLM call
   (gpt-oss-120b) given ONLY that JSON -> {summary (<=80 words), adjustments[3]}. Post-filter: drop any
   adjustment that cuts an essential (guardrails.mentions_cutting_essentials) and ask once more if fewer
   than 3 remain. Cache per month.
3. emailer.py with the Resend SDK: send(kind) -> an inline-styled HTML email (subject "FinPulse · 3 nudges
   for November" or "FinPulse · October review"), to profile.email or DEMO_EMAIL; from EMAIL_FROM
   (Resend test sender). POST /email/send {kind, month?} -> {id}. Mark the nudges as emailed.
Verify: uv run pytest -q; curl POST /email/send nudges and check the inbox; paste raw output. STOP.
```

### Suyash — Claude Code prompt

```
Enter Plan Mode. Read CLAUDE.md, docs/PLAYBOOK.md (slice 4). Frontend only.
1. Home: wire the nudges into AlertList (icon by kind, one line, tap -> the relevant page). An
   "Email me these" button -> POST /email/send {kind:"nudges"}, toast "Sent to <email>".
2. Report page: month picker; stat tiles; top-category changes as a small bar list with ↑/↓; the LLM
   summary in a card labelled "Coach summary"; the 3 adjustments; an "Email this report" button.
3. PWA check: manifest (name FinPulse, short_name FinPulse, start_url "/", display standalone, theme and
   background colours, 192/512 + maskable icons); sw.js caches the app shell only; an in-app "Install app"
   button using beforeinstallprompt (hidden when unsupported). Run a Lighthouse PWA/installability check
   via Playwright or the Chrome DevTools MCP and paste the result.
4. Final responsive pass: 360, 390, 768, 1280 widths. No horizontal scroll, tap targets ≥ 44px, and
   the bottom tabs don't cover content.
Verify: npm run build && npm run lint; Playwright run of the full demo path below at 390x844. STOP.
```

---

## 7. Final deploy + smoke test · 22:15–22:35

1. Merge everything to `main`. Render and Vercel redeploy automatically (or trigger them).
2. Run this on the **live URL**, on a real phone: the full demo path (section 9).
3. Warm the Render instance (open `/health`) right before recording.
4. Reset the demo state: a `POST /admin/reset-demo` route, or a SQL script in `scripts/reset_demo.sql`, that truncates transactions, uploads, nudges and user rules and re-seeds the profile and goals. Rehearse once.

## 8. Submit · 22:35–23:30

### Vaishnavi — Claude Code prompt (README + disclosure)

```
Read CLAUDE.md, docs/PLAYBOOK.md, the git log. Finish README.md and AI_DISCLOSURE.md. Docs only.
README: one-line pitch; live URL + video link placeholders; Problem -> Solution -> Architecture (Mermaid:
PWA -> FastAPI [ingest+categorizer, engines, coach agent + guardrails] -> Supabase / LLM router (Groq ->
Gemini) / Resend); "How the learning loop works" (5 steps); "PS4 requirements -> where to see it" table
(8 rows + email, PWA, essentials guardrail); guardrails section; setup commands; env var NAMES only;
limitations (synthetic data, single user, no RLS, 'unused' is user-marked); AI disclosure link.
AI_DISCLOSURE.md: complete the contribution log from the git history — per slice, what we designed and
wrote ourselves vs what Claude Code generated, and who reviewed it. Be honest and specific.
```

### Suyash — demo video (2–3 min, record with OBS)

| Time | Screen | Voiceover |
|---|---|---|
| 0:00–0:15 | Home on phone | "Budget apps label transactions and stop. FinPulse learns from you and models your goals." |
| 0:15–0:45 | Paste Oct SMS → 71% → fix 4 → Apply to 6 similar | "Messy SMS, CSV, PDF. When I fix a category, it becomes a rule." |
| 0:45–1:05 | Load Nov → 96%, Learned badges, auto-rate sparkline | "Next month it barely needs me. That number is the learning loop." |
| 1:05–1:25 | Home: Netflix ₹499→₹649, gym unused, Food Delivery 82% nudge → Email → inbox on phone | "It catches subscription changes and drift, on the dashboard and in email." |
| 1:25–1:55 | Plan: Food Delivery −30% → goal date moves | "Every rupee here is computed in Python, not guessed by the model." |
| 1:55–2:25 | Coach: emergency-fund question → trace shows simulate → chart | "The coach is an agent: it decides which tool to call, and you can see it." |
| 2:25–2:45 | "Should I buy Reliance?" → refusal + lesson; then the rent question | "It teaches, never picks securities, and never tells you to cut essentials." |
| 2:45–3:00 | Architecture slide + GitHub URL | "Next.js PWA, FastAPI, Supabase, Groq with Gemini fallback." |

Record one clean take plus spare clips for tomorrow's LinkedIn post.

### Submission checklist (submit by 23:30)

- [ ] Live Vercel URL works on phone and desktop
- [ ] GitHub repo public; README complete; `AI_DISCLOSURE.md` complete
- [ ] Demo video uploaded (YouTube unlisted / Drive with access open) and linked in the README
- [ ] Product Space "Submit project": URL, repo, video, short explanation (use the README pitch + the "learning loop" paragraph)
- [ ] Check the WhatsApp group / Unstop for any extra submission step
- [ ] Spare clips + 2 screenshots saved for the LinkedIn post

## 9. Demo path (used for every verification and for the video)

1. Reset the demo state.
2. Paste Oct SMS → note the auto-rate.
3. Fix the 4 cryptic merchants → Apply similar.
4. Ingest Nov SMS + Nov PDF → Learned badges, auto-rate up, "reconciled ✓".
5. Home: Netflix price rise, gym marked unused, Food Delivery nudge → Email me → check the phone.
6. Plan: Food Delivery −30% → emergency-fund date moves earlier.
7. Coach: the 4 suggested prompts.
8. Report: October review → Email this report.

## 10. When something breaks (G5 triage prompt)

```
/triage <paste the error + the command that produced it>
Rules: give a 3-bullet root-cause hypothesis BEFORE any edit. Minimal fix only. Don't touch openapi.yaml
or the pinned model IDs without asking. One verification command with raw output. If the fix fails
twice: stop and tell me to /rewind, with a clean re-prompt.
```

**15-minute rule:** if one bug eats more than 15 minutes, cut the feature using the cut list and move on.
