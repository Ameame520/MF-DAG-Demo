from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from mfdag.harness.prompt_builder import SYSTEM_PROMPT, build_representative_prompt
from mfdag.harness.signal_parser import default_signal, normalize_decision_signal
from mfdag.utils.io import append_jsonl


class DecisionHarness:
    def __init__(
        self,
        llm_client,
        decisions_path,
        *,
        text_max_chars: int = 200,
        use_memory: bool = True,
    ):
        self.llm = llm_client
        self.decisions_path = decisions_path
        self.text_max_chars = text_max_chars
        self.use_memory = use_memory

    def decide_cohort(
        self,
        *,
        method: str,
        mean_field_state: Dict[str, Any],
        global_memories: List[Dict[str, Any]],
        cohort_memories: List[Dict[str, Any]],
        representative_profile: Dict[str, Any],
    ) -> Dict[str, Any]:
        cohort_id = mean_field_state["cohort_id"]
        signal_id = str(uuid.uuid4())

        if not self.use_memory:
            global_memories = []
            cohort_memories = []

        user_prompt = build_representative_prompt(
            mean_field_state,
            global_memories,
            cohort_memories,
            representative_profile,
            self.text_max_chars,
        )
        try:
            raw = self.llm.complete_json(
                method=method,
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                meta={
                    "thread_id": mean_field_state.get("thread_id"),
                    "step_id": mean_field_state.get("step_id"),
                    "cohort_id": cohort_id,
                },
            )
            signal = normalize_decision_signal(raw, cohort_id)
        except Exception as exc:
            signal = default_signal(cohort_id, mean_field_state.get("observed_participation_rate", 0.0))
            signal["rationale"] = f"parse/error fallback: {exc}"

        record = {
            "decision_signal_id": signal_id,
            "method": method,
            "thread_id": mean_field_state.get("thread_id"),
            "step_id": mean_field_state.get("step_id"),
            "cohort_id": cohort_id,
            "mean_field_state": mean_field_state,
            "retrieved_global_ids": [m.get("memory_id") for m in global_memories],
            "retrieved_cohort_ids": [m.get("memory_id") for m in cohort_memories],
            "decision_signal": signal,
        }
        append_jsonl(self.decisions_path, record)
        record["signal"] = signal
        return record
