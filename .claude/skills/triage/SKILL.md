---
name: triage
description: Structured bug triage with the 2-strike rule. Use when a slice breaks or a test fails.
argument-hint: [paste error]
disable-model-invocation: true
---
Structured bug triage. Do not explore unrelated files.
Bug report: $ARGUMENTS
If not already given, ask for: EXPECTED, ACTUAL, ERROR (verbatim), REPRO, RECENT CHANGE, SUSPECT.
1. Root-cause hypothesis in <=3 bullets BEFORE editing.
2. Minimal fix; no refactors; never change pinned model IDs or openapi.yaml without asking.
3. Verify with one command and paste raw output.
4. One retry max. If still broken: stop, list what you ruled out, and tell the human to /rewind
   and re-prompt with a cleaner report.
