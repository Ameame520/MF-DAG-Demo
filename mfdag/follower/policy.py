from __future__ import annotations

import random
from typing import Any, Dict


def participation_probability(
    agent_profile: Dict[str, Any],
    decision_signal: Dict[str, Any],
    *,
    already_participated: bool,
    random_seed: int,
) -> float:
    base = float(decision_signal.get("participation_intensity", 0.0))
    action_bias = decision_signal.get("action_bias") or {}
    base = float(action_bias.get("participate", base))

    score = agent_profile.get("activity_score", 0.0)
    score_factor = min(1.5, 0.5 + score / 20.0)
    p = base * score_factor
    if already_participated:
        p = min(1.0, p * 1.2)
    p = max(0.0, min(1.0, p))
    return p


def sample_action(probability: float, rng: random.Random) -> str:
    return "participate" if rng.random() < probability else "inactive"
