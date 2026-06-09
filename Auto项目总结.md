# MF-DAG 本地数据体检报告（可直接复制给另一个 LLM）

> 检查时间：2026-06-08  
> 检查目录：`/Users/fgod/Desktop/FGOD/MF-DAG/MF-DAG/data/`（注：用户指定的 `data/raw` 子目录**不存在**，实际数据在 `data/` 根下）  
> 检查者：当前 Cursor 会话（Composer）

---

## 重要说明

本报告基于**快速扫描**（`head`、`wc -l`、全量日期/类型扫描、feed_posts 全量遍历、followers capture-recapture 抽样），未对 6GB+ 大文件做逐行深度解析。所有数字均来自本次本地实测。

---

## A. 数据文件清单

### 解压后实际目录结构

```
data/
├── followers.csv                       (1.8 GB, 144,581,603 行)
├── interactions.csv                    (6.0 GB, 152,728,104 行)
├── feed_bookmarks.csv                  (540 KB, 18,324 行)
├── feed_posts/
│   └── feed_posts/                     (11 个 .jsonl.gz，按 feed 切片)
│       ├── #Disability.jsonl.gz
│       ├── #UkrainianView.jsonl.gz
│       ├── AcademicSky.jsonl.gz
│       ├── Blacksky.jsonl.gz
│       ├── BookSky.jsonl.gz
│       ├── Game Dev.jsonl.gz
│       ├── GreenSky.jsonl.gz
│       ├── News.jsonl.gz
│       ├── Political Science.jsonl.gz
│       ├── Science.jsonl.gz
│       └── What's History.jsonl.gz
├── feed_posts_likes/
│   └── feed_posts_likes/               (11 个 .csv.gz，与 feed_posts 一一对应)
├── graphs/
│   └── graphs/
│       ├── replies.csv                 (1.8 GB, 87,550,414 行)
│       ├── reposts.csv                 (1.3 GB, 63,438,069 行)
│       ├── quotes.csv                  (250 MB, 12,085,583 行)
│       └── threads.txt.gz              (261 MB, 19,486,141 行)
└── scripts/
    └── scripts/                        (数据采集/清洗/实验脚本，非原始数据)
```

### 与 Zenodo 页面对照

| Zenodo 提及 | 本地是否存在 | 备注 |
|---|---|---|
| `followers.csv.gz` | ✅ `followers.csv` | 已解压 |
| `interactions.csv.gz` | ✅ `interactions.csv` | 已解压 |
| `posts/` | ✅ `feed_posts/feed_posts/*.jsonl.gz` | 命名不同，按 feed 切片 |
| `graphs/` | ✅ `graphs/graphs/*.csv` + `threads.txt.gz` | **threads.txt.gz 是 Zenodo 未强调的关键文件** |
| `feed_post_likes/` | ✅ `feed_posts_likes/feed_posts_likes/*.csv.gz` | 命名略有差异 |
| — | ✅ `feed_bookmarks.csv` | Zenodo 未提及，额外文件 |

### 关键字段存在性确认

| 字段名 | 是否存在 | 所在文件 | 说明 |
|---|---|---|---|
| `post_id` | ✅ | `feed_posts/*.jsonl.gz`, `feed_posts_likes/*.csv.gz` | post 级唯一 ID |
| `thread_id` | ❌ | — | **无此字段名** |
| `root_post_id` | ⚠️ 等价字段 | `feed_posts` 中的 `thread_root` | 仅 3.45% post 非空 |
| `reply_to` | ✅ | `feed_posts` | 被回复 post 的 `post_id`，仅 3.45% 非空 |
| `repost_of` | ❌ | — | **无此字段名**；repost 仅有 author 级 `reposted_author` |
| `quote_of` | ⚠️ 等价字段 | `feed_posts` 中的 `quotes` | 被引用 post 的 `post_id`，18.27% 非空 |
| `author_id` | ⚠️ 等价字段 | 各文件中的 `user_id` / `src` / `dst` | 统一整数 ID 体系 |
| `created_at` / `timestamp` | ⚠️ 等价字段 | 各文件中的 `date` | 格式 `yyyymmddhhmm`（12 位）或 `yyyymmdd`（8 位） |

---

## B. 每个核心文件的前几行

### `head -n 5 followers.csv`

```
0,1
0,10
0,100
0,101
0,102
```

含义：`u, v` = 用户 u follow 用户 v。无表头。

---

### `head -n 5 interactions.csv`

```
836672,None,None,833271,None,202309192352
836672,None,None,61971,None,202310021913
836672,None,None,47191,None,202309231547
836672,None,None,17234,None,202309301358
836672,None,None,20490,None,202307261536
```

无表头。6 列顺序（与 Zenodo 描述一致）：

```
user_id, replied_author, thread_root_author, reposted_author, quoted_author, date
```

- `None` 用字符串 `"None"` 表示空值
- `date` 格式：`YYYYMMDDHHMM`（12 位无分隔符）
- 一行可同时填多个 `*_author` 字段（一行 post 触发多种互动）

---

### `head -n 5 feed_bookmarks.csv`

```
Science,408833,202309192111
Science,204992,202307290107
Science,1798953,202309232103
Science,1428436,202311051321
Science,976464,202309131041
```

含义：`feed_name, user_id, date`。用户订阅/书签某 feed。

---

### `head -n 5 graphs/graphs/replies.csv`

```
836672,44300,20230827
836672,169982,20230826
45957,168349,20240209
45957,46191,20231223
45957,46191,20231223
```

### `head -n 5 graphs/graphs/reposts.csv`

```
836672,833271,20230919
836672,61971,20231002
836672,47191,20230923
836672,17234,20230930
836672,20490,20230726
```

### `head -n 5 graphs/graphs/quotes.csv`

```
836672,559307,20230826
45957,45957,20231222
45957,45957,20231222
45957,86070,20231108
45957,703707,20231023
```

三文件均无表头，列：`src_author_id, dst_author_id, date`（date 为 8 位 `yyyymmdd`）。**仅有 author→author 方向，无 post_id。**

---

### `head -n 5 graphs/graphs/threads.txt.gz`（tab 分隔）

```
47	202308261051	1074176,119298,119299,720392,587786,...(共 134 个 author)
54	202308261844	836672,243265,392482,243266,856517,629854,102570,699309,121296,50489,169982
60	202402090131	45957,750410,302188,1252333,137650,817691,168349,198942
94	202312221808	152071,205832,131082,...(共 100+ 个 author)
103	202312161652	45957,131135
```

列：

1. `thread_root_id`（整数，thread root 的内部分配 ID，**不是 post_id**）
2. `root_time`（root post 创建时间，`yyyymmddhhmm`）
3. `participants`（参与该 thread 的 `author_id` 列表，逗号分隔，按加入顺序）

---

### `head -n 3 feed_posts/feed_posts/Blacksky.jsonl.gz`

```json
{"post_id": 34631950, "user_id": 37717, "instance": "bsky.social", "date": 202403182357, "text": "I know for a fact that even were I to cast my vote for Biden, too many other Americans have said no, I cannot check a box on a ballot for a man who is committing genocide, for him to be able to be victorious at the polls in November.", "langs": ["eng"], "like_count": 9, "reply_count": 0, "repost_count": 4, "reply_to": null, "replied_author": null, "thread_root": null, "thread_root_author": null, "quotes": null, "quoted_author": null, "labels": null}
{"post_id": 194684721, "user_id": 34671, "instance": "bsky.social", "date": 202403182357, "text": "In good news I haven't messaged them in 21 days which is wholly a record for me, and I honestly may never message them again", "langs": ["eng"], "like_count": 5, "reply_count": 1, "repost_count": 0, "reply_to": null, "replied_author": null, "thread_root": null, "thread_root_author": null, "quotes": 194684722, "quoted_author": 34671, "labels": null}
{"post_id": 194684722, "user_id": 34671, "instance": "bsky.social", "date": 202403182356, "text": "Since the Discord update there's a 50/50 chance that it's going to flash random profiles of people I'm friends with at the top of my messages as it's loading in the actual account activity thing, & I hate this because it almost always flashes my ex's profile first which just makes me sad", "langs": ["eng"], "like_count": 3, "reply_count": 0, "repost_count": 0, "reply_to": null, "replied_author": null, "thread_root": null, "thread_root_author": null, "quotes": null, "quoted_author": null, "labels": null}
```

完整 16 个字段：

```
post_id, user_id, instance, date, text, langs, like_count, reply_count, repost_count,
reply_to, replied_author, thread_root, thread_root_author, quotes, quoted_author, labels
```

---

### `head -n 5 feed_posts_likes/feed_posts_likes/Blacksky.csv.gz`

```
518419,37717,34631950,202403190307
233280,37717,34631950,202403190006
66817,37717,34631950,202403190002
283286,37717,34631950,202403190002
9315,37717,34631950,202403190010
```

无表头，列：`liker_user_id, post_author_id, post_id, date`。

---

## C. 字段名、数据量、时间范围

### 核心规模汇总

| 指标 | 数值 |
|---|---|
| **interactions 行数** | 152,728,104 |
| **followers 行数** | 144,581,603 |
| **posts 行数**（11 feed 合计） | 168,463 |
| **like 边数**（feed_posts_likes 合计） | 4,895,318 |
| **threads 数**（threads.txt.gz） | 19,486,141 |
| **replies 边数** | 87,550,414 |
| **reposts 边数** | 63,438,069 |
| **quotes 边数** | 12,085,583 |

### 时间范围

| 数据源 | 最早 | 最晚 |
|---|---|---|
| interactions.csv（全量扫描） | 202302170001 | 202403182359 |
| feed_posts（全量扫描） | 202302200227 | 202403182359 |
| threads.txt.gz（抽样） | 20230217 | 20240318 |
| graphs/replies.csv（抽样） | 20230404 | 20240318 |
| graphs/reposts.csv（抽样） | 20230419 | 20240318 |
| graphs/quotes.csv（抽样） | 20230429 | 20240318 |
| feed_bookmarks.csv | 202307 | 202311 |

**整体跨度：约 13 个月（2023-02-17 ~ 2024-03-18）**

> 注意：`feed_posts` 是 firehose 按 feed 标签筛的子集，时间集中在 2024-03；而 `followers` / `interactions` / `graphs` 覆盖完整 13 个月。

### 用户数量

- `followers.csv` 中最大 `user_id`：4,099,698（ID 稀疏，不等于用户数）
- Capture-recapture 估计（两个不相交 1% 采样）：**约 1,930,000 unique users**
- 综合判断：**活跃核心约 1.4M ~ 2.8M unique users**（重尾分布）

### interactions.csv 互动类型分布（全量扫描，每行可多标签）

| 类型 | 行数 | 占比 |
|---|---|---|
| reply（`replied_author` 非 None） | 87,550,422 | 57.3% |
| thread_root（`thread_root_author` 非 None） | 87,550,422 | 57.3% |
| repost（`reposted_author` 非 None） | 63,438,073 | 41.5% |
| quote（`quoted_author` 非 None） | 12,085,583 | 7.9% |

- 约 **61%** 的行同时属于多种互动类型（如同一 post 既 reply 又 repost）
- **interactions.csv 没有 like 类型**；like 在 `feed_posts_likes` 中

### feed_posts 各 feed 明细

| feed | posts | reply_to 非空 | thread_root 非空 | quotes 非空 | 含 text |
|---|---|---|---|---|---|
| #Disability | 566 | 0 | 0 | 80 | 566 (100%) |
| #UkrainianView | 2,098 | 204 | 204 | 352 | 2,097 (100%) |
| AcademicSky | 913 | 71 | 71 | 77 | 913 (100%) |
| **Blacksky** | **86,490** | **0** | **0** | **24,776** | 85,411 (98.8%) |
| BookSky | 638 | 57 | 57 | 71 | 638 (100%) |
| Game Dev | 635 | 106 | 106 | 21 | 635 (100%) |
| GreenSky | 662 | 288 | 288 | 59 | 662 (100%) |
| News | 42,112 | 683 | 683 | 0 | 41,639 (98.9%) |
| Political Science | 357 | 0 | 0 | 231 | 357 (100%) |
| Science | 33,831 | 4,399 | 4,399 | 5,063 | 33,831 (100%) |
| What's History | 161 | 0 | 0 | 41 | 161 (100%) |
| **合计** | **168,463** | **5,808 (3.45%)** | **5,808 (3.45%)** | **30,771 (18.27%)** | **166,910 (99.1%)** |

### threads.txt.gz 统计

- 行数：19,486,141
- 每 thread 参与者数：min=1, max=10,808, avg=3.1

---

## D. 是否能还原传播链

### 结论先行

| 传播链类型 | post-level 可还原？ | 数据来源 | 可靠度 |
|---|---|---|---|
| **Author-level cascade / thread propagation** | ✅ 完全可以 | `threads.txt.gz` | ⭐⭐⭐ 最稳，MF-DAG 论文核心输入 |
| **Quote 链** | ✅ 可以 | `feed_posts.quotes` → `post_id` | ⭐⭐⭐ 18% post 有 quote 目标 |
| **Like 链** | ✅ 可以 | `feed_posts_likes` 有 `post_id` | ⭐⭐⭐ |
| **Reply 链** | ⚠️ 极稀疏 | `feed_posts.reply_to` / `thread_root` | ⭐ 仅 3.45% 非空 |
| **Repost 链** | ❌ 不可 | 仅 `reposted_author`，无 `post_id` | — |

### D1. Author-level cascade（推荐，最稳）

`graphs/graphs/threads.txt.gz` 直接给出 **19.5M 个 thread**，每行：

```
thread_root_id \t root_time \t author_1,author_2,author_3,...
```

可还原的传播结构（author 级）：

```
thread root (author A, time T)
 ├── author B 加入
 ├── author C 加入
 ├── author D 加入（reply）
 └── author E 加入（repost/quote 参与者)
```

**这是 MF-DAG 论文的标准做法**：超图由 thread_root 切分，节点是 author，超边是 thread 参与者集合。

可做：thread 长度/深度/宽度分布、author 参与时序、cohort 历史行为、传播形状特征。

### D2. Post-level cascade（受限）

理想结构：

```
root post A (post_id=xxx)
 ├── reply 1 (reply_to=xxx)
 ├── repost 1 (repost_of=xxx)    ← 本地无此字段
 ├── quote 1 (quotes=xxx)
 └── reply 2 (reply_to=reply1)
```

**实际情况：**

1. **Reply 链**：`feed_posts` 有 `reply_to` 和 `thread_root` 字段，但本地未清理版中 **96.55% 为 null**。原因是 feed_posts 是 firehose 按 feed 标签筛的子集，很多 post 缺少完整 reply 引用结构。`interactions.csv` 的 `replied_author` / `thread_root_author` 仅有 author_id，**无 post_id**。

2. **Quote 链**：`feed_posts.quotes` 字段给出被引用 post 的 `post_id`，**可严格 post-level 还原**。Blacksky 单 feed 就有 24,776 条 quote 边。

3. **Repost 链**：`reposts.csv` 和 `interactions.reposted_author` 仅有 author→author 边，**无 post_id**，无法做 post-level repost 树。

4. **Like 链**：`feed_posts_likes` 有完整 `(liker, post_id, date)`，可做 post-level like 传播分析。

### D3. interactions.csv 关键限制

```
replied_author ≠ replied_post_id
thread_root_author ≠ root_post_id
reposted_author ≠ reposted_post_id
quoted_author ≠ quoted_post_id
```

无法从 `interactions.csv` 直接还原 post-level 树。需要 join `feed_posts`（但 `reply_to` 在那里也大多 None）。

### D4. 实验设计建议

| 实验目标 | 推荐数据 | 理由 |
|---|---|---|
| MF-DAG 风格超图传播 | `threads.txt.gz` | 现成 19.5M thread，author 级传播链 |
| Follow + 互动图组合 | `followers.csv` + `interactions.csv` + `graphs/*.csv` | 齐全，13 个月 |
| Post-level quote cascade | `feed_posts.quotes` | 字段完整 |
| LLM-agent 读文本决策 | `feed_posts.text` | 99.1% 有文本 |
| 传播速度/比例统计 | `interactions.csv` 按 `thread_root_author` + 时间窗口聚合 | 结构化状态，无需文本 |

---

## E. 是否有文本内容

### 结论：✅ 有文本，覆盖率 99.1%

`feed_posts/*.jsonl.gz` 中 **166,910 / 168,463** 条 post 有 `text` 字段。

各 feed 文本覆盖率见 C 节表格（绝大多数 100%，Blacksky 98.8%，News 98.9%）。

### 文本示例（Blacksky 实测）

```
post_id=34631950, user_id=37717
text="I know for a fact that even were I to cast my vote for Biden, too many other Americans have said no, I cannot check a box on a ballot for a man who is committing genocide, for him to be able to be victorious at the polls in November."
```

### 有 `reply_to` 的 post 示例（Science feed）

```json
{"post_id": 215542741, "user_id": 35328, "reply_to": 45969007, "thread_root": ..., "text": "Seeing more content from folks I'm following..."}
```

### LLM-agent 可用输入

| 输入类型 | 是否可用 | 数据来源 |
|---|---|---|
| root post 文本摘要 | ✅ | `feed_posts.text` |
| 高互动 reply/quote 文本 | ✅（quote 链完整；reply 链稀疏） | `feed_posts` |
| cohort 历史行为摘要 | ✅ | `interactions.csv` + `graphs/*.csv` + `threads.txt.gz` |
| 当前传播速度 | ✅ | `interactions.csv` 时间窗口聚合 |
| reply/repost/quote 比例 | ✅ | `interactions.csv` 类型统计 |
| cohort 活跃度 | ✅ | `followers.csv` + 互动频率 |

### 时间窗口注意

- **文本**集中在 2024-03（feed_posts 是 firehose 抽样子集）
- **结构化行为**覆盖 2023-02 ~ 2024-03 完整 13 个月
- LLM 读文本 + 结构化历史行为是可行组合，但需注意两者时间覆盖不完全对齐

---

## 关键 Takeaway（给另一个 LLM 的速查）

1. **想做严格 post-level cascade**：只能用 **quote 链**（`feed_posts.quotes` 完整）和 **like 链**；reply 链在 feed_posts 里太稀疏（3.45%）；repost 无 post_id。

2. **想做 author-level cascade / MF-DAG 超图传播**：用 **`graphs/graphs/threads.txt.gz`**，19.5M thread，每行 = root time + 按时间序的 author 列表。这是论文核心输入。

3. **follow graph + 互动图**：`followers.csv`（1.45 亿边）+ `interactions.csv`（1.53 亿行）+ `graphs/*.csv` 齐全。

4. **LLM-agent 可读真实文本**：feed_posts 99.1% 有 `text`。

5. **时间跨度**：2023-02-17 ~ 2024-03-18（13 个月）。

6. **规模**：~1.9M unique users，1.53 亿 interactions，1.45 亿 follower 边，19.5M threads。

7. **陷阱**：`interactions.csv` 6 列与 Zenodo 一致，但 `*_author` 字段是 author_id 不是 post_id；`feed_posts` 虽有 `reply_to`/`thread_root` 字段名，但 96.55% 为 null，不要被字段名误导。

8. **额外宝藏**：`feed_bookmarks.csv`（feed 级兴趣）和 `threads.txt.gz`（现成传播链）是 Zenodo 页面未强调但对实验极有用的文件。

---

*报告生成方式：本地 `head` / `wc -l` / Python 快速扫描，未下载或联网核验 Zenodo 页面。*
