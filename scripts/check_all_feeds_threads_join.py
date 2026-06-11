#!/usr/bin/env python3
"""
批量检查所有 feed_posts 与 threads.txt 的 post_id join 覆盖率，并推荐最适合 MF-DAG 主实验的 feed。

流程：
  1. 载入 feed_posts/feed_posts/*.jsonl.gz，建立 post_id -> feed/user 全局索引
  2. 单次流式扫描 threads.txt，对每个 feed / 合并方案累计 join 统计
  3. 排名、输出 Markdown / JSON / CSV 报告
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# 复用单 feed 检查脚本中的公共逻辑
from check_news_threads_join import (
    AGENT_TARGET,
    CONDITIONS,
    ConditionAccumulator,
    assign_activity_level,
    open_text_maybe_gzip,
    parse_thread_line,
    percentile_threshold,
    resolve_threads_path,
    summarize_distribution,
)


# 合并 feed 方案（名称 -> feed 列表）
MERGED_FEED_PLANS: Dict[str, List[str]] = {
    "Science + AcademicSky": ["Science", "AcademicSky"],
    "Science + News": ["Science", "News"],
    "AcademicSky + Science + News": ["AcademicSky", "Science", "News"],
    "Blacksky": ["Blacksky"],
    "All feeds merged": [],  # 空列表表示全部 feed
}

PRIMARY_USER_CONDITION = "condition_1"
RANKING_CONDITIONS = ("condition_2", "condition_3")


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------
@dataclass
class FeedJoinState:
    """单个 feed 或合并方案在 threads 扫描过程中的累计状态。"""

    name: str
    post_ids: Set[int] = field(default_factory=set)
    matched_posts: Set[int] = field(default_factory=set)
    threads_hit_1: int = 0
    threads_hit_2: int = 0
    threads_hit_3: int = 0
    threads_hit_5: int = 0
    condition_acc: Dict[str, ConditionAccumulator] = field(default_factory=dict)
    user_matched_counts: Dict[int, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.condition_acc:
            self.condition_acc = {n: ConditionAccumulator() for n in CONDITIONS}

    def record_thread(
        self,
        thread_len: int,
        matched_post_ids: List[int],
        post_to_user: Dict[int, int],
    ) -> None:
        matched_count = len(matched_post_ids)
        coverage = matched_count / thread_len if thread_len > 0 else 0.0

        for pid in matched_post_ids:
            self.matched_posts.add(pid)

        if matched_count >= 1:
            self.threads_hit_1 += 1
        if matched_count >= 2:
            self.threads_hit_2 += 1
        if matched_count >= 3:
            self.threads_hit_3 += 1
        if matched_count >= 5:
            self.threads_hit_5 += 1

        matched_users: Set[int] = set()
        for pid in matched_post_ids:
            uid = post_to_user.get(pid)
            if uid is not None:
                matched_users.add(uid)

        for cname, predicate in CONDITIONS.items():
            if predicate(thread_len, matched_count, coverage):
                self.condition_acc[cname].add(
                    thread_len, matched_count, coverage, matched_users
                )

        # condition_1 用户活跃度：累计 matched post 出现次数
        if CONDITIONS[PRIMARY_USER_CONDITION](thread_len, matched_count, coverage):
            for pid in matched_post_ids:
                uid = post_to_user.get(pid)
                if uid is not None:
                    self.user_matched_counts[uid] = (
                        self.user_matched_counts.get(uid, 0) + 1
                    )


# ---------------------------------------------------------------------------
# Step 1: 载入所有 feed
# ---------------------------------------------------------------------------
def feed_name_from_path(path: Path) -> str:
    """从 .jsonl.gz 文件名提取 feed 名称（去掉后缀）。"""
    return path.name[: -len(".jsonl.gz")] if path.name.endswith(".jsonl.gz") else path.stem


def discover_feed_files(feed_dir: Path) -> List[Path]:
    return sorted(feed_dir.glob("*.jsonl.gz"))


def load_feed_posts(feed_path: Path) -> Tuple[Dict[int, Dict[str, Any]], Dict[str, Any]]:
    """读取单个 feed，返回 post_id -> record 与基础统计。"""
    import statistics

    feed_name = feed_name_from_path(feed_path)
    posts: Dict[int, Dict[str, Any]] = {}
    like_counts: List[int] = []
    reply_counts: List[int] = []
    repost_counts: List[int] = []
    dates: List[int] = []
    user_ids: Set[int] = set()
    text_nonempty = 0
    reply_to_nonempty = 0
    quotes_nonempty = 0
    total_lines = 0

    with gzip.open(feed_path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total_lines += 1
            rec = json.loads(line)
            post_id = int(rec["post_id"])
            user_id = int(rec["user_id"])
            posts[post_id] = rec
            user_ids.add(user_id)

            if str(rec.get("text") or "").strip():
                text_nonempty += 1
            if rec.get("reply_to") is not None:
                reply_to_nonempty += 1
            if rec.get("quotes") is not None:
                quotes_nonempty += 1

            like_counts.append(int(rec.get("like_count") or 0))
            reply_counts.append(int(rec.get("reply_count") or 0))
            repost_counts.append(int(rec.get("repost_count") or 0))
            dates.append(int(rec.get("date") or 0))

    def count_stats(vals: List[int]) -> Dict[str, Any]:
        return {
            "mean": round(statistics.mean(vals), 2) if vals else None,
            "median": statistics.median(vals) if vals else None,
            "max": max(vals) if vals else None,
        }

    stats = {
        "feed_name": feed_name,
        "feed_path": str(feed_path),
        "total_posts": total_lines,
        "unique_post_ids": len(posts),
        "unique_user_ids": len(user_ids),
        "date_min": min(dates) if dates else None,
        "date_max": max(dates) if dates else None,
        "text_nonempty_count": text_nonempty,
        "text_nonempty_ratio": round(text_nonempty / total_lines, 4) if total_lines else 0,
        "reply_to_nonempty_count": reply_to_nonempty,
        "quotes_nonempty_count": quotes_nonempty,
        "like_count": count_stats(like_counts),
        "reply_count": count_stats(reply_counts),
        "repost_count": count_stats(repost_counts),
    }
    return posts, stats


def load_all_feeds(feed_dir: Path) -> Tuple[Dict[str, Dict[int, Dict]], Dict[str, Dict]]:
    """载入目录下全部 feed，返回 feed_name -> posts 与 feed_name -> stats。"""
    all_posts: Dict[str, Dict[int, Dict[str, Any]]] = {}
    all_stats: Dict[str, Dict[str, Any]] = {}
    for fp in discover_feed_files(feed_dir):
        posts, stats = load_feed_posts(fp)
        name = stats["feed_name"]
        all_posts[name] = posts
        all_stats[name] = stats
        print(f"  载入 feed [{name}]: {len(posts):,} unique posts, "
              f"{stats['unique_user_ids']:,} users")
    return all_posts, all_stats


def build_global_index(
    all_posts: Dict[str, Dict[int, Dict[str, Any]]],
) -> Tuple[Dict[int, int], Dict[int, Set[str]]]:
    """
    建立全局 post_id -> user_id 与 post_id -> feed_names 索引。
    同一 post_id 若出现在多个 feed（极少），记录全部 feed。
    """
    post_to_user: Dict[int, int] = {}
    post_to_feeds: Dict[int, Set[str]] = defaultdict(set)
    for feed_name, posts in all_posts.items():
        for pid, rec in posts.items():
            post_to_user[pid] = int(rec["user_id"])
            post_to_feeds[pid].add(feed_name)
    return post_to_user, dict(post_to_feeds)


def build_join_states(
    all_posts: Dict[str, Dict[int, Dict[str, Any]]],
    merged_plans: Dict[str, List[str]],
) -> Tuple[Dict[str, FeedJoinState], Dict[str, FeedJoinState]]:
    """为每个单 feed 与每个合并方案初始化 FeedJoinState。"""
    feed_states = {
        name: FeedJoinState(name=name, post_ids=set(posts.keys()))
        for name, posts in all_posts.items()
    }

    all_feed_names = list(all_posts.keys())
    merged_states: Dict[str, FeedJoinState] = {}
    for plan_name, members in merged_plans.items():
        if not members:
            members = all_feed_names
        post_ids: Set[int] = set()
        for m in members:
            if m in all_posts:
                post_ids.update(all_posts[m].keys())
        merged_states[plan_name] = FeedJoinState(name=plan_name, post_ids=post_ids)

    return feed_states, merged_states


# ---------------------------------------------------------------------------
# Step 2: 单次流式扫描 threads.txt
# ---------------------------------------------------------------------------
def scan_threads_all_feeds(
    threads_path: Path,
    is_gzip: bool,
    post_to_user: Dict[int, int],
    post_to_feeds: Dict[int, Set[str]],
    feed_states: Dict[str, FeedJoinState],
    merged_states: Dict[str, FeedJoinState],
    progress_every: int = 500_000,
) -> int:
    """
    单次流式扫描 threads.txt，同时更新所有 feed / 合并方案统计。
    返回扫描的有效 thread 总数。
    """
    global_post_ids = set(post_to_user.keys())
    total_threads = 0

    # 合并方案：post_id 属于哪些 plan（预计算加速）
    merged_post_to_plans: Dict[int, List[str]] = defaultdict(list)
    for plan_name, state in merged_states.items():
        for pid in state.post_ids:
            merged_post_to_plans[pid].append(plan_name)

    with open_text_maybe_gzip(threads_path, is_gzip) as f:
        for line_no, line in enumerate(f, 1):
            parsed = parse_thread_line(line)
            if parsed is None:
                continue

            _, _, post_ids = parsed
            thread_len = len(post_ids)
            total_threads += 1

            # 本 thread 命中的全局 feed posts
            matched_global: List[int] = [pid for pid in post_ids if pid in global_post_ids]
            if not matched_global:
                if progress_every and line_no % progress_every == 0:
                    print(
                        f"  [进度] 行 {line_no:,} | threads {total_threads:,}",
                        file=sys.stderr,
                    )
                continue

            # 按 feed 分组 matched posts
            matched_by_feed: Dict[str, List[int]] = defaultdict(list)
            for pid in matched_global:
                for fname in post_to_feeds.get(pid, ()):
                    matched_by_feed[fname].append(pid)

            for fname, mids in matched_by_feed.items():
                if fname in feed_states:
                    feed_states[fname].record_thread(thread_len, mids, post_to_user)

            # 合并方案：按 plan 聚合（去重 post_id）
            matched_by_plan: Dict[str, List[int]] = defaultdict(list)
            seen_plan_pid: Dict[str, Set[int]] = defaultdict(set)
            for pid in matched_global:
                for plan_name in merged_post_to_plans.get(pid, ()):
                    if pid not in seen_plan_pid[plan_name]:
                        seen_plan_pid[plan_name].add(pid)
                        matched_by_plan[plan_name].append(pid)

            for plan_name, mids in matched_by_plan.items():
                merged_states[plan_name].record_thread(thread_len, mids, post_to_user)

            if progress_every and line_no % progress_every == 0:
                print(
                    f"  [进度] 行 {line_no:,} | threads {total_threads:,} | "
                    f"本行命中 {len(matched_global)} posts",
                    file=sys.stderr,
                )

    return total_threads


# ---------------------------------------------------------------------------
# Step 3: 汇总单 feed / 合并方案结果
# ---------------------------------------------------------------------------
def covered_users(matched_posts: Set[int], post_to_user: Dict[int, int]) -> Set[int]:
    return {post_to_user[pid] for pid in matched_posts if pid in post_to_user}


def summarize_join_state(
    state: FeedJoinState,
    post_to_user: Dict[int, int],
    feed_stats: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """将 FeedJoinState 转为可序列化的汇总 dict。"""
    n_posts = len(state.post_ids)
    join_ratio = len(state.matched_posts) / n_posts if n_posts else 0.0
    cov_users = covered_users(state.matched_posts, post_to_user)

    condition_summaries = {
        name: acc.summarize() for name, acc in state.condition_acc.items()
    }

    return {
        "name": state.name,
        "total_posts": feed_stats.get("total_posts") if feed_stats else n_posts,
        "unique_post_ids": n_posts,
        "unique_user_ids_in_feed": feed_stats.get("unique_user_ids") if feed_stats else None,
        "join_stats": {
            "threads_with_at_least_1": state.threads_hit_1,
            "threads_with_at_least_2": state.threads_hit_2,
            "threads_with_at_least_3": state.threads_hit_3,
            "threads_with_at_least_5": state.threads_hit_5,
            "posts_matched_in_threads": len(state.matched_posts),
            "posts_matched_ratio": round(join_ratio, 4),
            "covered_unique_user_ids": len(cov_users),
        },
        "condition_summaries": condition_summaries,
    }


def analyze_agent_sampling(
    posts: Dict[int, Dict[str, Any]],
    user_matched_counts: Dict[int, int],
) -> Dict[str, Any]:
    """activity_score = feed 发帖数 + 候选 matched posts 出现次数。"""
    post_count_by_user: Dict[int, int] = defaultdict(int)
    for rec in posts.values():
        post_count_by_user[int(rec["user_id"])] += 1

    candidate_users = set(user_matched_counts.keys())
    scores: List[int] = []
    tier_counts = {"high": 0, "middle": 0, "low": 0}

    for uid in candidate_users:
        scores.append(post_count_by_user.get(uid, 0) + user_matched_counts.get(uid, 0))

    sorted_scores = sorted(scores)
    high_thresh = percentile_threshold(sorted_scores, 0.20)
    low_thresh = percentile_threshold(sorted_scores, 0.30)

    for uid in candidate_users:
        score = post_count_by_user.get(uid, 0) + user_matched_counts.get(uid, 0)
        level = assign_activity_level(score, high_thresh, low_thresh)
        tier_counts[level] += 1

    stratified_targets = {
        "high": int(AGENT_TARGET * 0.20),
        "middle": int(AGENT_TARGET * 0.50),
        "low": int(AGENT_TARGET * 0.30),
    }
    tier_sufficient = {
        t: tier_counts[t] >= stratified_targets[t] for t in ("high", "middle", "low")
    }
    can_sample = (
        all(tier_sufficient.values()) and len(candidate_users) >= AGENT_TARGET
    )

    gaps: List[str] = []
    if len(candidate_users) < AGENT_TARGET:
        gaps.append(f"候选 user {len(candidate_users)} < {AGENT_TARGET}")
    for t in ("high", "middle", "low"):
        if not tier_sufficient[t]:
            gaps.append(
                f"{t} 层 {tier_counts[t]} 人 < 目标 {stratified_targets[t]} 人"
            )

    return {
        "candidate_user_count": len(candidate_users),
        "activity_score_distribution": summarize_distribution(scores),
        "activity_tier_counts": tier_counts,
        "stratified_sampling_targets": stratified_targets,
        "stratified_tier_sufficient": tier_sufficient,
        "can_stratified_sample_200_agents": can_sample,
        "gaps": gaps,
        "recommended_stratification": "high 20% / middle 50% / low 30%",
    }


def pick_recommended_condition(condition_summaries: Dict[str, Any]) -> str:
    for c in ("condition_2", "condition_3", "condition_1"):
        s = condition_summaries.get(c, {})
        if s.get("candidate_thread_count", 0) >= 500:
            return c
    for c in ("condition_2", "condition_3", "condition_1"):
        s = condition_summaries.get(c, {})
        if s.get("candidate_thread_count", 0) > 0:
            return c
    return "condition_1"


def best_ranking_condition(condition_summaries: Dict[str, Any]) -> Tuple[str, Dict]:
    """取 condition_2/3 中更优者（优先 users>=200，其次 threads>=500）。"""
    best_name = "condition_2"
    best_score = (-1, -1, -1.0)
    for cname in RANKING_CONDITIONS:
        s = condition_summaries.get(cname, {})
        users = s.get("unique_user_ids", 0)
        threads = s.get("candidate_thread_count", 0)
        jc = s.get("join_coverage", {}).get("mean") or 0
        score = (
            1 if users >= AGENT_TARGET else 0,
            1 if threads >= 500 else 0,
            float(jc),
        )
        if score > best_score:
            best_score = score
            best_name = cname
    return best_name, condition_summaries.get(best_name, {})


def rank_feeds(
    feed_results: Dict[str, Dict[str, Any]],
    feed_stats_map: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    按优先级排名：
      1. condition_2/3 unique_user >= 200
      2. condition_2/3 candidate_threads >= 500
      3. join 覆盖率
      4. 文本覆盖率 + propagation 分布（matched_post_count median, thread_len median）
    """
    rows: List[Dict[str, Any]] = []
    for fname, result in sorted(feed_results.items()):
        cond_name, cond = best_ranking_condition(result["condition_summaries"])
        join = result["join_stats"]
        fstats = feed_stats_map[fname]
        agent = result["agent_sampling"]

        users = cond.get("unique_user_ids", 0)
        threads = cond.get("candidate_thread_count", 0)
        join_cov = join.get("posts_matched_ratio", 0)
        text_ratio = fstats.get("text_nonempty_ratio", 0)
        mc_med = cond.get("matched_post_count", {}).get("median") or 0
        tl_med = cond.get("thread_len", {}).get("median") or 0

        priority = (
            1 if users >= AGENT_TARGET else 0,
            1 if threads >= 500 else 0,
            users,
            join_cov,
            text_ratio,
            mc_med if isinstance(mc_med, (int, float)) else 0,
            tl_med if isinstance(tl_med, (int, float)) else 0,
        )

        reasons: List[str] = []
        if users >= AGENT_TARGET:
            reasons.append(f"users>={AGENT_TARGET}")
        else:
            reasons.append(f"users={users}<{AGENT_TARGET}")
        if threads >= 500:
            reasons.append("threads>=500")
        else:
            reasons.append(f"threads={threads}<500")
        reasons.append(f"join={join_cov:.2%}")
        if agent.get("can_stratified_sample_200_agents"):
            reasons.append("可分层抽200人")

        rows.append(
            {
                "feed_name": fname,
                "recommended_condition": cond_name,
                "candidate_threads": threads,
                "unique_users": users,
                "join_coverage": join_cov,
                "text_nonempty_ratio": text_ratio,
                "matched_post_count_median": mc_med,
                "thread_len_median": tl_med,
                "sufficient_200_agents": users >= AGENT_TARGET,
                "sufficient_500_threads": threads >= 500,
                "sufficient_1000_threads": cond.get("sufficient_for_1000_threads", False),
                "sufficient_2000_threads": cond.get("sufficient_for_2000_threads", False),
                "can_stratified_sample_200": agent.get(
                    "can_stratified_sample_200_agents", False
                ),
                "priority_tuple": priority,
                "reason": "; ".join(reasons),
            }
        )

    rows.sort(key=lambda r: r["priority_tuple"], reverse=True)
    for i, row in enumerate(rows, start=1):
        row["rank"] = i
    return rows


def build_overall_conclusion(
    ranking: List[Dict[str, Any]],
    merged_summaries: List[Dict[str, Any]],
) -> Dict[str, Any]:
    viable_single = [
        r for r in ranking
        if r["sufficient_200_agents"] and r["sufficient_500_threads"]
    ]
    # 单 feed 无法满足 200 agents 时，取 threads>=500 且 users 最多的作为「最佳单 feed」
    partial_single = [
        r for r in ranking if r["sufficient_500_threads"]
    ]
    best_partial_single = partial_single[0] if partial_single else (ranking[0] if ranking else None)

    best_merged = None
    for m in merged_summaries:
        users = max(m.get("cond2_users", 0), m.get("cond3_users", 0))
        threads = max(m.get("cond2_threads", 0), m.get("cond3_threads", 0))
        if users >= AGENT_TARGET and threads >= 500:
            if best_merged is None or users > max(
                best_merged.get("cond2_users", 0), best_merged.get("cond3_users", 0)
            ):
                best_merged = m

    if viable_single:
        top_name = viable_single[0]["feed_name"]
    elif best_merged:
        top_name = best_merged["merge_name"]
    elif best_partial_single:
        top_name = best_partial_single["feed_name"]
    else:
        top_name = None

    retreat: List[str] = []
    if not viable_single:
        retreat.append(
            "无单 feed 在 condition_2/3 下同时满足 200 agents + 500 threads。"
        )
        if best_partial_single:
            retreat.append(
                f"最佳单 feed 为 {best_partial_single['feed_name']}（"
                f"cond2: {best_partial_single['candidate_threads']} threads, "
                f"{best_partial_single['unique_users']} users），需合并其他 feed 或扩展 user 池。"
            )
    if best_merged and not viable_single:
        retreat.append(
            f"推荐合并方案：{best_merged['merge_name']}（"
            f"cond2: {best_merged['cond2_threads']} threads, "
            f"{best_merged['cond2_users']} users）。"
        )
    if not viable_single and not best_merged:
        retreat.append("考虑：合并全部 feed、放宽至 condition_1、或从 thread 全体参与者扩展 user 池。")
        retreat.append("agents 可降至 50–100 做 pilot；threads 可用 condition_1 宽松筛选。")

    return {
        "top_recommended_feed": top_name,
        "best_single_feed_partial": best_partial_single["feed_name"] if best_partial_single else None,
        "viable_single_feeds": [r["feed_name"] for r in viable_single],
        "backup_feeds": [r["feed_name"] for r in ranking[1:4]] if len(ranking) > 1 else [],
        "not_recommended_feeds": [
            r["feed_name"]
            for r in ranking
            if not r["sufficient_500_threads"] and r["unique_users"] < 50
        ],
        "best_merged_plan": best_merged["merge_name"] if best_merged else None,
        "single_feed_feasible": len(viable_single) > 0,
        "merged_feed_feasible": best_merged is not None,
        "mf_dag_main_experiment_feasible": len(viable_single) > 0 or best_merged is not None,
        "retreat_options": retreat,
    }


# ---------------------------------------------------------------------------
# Step 4: 写输出
# ---------------------------------------------------------------------------
def write_feed_ranking_csv(path: Path, ranking: List[Dict[str, Any]]) -> None:
    fields = [
        "rank", "feed_name", "recommended_condition", "candidate_threads",
        "unique_users", "join_coverage", "text_nonempty_ratio",
        "sufficient_200_agents", "sufficient_500_threads",
        "can_stratified_sample_200", "reason",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in ranking:
            w.writerow(
                {
                    **row,
                    "join_coverage": round(row["join_coverage"], 4),
                    "can_stratified_sample_200": row.get("can_stratified_sample_200"),
                }
            )


def write_all_feeds_summary_csv(
    path: Path,
    feed_results: Dict[str, Dict[str, Any]],
    feed_stats_map: Dict[str, Dict[str, Any]],
) -> None:
    fields = [
        "feed_name", "total_posts", "unique_post_ids", "unique_user_ids",
        "date_min", "date_max", "text_nonempty_ratio",
        "posts_matched_in_threads", "posts_matched_ratio",
        "covered_unique_user_ids",
        "threads_hit_ge1", "threads_hit_ge2", "threads_hit_ge3", "threads_hit_ge5",
        "cond2_threads", "cond2_users", "cond3_threads", "cond3_users",
        "cond1_threads", "cond1_users",
        "can_sample_200_agents", "recommended_condition",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for fname, result in sorted(feed_results.items()):
            fs = feed_stats_map[fname]
            js = result["join_stats"]
            cs = result["condition_summaries"]
            rec_cond = pick_recommended_condition(cs)
            w.writerow(
                {
                    "feed_name": fname,
                    "total_posts": fs["total_posts"],
                    "unique_post_ids": fs["unique_post_ids"],
                    "unique_user_ids": fs["unique_user_ids"],
                    "date_min": fs["date_min"],
                    "date_max": fs["date_max"],
                    "text_nonempty_ratio": fs["text_nonempty_ratio"],
                    "posts_matched_in_threads": js["posts_matched_in_threads"],
                    "posts_matched_ratio": js["posts_matched_ratio"],
                    "covered_unique_user_ids": js["covered_unique_user_ids"],
                    "threads_hit_ge1": js["threads_with_at_least_1"],
                    "threads_hit_ge2": js["threads_with_at_least_2"],
                    "threads_hit_ge3": js["threads_with_at_least_3"],
                    "threads_hit_ge5": js["threads_with_at_least_5"],
                    "cond2_threads": cs["condition_2"]["candidate_thread_count"],
                    "cond2_users": cs["condition_2"]["unique_user_ids"],
                    "cond3_threads": cs["condition_3"]["candidate_thread_count"],
                    "cond3_users": cs["condition_3"]["unique_user_ids"],
                    "cond1_threads": cs["condition_1"]["candidate_thread_count"],
                    "cond1_users": cs["condition_1"]["unique_user_ids"],
                    "can_sample_200_agents": result["agent_sampling"][
                        "can_stratified_sample_200_agents"
                    ],
                    "recommended_condition": rec_cond,
                }
            )


def write_merged_feeds_summary_csv(
    path: Path,
    merged_results: List[Dict[str, Any]],
) -> None:
    fields = [
        "merge_name", "feeds_included", "total_posts", "unique_post_ids",
        "unique_user_ids", "posts_matched_in_threads", "join_coverage",
        "cond2_threads", "cond2_users", "cond3_threads", "cond3_users",
        "sufficient_200_agents", "sufficient_500_threads",
        "sufficient_1000_threads", "sufficient_2000_threads",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for m in merged_results:
            w.writerow(m)


def write_markdown_report(
    path: Path,
    data_root: Path,
    threads_path: Path,
    total_threads: int,
    feed_stats_map: Dict[str, Dict],
    feed_results: Dict[str, Dict],
    ranking: List[Dict],
    merged_results: List[Dict],
    conclusion: Dict,
) -> None:
    lines: List[str] = []
    lines.append("# 全 Feed × threads Join 覆盖率检查报告\n")
    lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    lines.append("## 1. 检查目标\n")
    lines.append(
        "为 MF-DAG 第一版主实验筛选最适合的 feed/topic："
        "基于 `threads.txt` 的 post-level thread sequence propagation，"
        "目标 500–2000 threads、200 agents。\n"
    )

    lines.append("## 2. 数据路径\n")
    lines.append(f"- 数据根目录：`{data_root}`")
    lines.append(f"- feed_posts：`{data_root / 'feed_posts' / 'feed_posts'}`")
    lines.append(f"- threads：`{threads_path}`")
    lines.append(f"- 扫描 thread 总数：{total_threads:,}\n")

    lines.append("## 3. 单 Feed 统计摘要\n")
    lines.append(
        "| feed | posts | users | join% | cond2 threads | cond2 users | "
        "cond3 threads | cond3 users | 200 agents |"
    )
    lines.append("|" + "---|" * 9)
    for row in ranking:
        fr = feed_results[row["feed_name"]]
        js = fr["join_stats"]
        c2 = fr["condition_summaries"]["condition_2"]
        c3 = fr["condition_summaries"]["condition_3"]
        ag = "是" if row["can_stratified_sample_200"] else "否"
        lines.append(
            f"| {row['feed_name']} | {feed_stats_map[row['feed_name']]['unique_post_ids']:,} "
            f"| {feed_stats_map[row['feed_name']]['unique_user_ids']:,} "
            f"| {js['posts_matched_ratio']:.2%} "
            f"| {c2['candidate_thread_count']:,} | {c2['unique_user_ids']:,} "
            f"| {c3['candidate_thread_count']:,} | {c3['unique_user_ids']:,} | {ag} |"
        )
    lines.append("")

    lines.append("## 4. Feed 排名\n")
    lines.append("| rank | feed | condition | threads | users | join | reason |")
    lines.append("|------|------|-----------|---------|-------|------|--------|")
    for row in ranking:
        lines.append(
            f"| {row['rank']} | {row['feed_name']} | {row['recommended_condition']} "
            f"| {row['candidate_threads']:,} | {row['unique_users']:,} "
            f"| {row['join_coverage']:.2%} | {row['reason']} |"
        )
    lines.append("")

    lines.append("## 5. 合并 Feed 可行性\n")
    lines.append(
        "| 方案 | posts | users | join% | cond2 threads | cond2 users | "
        "200 agents | 500 threads |"
    )
    lines.append("|" + "---|" * 8)
    for m in merged_results:
        lines.append(
            f"| {m['merge_name']} | {m['unique_post_ids']:,} | {m['unique_user_ids']:,} "
            f"| {m['join_coverage']:.4f} | {m['cond2_threads']:,} | {m['cond2_users']:,} "
            f"| {'是' if m['sufficient_200_agents'] else '否'} "
            f"| {'是' if m['sufficient_500_threads'] else '否'} |"
        )
    lines.append("")

    lines.append("## 6. 推荐主实验 Feed\n")
    if conclusion.get("best_merged_plan") and not conclusion["viable_single_feeds"]:
        lines.append(f"- **最推荐（合并）**：`{conclusion['best_merged_plan']}`")
    if conclusion.get("best_single_feed_partial"):
        lines.append(
            f"- **最佳单 feed（未达 200 agents）**：`{conclusion['best_single_feed_partial']}`"
        )
    if conclusion["top_recommended_feed"] and conclusion["viable_single_feeds"]:
        lines.append(f"- **最推荐**：`{conclusion['top_recommended_feed']}`")
    if conclusion["viable_single_feeds"]:
        lines.append(
            f"- **满足主实验门槛的单 feed**：{', '.join(conclusion['viable_single_feeds'])}"
        )
    else:
        lines.append("- **无单 feed 同时满足** condition_2/3 下 threads>=500 且 users>=200")
    if conclusion["backup_feeds"]:
        lines.append(f"- **备选**：{', '.join(conclusion['backup_feeds'])}")
    if conclusion["not_recommended_feeds"]:
        lines.append(f"- **不推荐**：{', '.join(conclusion['not_recommended_feeds'])}")
    if conclusion["best_merged_plan"]:
        lines.append(f"- **最佳合并方案**：`{conclusion['best_merged_plan']}`")
    lines.append("")

    lines.append("## 7. MF-DAG 主实验可行性结论\n")
    lines.append(
        f"- 单 feed 可行：**{'是' if conclusion['single_feed_feasible'] else '否'}**"
    )
    lines.append(
        f"- 合并 feed 可行：**{'是' if conclusion['merged_feed_feasible'] else '否'}**"
    )
    lines.append(
        f"- 总体可行：**{'是' if conclusion['mf_dag_main_experiment_feasible'] else '否'}**"
    )
    lines.append("")

    lines.append("## 8. 退路方案\n")
    if conclusion["retreat_options"]:
        for opt in conclusion["retreat_options"]:
            lines.append(f"- {opt}")
    else:
        lines.append("- 当前有 feed/合并方案满足主实验需求。")

    path.write_text("\n".join(lines), encoding="utf-8")


def print_terminal_summary(
    ranking: List[Dict],
    merged_results: List[Dict],
    conclusion: Dict,
) -> None:
    print("\n" + "=" * 70)
    print("全 Feed × threads Join 检查 — 关键摘要")
    print("=" * 70)
    print(f"{'Rank':<5} {'Feed':<25} {'Cond':<12} {'Threads':>8} {'Users':>7} {'Join':>7}")
    print("-" * 70)
    for row in ranking:
        print(
            f"{row['rank']:<5} {row['feed_name']:<25} "
            f"{row['recommended_condition']:<12} "
            f"{row['candidate_threads']:>8,} {row['unique_users']:>7,} "
            f"{row['join_coverage']:>6.2%}"
        )
    print("\n合并方案（condition_2）：")
    for m in merged_results:
        print(
            f"  {m['merge_name']:<35} threads={m['cond2_threads']:>7,} "
            f"users={m['cond2_users']:>5,} join={m['join_coverage']:.2%}"
        )
    print(f"\n最推荐 feed: {conclusion.get('top_recommended_feed')}")
    print(f"最佳合并: {conclusion.get('best_merged_plan')}")
    print(
        f"MF-DAG 主实验可行: "
        f"{'是' if conclusion['mf_dag_main_experiment_feasible'] else '否'}"
    )
    print("=" * 70 + "\n")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="批量检查所有 feed 与 threads.txt 的 join 覆盖率并推荐主实验 feed"
    )
    parser.add_argument(
        "--data_root",
        type=Path,
        default=Path("/Users/fgod/Desktop/FGOD/MF-DAG/MF-DAG/data"),
    )
    parser.add_argument(
        "--output_dir",
        type=Path,
        default=Path("outputs/data_checks"),
    )
    parser.add_argument("--progress_every", type=int, default=500_000)
    args = parser.parse_args()

    data_root = args.data_root
    feed_dir = data_root / "feed_posts" / "feed_posts"
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    threads_path, is_gzip = resolve_threads_path(data_root)

    print("[1/5] 载入所有 feed_posts …")
    all_posts, feed_stats_map = load_all_feeds(feed_dir)
    if not all_posts:
        sys.exit(f"错误：{feed_dir} 下未找到任何 .jsonl.gz feed 文件")

    print("[2/5] 建立全局 post_id 索引 …")
    post_to_user, post_to_feeds = build_global_index(all_posts)
    print(f"      全局 unique post_id: {len(post_to_user):,}")

    feed_states, merged_states = build_join_states(all_posts, MERGED_FEED_PLANS)

    print(f"[3/5] 单次流式扫描 threads（{threads_path.name}）…")
    total_threads = scan_threads_all_feeds(
        threads_path,
        is_gzip,
        post_to_user,
        post_to_feeds,
        feed_states,
        merged_states,
        progress_every=args.progress_every,
    )
    print(f"      扫描完成，有效 thread: {total_threads:,}")

    print("[4/5] 汇总统计与排名 …")
    feed_results: Dict[str, Dict[str, Any]] = {}
    for fname, state in feed_states.items():
        summary = summarize_join_state(state, post_to_user, feed_stats_map[fname])
        summary["agent_sampling"] = analyze_agent_sampling(
            all_posts[fname], state.user_matched_counts
        )
        summary["feed_stats"] = feed_stats_map[fname]
        feed_results[fname] = summary

    ranking = rank_feeds(feed_results, feed_stats_map)

    merged_results: List[Dict[str, Any]] = []
    for plan_name, state in merged_states.items():
        members = MERGED_FEED_PLANS.get(plan_name, [])
        if not members:
            members = list(all_posts.keys())
        unique_users: Set[int] = set()
        total_posts_lines = 0
        for m in members:
            if m in feed_stats_map:
                total_posts_lines += feed_stats_map[m]["total_posts"]
                for rec in all_posts[m].values():
                    unique_users.add(int(rec["user_id"]))

        summary = summarize_join_state(state, post_to_user)
        c2 = summary["condition_summaries"]["condition_2"]
        c3 = summary["condition_summaries"]["condition_3"]
        users_best = max(c2["unique_user_ids"], c3["unique_user_ids"])
        threads_best = max(
            c2["candidate_thread_count"], c3["candidate_thread_count"]
        )
        merged_results.append(
            {
                "merge_name": plan_name,
                "feeds_included": " + ".join(members),
                "total_posts": total_posts_lines,
                "unique_post_ids": len(state.post_ids),
                "unique_user_ids": len(unique_users),
                "posts_matched_in_threads": summary["join_stats"]["posts_matched_in_threads"],
                "join_coverage": summary["join_stats"]["posts_matched_ratio"],
                "condition_2": c2,
                "condition_3": c3,
                "cond2_threads": c2["candidate_thread_count"],
                "cond2_users": c2["unique_user_ids"],
                "cond3_threads": c3["candidate_thread_count"],
                "cond3_users": c3["unique_user_ids"],
                "sufficient_200_agents": users_best >= AGENT_TARGET,
                "sufficient_500_threads": threads_best >= 500,
                "sufficient_1000_threads": max(
                    c2["sufficient_for_1000_threads"],
                    c3["sufficient_for_1000_threads"],
                ),
                "sufficient_2000_threads": max(
                    c2["sufficient_for_2000_threads"],
                    c3["sufficient_for_2000_threads"],
                ),
            }
        )

    conclusion = build_overall_conclusion(ranking, merged_results)

    json_payload = {
        "generated_at": datetime.now().isoformat(),
        "data_root": str(data_root),
        "threads_path": str(threads_path),
        "total_threads_scanned": total_threads,
        "feed_count": len(all_posts),
        "feed_names": sorted(all_posts.keys()),
        "feed_stats": feed_stats_map,
        "feed_results": {
            k: {
                "join_stats": v["join_stats"],
                "condition_summaries": v["condition_summaries"],
                "agent_sampling": v["agent_sampling"],
            }
            for k, v in feed_results.items()
        },
        "ranking": [{k: v for k, v in r.items() if k != "priority_tuple"} for r in ranking],
        "merged_results": merged_results,
        "conclusion": conclusion,
    }

    print("[5/5] 写入报告 …")
    with open(output_dir / "all_feeds_threads_join_report.json", "w", encoding="utf-8") as f:
        json.dump(json_payload, f, ensure_ascii=False, indent=2)

    write_markdown_report(
        output_dir / "all_feeds_threads_join_report.md",
        data_root,
        threads_path,
        total_threads,
        feed_stats_map,
        feed_results,
        ranking,
        merged_results,
        conclusion,
    )
    write_all_feeds_summary_csv(
        output_dir / "all_feeds_summary.csv", feed_results, feed_stats_map
    )
    write_feed_ranking_csv(output_dir / "feed_ranking.csv", ranking)
    write_merged_feeds_summary_csv(
        output_dir / "merged_feeds_summary.csv", merged_results
    )

    print_terminal_summary(ranking, merged_results, conclusion)
    print(f"报告已保存至：{output_dir.resolve()}")


if __name__ == "__main__":
    main()
