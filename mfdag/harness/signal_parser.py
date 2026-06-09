from __future__ import annotations

from typing import Any, Dict


def normalize_decision_signal(raw: Dict[str, Any], cohort_id: str) -> Dict[str, Any]:
    participate = float(raw.get("participation_intensity", 0.0))
    action_bias = raw.get("action_bias") or {}
    if not action_bias:
        inactive = max(0.0, 1.0 - participate)
        action_bias = {"participate": participate, "inactive": inactive}
    return {
        "cohort_id": raw.get("cohort_id", cohort_id),
        "participation_intensity": participate,
        "action_bias": action_bias,
        "expected_growth": raw.get("expected_growth", "medium"),
        "attitude_or_interest_shift": raw.get("attitude_or_interest_shift", "stable"),
        "confidence": float(raw.get("confidence", 0.5)),
        "rationale": raw.get("rationale", ""),
    }


def default_signal(cohort_id: str, observed_rate: float) -> Dict[str, Any]:
    p = min(1.0, max(0.0, observed_rate))
    return normalize_decision_signal(
        {
            "cohort_id": cohort_id,
            "participation_intensity": p,
            "action_bias": {"participate": p, "inactive": 1 - p},
            "expected_growth": "medium",
            "attitude_or_interest_shift": "stable",
            "confidence": 0.3,
            "rationale": "fallback signal",
        },
        cohort_id,
    )
