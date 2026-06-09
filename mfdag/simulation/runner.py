from __future__ import annotations

import shutil
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

from mfdag.agents.profile import build_agent_profile
from mfdag.config import processed_dir
from mfdag.data.split import split_threads_by_time
from mfdag.harness.decision_harness import DecisionHarness
from mfdag.mean_field.compressor import MeanFieldCompressor
from mfdag.memory_bank.retrieval import MemoryRetriever
from mfdag.memory_bank.schema import new_memory_event
from mfdag.memory_bank.store import MemoryBank
from mfdag.simulation.transition import (
    build_real_next_state,
    build_simulated_next_state,
    compute_prediction_error,
    log_transition,
)
from mfdag.follower.updater import FollowerUpdater
from mfdag.utils.io import append_jsonl, read_csv, read_jsonl, write_json
from mfdag.utils.llm_client import DeepSeekClient, LLMUsageTracker


def subset_processed_data(
    data: "ProcessedData",
    max_agents: Optional[int] = None,
    max_cohorts: Optional[int] = None,
) -> None:
    runner_stub = object.__new__(SimulationRunner)
    runner_stub.data = data
    if max_cohorts:
        runner_stub._limit_cohorts(max_cohorts)
    if max_agents:
        runner_stub._filter_agents(max_agents, max_cohorts=max_cohorts)


class ProcessedData:
    def __init__(self, cfg: Dict[str, Any]):
        out = processed_dir(cfg)
        self.post_index = {int(r["post_id"]): r for r in read_jsonl(out / "post_index.jsonl")}
        self.threads = read_csv(out / "candidate_threads.csv")
        self.agents = read_csv(out / "agents.csv")
        self.cohort_rows = read_csv(out / "agent_cohorts.csv")
        self.representatives = {r["cohort_id"]: r for r in read_csv(out / "representatives.csv")}
        self.agent_profiles: Dict[str, Dict[str, Any]] = {}
        self.user_to_cohort: Dict[int, str] = {}
        self.cohort_members: Dict[str, List[str]] = defaultdict(list)
        agent_map = {a["agent_id"]: a for a in self.agents}
        for row in self.cohort_rows:
            agent = agent_map[row["agent_id"]]
            profile = build_agent_profile(agent, row["cohort_id"])
            self.agent_profiles[row["agent_id"]] = profile
            self.user_to_cohort[int(row["user_id"])] = row["cohort_id"]
            self.cohort_members[row["cohort_id"]].append(row["agent_id"])


def truncate_text(text: str, max_chars: int) -> str:
    text = (text or "").strip().replace("\n", " ")
    return text[:max_chars] + ("..." if len(text) > max_chars else "")


def build_simulation_steps(thread_row: Dict[str, str], prediction_mode: str) -> List[Dict[str, Any]]:
    pids = [int(x) for x in thread_row["matched_post_ids"].split(",") if x]
    uids = [int(x) for x in thread_row["matched_user_ids"].split(",") if x]
    if len(pids) < 2:
        return []
    steps: List[Dict[str, Any]] = []
    if prediction_mode == "one_step":
        steps.append(
            {
                "step_id": 0,
                "observed_post_ids": pids[:1],
                "observed_user_ids": uids[:1],
                "target_post_id": pids[1],
                "target_user_id": uids[1],
            }
        )
    else:
        for i in range(1, len(pids)):
            steps.append(
                {
                    "step_id": i - 1,
                    "observed_post_ids": pids[:i],
                    "observed_user_ids": uids[:i],
                    "target_post_id": pids[i],
                    "target_user_id": uids[i],
                }
            )
    return steps


class SimulationRunner:
    def __init__(
        self,
        cfg: Dict[str, Any],
        run_dir: Path,
        *,
        method: str = "mfdag",
        use_memory: bool = True,
        use_mean_field: bool = True,
        use_follower: bool = True,
        max_threads: Optional[int] = None,
        max_agents: Optional[int] = None,
        max_cohorts: Optional[int] = None,
    ):
        self.cfg = cfg
        self.run_dir = run_dir
        self.method = method
        self.use_memory = use_memory
        self.use_mean_field = use_mean_field
        self.use_follower = use_follower
        self.data = ProcessedData(cfg)
        self.prediction_mode = cfg["simulation"].get("prediction_mode", "one_step")
        self.text_max_chars = cfg["simulation"].get("prompt_text_max_chars", 200)
        self.eval_ratio = cfg["simulation"].get("eval_ratio", 0.3)
        self.random_seed = cfg["simulation"].get("random_seed", 42)

        if max_cohorts:
            self._limit_cohorts(max_cohorts)
        if max_agents:
            self._filter_agents(max_agents, max_cohorts=max_cohorts)
        threads = sorted(self.data.threads, key=lambda t: t["root_time"])
        if max_threads:
            threads = threads[:max_threads]
        self.threads = threads
        self.cohort_ids = sorted(self.data.cohort_members.keys())

        _, _, self.eval_thread_ids = split_threads_by_time(self.threads, self.eval_ratio)

        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "memory").mkdir(exist_ok=True)
        (run_dir / "decisions").mkdir(exist_ok=True)
        (run_dir / "simulation").mkdir(exist_ok=True)
        (run_dir / "metrics").mkdir(exist_ok=True)

        self.tracker = LLMUsageTracker(log_path=run_dir / "llm_calls.jsonl")
        self.llm = DeepSeekClient(cfg, self.tracker)
        self.compressor = MeanFieldCompressor(self.data.agent_profiles, self.data.cohort_members)
        self.memory_bank = MemoryBank(
            run_dir / "memory" / "memory_events.jsonl",
            run_dir / "memory" / "retrieval_logs.jsonl",
        )
        self.retriever = MemoryRetriever(self.compressor, run_dir / "memory" / "retrieval_logs.jsonl")
        self.harness = DecisionHarness(
            self.llm,
            run_dir / "decisions" / "representative_decisions.jsonl",
            text_max_chars=self.text_max_chars,
            use_memory=self.use_memory,
        )
        self.follower = FollowerUpdater(run_dir / "simulation" / "follower_actions.jsonl", self.random_seed)
        self.mean_field_path = run_dir / "simulation" / "mean_field_states.jsonl"
        self.transition_path = run_dir / "simulation" / "state_transitions.jsonl"
        self.eval_records: List[Dict[str, Any]] = []
        self.t0 = time.time()

    def _limit_cohorts(self, max_cohorts: int) -> None:
        cohort_ids = sorted(self.data.cohort_members.keys())[:max_cohorts]
        kept = set(cohort_ids)
        self.data.cohort_rows = [r for r in self.data.cohort_rows if r["cohort_id"] in kept]
        self.data.cohort_members = defaultdict(list)
        for row in self.data.cohort_rows:
            self.data.cohort_members[row["cohort_id"]].append(row["agent_id"])
        self.data.representatives = {
            k: v for k, v in self.data.representatives.items() if k in kept
        }

    def _filter_agents(self, max_agents: int, max_cohorts: Optional[int] = None) -> None:
        if max_cohorts and max_cohorts > 1:
            per = max(1, max_agents // max_cohorts)
            keep_ids: Set[str] = set()
            agent_map = {a["agent_id"]: a for a in self.data.agents}
            for cohort_id in sorted(self.data.cohort_members.keys()):
                members = sorted(
                    self.data.cohort_members[cohort_id],
                    key=lambda aid: agent_map[aid]["activity_score"] if aid in agent_map else 0,
                    reverse=True,
                )
                keep_ids.update(members[:per])
            if len(keep_ids) < max_agents:
                for a in self.data.agents:
                    if a["agent_id"] not in keep_ids:
                        keep_ids.add(a["agent_id"])
                    if len(keep_ids) >= max_agents:
                        break
        else:
            keep_ids = {a["agent_id"] for a in self.data.agents[:max_agents]}

        self.data.agents = [a for a in self.data.agents if a["agent_id"] in keep_ids]
        self.data.cohort_rows = [r for r in self.data.cohort_rows if r["agent_id"] in keep_ids]
        self.data.agent_profiles = {k: v for k, v in self.data.agent_profiles.items() if k in keep_ids}
        self.data.cohort_members = defaultdict(list)
        self.data.user_to_cohort = {}
        for row in self.data.cohort_rows:
            if row["agent_id"] in keep_ids:
                self.data.cohort_members[row["cohort_id"]].append(row["agent_id"])
                self.data.user_to_cohort[int(row["user_id"])] = row["cohort_id"]

    def run(self) -> Dict[str, Any]:
        mem_cfg = self.cfg["memory"]
        for thread_row in self.threads:
            steps = build_simulation_steps(thread_row, self.prediction_mode)
            for step in steps:
                self._run_step(thread_row, step, mem_cfg)

        runtime = time.time() - self.t0
        summary = {
            "run_id": self.run_dir.name,
            "method": self.method,
            "threads_processed": len(self.threads),
            "eval_threads": len(self.eval_thread_ids),
            "agents": len(self.data.agents),
            "cohorts": len(self.cohort_ids),
            "runtime_s": round(runtime, 2),
            **self.tracker.summary(),
        }
        write_json(self.run_dir / "run_summary.json", summary)
        return summary

    def _run_step(self, thread_row: Dict[str, str], step: Dict[str, Any], mem_cfg: Dict[str, Any]) -> None:
        thread_id = thread_row["thread_id"]
        step_id = step["step_id"]
        observed_users: Set[int] = set(step["observed_user_ids"])
        observed_texts = [
            truncate_text(self.data.post_index[pid].get("text", ""), self.text_max_chars)
            for pid in step["observed_post_ids"]
            if pid in self.data.post_index
        ]
        thread_meta = {
            "thread_len": int(thread_row["thread_len"]),
            "matched_post_count": int(thread_row["matched_post_count"]),
            "join_coverage": float(thread_row["join_coverage"]),
        }

        all_follower_actions: List[Dict[str, Any]] = []
        cohort_signals: Dict[str, Dict[str, Any]] = {}

        for cohort_id in self.cohort_ids:
            mf_state = self.compressor.compress(
                thread_id=thread_id,
                step_id=step_id,
                cohort_id=cohort_id,
                thread_meta=thread_meta,
                observed_user_ids=observed_users,
                observed_post_texts=observed_texts,
            )
            append_jsonl(self.mean_field_path, mf_state)

            retrieved = {"global": [], "cohort": []}
            if self.use_memory and mem_cfg.get("enabled", True):
                retrieved = self.retriever.retrieve_all(
                    self.memory_bank,
                    cohort_id,
                    mf_state,
                    mem_cfg.get("retrieval_top_k_global", 3),
                    mem_cfg.get("retrieval_top_k_cohort", 3),
                    thread_id,
                    step_id,
                )

            rep_row = self.data.representatives.get(cohort_id, {})
            rep_profile = self.data.agent_profiles.get(rep_row.get("agent_id", ""), {})
            decision = self.harness.decide_cohort(
                method=self.method,
                mean_field_state=mf_state,
                global_memories=retrieved["global"],
                cohort_memories=retrieved["cohort"],
                representative_profile=rep_profile,
            )
            signal = decision["decision_signal"]
            cohort_signals[cohort_id] = signal

            if self.use_follower:
                members = [
                    self.data.agent_profiles[aid]
                    for aid in self.data.cohort_members.get(cohort_id, [])
                    if aid in self.data.agent_profiles
                ]
                actions = self.follower.update_followers(
                    thread_id=thread_id,
                    step_id=step_id,
                    cohort_id=cohort_id,
                    decision_signal_id=decision["decision_signal_id"],
                    decision_signal=signal,
                    member_profiles=members,
                    observed_user_ids=observed_users,
                )
                all_follower_actions.extend(actions)

        target_uid = int(step["target_user_id"])
        target_cohort = self.data.user_to_cohort.get(target_uid, "")
        real_next = build_real_next_state(
            target_user_id=target_uid,
            target_cohort_id=target_cohort,
            target_post_id=int(step["target_post_id"]),
        )
        sim_next = build_simulated_next_state(all_follower_actions, self.data.user_to_cohort)
        pred_err = compute_prediction_error(real_next, sim_next)

        transition = {
            "thread_id": thread_id,
            "root_time": thread_row["root_time"],
            "step_id": step_id,
            "method": self.method,
            "is_eval": thread_id in self.eval_thread_ids,
            "real_next_state": real_next,
            "simulated_next_state": sim_next,
            "prediction_error": pred_err,
        }
        log_transition(self.transition_path, transition)
        if thread_id in self.eval_thread_ids:
            self.eval_records.append(transition)

        text_summary = (
            f"Thread {thread_id} step {step_id}: real users={real_next['participation_count']}, "
            f"sim users={sim_next['participation_count']}, f1={pred_err['user_f1']}"
        )
        if self.use_memory and mem_cfg.get("enabled", True):
            self._update_memory(thread_row, step_id, mf_state, cohort_signals, real_next, sim_next, pred_err, text_summary)

        for cohort_id in self.cohort_ids:
            rate = sum(
                1
                for uid in observed_users
                if self.data.user_to_cohort.get(uid) == cohort_id
            ) / max(len(self.data.cohort_members.get(cohort_id, [])), 1)
            self.compressor.record_historical(cohort_id, rate)

    def _update_memory(
        self,
        thread_row: Dict[str, str],
        step_id: int,
        last_mf_state: Dict[str, Any],
        cohort_signals: Dict[str, Dict[str, Any]],
        real_next: Dict[str, Any],
        sim_next: Dict[str, Any],
        pred_err: Dict[str, Any],
        text_summary: str,
    ) -> None:
        feed_name = self.cfg["data"]["feed_name"]
        global_event = new_memory_event(
            memory_type="global",
            memory_subtype="trajectory",
            feed_name=feed_name,
            thread_id=thread_row["thread_id"],
            root_time=thread_row["root_time"],
            step_id=step_id,
            cohort_id=None,
            state_summary=last_mf_state,
            decision_signal={"cohort_signals": cohort_signals},
            real_next_state=real_next,
            simulated_next_state=sim_next,
            prediction_error=pred_err,
            text_summary=text_summary,
        )
        self.memory_bank.add(global_event)
        for cohort_id, signal in cohort_signals.items():
            cohort_event = new_memory_event(
                memory_type="cohort",
                memory_subtype="feedback",
                feed_name=feed_name,
                thread_id=thread_row["thread_id"],
                root_time=thread_row["root_time"],
                step_id=step_id,
                cohort_id=cohort_id,
                state_summary=last_mf_state,
                decision_signal=signal,
                real_next_state=real_next,
                simulated_next_state=sim_next,
                prediction_error=pred_err,
                text_summary=f"Cohort {cohort_id}: {text_summary}",
            )
            self.memory_bank.add(cohort_event)


def create_run_dir(cfg: Dict[str, Any], method: str) -> Path:
    base = Path(cfg["_config_path"]).parent.parent / "outputs" / "runs"
    run_id = f"{method}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    run_dir = base / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(cfg["_config_path"], run_dir / "config.yaml")
    with open(run_dir / "config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, allow_unicode=True)
    return run_dir
