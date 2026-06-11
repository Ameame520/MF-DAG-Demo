from __future__ import annotations

import random
from typing import Any, Dict, List, Set

from mfdag.follower.policy import participation_probability, sample_action
from mfdag.utils.io import append_jsonl


class FollowerUpdater:
    def __init__(self, actions_path, random_seed: int = 42):
        self.actions_path = actions_path
        self.rng = random.Random(random_seed)

    def update_followers(
        self,
        *,
        thread_id: str,
        step_id: int,
        cohort_id: str,
        decision_signal_id: str,
        decision_signal: Dict[str, Any],
        member_profiles: List[Dict[str, Any]],
        observed_user_ids: Set[int],
    ) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        for profile in member_profiles:
            already = profile["user_id"] in observed_user_ids
            prob = participation_probability(
                profile,
                decision_signal,
                already_participated=already,
                random_seed=self.rng.randint(0, 10**9),
            )
            action = sample_action(prob, self.rng)
            rec = {
                "thread_id": thread_id,
                "step_id": step_id,
                "agent_id": profile["agent_id"],
                "user_id": profile["user_id"],
                "cohort_id": cohort_id,
                "decision_signal_id": decision_signal_id,
                "participation_probability": round(prob, 4),
                "sampled_action": action,
                "random_seed": self.rng.randint(0, 10**9),
            }
            records.append(rec)
            append_jsonl(self.actions_path, rec)
        return records
