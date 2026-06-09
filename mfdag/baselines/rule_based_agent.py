from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Dict, List, Set

from mfdag.harness.prompt_builder import RULE_BASED_SYSTEM, build_full_agent_prompt
from mfdag.simulation.runner import ProcessedData, build_simulation_steps, truncate_text
from mfdag.simulation.transition import build_real_next_state, build_simulated_next_state, compute_prediction_error, log_transition
from mfdag.utils.io import append_jsonl, write_json
from mfdag.utils.llm_client import DeepSeekClient, LLMUsageTracker
import time


class RuleBasedAgentBaseline:
    def __init__(self, cfg: Dict[str, Any], run_dir: Path, data: ProcessedData, threads: List[Dict], eval_thread_ids: Set[str]):
        self.cfg = cfg
        self.run_dir = run_dir
        self.data = data
        self.threads = threads
        self.eval_thread_ids = eval_thread_ids
        self.text_max_chars = cfg["simulation"].get("prompt_text_max_chars", 200)
        self.prediction_mode = cfg["simulation"].get("prediction_mode", "one_step")
        self.tracker = LLMUsageTracker(log_path=run_dir / "llm_calls.jsonl")
        self.llm = DeepSeekClient(cfg, self.tracker)
        self.actions_path = run_dir / "simulation" / "follower_actions.jsonl"
        self.transition_path = run_dir / "simulation" / "state_transitions.jsonl"
        self.actions_path.parent.mkdir(parents=True, exist_ok=True)
        self.t0 = time.time()

    def run(self) -> Dict[str, Any]:
        for thread_row in self.threads:
            steps = build_simulation_steps(thread_row, self.prediction_mode)
            for step in steps:
                self._run_step(thread_row, step)
        runtime = time.time() - self.t0
        summary = {
            "run_id": self.run_dir.name,
            "method": "rule_based_agent",
            "threads_processed": len(self.threads),
            "runtime_s": round(runtime, 2),
            **self.tracker.summary(),
        }
        write_json(self.run_dir / "run_summary.json", summary)
        return summary

    def _run_step(self, thread_row: Dict[str, str], step: Dict[str, Any]) -> None:
        thread_id = thread_row["thread_id"]
        step_id = step["step_id"]
        observed_users: Set[int] = set(step["observed_user_ids"])
        observed_texts = [
            truncate_text(self.data.post_index[pid].get("text", ""), self.text_max_chars)
            for pid in step["observed_post_ids"]
            if pid in self.data.post_index
        ]
        thread_state = {
            "thread_id": thread_id,
            "step_id": step_id,
            "thread_len": int(thread_row["thread_len"]),
            "matched_post_count": int(thread_row["matched_post_count"]),
            "join_coverage": float(thread_row["join_coverage"]),
            "observed_post_texts": observed_texts,
            "known_participant_users": sorted(observed_users),
        }

        actions: List[Dict[str, Any]] = []
        for agent in self.data.agents:
            profile = self.data.agent_profiles[agent["agent_id"]]
            rule_profile = {
                **profile,
                "rule": "participate if activity_level is high and matched_thread_post_count >= 2 else inactive tendency",
            }
            prompt = build_full_agent_prompt(rule_profile, thread_state, self.text_max_chars)
            try:
                raw = self.llm.complete_json(
                    method="rule_based_agent",
                    system_prompt=RULE_BASED_SYSTEM,
                    user_prompt=prompt,
                    meta={"thread_id": thread_id, "agent_id": agent["agent_id"]},
                )
                participate = bool(raw.get("participate", profile["activity_level"] == "high"))
            except Exception:
                participate = profile["activity_level"] == "high"
            action = "participate" if participate else "inactive"
            rec = {
                "thread_id": thread_id,
                "step_id": step_id,
                "agent_id": agent["agent_id"],
                "user_id": int(agent["user_id"]),
                "cohort_id": profile["cohort_id"],
                "decision_signal_id": str(uuid.uuid4()),
                "participation_probability": 1.0 if participate else 0.0,
                "sampled_action": action,
            }
            actions.append(rec)
            append_jsonl(self.actions_path, rec)

        target_uid = int(step["target_user_id"])
        real_next = build_real_next_state(
            target_user_id=target_uid,
            target_cohort_id=self.data.user_to_cohort.get(target_uid, ""),
            target_post_id=int(step["target_post_id"]),
        )
        sim_next = build_simulated_next_state(actions, self.data.user_to_cohort)
        pred_err = compute_prediction_error(real_next, sim_next)
        log_transition(
            self.transition_path,
            {
                "thread_id": thread_id,
                "root_time": thread_row["root_time"],
                "step_id": step_id,
                "method": "rule_based_agent",
                "is_eval": thread_id in self.eval_thread_ids,
                "real_next_state": real_next,
                "simulated_next_state": sim_next,
                "prediction_error": pred_err,
            },
        )
