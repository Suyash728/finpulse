---
name: demoprep
description: Prepare the demo - seed data, offline (Tier 3) run, screen-record checklist
disable-model-invocation: true
---
1. Check backend/app/seed.py has 2-3 realistic cases and "Load sample case" works from a fresh browser profile.
2. Offline rehearsal: `bash scripts/vllm-up.sh coding`, then `bash scripts/smoke_demo.sh --privacy`; paste output.
   Every trace event must show tier_used=local.
3. Cloud rehearsal: `bash scripts/smoke_demo.sh` with keys set; note which tier answered.
4. Hit the Render /health and the Vercel URL; open the Supabase dashboard (free projects pause).
5. Use the demo-tester subagent to click the 90-second path with Playwright and screenshot each step.
6. Print the recording checklist: OBS 1080p, one window shared, browser zoom 125%, notifications off,
   .env files closed, backup video on USB + phone.
