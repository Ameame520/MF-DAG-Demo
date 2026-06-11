#!/usr/bin/env python3
"""
MF-DAG 数据可行性检查：News feed_posts 与 threads.txt 的 post_id join 覆盖率。

步骤概览：
  1. 流式/全量读取 News.jsonl.gz，建立 post_id -> post_info 映射，并统计 News 基础指标
  2. 流式扫描 threads.txt（或 .gz），逐条计算 join 覆盖率
  3. 汇总 thread / user 级统计，评估 500–2000 threads 与 200 agents 可行性
  4. 输出 Markdown / JSON / CSV 报告
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, TextIO, Tuple


# ---------------------------------------------------------------------------
# 筛选条件定义（候选 thread）
# ---------------------------------------------------------------------------
CONDITIONS: Dict[str, callable] = {
    "condition_1": lambda tl, mc, cov: tl >= 2 and mc >= 1,
    "condition_2": lambda tl, mc, cov: tl >= 3 and mc >= 2,
    "condition_3": lambda tl, mc, cov: tl >= 5 and mc >= 2,
    "condition_4": lambda tl, mc, cov: tl >= 5 and mc >= 3,
    "condition_5": lambda tl, mc, cov: tl >= 5 and cov >= 0.5,
    "condition_6": lambda tl, mc, cov: tl >= 10 and mc >= 3,
}

# 主候选集：用于导出 CSV 与 user activity 分析
PRIMARY_CANDIDATE_CONDITION = "condition_1"

THREAD_TARGETS = (500, 1000, 2000)
AGENT_TARGET = 200


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def resolve_threads_path(data_root: Path) -> Tuple[Path, bool]:
    """解析 threads 文件路径；优先 .txt，不存在则 fallback 到 .gz。"""
    graphs_dir = data_root / "graphs" / "graphs"
    txt_path = graphs_dir / "threads.txt"
    gz_path = graphs_dir / "threads.txt.gz"
    if txt_path.exists():
        return txt_path, False
    if gz_path.exists():
        return gz_path, True
    raise FileNotFoundError(
        f"未找到 threads 文件：{txt_path} 或 {gz_path}"
    )


def open_text_maybe_gzip(path: Path, is_gzip: bool) -> TextIO:
    if is_gzip:
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return open(path, "r", encoding="utf-8", errors="replace")


def safe_median(values: List[float]) -> Optional[float]:
    return statistics.median(values) if values else None


def safe_mean(values: List[float]) -> Optional[float]:
    return statistics.mean(values) if values else None


def percentile_threshold(sorted_scores: List[int], pct: float) -> float:
    """返回使 pct 比例用户处于该档及以上的最低分数（0~1 之间）。"""
    if not sorted_scores:
        return 0.0
    idx = int(len(sorted_scores) * (1 - pct))
    idx = min(max(idx, 0), len(sorted_scores) - 1)
    return float(sorted_scores[idx])


def assign_activity_level(
    score: int,
    high_thresh: float,
    low_thresh: float,
) -> str:
    if score >= high_thresh:
        return "high"
    if score >= low_thresh:
        return "middle"
    return "low"


def summarize_distribution(values: List[int]) -> Dict[str, Any]:
    if not values:
        return {"min": None, "max": None, "mean": None, "median": None, "p25": None, "p75": None}
    sorted_v = sorted(values)
    n = len(sorted_v)

    def pct(p: float) -> float:
        idx = int(n * p)
        idx = min(max(idx, 0), n - 1)
        return float(sorted_v[idx])

    return {
        "min": sorted_v[0],
        "max": sorted_v[-1],
        "mean": round(statistics.mean(sorted_v), 2),
        "median": float(statistics.median(sorted_v)),
        "p25": pct(0.25),
        "p75": pct(0.75),
    }


# ---------------------------------------------------------------------------
# Step 1: 读取 News feed_posts
# ---------------------------------------------------------------------------
def load_news_posts(feed_path: Path) -> Tuple[Dict[int, Dict[str, Any]], Dict[str, Any]]:
    """
    读取 News.jsonl.gz，建立 post_id -> post_info 映射，并计算基础统计。
    News 文件较小（~4MB 压缩），可完整载入内存。
    """
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

            text = rec.get("text") or ""
            if str(text).strip():
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

    news_stats = {
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
    return posts, news_stats


# ---------------------------------------------------------------------------
# Step 2: 流式扫描 threads.txt
# ---------------------------------------------------------------------------
@dataclass
class ConditionAccumulator:
    """单个筛选条件下的增量统计。"""

    count: int = 0
    thread_lens: List[int] = field(default_factory=list)
    matched_counts: List[int] = field(default_factory=list)
    coverages: List[float] = field(default_factory=list)
    user_ids: Set[int] = field(default_factory=set)

    def add(self, thread_len: int, matched: int, coverage: float, users: Set[int]) -> None:
        self.count += 1
        self.thread_lens.append(thread_len)
        self.matched_counts.append(matched)
        self.coverages.append(coverage)
        self.user_ids.update(users)

    def summarize(self) -> Dict[str, Any]:
        return {
            "candidate_thread_count": self.count,
            "thread_len": {
                "mean": round(safe_mean(self.thread_lens), 2) if self.thread_lens else None,
                "median": safe_median(self.thread_lens),
                "max": max(self.thread_lens) if self.thread_lens else None,
            },
            "matched_post_count": {
                "mean": round(safe_mean(self.matched_counts), 2) if self.matched_counts else None,
                "median": safe_median(self.matched_counts),
                "max": max(self.matched_counts) if self.matched_counts else None,
            },
            "join_coverage": {
                "mean": round(safe_mean(self.coverages), 4) if self.coverages else None,
                "median": safe_median(self.coverages),
            },
            "unique_user_ids": len(self.user_ids),
            "sufficient_for_200_agents": len(self.user_ids) >= AGENT_TARGET,
            "sufficient_for_500_threads": self.count >= 500,
            "sufficient_for_1000_threads": self.count >= 1000,
            "sufficient_for_2000_threads": self.count >= 2000,
        }


def parse_thread_line(line: str) -> Optional[Tuple[str, str, List[int]]]:
    """解析 threads.txt 单行：thread_root_id, root_time, post_id 列表。"""
    line = line.strip()
    if not line:
        return None
    parts = line.split("\t")
    if len(parts) < 3:
        return None
    thread_root_id = parts[0].strip()
    root_time = parts[1].strip()
    raw_ids = parts[2].strip().rstrip(",")
    if not raw_ids:
        post_ids: List[int] = []
    else:
        post_ids = [int(x) for x in raw_ids.split(",") if x.strip()]
    return thread_root_id, root_time, post_ids


def scan_threads(
    threads_path: Path,
    is_gzip: bool,
    news_posts: Dict[int, Dict[str, Any]],
    progress_every: int = 500_000,
) -> Dict[str, Any]:
    """
    流式扫描 threads，计算 join 覆盖率与各条件候选集统计。
    不将整个 threads 文件载入内存。
    """
    news_post_ids: Set[int] = set(news_posts.keys())
    matched_news_posts: Set[int] = set()

    total_threads = 0
    threads_hit_1 = 0
    threads_hit_2 = 0
    threads_hit_3 = 0
    threads_hit_5 = 0

    condition_acc: Dict[str, ConditionAccumulator] = {
        name: ConditionAccumulator() for name in CONDITIONS
    }

    # 主候选集 thread 记录（condition_1）与 user 在 matched posts 中的出现次数
    candidate_thread_rows: List[Dict[str, Any]] = []
    user_matched_thread_post_count: Dict[int, int] = defaultdict(int)

    with open_text_maybe_gzip(threads_path, is_gzip) as f:
        for line_no, line in enumerate(f, start=1):
            parsed = parse_thread_line(line)
            if parsed is None:
                continue

            thread_root_id, root_time, post_ids = parsed
            thread_len = len(post_ids)
            total_threads += 1

            matched_post_ids: List[int] = []
            matched_user_ids: Set[int] = set()
            for pid in post_ids:
                if pid in news_post_ids:
                    matched_post_ids.append(pid)
                    matched_news_posts.add(pid)
                    matched_user_ids.add(int(news_posts[pid]["user_id"]))

            matched_count = len(matched_post_ids)
            coverage = matched_count / thread_len if thread_len > 0 else 0.0

            if matched_count >= 1:
                threads_hit_1 += 1
            if matched_count >= 2:
                threads_hit_2 += 1
            if matched_count >= 3:
                threads_hit_3 += 1
            if matched_count >= 5:
                threads_hit_5 += 1

            for name, predicate in CONDITIONS.items():
                if predicate(thread_len, matched_count, coverage):
                    condition_acc[name].add(
                        thread_len, matched_count, coverage, matched_user_ids
                    )

            # 主候选集：导出 CSV 并累计 user matched 次数
            if CONDITIONS[PRIMARY_CANDIDATE_CONDITION](
                thread_len, matched_count, coverage
            ):
                candidate_thread_rows.append(
                    {
                        "thread_root_id": thread_root_id,
                        "root_time": root_time,
                        "thread_len": thread_len,
                        "matched_post_count": matched_count,
                        "join_coverage": round(coverage, 4),
                        "matched_post_ids": ",".join(str(x) for x in matched_post_ids),
                        "matched_user_ids": ",".join(
                            str(x) for x in sorted(matched_user_ids)
                        ),
                    }
                )
                for uid in matched_user_ids:
                    user_matched_thread_post_count[uid] += sum(
                        1 for pid in matched_post_ids
                        if int(news_posts[pid]["user_id"]) == uid
                    )

            if progress_every and line_no % progress_every == 0:
                print(
                    f"  [进度] 已扫描 {line_no:,} 行，"
                    f"有效 thread {total_threads:,}，"
                    f"命中 News >=1: {threads_hit_1:,}",
                    file=sys.stderr,
                )

    covered_users: Set[int] = set()
    for pid in matched_news_posts:
        covered_users.add(int(news_posts[pid]["user_id"]))

    join_stats = {
        "threads_file": str(threads_path),
        "threads_is_gzip": is_gzip,
        "total_threads_scanned": total_threads,
        "threads_with_at_least_1_news_post": threads_hit_1,
        "threads_with_at_least_2_news_posts": threads_hit_2,
        "threads_with_at_least_3_news_posts": threads_hit_3,
        "threads_with_at_least_5_news_posts": threads_hit_5,
        "news_posts_matched_in_threads": len(matched_news_posts),
        "news_posts_matched_ratio": round(
            len(matched_news_posts) / len(news_post_ids), 4
        )
        if news_post_ids
        else 0,
        "covered_news_unique_user_ids": len(covered_users),
    }

    condition_summaries = {
        name: acc.summarize() for name, acc in condition_acc.items()
    }

    return {
        "join_stats": join_stats,
        "condition_summaries": condition_summaries,
        "candidate_thread_rows": candidate_thread_rows,
        "user_matched_thread_post_count": dict(user_matched_thread_post_count),
        "matched_news_posts": matched_news_posts,
    }


# ---------------------------------------------------------------------------
# Step 3: 200 agents 分层抽样可行性
# ---------------------------------------------------------------------------
def analyze_agent_sampling(
    news_posts: Dict[int, Dict[str, Any]],
    user_matched_counts: Dict[int, int],
    primary_condition_summary: Dict[str, Any],
) -> Dict[str, Any]:
    """
    activity_score = News 发帖数 + 候选 thread matched posts 出现次数。
    分层：high top 20%, middle 50%, low bottom 30%。
    """
    news_post_count_by_user: Dict[int, int] = defaultdict(int)
    for rec in news_posts.values():
        news_post_count_by_user[int(rec["user_id"])] += 1

    candidate_users = set(news_post_count_by_user.keys()) | set(user_matched_counts.keys())
    # 仅保留在候选 thread 中出现过的 user
    candidate_users = set(user_matched_counts.keys())

    user_rows: List[Dict[str, Any]] = []
    scores: List[int] = []
    for uid in candidate_users:
        npc = news_post_count_by_user.get(uid, 0)
        mtpc = user_matched_counts.get(uid, 0)
        score = npc + mtpc
        scores.append(score)
        user_rows.append(
            {
                "user_id": uid,
                "news_post_count": npc,
                "matched_thread_post_count": mtpc,
                "activity_score": score,
                "activity_level": "",  # 稍后填充
            }
        )

    sorted_scores = sorted(scores)
    high_thresh = percentile_threshold(sorted_scores, 0.20)
    low_thresh = percentile_threshold(sorted_scores, 0.30)

    tier_counts = {"high": 0, "middle": 0, "low": 0}
    for row in user_rows:
        level = assign_activity_level(row["activity_score"], high_thresh, low_thresh)
        row["activity_level"] = level
        tier_counts[level] += 1

    # 分层抽样目标：200 人中 high 20% / middle 50% / low 30%
    stratified_targets = {
        "high": int(AGENT_TARGET * 0.20),
        "middle": int(AGENT_TARGET * 0.50),
        "low": int(AGENT_TARGET * 0.30),
    }
    tier_sufficient = {
        tier: tier_counts[tier] >= stratified_targets[tier]
        for tier in ("high", "middle", "low")
    }
    can_sample_200 = all(tier_sufficient.values()) and len(candidate_users) >= AGENT_TARGET

    alternatives: List[str] = []
    if not can_sample_200:
        if len(candidate_users) < AGENT_TARGET:
            alternatives.append(
                f"候选 user 仅 {len(candidate_users)} 人，不足 {AGENT_TARGET}；"
                "可放宽 thread 筛选条件（如 condition_1）或合并多个 feed。"
            )
        for tier in ("high", "middle", "low"):
            if not tier_sufficient[tier]:
                alternatives.append(
                    f"{tier} 活跃度层仅 {tier_counts[tier]} 人，"
                    f"不足目标 {stratified_targets[tier]} 人；"
                    "可调整分层比例或降低 activity 分档阈值。"
                )

    return {
        "candidate_user_count": len(candidate_users),
        "activity_score_distribution": summarize_distribution(scores),
        "activity_tier_counts": tier_counts,
        "activity_tier_thresholds": {
            "high_min_score": high_thresh,
            "low_max_score_exclusive": low_thresh,
        },
        "stratified_sampling_targets": stratified_targets,
        "stratified_tier_sufficient": tier_sufficient,
        "can_stratified_sample_200_agents": can_sample_200,
        "alternatives_if_insufficient": alternatives,
        "user_rows": sorted(user_rows, key=lambda r: -r["activity_score"]),
    }


# ---------------------------------------------------------------------------
# Step 4: 可行性结论
# ---------------------------------------------------------------------------
def build_feasibility_conclusion(
    news_stats: Dict[str, Any],
    join_stats: Dict[str, Any],
    condition_summaries: Dict[str, Any],
    agent_analysis: Dict[str, Any],
) -> Dict[str, Any]:
    """综合判断 MF-DAG 主实验是否可行。"""
    # 优先用 condition_2 作为「质量较好」的默认判断；condition_1 作为宽松下界
    cond2 = condition_summaries.get("condition_2", {})
    cond1 = condition_summaries.get("condition_1", {})

    threads_ok_500 = cond2.get("sufficient_for_500_threads", False) or cond1.get(
        "sufficient_for_500_threads", False
    )
    threads_ok_2000 = cond2.get("sufficient_for_2000_threads", False) or cond1.get(
        "sufficient_for_2000_threads", False
    )
    agents_ok = agent_analysis.get("can_stratified_sample_200_agents", False)
    join_ratio = join_stats.get("news_posts_matched_ratio", 0)

    feasible = (
        threads_ok_500
        and agents_ok
        and join_ratio >= 0.05
        and news_stats.get("unique_post_ids", 0) > 0
    )

    retreat_options: List[str] = []
    if join_ratio < 0.3:
        retreat_options.append(
            "News post 在 threads 中覆盖率偏低，可仅用 matched posts 做 cascade 子集实验，"
            "或换用覆盖面更大的 feed（如 Popular 或全 interactions 推导的 thread）。"
        )
    if not threads_ok_2000:
        retreat_options.append(
            "若不足 2000 条高质量 thread，可将实验规模定为 500–1000，"
            "或放宽 condition（thread_len / matched_post_count 阈值）。"
        )
    if not agents_ok:
        retreat_options.extend(agent_analysis.get("alternatives_if_insufficient", []))
    if join_stats.get("threads_with_at_least_1_news_post", 0) == 0:
        retreat_options.append(
            "threads 与 News post_id 完全无交集，需核对 post_id 编码或数据源版本是否一致。"
        )

    return {
        "news_feed_usable": news_stats.get("unique_post_ids", 0) > 0,
        "sufficient_for_500_2000_threads": threads_ok_500,
        "sufficient_for_2000_threads_strict": threads_ok_2000,
        "sufficient_for_200_agents": agents_ok,
        "post_level_thread_propagation_feasible": feasible,
        "recommended_condition": "condition_2"
        if cond2.get("candidate_thread_count", 0) >= 500
        else "condition_1",
        "retreat_options": retreat_options,
    }


# ---------------------------------------------------------------------------
# Step 5: 写输出文件
# ---------------------------------------------------------------------------
def write_candidate_threads_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    fieldnames = [
        "thread_root_id",
        "root_time",
        "thread_len",
        "matched_post_count",
        "join_coverage",
        "matched_post_ids",
        "matched_user_ids",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_candidate_users_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    fieldnames = [
        "user_id",
        "news_post_count",
        "matched_thread_post_count",
        "activity_score",
        "activity_level",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json_report(path: Path, payload: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def write_markdown_report(
    path: Path,
    data_root: Path,
    feed_name: str,
    news_stats: Dict[str, Any],
    join_stats: Dict[str, Any],
    condition_summaries: Dict[str, Any],
    agent_analysis: Dict[str, Any],
    conclusion: Dict[str, Any],
    feed_path: Path,
    threads_path: Path,
) -> None:
    lines: List[str] = []
    lines.append("# News × threads Join 覆盖率检查报告\n")
    lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    lines.append("## 1. 检查目标\n")
    lines.append(
        "验证 Bluesky News feed 的 `post_id` 能否与 `threads.txt` 有效 join，"
        "并评估是否足以支撑 MF-DAG 主实验（500–2000 threads、200 agents、"
        "post-level thread sequence propagation）。\n"
    )

    lines.append("## 2. 数据路径\n")
    lines.append(f"- 数据根目录：`{data_root}`")
    lines.append(f"- Feed：`{feed_name}` → `{feed_path}`")
    lines.append(f"- Threads：`{threads_path}`（gzip={join_stats.get('threads_is_gzip')}）\n")

    lines.append("## 3. News feed 基础统计（A）\n")
    lines.append(f"| 指标 | 值 |")
    lines.append(f"|------|-----|")
    lines.append(f"| 总 posts | {news_stats['total_posts']:,} |")
    lines.append(f"| unique post_id | {news_stats['unique_post_ids']:,} |")
    lines.append(f"| unique user_id | {news_stats['unique_user_ids']:,} |")
    lines.append(f"| 时间范围 | {news_stats['date_min']} – {news_stats['date_max']} |")
    lines.append(
        f"| text 非空 | {news_stats['text_nonempty_count']:,} "
        f"({news_stats['text_nonempty_ratio']:.2%}) |"
    )
    lines.append(f"| reply_to 非空 | {news_stats['reply_to_nonempty_count']:,} |")
    lines.append(f"| quotes 非空 | {news_stats['quotes_nonempty_count']:,} |")
    for metric in ("like_count", "reply_count", "repost_count"):
        s = news_stats[metric]
        lines.append(
            f"| {metric} mean/median/max | "
            f"{s['mean']} / {s['median']} / {s['max']} |"
        )
    lines.append("")

    lines.append("## 4. threads join 覆盖率（B）\n")
    lines.append(f"| 指标 | 值 |")
    lines.append(f"|------|-----|")
    lines.append(f"| 扫描 thread 总数 | {join_stats['total_threads_scanned']:,} |")
    lines.append(f"| 至少命中 1 个 News post | {join_stats['threads_with_at_least_1_news_post']:,} |")
    lines.append(f"| 至少命中 2 个 News post | {join_stats['threads_with_at_least_2_news_posts']:,} |")
    lines.append(f"| 至少命中 3 个 News post | {join_stats['threads_with_at_least_3_news_posts']:,} |")
    lines.append(f"| 至少命中 5 个 News post | {join_stats['threads_with_at_least_5_news_posts']:,} |")
    lines.append(
        f"| News post 被 threads 覆盖 | "
        f"{join_stats['news_posts_matched_in_threads']:,} "
        f"({join_stats['news_posts_matched_ratio']:.2%}) |"
    )
    lines.append(
        f"| 被覆盖 News posts 涉及 unique user | "
        f"{join_stats['covered_news_unique_user_ids']:,} |"
    )
    lines.append("")

    lines.append("## 5. 候选 thread 筛选结果（C）\n")
    for name, summary in condition_summaries.items():
        lines.append(f"### {name}\n")
        lines.append(f"- 候选 thread 数：**{summary['candidate_thread_count']:,}**")
        tl = summary["thread_len"]
        mc = summary["matched_post_count"]
        jc = summary["join_coverage"]
        lines.append(
            f"- thread_len：mean={tl['mean']}, median={tl['median']}, max={tl['max']}"
        )
        lines.append(
            f"- matched_post_count：mean={mc['mean']}, median={mc['median']}, max={mc['max']}"
        )
        lines.append(
            f"- join_coverage：mean={jc['mean']}, median={jc['median']}"
        )
        lines.append(f"- unique user_id：{summary['unique_user_ids']:,}")
        lines.append(
            f"- 足够 200 agents：{'是' if summary['sufficient_for_200_agents'] else '否'} | "
            f"500 threads：{'是' if summary['sufficient_for_500_threads'] else '否'} | "
            f"1000：{'是' if summary['sufficient_for_1000_threads'] else '否'} | "
            f"2000：{'是' if summary['sufficient_for_2000_threads'] else '否'}"
        )
        lines.append("")

    lines.append("## 6. 200 agents 分层抽样可行性（D）\n")
    lines.append(f"- 候选 user 总数：**{agent_analysis['candidate_user_count']:,}**")
    dist = agent_analysis["activity_score_distribution"]
    lines.append(
        f"- activity_score 分布：min={dist['min']}, p25={dist['p25']}, "
        f"median={dist['median']}, p75={dist['p75']}, max={dist['max']}, mean={dist['mean']}"
    )
    tiers = agent_analysis["activity_tier_counts"]
    targets = agent_analysis["stratified_sampling_targets"]
    suff = agent_analysis["stratified_tier_sufficient"]
    lines.append(
        f"- 分层方案（200 人）：high 20%={targets['high']}, "
        f"middle 50%={targets['middle']}, low 30%={targets['low']}"
    )
    lines.append(
        f"- 各层可用人数：high={tiers['high']}, middle={tiers['middle']}, low={tiers['low']}"
    )
    lines.append(
        f"- 能否分层抽 200 人：**"
        f"{'可以' if agent_analysis['can_stratified_sample_200_agents'] else '不足'}**"
    )
    if agent_analysis.get("alternatives_if_insufficient"):
        lines.append("\n替代方案：")
        for alt in agent_analysis["alternatives_if_insufficient"]:
            lines.append(f"- {alt}")
    lines.append("")

    lines.append("## 7. MF-DAG 主实验可行性结论\n")
    lines.append(
        f"- News feed 可用：**{'是' if conclusion['news_feed_usable'] else '否'}**"
    )
    lines.append(
        f"- 支撑 500–2000 threads：**"
        f"{'是' if conclusion['sufficient_for_500_2000_threads'] else '否'}**"
    )
    lines.append(
        f"- 支撑 200 agents：**{'是' if conclusion['sufficient_for_200_agents'] else '否'}**"
    )
    lines.append(
        f"- post-level thread propagation 可行：**"
        f"{'是' if conclusion['post_level_thread_propagation_feasible'] else '否'}**"
    )
    lines.append(f"- 推荐筛选条件：`{conclusion['recommended_condition']}`\n")

    lines.append("## 8. 退路方案\n")
    if conclusion.get("retreat_options"):
        for opt in conclusion["retreat_options"]:
            lines.append(f"- {opt}")
    else:
        lines.append("- 当前数据满足主实验需求，无需退路。")

    path.write_text("\n".join(lines), encoding="utf-8")


def print_terminal_summary(
    news_stats: Dict[str, Any],
    join_stats: Dict[str, Any],
    condition_summaries: Dict[str, Any],
    agent_analysis: Dict[str, Any],
    conclusion: Dict[str, Any],
) -> None:
    """在 terminal 打印关键摘要。"""
    print("\n" + "=" * 60)
    print("News × threads Join 覆盖率检查 — 关键摘要")
    print("=" * 60)
    print(f"News posts: {news_stats['total_posts']:,} | "
          f"users: {news_stats['unique_user_ids']:,}")
    print(f"Threads scanned: {join_stats['total_threads_scanned']:,}")
    print(
        f"Threads hit >=1 News post: "
        f"{join_stats['threads_with_at_least_1_news_post']:,}"
    )
    print(
        f"News posts covered in threads: "
        f"{join_stats['news_posts_matched_in_threads']:,} "
        f"({join_stats['news_posts_matched_ratio']:.2%})"
    )
    print("\n候选 thread 数量（按条件）：")
    for name, summary in condition_summaries.items():
        print(f"  {name}: {summary['candidate_thread_count']:,}")
    print(
        f"\n候选 users（{PRIMARY_CANDIDATE_CONDITION}）: "
        f"{agent_analysis['candidate_user_count']:,}"
    )
    print(
        f"可分层抽 200 agents: "
        f"{'是' if agent_analysis['can_stratified_sample_200_agents'] else '否'}"
    )
    print(
        f"\n结论 — MF-DAG 主实验可行: "
        f"{'是' if conclusion['post_level_thread_propagation_feasible'] else '否'}"
    )
    print(f"推荐条件: {conclusion['recommended_condition']}")
    if conclusion.get("retreat_options"):
        print("\n退路方案:")
        for opt in conclusion["retreat_options"]:
            print(f"  - {opt}")
    print("=" * 60 + "\n")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="检查 News feed_posts 与 threads.txt 的 post_id join 覆盖率"
    )
    parser.add_argument(
        "--data_root",
        type=Path,
        default=Path("/Users/fgod/Desktop/FGOD/MF-DAG/MF-DAG/data"),
        help="数据根目录",
    )
    parser.add_argument(
        "--feed_name",
        type=str,
        default="News",
        help="feed 名称（对应 feed_posts/feed_posts/{name}.jsonl.gz）",
    )
    parser.add_argument(
        "--output_dir",
        type=Path,
        default=Path("outputs/data_checks"),
        help="报告输出目录",
    )
    parser.add_argument(
        "--progress_every",
        type=int,
        default=500_000,
        help="threads 扫描进度打印间隔（行数）",
    )
    args = parser.parse_args()

    data_root: Path = args.data_root
    feed_path = data_root / "feed_posts" / "feed_posts" / f"{args.feed_name}.jsonl.gz"
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    if not feed_path.exists():
        sys.exit(f"错误：找不到 feed 文件 {feed_path}")

    threads_path, is_gzip = resolve_threads_path(data_root)

    print(f"[1/4] 读取 {args.feed_name} feed_posts …")
    news_posts, news_stats = load_news_posts(feed_path)
    print(f"      载入 {len(news_posts):,} 条 post")

    print(f"[2/4] 流式扫描 threads（{threads_path.name}）…")
    scan_result = scan_threads(
        threads_path,
        is_gzip,
        news_posts,
        progress_every=args.progress_every,
    )

    print("[3/4] 分析 200 agents 分层抽样可行性 …")
    primary_summary = scan_result["condition_summaries"][PRIMARY_CANDIDATE_CONDITION]
    agent_analysis = analyze_agent_sampling(
        news_posts,
        scan_result["user_matched_thread_post_count"],
        primary_summary,
    )

    conclusion = build_feasibility_conclusion(
        news_stats,
        scan_result["join_stats"],
        scan_result["condition_summaries"],
        agent_analysis,
    )

    json_payload = {
        "generated_at": datetime.now().isoformat(),
        "data_root": str(data_root),
        "feed_name": args.feed_name,
        "feed_path": str(feed_path),
        "threads_path": str(threads_path),
        "news_stats": news_stats,
        "join_stats": scan_result["join_stats"],
        "condition_summaries": scan_result["condition_summaries"],
        "agent_sampling": {
            k: v for k, v in agent_analysis.items() if k != "user_rows"
        },
        "feasibility_conclusion": conclusion,
        "primary_candidate_condition": PRIMARY_CANDIDATE_CONDITION,
    }

    print("[4/4] 写入报告 …")
    write_json_report(output_dir / "news_threads_join_report.json", json_payload)
    write_markdown_report(
        output_dir / "news_threads_join_report.md",
        data_root,
        args.feed_name,
        news_stats,
        scan_result["join_stats"],
        scan_result["condition_summaries"],
        agent_analysis,
        conclusion,
        feed_path,
        threads_path,
    )
    write_candidate_threads_csv(
        output_dir / "news_candidate_threads.csv",
        scan_result["candidate_thread_rows"],
    )
    write_candidate_users_csv(
        output_dir / "news_candidate_users.csv",
        agent_analysis["user_rows"],
    )

    print_terminal_summary(
        news_stats,
        scan_result["join_stats"],
        scan_result["condition_summaries"],
        agent_analysis,
        conclusion,
    )
    print(f"报告已保存至：{output_dir.resolve()}")


if __name__ == "__main__":
    main()
