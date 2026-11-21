#!/usr/bin/env bash
# Contract smoke: every route must return {success:true}. Usage: API=http://localhost:8787 bash scripts/smoke_demo.sh
set -euo pipefail
API="${API:-http://localhost:8787}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FAILS=0

check() {  # check <label> <curl args...>
  local label="$1"; shift
  local out
  out=$(curl -fsS "$@") || { echo "FAIL $label (http)"; FAILS=$((FAILS + 1)); return 0; }
  if [[ "$(jq -r '.success' <<<"$out")" == "true" ]]; then
    echo "ok   $label  $(jq -c '.data' <<<"$out" | cut -c1-90)"
  else
    echo "FAIL $label  $out"; FAILS=$((FAILS + 1))
  fi
}
J=(-H 'content-type: application/json')

check "GET  /health"               "$API/health"
SAMPLE="$ROOT/backend/samples/statement_oct.csv"
if [[ -f "$SAMPLE" ]]; then
  check "POST /ingest (csv file)"  -X POST "$API/ingest" -F "file=@$SAMPLE"
else
  echo "warn no $SAMPLE (run scripts/make_samples.py)"
fi
check "POST /ingest (sms json)"    -X POST "$API/ingest" "${J[@]}" -d '{"kind":"sms","text":"Rs.499.00 debited to NETFLIX"}'
check "GET  /transactions"         "$API/transactions?month=2026-10&needs_review=true"
check "POST /transactions/correct" -X POST "$API/transactions/tx_002/correct" "${J[@]}" -d '{"category":"Groceries"}'
check "POST /rules/apply"          -X POST "$API/rules/apply" "${J[@]}" -d '{"rule_id":"rule_001","transaction_ids":["tx_014"]}'
check "GET  /profile"              "$API/profile"
check "PUT  /profile"              -X PUT "$API/profile" "${J[@]}" -d '{"monthly_income":90000}'
check "GET  /goals"                "$API/goals"
check "POST /goals"                -X POST "$API/goals" "${J[@]}" -d '{"name":"Goa trip","target_amount":25000,"target_date":"2027-03-31"}'
check "GET  /recurring"            "$API/recurring"
check "POST /simulate"             -X POST "$API/simulate" "${J[@]}" -d '{"adjustments":[{"category":"Dining","pct_change":-30}]}'
check "GET  /nudges"               "$API/nudges"
check "GET  /report/2026-10"       "$API/report/2026-10"
check "POST /email/send"           -X POST "$API/email/send" "${J[@]}" -d '{"kind":"report","month":"2026-10"}'
check "GET  /stats/auto-rate"      "$API/stats/auto-rate"

RID=$(curl -fsS -X POST "$API/coach" "${J[@]}" -d '{"message":"Can I afford the Goa trip?","history":[]}' | jq -r .data.run_id)
echo "ok   POST /coach  run_id=$RID"
echo "== SSE /coach/$RID/events"
curl -sN --max-time 10 "$API/coach/$RID/events" | sed -n '1,8p' || true
check "GET  /coach/{run_id}"       "$API/coach/$RID"
ANS=$(curl -fsS "$API/coach/$RID" | jq -r '.data.answer // empty')
[[ -n "$ANS" ]] || { echo "FAIL coach produced no answer"; FAILS=$((FAILS + 1)); }

if [[ $FAILS -eq 0 ]]; then echo "SMOKE PASS"; else echo "SMOKE FAIL ($FAILS)"; exit 1; fi
