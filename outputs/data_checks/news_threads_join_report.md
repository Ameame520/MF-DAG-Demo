# News × threads Join 覆盖率检查报告

生成时间：2026-06-09 14:37:47

## 1. 检查目标

验证 Bluesky News feed 的 `post_id` 能否与 `threads.txt` 有效 join，并评估是否足以支撑 MF-DAG 主实验（500–2000 threads、200 agents、post-level thread sequence propagation）。

## 2. 数据路径

- 数据根目录：`/Users/fgod/Desktop/FGOD/MF-DAG/MF-DAG/data`
- Feed：`News` → `/Users/fgod/Desktop/FGOD/MF-DAG/MF-DAG/data/feed_posts/feed_posts/News.jsonl.gz`
- Threads：`/Users/fgod/Desktop/FGOD/MF-DAG/MF-DAG/data/graphs/graphs/threads.txt`（gzip=False）

## 3. News feed 基础统计（A）

| 指标 | 值 |
|------|-----|
| 总 posts | 42,112 |
| unique post_id | 41,685 |
| unique user_id | 75 |
| 时间范围 | 202302200227 – 202403182341 |
| text 非空 | 41,639 (98.88%) |
| reply_to 非空 | 683 |
| quotes 非空 | 0 |
| like_count mean/median/max | 43.18 / 3.0 / 4017 |
| reply_count mean/median/max | 1.62 / 0.0 / 441 |
| repost_count mean/median/max | 5.24 / 1.0 / 1197 |

## 4. threads join 覆盖率（B）

| 指标 | 值 |
|------|-----|
| 扫描 thread 总数 | 19,486,141 |
| 至少命中 1 个 News post | 56,889 |
| 至少命中 2 个 News post | 788 |
| 至少命中 3 个 News post | 76 |
| 至少命中 5 个 News post | 7 |
| News post 被 threads 覆盖 | 1,311 (3.15%) |
| 被覆盖 News posts 涉及 unique user | 46 |

## 5. 候选 thread 筛选结果（C）

### condition_1

- 候选 thread 数：**54,039**
- thread_len：mean=15.05, median=4, max=10808
- matched_post_count：mean=1.02, median=1, max=10
- join_coverage：mean=0.2817, median=0.25
- unique user_id：45
- 足够 200 agents：否 | 500 threads：是 | 1000：是 | 2000：是

### condition_2

- 候选 thread 数：**677**
- thread_len：mean=127.27, median=13, max=10808
- matched_post_count：mean=2.16, median=2, max=10
- join_coverage：mean=0.2385, median=0.15789473684210525
- unique user_id：25
- 足够 200 agents：否 | 500 threads：是 | 1000：否 | 2000：否

### condition_3

- 候选 thread 数：**539**
- thread_len：mean=158.98, median=25, max=10808
- matched_post_count：mean=2.18, median=2, max=10
- join_coverage：mean=0.141, median=0.08695652173913043
- unique user_id：24
- 足够 200 agents：否 | 500 threads：是 | 1000：否 | 2000：否

### condition_4

- 候选 thread 数：**65**
- thread_len：mean=372.38, median=24, max=10808
- matched_post_count：mean=3.48, median=3, max=10
- join_coverage：mean=0.1969, median=0.14285714285714285
- unique user_id：13
- 足够 200 agents：否 | 500 threads：否 | 1000：否 | 2000：否

### condition_5

- 候选 thread 数：**7**
- thread_len：mean=5.71, median=5, max=7
- matched_post_count：mean=3.29, median=3, max=4
- join_coverage：mean=0.5776, median=0.6
- unique user_id：5
- 足够 200 agents：否 | 500 threads：否 | 1000：否 | 2000：否

### condition_6

- 候选 thread 数：**53**
- thread_len：mean=455.19, median=31, max=10808
- matched_post_count：mean=3.55, median=3, max=10
- join_coverage：mean=0.1294, median=0.12
- unique user_id：13
- 足够 200 agents：否 | 500 threads：否 | 1000：否 | 2000：否

## 6. 200 agents 分层抽样可行性（D）

- 候选 user 总数：**45**
- activity_score 分布：min=13, p25=167.0, median=490.0, p75=1790.0, max=15692, mean=2094.73
- 分层方案（200 人）：high 20%=40, middle 50%=100, low 30%=60
- 各层可用人数：high=9, middle=5, low=31
- 能否分层抽 200 人：**不足**

替代方案：
- 候选 user 仅 45 人，不足 200；可放宽 thread 筛选条件（如 condition_1）或合并多个 feed。
- high 活跃度层仅 9 人，不足目标 40 人；可调整分层比例或降低 activity 分档阈值。
- middle 活跃度层仅 5 人，不足目标 100 人；可调整分层比例或降低 activity 分档阈值。
- low 活跃度层仅 31 人，不足目标 60 人；可调整分层比例或降低 activity 分档阈值。

## 7. MF-DAG 主实验可行性结论

- News feed 可用：**是**
- 支撑 500–2000 threads：**是**
- 支撑 200 agents：**否**
- post-level thread propagation 可行：**否**
- 推荐筛选条件：`condition_2`

## 8. 退路方案

- News post 在 threads 中覆盖率偏低，可仅用 matched posts 做 cascade 子集实验，或换用覆盖面更大的 feed（如 Popular 或全 interactions 推导的 thread）。
- 候选 user 仅 45 人，不足 200；可放宽 thread 筛选条件（如 condition_1）或合并多个 feed。
- high 活跃度层仅 9 人，不足目标 40 人；可调整分层比例或降低 activity 分档阈值。
- middle 活跃度层仅 5 人，不足目标 100 人；可调整分层比例或降低 activity 分档阈值。
- low 活跃度层仅 31 人，不足目标 60 人；可调整分层比例或降低 activity 分档阈值。