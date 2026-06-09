#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mfdag.config import load_config
from mfdag.metrics.report import evaluate_run
from mfdag.simulation.runner import SimulationRunner, create_run_dir
from mfdag.utils.logging import setup_logger


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Full MF-DAG on Blacksky")
    parser.add_argument("--config", default="configs/mfdag_blacksky.yaml")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--debug_threads", type=int, default=None)
    parser.add_argument("--debug_agents", type=int, default=None)
    parser.add_argument("--debug_cohorts", type=int, default=None)
    parser.add_argument("--run_dir", default=None)
    args = parser.parse_args()

    cfg = load_config(ROOT / args.config)
    logger = setup_logger("run_mfdag_blacksky")

    max_threads = None
    max_agents = None
    max_cohorts = None
    if args.debug or cfg.get("debug", {}).get("enabled"):
        dbg = cfg.get("debug", {})
        max_threads = args.debug_threads or dbg.get("debug_threads", 20)
        max_agents = args.debug_agents or dbg.get("debug_agents", 20)
        max_cohorts = args.debug_cohorts or dbg.get("debug_cohorts", 2)
        logger.info("Debug mode: threads=%s agents=%s cohorts=%s", max_threads, max_agents, max_cohorts)

    run_dir = Path(args.run_dir) if args.run_dir else create_run_dir(cfg, "mfdag")
    runner = SimulationRunner(
        cfg,
        run_dir,
        method="mfdag",
        use_memory=True,
        use_mean_field=True,
        use_follower=True,
        max_threads=max_threads,
        max_agents=max_agents,
        max_cohorts=max_cohorts,
    )
    summary = runner.run()
    logger.info("Run complete: %s", summary)
    metrics = evaluate_run(run_dir)
    logger.info("Metrics: %s", metrics)


if __name__ == "__main__":
    main()
