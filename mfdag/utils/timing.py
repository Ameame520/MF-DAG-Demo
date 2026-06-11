from __future__ import annotations

import statistics
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional


@dataclass
class StageTimer:
    """Accumulate per-stage wall-clock timings for profiling."""

    records: List[Dict[str, Any]] = field(default_factory=list)
    totals: Dict[str, float] = field(default_factory=dict)
    counts: Dict[str, int] = field(default_factory=dict)

    @contextmanager
    def track(
        self,
        stage: str,
        *,
        thread_id: Optional[str] = None,
        step_id: Optional[int] = None,
        cohort_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Iterator[None]:
        t0 = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - t0
            self.totals[stage] = self.totals.get(stage, 0.0) + elapsed
            self.counts[stage] = self.counts.get(stage, 0) + 1
            rec: Dict[str, Any] = {
                "stage": stage,
                "elapsed_s": round(elapsed, 6),
                "thread_id": thread_id,
                "step_id": step_id,
                "cohort_id": cohort_id,
            }
            if extra:
                rec.update(extra)
            self.records.append(rec)

    def summary(self, total_runtime_s: Optional[float] = None) -> Dict[str, Any]:
        grand = sum(self.totals.values())
        if total_runtime_s is None:
            total_runtime_s = grand
        stages: List[Dict[str, Any]] = []
        for stage, total in sorted(self.totals.items(), key=lambda x: x[1], reverse=True):
            times = [r["elapsed_s"] for r in self.records if r["stage"] == stage]
            stages.append(
                {
                    "stage": stage,
                    "total_s": round(total, 4),
                    "count": self.counts.get(stage, 0),
                    "mean_s": round(total / max(self.counts.get(stage, 1), 1), 4),
                    "median_s": round(statistics.median(times), 4) if times else 0.0,
                    "max_s": round(max(times), 4) if times else 0.0,
                    "pct_of_tracked": round(100 * total / grand, 2) if grand else 0.0,
                    "pct_of_runtime": round(100 * total / total_runtime_s, 2) if total_runtime_s else 0.0,
                }
            )
        return {
            "tracked_total_s": round(grand, 4),
            "wall_runtime_s": round(total_runtime_s, 4) if total_runtime_s else None,
            "untracked_s": round(max(0.0, (total_runtime_s or grand) - grand), 4),
            "stages": stages,
        }
