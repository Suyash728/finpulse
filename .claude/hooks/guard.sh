#!/bin/bash
# PreToolUse guard: exit 2 blocks the tool call and shows stderr to Claude. Needs jq.
input=$(cat)
tool=$(jq -r '.tool_name' <<<"$input")
cmd=$(jq -r '.tool_input.command // ""' <<<"$input")
file=$(basename "$(jq -r '.tool_input.file_path // ""' <<<"$input")")

if [[ "$tool" == "Bash" && "$cmd" =~ git[[:space:]]+push.*(main|master) ]]; then
  echo "Blocked: no direct push to main. Push a branch." >&2; exit 2; fi
if [[ "$file" == ".env" || "$file" == ".env.local" || "$cmd" =~ \.env([[:space:]]|$) ]]; then
  echo "Blocked: .env is off-limits. Use .env.example." >&2; exit 2; fi
if [[ ("$tool" == "Edit" || "$tool" == "Write") && "$file" == "openapi.yaml" ]]; then
  echo "Blocked: openapi.yaml is the frozen contract. Ask the human." >&2; exit 2; fi
exit 0
