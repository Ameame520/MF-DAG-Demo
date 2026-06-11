from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from mfdag.harness.prompt_builder import SYSTEM_PROMPT, build_representative_prompt
from mfdag.harness.signal_parser import default_signal, normalize_decision_signal
from mfdag.utils.io import append_jsonl

if TYPE_CHECKING:
    from mfdag.utils.timing import StageTimer


class DecisionHarness:
    def __init__(
        self,
        llm_client,
        decisions_path,
        *,
        text_max_chars: int = 200,
        use_memory: bool = True,
        timer: Optional["StageTimer"] = None,
    ):
        self.llm = llm_client
        self.decisions_path = decisions_path
        self.text_max_chars = text_max_chars
        self.use_memory = use_memory
        self.timer = timer

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

        t_prompt = time.perf_counter()
        user_prompt = build_representative_prompt(
            mean_field_state,
            global_memories,
            cohort_memories,
            representative_profile,
            self.text_max_chars,
        )
        prompt_build_s = time.perf_counter() - t_prompt
        if self.timer:
            self.timer.records.append(
                {
                    "stage": "prompt_build",
                    "elapsed_s": round(prompt_build_s, 6),
                    "thread_id": mean_field_state.get("thread_id"),
                    "step_id": mean_field_state.get("step_id"),
                    "cohort_id": cohort_id,
                }
            )
            self.timer.totals["prompt_build"] = self.timer.totals.get("prompt_build", 0.0) + prompt_build_s
            self.timer.counts["prompt_build"] = self.timer.counts.get("prompt_build", 0) + 1

        try:
            if self.timer:
                with self.timer.track(
                    "llm_api_call",
                    thread_id=mean_field_state.get("thread_id"),
                    step_id=mean_field_state.get("step_id"),
                    cohort_id=cohort_id,
                ):
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
            else:
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
            t_parse = time.perf_counter()
            signal = normalize_decision_signal(raw, cohort_id)
            parse_s = time.perf_counter() - t_parse
            if self.timer:
                self.timer.records.append(
                    {
                        "stage": "signal_parse",
                        "elapsed_s": round(parse_s, 6),
                        "thread_id": mean_field_state.get("thread_id"),
                        "step_id": mean_field_state.get("step_id"),
                        "cohort_id": cohort_id,
                    }
                )
                self.timer.totals["signal_parse"] = self.timer.totals.get("signal_parse", 0.0) + parse_s
                self.timer.counts["signal_parse"] = self.timer.counts.get("signal_parse", 0) + 1
        except Exception as exc:
            signal = default_signal(cohort_id, mean_field_state.get("observed_participation_rate", 0.0))
            signal["rationale"] = f"parse/error fallback: {exc}"

        t_log = time.perf_counter()
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
        log_s = time.perf_counter() - t_log
        if self.timer:
            self.timer.records.append(
                {
                    "stage": "decision_log_io",
                    "elapsed_s": round(log_s, 6),
                    "thread_id": mean_field_state.get("thread_id"),
                    "step_id": mean_field_state.get("step_id"),
                    "cohort_id": cohort_id,
                }
            )
            self.timer.totals["decision_log_io"] = self.timer.totals.get("decision_log_io", 0.0) + log_s
            self.timer.counts["decision_log_io"] = self.timer.counts.get("decision_log_io", 0) + 1
        record["signal"] = signal
        return record
