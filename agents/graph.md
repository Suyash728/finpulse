# Coach agent spec — plain function calling

Owner: Suyash. Code: `backend/app/agents/coach.py`. No LangGraph / CrewAI.

## Flow (one user message)
```
POST /coach {message, history}
  -> intent_guard(message)                      # BEFORE the agent; 1 small LLM call (gpt-oss-20b ok)
       securities pick? -> refusal + educational answer, emit {node: intent_guard, status: refused}, END
  -> loop step = 1..4 (MAX_STEPS = 4)
       llm.chat(messages, tools=TOOLS, tool_choice="auto")
       no tool_calls -> final answer, END
       for each tool_call: run Python tool, emit trace event, append tool result message
  -> step limit hit -> one last llm.chat(tools=None) to answer from what it has
  -> emit {node: answer, status: finished}; trace.close(run_id)
```

## Tools (all pure Python over Supabase via engines; return small JSON)
| tool | args | returns |
|---|---|---|
| query_transactions | {month?, category?, merchant?, limit<=50} | {items[], totals_by_category{}} |
| get_profile | {} | Profile (income, fixed_costs, emergency_fund, budgets) |
| update_profile | {monthly_income?, fixed_costs?, emergency_fund?, budgets?} | Profile |
| set_goal | {name, target_amount, target_date, saved_amount?} | Goal |
| get_recurring | {} | RecurringItem[] (active / changed / unused) |
| simulate | {adjustments: [{category, pct_change or abs_change}]} | {baseline, scenario, goal_dates, warnings} |
| get_nudges | {month?} | Nudge[] |

Tool results already contain every number the answer needs; the model only quotes them.

## Guardrails
1. **Securities (pre-check, before tools)**: intent classes `securities | planning | other`.
   `securities` = asks which stock / mutual fund / crypto / IPO to buy, sell or hold. Reply: we don't recommend
   specific securities, plus 3-4 lines of education (diversification, index vs active, emergency fund first,
   risk matches horizon) and a pointer to a SEBI-registered advisor. No tools run. Trace status `refused`.
   General education ("what is an index fund?") is `planning`/`other` and allowed.
2. **Essentials rule**: Rent, Utilities, Groceries, Medical, EMI, Insurance, Education are never proposed as cuts.
   The agent may *model* them rising (`simulate` with +abs_change). Post-check: if the draft answer suggests
   reducing an essential, regenerate once with a correction note; else strip that sentence.
   If essentials > income (simulate `warnings`), say so plainly, point to raising income or a human advisor.
3. **No arithmetic**: the model may not add, subtract or project; if it needs a number, it calls a tool.

## Trace events (SSE `GET /coach/{run_id}/events`)
`{node, status, tier_used, ms, args, result_summary}`; `node` = `intent_guard` | tool name | `answer`;
`status` = `start | ok | error | refused | finished`; `tier_used` is set for LLM steps, `null` for pure tools.
`result_summary` is under 80 chars, e.g. `"savings +900/mo; Goa trip Mar 2027 (was Apr)"`.

## System prompt outline
1. Role: friendly Indian personal-finance coach for one user; explains, models scenarios, educates.
2. Hard rules: never recommend specific securities; never suggest cutting essentials (list them);
   never compute numbers, always call a tool and quote its figures in ₹ with Indian digit grouping as given.
3. Tool-use policy: prefer `simulate` for any "what if"; `get_profile` + `get_recurring` for "where can I save";
   at most 4 tool calls; ask one clarifying question if the request lacks a category/amount.
4. Style: 2-5 short sentences or bullets, lead with the answer, end with one concrete next step in the app.
5. Few-shot: one what-if example and one refusal example.
