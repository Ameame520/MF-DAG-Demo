from __future__ import annotations

from typing import Any, Dict


def build_agent_profile(agent_row: Dict[str, Any], cohort_id: str) -> Dict[str, Any]:
    return {
        "agent_id": agent_row["agent_id"],
        "user_id": int(agent_row["user_id"]),
        "cohort_id": cohort_id,
        "activity_score": float(agent_row["activity_score"]),
        "activity_level": agent_row["activity_level"],
        "post_count": int(agent_row["post_count"]),
        "matched_thread_post_count": int(agent_row["matched_thread_post_count"]),
        "like_count_sum": int(agent_row["like_count_sum"]),
        "reply_count_sum": int(agent_row["reply_count_sum"]),
        "repost_count_sum": int(agent_row["repost_count_sum"]),
        "quote_count": int(agent_row["quote_count"]),
    }
