from __future__ import annotations

from typing import Any, Dict, List


def assign_cohorts_quantile(agents: List[Dict[str, Any]], cohort_count: int = 5) -> List[Dict[str, Any]]:
    if not agents:
        return []
    sorted_agents = sorted(agents, key=lambda a: a["activity_score"])
    n = len(sorted_agents)
    cohort_rows: List[Dict[str, Any]] = []
    for i, agent in enumerate(sorted_agents):
        if n == 1:
            bucket = 0
        else:
            bucket = min(cohort_count - 1, int(i / n * cohort_count))
        cohort_id = f"C{bucket}"
        cohort_rows.append(
            {
                "agent_id": agent["agent_id"],
                "user_id": agent["user_id"],
                "cohort_id": cohort_id,
                "activity_score": agent["activity_score"],
                "activity_level": agent["activity_level"],
                "strategy": "hybrid_activity_behavior",
            }
        )
    return cohort_rows


def cohort_summary(cohort_rows: List[Dict[str, Any]], agents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    agent_map = {a["agent_id"]: a for a in agents}
    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for row in cohort_rows:
        buckets.setdefault(row["cohort_id"], []).append(row)

    summaries: List[Dict[str, Any]] = []
    for cohort_id in sorted(buckets.keys()):
        members = buckets[cohort_id]
        scores = [m["activity_score"] for m in members]
        agent_details = [agent_map[m["agent_id"]] for m in members if m["agent_id"] in agent_map]
        summaries.append(
            {
                "cohort_id": cohort_id,
                "num_agents": len(members),
                "activity_score_mean": round(sum(scores) / len(scores), 4) if scores else 0.0,
                "activity_score_min": min(scores) if scores else 0.0,
                "activity_score_max": max(scores) if scores else 0.0,
                "avg_like_count": round(
                    sum(a["like_count_sum"] for a in agent_details) / len(agent_details), 2
                )
                if agent_details
                else 0.0,
                "avg_reply_count": round(
                    sum(a["reply_count_sum"] for a in agent_details) / len(agent_details), 2
                )
                if agent_details
                else 0.0,
                "avg_repost_count": round(
                    sum(a["repost_count_sum"] for a in agent_details) / len(agent_details), 2
                )
                if agent_details
                else 0.0,
            }
        )
    return summaries
