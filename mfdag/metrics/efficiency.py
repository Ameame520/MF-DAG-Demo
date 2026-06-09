from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from mfdag.utils.io import read_json


def load_efficiency(run_dir: Path) -> Dict[str, Any]:
    summary = read_json(run_dir / "run_summary.json")
    return {
        "method": summary.get("method"),
        "llm_calls": summary.get("llm_calls", 0),
        "input_tokens": summary.get("input_tokens", 0),
        "output_tokens": summary.get("output_tokens", 0),
        "total_tokens": summary.get("total_tokens", 0),
        "runtime_s": summary.get("runtime_s", 0),
        "threads_processed": summary.get("threads_processed", 0),
        "avg_runtime_per_thread": round(
            summary.get("runtime_s", 0) / max(summary.get("threads_processed", 1), 1), 4
        ),
    }


def compare_efficiency(baseline_runs: List[Dict[str, Any]], mfdag_run: Dict[str, Any]) -> Dict[str, Any]:
    full_llm = next((r for r in baseline_runs if r.get("method") == "full_llm_agent"), None)
    out = {"mfdag": mfdag_run}
    if full_llm and mfdag_run.get("llm_calls"):
        out["llm_call_reduction_ratio"] = round(
            1 - mfdag_run["llm_calls"] / max(full_llm.get("llm_calls", 1), 1), 4
        )
        out["token_reduction_ratio"] = round(
            1 - mfdag_run.get("total_tokens", 0) / max(full_llm.get("total_tokens", 1), 1), 4
        )
    return out
