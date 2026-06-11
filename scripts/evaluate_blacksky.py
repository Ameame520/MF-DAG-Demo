#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mfdag.metrics.report import evaluate_run
from mfdag.utils.logging import setup_logger


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate MF-DAG Blacksky run")
    parser.add_argument("--run_dir", required=True)
    parser.add_argument("--baseline_dir", action="append", default=[])
    args = parser.parse_args()

    logger = setup_logger("evaluate_blacksky")
    baseline_dirs = [Path(p) for p in args.baseline_dir]
    metrics = evaluate_run(Path(args.run_dir), baseline_dirs=baseline_dirs or None)
    logger.info("Evaluation complete: %s", metrics)


if __name__ == "__main__":
    main()
