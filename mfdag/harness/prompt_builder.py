from __future__ import annotations

import json
from typing import Any, Dict, List


SYSTEM_PROMPT = """You are a representative LLM agent for a social cohort on Bluesky.
Given the current thread mean-field state and retrieved collective memory, predict cohort-level participation in the next matched post.
Respond with JSON only, matching this schema:
{
  "cohort_id": "C0",
  "participation_intensity": 0.35,
  "action_bias": {"participate": 0.35, "inactive": 0.65, "reply": 0.2, "quote": 0.1, "repost": 0.05, "like": 0.15},
  "expected_growth": "low|medium|high",
  "attitude_or_interest_shift": "stable|increasing|decreasing",
  "confidence": 0.72,
  "rationale": "..."
}
Primary action space is participate vs inactive."""


def _truncate_texts(texts: List[str], max_chars: int) -> List[str]:
    out = []
    for t in texts:
        t = (t or "").strip().replace("\n", " ")
        if len(t) > max_chars:
            t = t[:max_chars] + "..."
        out.append(t)
    return out


def build_representative_prompt(
    mean_field_state: Dict[str, Any],
    global_memories: List[Dict[str, Any]],
    cohort_memories: List[Dict[str, Any]],
    representative_profile: Dict[str, Any],
    text_max_chars: int = 200,
) -> str:
    texts = _truncate_texts(mean_field_state.get("observed_post_texts", []), text_max_chars)
    payload = {
        "task": "Predict whether agents in this cohort will participate in the next matched post of the thread.",
        "mean_field_state": {**mean_field_state, "observed_post_texts": texts},
        "representative_profile": representative_profile,
        "retrieved_global_memory_summaries": [m.get("text_summary", "") for m in global_memories],
        "retrieved_cohort_memory_summaries": [m.get("text_summary", "") for m in cohort_memories],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_full_agent_prompt(
    agent_profile: Dict[str, Any],
    thread_state: Dict[str, Any],
    text_max_chars: int = 200,
) -> str:
    texts = _truncate_texts(thread_state.get("observed_post_texts", []), text_max_chars)
    payload = {
        "task": "Decide whether this agent will participate in the next matched post.",
        "agent_profile": agent_profile,
        "thread_state": {**thread_state, "observed_post_texts": texts},
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


FULL_AGENT_SYSTEM = """You are an individual Bluesky user agent.
Decide participate or inactive for the next matched post in the thread.
Respond JSON only: {"agent_id": "...", "participate": true/false, "confidence": 0.0-1.0, "rationale": "..."}"""


RULE_BASED_SYSTEM = """You are a rule-based Bluesky agent.
Use only structured profile fields; do not invent unseen context.
Respond JSON only: {"agent_id": "...", "participate": true/false, "confidence": 0.0-1.0, "rationale": "..."}"""
