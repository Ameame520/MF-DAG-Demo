#!/usr/bin/env python3
"""Run 4-method debug comparison and produce summary table."""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mfdag.metrics.efficiency import compare_efficiency, load_efficiency
from mfdag.utils.io import read_json, write_json

DEBUG_ARGS = ["--debug", "--debug_threads", "20", "--debug_agents", "20", "--debug_cohorts", "2"]

METHODS = [
    {
        "key": "mfdag",
        "label": "MF-DAG",
        "required": True,
        "cmd": [sys.executable, "scripts/run_mfdag_blacksky.py"],
    },
    {
        "key": "mean_field_llm",
        "label": "Mean-Field-LLM",
        "required": False,
        "cmd": [sys.executable, "scripts/run_baselines_blacksky.py", "--baseline", "mean_field_llm"],
    },
    {
        "key": "full_llm_agent",
        "label": "Full LLM-Agent",
        "required": False,
        "cmd": [sys.executable, "scripts/run_baselines_blacksky.py", "--baseline", "full_llm_agent"],
    },
    {
        "key": "rule_based_agent",
        "label": "Rule-based Agent",
        "required": False,
        "cmd": [sys.executable, "scripts/run_baselines_blacksky.py", "--baseline", "rule_based_agent"],
    },
]


def latest_run_dir(method_key: str, after_ts: float) -> Optional[Path]:
    runs = ROOT / "outputs" / "runs"
    if not runs.exists():
        return None
    candidates = [
        p for p in runs.iterdir()
        if p.is_dir() and p.name.startswith(f"{method_key}_") and p.stat().st_mtime >= after_ts - 5
    ]
    if not candidates:
        candidates = sorted(
            [p for p in runs.iterdir() if p.is_dir() and p.name.startswith(f"{method_key}_")],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return candidates[0] if candidates else None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def load_method_metrics(run_dir: Path) -> Dict[str, Any]:
    summary = read_json(run_dir / "run_summary.json")
    metrics = read_json(run_dir / "metrics" / "metrics_summary.json")
    eff = metrics.get("efficiency_metrics", {})
    prop = metrics.get("propagation_metrics", {})
    cohort = metrics.get("cohort_metrics", {})
    return {
        "run_dir": str(run_dir),
        "run_id": run_dir.name,
        "method": summary.get("method"),
        "status": "success",
        "llm_calls": eff.get("llm_calls", 0),
        "input_tokens": eff.get("input_tokens", 0),
        "output_tokens": eff.get("output_tokens", 0),
        "total_tokens": eff.get("total_tokens", 0),
        "runtime_s": eff.get("runtime_s", 0),
        "threads_processed": eff.get("threads_processed", 0),
        "avg_runtime_per_thread": eff.get("avg_runtime_per_thread", 0),
        "eval_steps": prop.get("eval_steps", 0),
        "continuation_size_mae": prop.get("continuation_size_mae", 0),
        "continuation_size_rmse": prop.get("continuation_size_rmse", 0),
        "user_f1_mean": prop.get("user_f1_mean", 0),
        "user_recall_mean": prop.get("user_recall_mean", 0),
        "cohort_js_distance_mean": cohort.get("cohort_js_distance_mean", 0),
        "cohort_kl_distance_mean": cohort.get("cohort_kl_distance_mean", 0),
    }


def build_comparison_table(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    mfdag = next((r for r in rows if r.get("method") == "mfdag" and r.get("status") == "success"), None)
    full_llm = next((r for r in rows if r.get("method") == "full_llm_agent" and r.get("status") == "success"), None)
    comparison: Dict[str, Any] = {"methods": rows}
    if mfdag and full_llm:
        eff_cmp = compare_efficiency([full_llm], mfdag)
        comparison["mfdag_vs_full_llm"] = {
            "llm_call_reduction_ratio": eff_cmp.get("llm_call_reduction_ratio"),
            "token_reduction_ratio": eff_cmp.get("token_reduction_ratio"),
        }
    if mfdag:
        mf_llm = next((r for r in rows if r.get("method") == "mean_field_llm" and r.get("status") == "success"), None)
        if mf_llm:
            comparison["mfdag_vs_mean_field_llm"] = {
                "user_f1_delta": round(mfdag["user_f1_mean"] - mf_llm["user_f1_mean"], 4),
                "size_mae_delta": round(mfdag["continuation_size_mae"] - mf_llm["continuation_size_mae"], 4),
                "cohort_js_delta": round(mfdag["cohort_js_distance_mean"] - mf_llm["cohort_js_distance_mean"], 4),
                "llm_calls_same": mfdag["llm_calls"] == mf_llm["llm_calls"],
            }
    return comparison


def write_outputs(out_dir: Path, comparison: Dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = comparison["methods"]
    fieldnames = [
        "label", "method", "status", "run_id", "llm_calls", "total_tokens", "runtime_s",
        "threads_processed", "eval_steps", "continuation_size_mae", "continuation_size_rmse",
        "user_f1_mean", "user_recall_mean", "cohort_js_distance_mean", "cohort_kl_distance_mean", "run_dir", "error",
    ]
    with open(out_dir / "debug_four_methods_comparison.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({**r, "label": r.get("label", r.get("method"))})

    write_json(out_dir / "debug_four_methods_comparison.json", comparison)

    lines = [
        "# Debug Four-Methods Comparison",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "Parameters: `--debug --debug_threads 20 --debug_agents 20 --debug_cohorts 2`",
        "",
        "## Summary Table",
        "",
        "| Method | Status | LLM Calls | Tokens | Runtime(s) | Size MAE | User F1 | Cohort JS | Cohort KL |",
        "|--------|--------|-----------|--------|------------|----------|---------|-----------|-----------|",
    ]
    for r in rows:
        lines.append(
            f"| {r.get('label', r.get('method'))} | {r.get('status')} | {r.get('llm_calls', '-')} | "
            f"{r.get('total_tokens', '-')} | {r.get('runtime_s', '-')} | "
            f"{r.get('continuation_size_mae', '-')} | {r.get('user_f1_mean', '-')} | "
            f"{r.get('cohort_js_distance_mean', '-')} | {r.get('cohort_kl_distance_mean', '-')} |"
        )
    if comparison.get("mfdag_vs_full_llm"):
        c = comparison["mfdag_vs_full_llm"]
        lines.extend([
            "",
            "## MF-DAG vs Full LLM-Agent",
            f"- LLM call reduction: {c.get('llm_call_reduction_ratio')}",
            f"- Token reduction: {c.get('token_reduction_ratio')}",
        ])
    if comparison.get("mfdag_vs_mean_field_llm"):
        c = comparison["mfdag_vs_mean_field_llm"]
        lines.extend([
            "",
            "## MF-DAG vs Mean-Field-LLM (memory value)",
            f"- User F1 delta (MF-DAG - MF-LLM): {c.get('user_f1_delta')}",
            f"- Size MAE delta: {c.get('size_mae_delta')}",
            f"- Cohort JS delta: {c.get('cohort_js_delta')}",
        ])
    lines.extend([
        "",
        "## Run Directories",
        "",
    ])
    for r in rows:
        lines.append(f"- **{r.get('label')}**: `{r.get('run_dir', 'N/A')}` ({r.get('status')})")
        if r.get("error"):
            lines.append(f"  - Error: {r['error']}")
    lines.extend([
        "",
        "## Notes",
        "- Metrics computed on eval split (last 30% threads, ~6 steps for 20 threads).",
        "- `user_f1` may be 0 under one_step setting when sim predicts many users but real next user is exactly 1.",
        "- Prefer `continuation_size_mae` and cohort JS/KL for interpretation.",
    ])
    (out_dir / "debug_four_methods_comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/mfdag_blacksky.yaml")
    parser.add_argument("--skip-run", action="store_true", help="Only aggregate existing runs")
    args = parser.parse_args()

    config_path = str(ROOT / args.config)
    results: List[Dict[str, Any]] = []
    batch_ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "outputs" / "comparisons" / f"debug_four_methods_{batch_ts}"
    start_time = __import__("time").time()

    if not args.skip_run:
        for spec in METHODS:
            row: Dict[str, Any] = {"key": spec["key"], "label": spec["label"], "method": spec["key"], "status": "pending"}
            cmd = spec["cmd"] + ["--config", config_path] + DEBUG_ARGS
            print(f"\n{'='*60}\nRunning {spec['label']}...\n{'='*60}", flush=True)
            t0 = __import__("time").time()
            try:
                proc = subprocess.run(cmd, cwd=ROOT, capture_output=False)
                if proc.returncode != 0:
                    raise RuntimeError(f"exit code {proc.returncode}")
                run_dir = latest_run_dir(spec["key"], t0)
                if run_dir is None:
                    raise RuntimeError("no run directory found")
                row.update(load_method_metrics(run_dir))
                row["status"] = "success"
                print(f"OK: {spec['label']} -> {run_dir}", flush=True)
            except Exception as exc:
                row["status"] = "failed"
                row["error"] = str(exc)
                print(f"FAILED: {spec['label']}: {exc}", flush=True)
                if spec["required"]:
                    results.append(row)
                    comparison = build_comparison_table(results)
                    write_outputs(out_dir, comparison)
                    print(f"\nMF-DAG (required) failed. Partial results: {out_dir}", flush=True)
                    sys.exit(1)
            results.append(row)

    else:
        for spec in METHODS:
            run_dir = latest_run_dir(spec["key"], start_time + 1e9)
            row = {"key": spec["key"], "label": spec["label"], "method": spec["key"]}
            if run_dir and (run_dir / "metrics" / "metrics_summary.json").exists():
                row.update(load_method_metrics(run_dir))
                row["status"] = "success"
            else:
                row["status"] = "not_found"
            results.append(row)

    comparison = build_comparison_table(results)
    comparison["batch_params"] = {
        "debug_threads": 20,
        "debug_agents": 20,
        "debug_cohorts": 2,
    }
    comparison["total_batch_runtime_s"] = round(__import__("time").time() - start_time, 2)
    write_outputs(out_dir, comparison)
    print(f"\nComparison written to: {out_dir}", flush=True)


if __name__ == "__main__":
    main()
