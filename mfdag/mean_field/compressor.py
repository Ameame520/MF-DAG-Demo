from __future__ import annotations

from typing import Any, Dict, List, Set

from mfdag.mean_field.schema import mean_field_state_template


class MeanFieldCompressor:
    def __init__(self, agent_profiles: Dict[str, Dict[str, Any]], cohort_members: Dict[str, List[str]]):
        self.agent_profiles = agent_profiles
        self.cohort_members = cohort_members
        self._historical_rates: Dict[str, List[float]] = {}

    def record_historical(self, cohort_id: str, rate: float) -> None:
        self._historical_rates.setdefault(cohort_id, []).append(rate)

    def compress(
        self,
        *,
        thread_id: str,
        step_id: int,
        cohort_id: str,
        thread_meta: Dict[str, Any],
        observed_user_ids: Set[int],
        observed_post_texts: List[str],
        recent_growth: int = 0,
    ) -> Dict[str, Any]:
        member_ids = self.cohort_members.get(cohort_id, [])
        members = [self.agent_profiles[aid] for aid in member_ids if aid in self.agent_profiles]
        num_agents = len(members)
        known = {uid for uid in observed_user_ids if any(m["user_id"] == uid for m in members)}
        obs_count = len(known)
        obs_rate = obs_count / num_agents if num_agents else 0.0
        hist = self._historical_rates.get(cohort_id, [])
        hist_rate = sum(hist) / len(hist) if hist else obs_rate
        activity_mean = sum(m["activity_score"] for m in members) / num_agents if num_agents else 0.0
        engagement_mean = (
            sum(m["like_count_sum"] + m["reply_count_sum"] + m["repost_count_sum"] for m in members)
            / num_agents
            if num_agents
            else 0.0
        )

        state = mean_field_state_template()
        state.update(
            {
                "thread_id": thread_id,
                "step_id": step_id,
                "cohort_id": cohort_id,
                "num_agents": num_agents,
                "observed_participation_count": obs_count,
                "observed_participation_rate": round(obs_rate, 4),
                "historical_participation_rate": round(hist_rate, 4),
                "activity_mean": round(activity_mean, 4),
                "engagement_mean": round(engagement_mean, 4),
                "recent_growth": recent_growth,
                "thread_len": int(thread_meta.get("thread_len", 0)),
                "matched_post_count": int(thread_meta.get("matched_post_count", 0)),
                "join_coverage": float(thread_meta.get("join_coverage", 0.0)),
                "known_participant_users": sorted(known),
                "observed_post_texts": observed_post_texts,
                "summary": (
                    f"Cohort {cohort_id}: {obs_count}/{num_agents} observed participants; "
                    f"thread matched {thread_meta.get('matched_post_count')}/{thread_meta.get('thread_len')}."
                ),
            }
        )
        return state

    def feature_vector(self, state: Dict[str, Any]) -> List[float]:
        return [
            float(state.get("observed_participation_rate", 0)),
            float(state.get("historical_participation_rate", 0)),
            float(state.get("activity_mean", 0)),
            float(state.get("engagement_mean", 0)),
            float(state.get("recent_growth", 0)),
            float(state.get("join_coverage", 0)),
            float(state.get("matched_post_count", 0)) / max(float(state.get("thread_len", 1)), 1.0),
        ]
