from __future__ import annotations

import statistics
from typing import Any, Dict, List

from mfdag.utils.io import read_jsonl


def compute_propagation_metrics(run_dir) -> Dict[str, Any]:
    transitions = [t for t in read_jsonl(run_dir / "simulation" / "state_transitions.jsonl") if t.get("is_eval")]
    if not transitions:
        transitions = list(read_jsonl(run_dir / "simulation" / "state_transitions.jsonl"))
    size_errors = []
    f1s = []
    recalls = []
    for t in transitions:
        err = t.get("prediction_error", {})
        size_errors.append(float(err.get("continuation_size_error", 0)))
        f1s.append(float(err.get("user_f1", 0)))
        recalls.append(float(err.get("user_recall", 0)))
    return {
        "eval_steps": len(transitions),
        "continuation_size_mae": round(statistics.mean(size_errors), 4) if size_errors else 0.0,
        "continuation_size_rmse": round(
            (statistics.mean([e * e for e in size_errors]) ** 0.5) if size_errors else 0.0,
            4,
        ),
        "user_f1_mean": round(statistics.mean(f1s), 4) if f1s else 0.0,
        "user_recall_mean": round(statistics.mean(recalls), 4) if recalls else 0.0,
    }
