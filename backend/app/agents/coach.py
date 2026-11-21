"""Coach agent: plain function calling (spec: agents/graph.md). Owner: Suyash. TODO(slice 10).

Flow: intent_guard -> up to MAX_STEPS tool calls -> answer.
Each step emits trace.emit(run_id, node=<tool_name>, status, tier_used, ms, args=..., result_summary=...).
All model calls via app.services.llm.chat(); every rupee figure comes from a tool result.
"""

from __future__ import annotations

MAX_STEPS = 4

TOOL_NAMES = ("query_transactions", "get_profile", "update_profile", "set_goal",
              "get_recurring", "simulate", "get_nudges")


def intent_guard(message: str) -> dict:
    """Classify BEFORE the agent: {'intent': 'securities'|'planning'|'other', 'tier_used', 'ms'}.
    'securities' (stock/fund/crypto picks) -> refusal + educational answer, no tools. TODO(slice 10)
    """
    raise NotImplementedError


def tool_schemas() -> list[dict]:
    """OpenAI-format tool definitions for TOOL_NAMES. TODO(slice 10)"""
    raise NotImplementedError


def run(run_id: str, message: str, history: list[dict]) -> dict:
    """Execute the loop, emitting trace events. Returns {answer, refused}. TODO(slice 10)"""
    raise NotImplementedError
