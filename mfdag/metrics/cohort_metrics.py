from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Tuple

import numpy as np
from scipy.spatial.distance import jensenshannon
from scipy.special import rel_entr

from mfdag.utils.io import read_jsonl


def _dist_vector(dist: Dict[str, int], keys: List[str]) -> np.ndarray:
    vals = np.array([float(dist.get(k, 0)) for k in keys], dtype=float)
    s = vals.sum()
    if s == 0:
        return np.ones(len(keys)) / len(keys)
    return vals / s


def compute_cohort_metrics(run_dir) -> Dict[str, Any]:
    transitions = [t for t in read_jsonl(run_dir / "simulation" / "state_transitions.jsonl") if t.get("is_eval")]
    if not transitions:
        transitions = list(read_jsonl(run_dir / "simulation" / "state_transitions.jsonl"))

    js_vals = []
    kl_vals = []
    for t in transitions:
        real = t["real_next_state"]
        sim = t["simulated_next_state"]
        real_cohorts = real.get("participating_cohorts", [])
        sim_dist = sim.get("cohort_distribution", {})
        keys = sorted(set(list(sim_dist.keys()) + real_cohorts))
        if not keys:
            continue
        real_counter = Counter(real_cohorts)
        p = _dist_vector(dict(real_counter), keys)
        q = _dist_vector(sim_dist, keys)
        js = float(jensenshannon(p, q, base=2) ** 2)
        kl = float(np.sum(rel_entr(p + 1e-12, q + 1e-12)))
        js_vals.append(js)
        kl_vals.append(kl)

    return {
        "cohort_js_distance_mean": round(float(np.mean(js_vals)), 4) if js_vals else 0.0,
        "cohort_kl_distance_mean": round(float(np.mean(kl_vals)), 4) if kl_vals else 0.0,
        "eval_steps": len(transitions),
    }
