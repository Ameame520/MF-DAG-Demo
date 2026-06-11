from __future__ import annotations

import math
import random
from collections import defaultdict
from typing import Any, Dict, List, Set, Tuple


def assign_activity_level(score: float, scores_sorted: List[float]) -> str:
    if not scores_sorted:
        return "middle"
    n = len(scores_sorted)
    high_thresh = scores_sorted[int(n * 0.67)] if n > 2 else scores_sorted[-1]
    low_thresh = scores_sorted[int(n * 0.33)] if n > 2 else scores_sorted[0]
    if score >= high_thresh:
        return "high"
    if score >= low_thresh:
        return "middle"
    return "low"


def build_agents(
    candidate_threads: List[Dict],
    user_post_count: Dict[int, int],
    user_stats: Dict[int, Dict[str, Any]],
    user_matched_counts: Dict[int, int],
    *,
    target_agent_count: int | None = None,
    use_all_available: bool = True,
    sampling_strategy: str = "stratified_by_activity",
    random_seed: int = 42,
) -> List[Dict[str, Any]]:
    candidate_users: Set[int] = set()
    for row in candidate_threads:
        for uid in row["matched_user_ids"].split(","):
            if uid.strip():
                candidate_users.add(int(uid))

    rows: List[Dict[str, Any]] = []
    for uid in candidate_users:
        stats = user_stats.get(uid, {})
        post_count = user_post_count.get(uid, 0)
        matched_cnt = user_matched_counts.get(uid, 0)
        like_sum = int(stats.get("like_count_sum", 0))
        reply_sum = int(stats.get("reply_count_sum", 0))
        repost_sum = int(stats.get("repost_count_sum", 0))
        quote_cnt = int(stats.get("quote_count", 0))
        engagement = like_sum + reply_sum + repost_sum
        activity_score = post_count + matched_cnt + math.log1p(engagement)
        rows.append(
            {
                "user_id": uid,
                "post_count": post_count,
                "matched_thread_post_count": matched_cnt,
                "activity_score": round(activity_score, 4),
                "reply_count_sum": reply_sum,
                "repost_count_sum": repost_sum,
                "like_count_sum": like_sum,
                "quote_count": quote_cnt,
            }
        )

    rows.sort(key=lambda r: r["activity_score"], reverse=True)
    scores_sorted = sorted(r["activity_score"] for r in rows)

    if not use_all_available and target_agent_count:
        rows = _sample_agents(rows, target_agent_count, sampling_strategy, random_seed)

    for i, row in enumerate(rows):
        row["agent_id"] = f"A{i:04d}"
        row["activity_level"] = assign_activity_level(row["activity_score"], scores_sorted)
    return rows


def _sample_agents(
    rows: List[Dict[str, Any]],
    target: int,
    strategy: str,
    seed: int,
) -> List[Dict[str, Any]]:
    if len(rows) <= target:
        return rows
    rng = random.Random(seed)
    if strategy != "stratified_by_activity":
        return rng.sample(rows, target)

    by_level: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    scores_sorted = sorted(r["activity_score"] for r in rows)
    for r in rows:
        level = assign_activity_level(r["activity_score"], scores_sorted)
        by_level[level].append(r)

    selected: List[Dict[str, Any]] = []
    levels = ["high", "middle", "low"]
    per = max(1, target // len(levels))
    for level in levels:
        pool = by_level[level]
        k = min(per, len(pool))
        selected.extend(rng.sample(pool, k))
    if len(selected) < target:
        remaining = [r for r in rows if r not in selected]
        need = min(target - len(selected), len(remaining))
        selected.extend(rng.sample(remaining, need))
    return selected[:target]


def compute_user_matched_counts(candidate_threads: List[Dict]) -> Dict[int, int]:
    counts: Dict[int, int] = defaultdict(int)
    for row in candidate_threads:
        for uid in row["matched_user_ids"].split(","):
            if uid.strip():
                counts[int(uid)] += 1
    return dict(counts)
