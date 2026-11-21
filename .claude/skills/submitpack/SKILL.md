---
name: submitpack
description: Produce the submission pack - README, AI_DISCLOSURE.md, demo video script, deck outline, judge Q&A
argument-hint: [video-minutes]
disable-model-invocation: true
---
Read the repo (CLAUDE.md, openapi.yaml, agents/graph.md, git log).
1. Rewrite README.md: pitch line, Mermaid architecture, quickstart (exact commands), env var NAMES only,
   rubric-alignment table, "Works offline" (Tier 3 vLLM), link to AI_DISCLOSURE.md.
2. Fill AI_DISCLOSURE.md: every tool, model, API and dataset actually used (grep the code to confirm).
3. A ${ARGUMENTS:-2}-minute demo video script as a 2-column table (screen action | voiceover).
4. Deck outline: 30 s problem, 60 s live demo, 20 s architecture + agent trace, 10 s impact.
5. The 8 hardest judge questions with 2-sentence answers.
Never print secrets; never read .env.
