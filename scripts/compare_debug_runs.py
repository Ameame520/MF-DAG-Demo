#!/usr/bin/env python3
"""Aggregate specified run dirs into a debug comparison table."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.run_debug_four_methods import build_comparison_table, load_method_metrics, write_outputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--run", action="append", default=[], help="label=path e.g. mfdag=outputs/runs/...")
    parser.add_argument("--skip", action="append", default=[], help="label to mark skipped")
    args = parser.parse_args()

    rows = []
    for item in args.run:
        label, _, path = item.partition("=")
        run_dir = Path(path)
        if not run_dir.is_absolute():
            run_dir = ROOT / run_dir
        row = load_method_metrics(run_dir)
        row["label"] = label
        row["key"] = row.get("method", label)
        rows.append(row)

    for label in args.skip:
        rows.append({
            "label": label,
            "method": label.lower().replace(" ", "_").replace("-", "_"),
            "status": "skipped",
            "error": "skipped by user request",
        })

    comparison = build_comparison_table([r for r in rows if r.get("status") == "success"])
    comparison["methods"] = rows
    comparison["batch_params"] = {
        "debug_threads": 20,
        "debug_agents": 20,
        "debug_cohorts": 2,
    }
    comparison["note"] = "Full LLM-Agent and Rule-based skipped; comparison based on completed runs only."
    write_outputs(Path(args.out_dir), comparison)
    print(f"Written: {args.out_dir}")


if __name__ == "__main__":
    main()
