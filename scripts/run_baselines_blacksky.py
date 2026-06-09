#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mfdag.baselines.full_llm_agent import FullLLMAgentBaseline
from mfdag.baselines.mean_field_llm import run_mean_field_llm
from mfdag.baselines.rule_based_agent import RuleBasedAgentBaseline
from mfdag.config import load_config
from mfdag.data.split import split_threads_by_time
from mfdag.metrics.report import evaluate_run
from mfdag.simulation.runner import ProcessedData, create_run_dir, subset_processed_data
from mfdag.utils.logging import setup_logger


def main() -> None:
    parser = argparse.ArgumentParser(description="Run MF-DAG baselines on Blacksky")
    parser.add_argument("--config", default="configs/mfdag_blacksky.yaml")
    parser.add_argument(
        "--baseline",
        required=True,
        choices=["full_llm_agent", "mean_field_llm", "rule_based_agent"],
    )
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--debug_threads", type=int, default=None)
    parser.add_argument("--debug_agents", type=int, default=None)
    parser.add_argument("--debug_cohorts", type=int, default=None)
    parser.add_argument("--run_dir", default=None)
    args = parser.parse_args()

    cfg = load_config(ROOT / args.config)
    logger = setup_logger("run_baselines_blacksky")
    data = ProcessedData(cfg)

    max_threads = None
    max_agents = None
    max_cohorts = None
    if args.debug or cfg.get("debug", {}).get("enabled"):
        dbg = cfg.get("debug", {})
        max_threads = args.debug_threads or dbg.get("debug_threads", 20)
        max_agents = args.debug_agents or dbg.get("debug_agents", 20)
        max_cohorts = args.debug_cohorts or dbg.get("debug_cohorts", 2)
    elif args.baseline == "full_llm_agent":
        max_threads = cfg.get("baselines", {}).get("full_llm_agent_max_threads", 100)

    threads = sorted(data.threads, key=lambda t: t["root_time"])
    if max_threads:
        threads = threads[:max_threads]

    if max_agents or max_cohorts:
        subset_processed_data(data, max_agents=max_agents, max_cohorts=max_cohorts)

    _, _, eval_ids = split_threads_by_time(threads, cfg["simulation"].get("eval_ratio", 0.3))
    run_dir = Path(args.run_dir) if args.run_dir else create_run_dir(cfg, args.baseline)

    if args.baseline == "mean_field_llm":
        summary = run_mean_field_llm(
            cfg,
            run_dir,
            max_threads=max_threads,
            max_agents=max_agents,
            max_cohorts=max_cohorts,
        )
    elif args.baseline == "full_llm_agent":
        runner = FullLLMAgentBaseline(cfg, run_dir, data, threads, eval_ids)
        summary = runner.run()
    else:
        runner = RuleBasedAgentBaseline(cfg, run_dir, data, threads, eval_ids)
        summary = runner.run()

    logger.info("Baseline complete: %s", summary)
    metrics = evaluate_run(run_dir)
    logger.info("Metrics: %s", metrics)


if __name__ == "__main__":
    main()
