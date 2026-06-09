from __future__ import annotations

from typing import Any, Dict, List


def mean_field_state_template() -> Dict[str, Any]:
    return {
        "thread_id": "",
        "step_id": 0,
        "cohort_id": "",
        "num_agents": 0,
        "observed_participation_count": 0,
        "observed_participation_rate": 0.0,
        "historical_participation_rate": 0.0,
        "activity_mean": 0.0,
        "engagement_mean": 0.0,
        "recent_growth": 0,
        "thread_len": 0,
        "matched_post_count": 0,
        "join_coverage": 0.0,
        "known_participant_users": [],
        "observed_post_texts": [],
        "summary": "",
    }
