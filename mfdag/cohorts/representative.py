from __future__ import annotations

from typing import Any, Dict, List


def select_representatives(
    cohort_rows: List[Dict[str, Any]],
    agents: List[Dict[str, Any]],
    strategy: str = "highest_activity",
) -> List[Dict[str, Any]]:
    agent_map = {a["agent_id"]: a for a in agents}
    by_cohort: Dict[str, List[Dict[str, Any]]] = {}
    for row in cohort_rows:
        by_cohort.setdefault(row["cohort_id"], []).append(row)

    reps: List[Dict[str, Any]] = []
    for cohort_id in sorted(by_cohort.keys()):
        members = by_cohort[cohort_id]
        if strategy == "highest_activity":
            best = max(members, key=lambda m: m["activity_score"])
        else:
            best = members[0]
        agent = agent_map[best["agent_id"]]
        reps.append(
            {
                "cohort_id": cohort_id,
                "agent_id": best["agent_id"],
                "user_id": best["user_id"],
                "activity_score": best["activity_score"],
                "strategy": strategy,
                "post_count": agent["post_count"],
                "matched_thread_post_count": agent["matched_thread_post_count"],
            }
        )
    return reps
