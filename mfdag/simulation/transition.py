from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Set

from mfdag.utils.io import append_jsonl


def build_real_next_state(
    *,
    target_user_id: int,
    target_cohort_id: str,
    target_post_id: int,
) -> Dict[str, Any]:
    return {
        "participating_users": [target_user_id],
        "participating_cohorts": [target_cohort_id] if target_cohort_id else [],
        "participation_count": 1,
        "target_post_id": target_post_id,
        "continuation_size": 1,
    }


def build_simulated_next_state(
    follower_actions: List[Dict[str, Any]],
    user_to_cohort: Dict[int, str],
) -> Dict[str, Any]:
    participating_users = [a["user_id"] for a in follower_actions if a["sampled_action"] == "participate"]
    cohorts = sorted({user_to_cohort.get(uid, "unknown") for uid in participating_users})
    action_dist = dict(Counter(a["sampled_action"] for a in follower_actions))
    cohort_dist = dict(Counter(user_to_cohort.get(a["user_id"], "unknown") for a in follower_actions if a["sampled_action"] == "participate"))
    return {
        "participating_users": participating_users,
        "participating_cohorts": cohorts,
        "participation_count": len(participating_users),
        "cohort_distribution": cohort_dist,
        "action_distribution": action_dist,
        "continuation_size": len(participating_users),
    }


def compute_prediction_error(real: Dict[str, Any], simulated: Dict[str, Any]) -> Dict[str, Any]:
    real_users = set(real.get("participating_users", []))
    sim_users = set(simulated.get("participating_users", []))
    tp = len(real_users & sim_users)
    fp = len(sim_users - real_users)
    fn = len(real_users - sim_users)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    size_err = abs(int(real.get("participation_count", 0)) - int(simulated.get("participation_count", 0)))
    return {
        "user_precision": round(precision, 4),
        "user_recall": round(recall, 4),
        "user_f1": round(f1, 4),
        "continuation_size_error": size_err,
        "real_participation_count": len(real_users),
        "sim_participation_count": len(sim_users),
    }


def log_transition(path, record: Dict[str, Any]) -> None:
    append_jsonl(path, record)
