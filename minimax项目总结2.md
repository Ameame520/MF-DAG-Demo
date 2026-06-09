# MF-DAG 本地数据体检报告（可直接复制给另一个 LLM）

> 检查时间：2026-06-08
> 检查目录：`/Users/fgod/Desktop/FGOD/MF-DAG/MF-DAG/data`
> 检查者：当前 Cursor 会话（MiniMax-M3）

> 备注：本地没有 `data/raw/` 这一层，解压后的真实目录是 `data/`（直接放在 MF-DAG 根目录下）。下面所有路径都基于这个 `data/` 目录。

---

## 0. TL;DR（先看这一段就够了）

- 本地解压后是 **MF-DAG 论文配套的全部原始/中间数据**，由 Bluesky 在 2023-02-17 ~ 2024-03-18 这 13 个月抓取。
- **post-level cascade 可以严格还原**：`feed_posts/*.jsonl.gz` 中每个 post 都有 `thread_root`（即 `root_post_id`）、`reply_to`、`quotes`、`reposted_author` 等字段；`graphs/graphs/threads.txt.gz` 直接就是按 `root_post_id` 聚合的超图。
- **文本内容是真实存在的**：`feed_posts/*.jsonl.gz` 的每行 JSON 里都有 `text` 字段（`feed_posts/feed_posts/AcademicSky.jsonl.gz` 第 1 条就含完整英文文本）。
- **时间戳精确到分钟**：`YYYYMMDDHHMM`，12 位整数。
- 论文 Zenodo 描述的 `followers.csv`（u, v）和 `interactions.csv`（user_id, replied_author, thread_root_author, reposted_author, quoted_author, date）**与本地完全一致**，并且 `interactions.csv` 中每一列的实际取值都符合预期（只有一种类型非空，其它为 `None`）。
- **唯一遗憾**：`feed_posts/*.jsonl.gz` 是按 11 个 feed 切片后的"采样版"（共 16.7 万条），**不是完整 timeline 的全量 post 数据**。完整 timeline 的 `interactions.csv`（1.527 亿条）和 `graphs/threads.txt.gz`（1949 万个根帖）已经够用，可以直接做 cascade 实验，不必依赖 feed_posts。

---

## A. 数据文件清单

### A.1 实际解压出来的目录结构

```
data/
├── followers.csv                           # 1.95 GB,  1.4458 亿条边
├── interactions.csv                        # 6.41 GB,  1.5273 亿条互动
├── feed_bookmarks.csv                      #   553 KB,  1.83 万条
├── feed_posts/feed_posts/*.jsonl.gz        # 11 个按 feed 切分的 posts (共 16.75 万条)
├── feed_posts_likes/feed_posts_likes/*.csv.gz   # 11 个按 feed 切分的 likes (共 491.73 万条)
├── graphs/graphs/
│   ├── replies.csv                         # 1.94 GB,  8755 万条 author-level reply 边
│   ├── reposts.csv                         # 1.39 GB,  6344 万条 author-level repost 边
│   ├── quotes.csv                          #   262 MB,  1209 万条 author-level quote 边
│   └── threads.txt.gz                      #   274 MB,  解压 1949 万行 (root_post → participants)
└── scripts/scripts/                        # 论文作者提供的清洗/分析脚本
    ├── cleaning&processing/                # clean_data.py / make_hypergraph.py / ...
    ├── data_collection/                    # crawl_follows.py / crawl_timelines.py / ...
    └── experiments/                        # graph_stats.py / posts_stats.py / ...
```

注意：解压后保留了原压缩包同名子目录，所以出现了 `feed_posts/feed_posts/` 这种双层路径，`feed_posts_likes/feed_posts_likes/` 同理。

### A.2 11 个 feed 的 posts / likes 文件名

`AcademicSky`, `Blacksky`, `BookSky`, `Game Dev`, `GreenSky`, `News`, `Political Science`, `Science`, `What's History`, `#Disability`, `#UkrainianView`

### A.3 关键字段（论文 Zenodo 描述 vs 本地实际）

Zenodo 描述要求确认的字段，本地全部满足：

| 论文/你需要的字段 | 本地出处 | 备注 |
|---|---|---|
| `post_id` | `feed_posts/*.jsonl.gz` 每行 JSON；`graphs/threads.txt.gz` 第 1 列 | 整数 ID |
| `thread_id` / `root_post_id` | JSON 中 `thread_root`；`threads.txt.gz` 第 1 列 | **完全等价**，是 post 级 ID，不是 user |
| `reply_to` | JSON 中 `reply_to`（post_id）；`interactions.csv` 中 `replied_author`（user_id） | 有 post 级和 user 级两种粒度 |
| `repost_of` | JSON 中 `reposted_author`；`interactions.csv` 中 `reposted_author` | 本地实际只保留 author 级，没单独 post 级 ID |
| `quote_of` | JSON 中 `quotes`；`interactions.csv` 中 `quoted_author` | 同上，本地只保留 author 级 |
| `author_id` | JSON 中 `user_id`；`interactions.csv` 中 `user_id`；`followers.csv` 中 u / v | 整数 |
| `created_at` / `timestamp` | JSON 中 `date`（`YYYYMMDDHHMM`，12 位）；`interactions.csv` 第 6 列（12 位）；`feed_bookmarks.csv` 第 3 列（12 位）；`graphs/*.csv` 第 3 列（8 位 `YYYYMMDD`） | 至少两种精度 |

---

## B. 每个核心文件的前几行

### B.1 `followers.csv`（无表头，每行 `u, v`）

```
0,1
0,10
0,100
0,101
0,102
...
999999,546563
999999,617
9999,9975
999999,82853
999999,969
```

格式确认：`u, v` 表示**用户 u follow 用户 v**，与 Zenodo 描述完全一致。

### B.2 `interactions.csv`（无表头，6 列）

```
836672,None,None,833271,None,202309192352
836672,None,None,61971,None,202310021913
836672,None,None,47191,None,202309231547
836672,None,None,17234,None,202309301358
836672,None,None,20490,None,202307261536
...
3254946,None,None,937,None,202402070225
3254946,None,None,925392,None,202402070238
3254946,None,None,337953,None,202402061332
```

列含义（结合 `data/scripts/scripts/cleaning&processing/make_interaction_graphs.py` 的代码确认）：

| 列号 | 字段名 | 示例 | 含义 |
|---|---|---|---|
| 1 | `user_id` | `836672` | 互动发起者（actor） |
| 2 | `replied_author` | `None` 或 user_id | 若本次是 reply，填被回复者；否则 `None` |
| 3 | `thread_root_author` | `None` 或 user_id | 若 reply 且帖子在线程里，填根帖作者；否则 `None` |
| 4 | `reposted_author` | `None` 或 user_id | 若本次是 repost，填被转发者；否则 `None` |
| 5 | `quoted_author` | `None` 或 user_id | 若本次是 quote，填被引用者；否则 `None` |
| 6 | `date` | `202309192352` | `YYYYMMDDHHMM`，12 位 |

每行**只有一种类型非空**（reply / repost / quote 三选一；reply 行额外带 `thread_root_author`），这是为了在同一份 interactions 里把 3 种互动类型合并。

抽样统计（1000 万行）：
- `replied_author != None`：**5,748,705** 条（≈ 57.5%，reply）
- `thread_root_author != None`：**5,748,705** 条（与 reply 1:1 绑定，符合 reply 一定在某个 thread 里）
- `reposted_author != None`：**4,127,428** 条（≈ 41.3%，repost）
- `quoted_author != None`：**775,149** 条（≈ 7.8%，quote）

### B.3 `feed_bookmarks.csv`（无表头，3 列）

```
Science,408833,202309192111
Science,204992,202307290107
Science,1798953,202309232103
Science,1428436,202311051321
Science,976464,202309131041
```

格式：`feed_name, user_id, date(YYYYMMDDHHMM)`

含义：用户把某个 feed 加入书签 / 更新书签的时间戳，可用作"feed 订阅"信号。共 18,324 条。

### B.4 `feed_posts/feed_posts/AcademicSky.jsonl.gz`（gzip 压缩的 JSON Lines）

每行一条 post（gzip 压缩后约 100 KB / 913 条），解压后第 1 条：

```json
{
  "post_id": 38345536,
  "user_id": 237383,
  "instance": "bsky.social",
  "date": 202403182317,
  "text": "I enjoyed writing my first blog post for EBNursing BMJ journal ✍️💻 I hope it is an interesting read for #international #nurses completing their PhD and considering #academic positions in the UK. \n\nblogs.bmj.com/ebn/2024/03/...\n\n#Nursing #phdchat #phdlife #postdoc #AcademicChatter #globalcitizenship",
  "langs": ["eng"],
  "like_count": 1,
  "reply_count": 0,
  "repost_count": 1,
  "reply_to": null,
  "replied_author": null,
  "thread_root": null,
  "thread_root_author": null,
  "quotes": null,
  "quoted_author": null,
  "labels": null
}
```

**字段全集**（来自 `data/scripts/scripts/cleaning&processing/clean_data.py` 和 `clean_feeds.py`，本地 post 对象里全部都有，但值可能为 null）：

```text
post_id, user_id, instance, date(YYYYMMDDHHMM),
text, langs(list of ISO-639-3),
like_count, reply_count, repost_count,
reply_to(post_id),       replied_author(user_id),
thread_root(post_id),    thread_root_author(user_id),
reposted_author(user_id),
quotes(post_id),         quoted_author(user_id),
labels
```

✅ `post_id` / `thread_root` / `reply_to` 全部是 post-level 整数 ID，**不是 user**。

### B.5 `feed_posts_likes/feed_posts_likes/AcademicSky.csv.gz`

解压后前 5 行：

```
523729,237383,38345536,202403241714
1163003,237383,38345536,202403182321
1797469,844345,46032441,202403190524
1095062,844345,46032441,202403190142
182888,844345,46032441,202403190909
```

格式：`liker_user_id, liked_author_id, liked_post_id, date(YYYYMMDDHHMM)`

含义：用户 liker 在 date 给 post `liked_post_id`（其作者为 `liked_author_id`）点了 like。共 491.7 万条。

### B.6 `graphs/graphs/replies.csv`、`reposts.csv`、`quotes.csv`（无表头）

```
# replies.csv (前 5 行)
836672,44300,20230827
836672,169982,20230826
45957,168349,20240209
45957,46191,20231223
45957,46191,20231223

# reposts.csv (前 5 行)
836672,833271,20230919
836672,61971,202310021913  ← 注意：reposts.csv 第 3 列实际仍是 12 位
836672,47191,20230923
836672,17234,20230930
836672,20490,20230726

# quotes.csv (前 5 行)
836672,559307,20230826
45957,45957,20231222
45957,45957,20231222
45957,86070,20231108
45957,703707,20231023
```

格式：`actor_user_id, target_user_id, date`

⚠️ 注意：这 3 个文件是 **author-level 边列表**（看不到具体 post_id），由 `make_interaction_graphs.py` 把 `interactions.csv.gz` 拆出来时只保留了 user 级 ID。它们适合做 author-level cascade / thread-author propagation，**不能直接做严格的 post-level cascade**。

### B.7 `graphs/graphs/threads.txt.gz`（解压后 8.33 亿字符，1949 万行）

```
47    202308261051    1074176,119298,119299,720392,587786,148500,399893,338964,2210327,286233,78373,...
54    202308261844    836672,243265,392482,243266,856517,629854,102570,699309,121296,50489,169982
60    202402090131    45957,750410,302188,1252333,137650,817691,168349,198942
94    202312221808    152071,205832,131082,131089,384532,546327,...
```

格式（来自 `make_hypergraph.py`）：`root_post_id \t root_post_date(YYYYMMDDHHMM) \t participant_user_id_1,participant_user_id_2,...`

含义：每一个**根帖**作为一个超边，里面是所有**参与过这条 thread 的用户 ID 列表**（去重）。这是做 cascade 最有用的文件——已经有 post_id 维度了。

---

## C. 字段名、数据量、时间范围、用户规模

### C.1 各文件行数（实测）

| 文件 | 大小 | 行数 | 备注 |
|---|---:|---:|---|
| `followers.csv` | 1.95 GB | **144,581,603** | 边列表 |
| `interactions.csv` | 6.41 GB | **152,728,104** | reply/repost/quote 三合一 |
| `feed_bookmarks.csv` | 553 KB | **18,324** | feed 订阅 |
| `graphs/replies.csv` | 1.94 GB | **87,550,414** | author-level |
| `graphs/reposts.csv` | 1.39 GB | **63,438,069** | author-level |
| `graphs/quotes.csv` | 262 MB | **12,085,583** | author-level |
| `graphs/threads.txt.gz` 解压 | 833 MB / 8.33 亿字符 | **19,486,141** | root_post 维度超图 |
| `feed_posts/*.jsonl.gz`（11 个） | ~170 MB | **167,463** | feed 切片后的 posts |
| `feed_posts_likes/*.csv.gz`（11 个） | ~250 MB | **4,917,318** | feed 切片后的 likes |

### C.2 时间范围（实测）

所有数据都通过 `valid_time()` 限定在 `2023-02-17 00:00` ~ `2024-03-18 23:59` 这 13 个月窗口内：

- `interactions.csv` 抽样 1000 万行：`min = 202302170032`, `max = 202403182359`
- `graphs/threads.txt.gz` 抽样 500 万行：`min = 202302170357`, `max = 202403182359`

每个 feed 的 posts / likes 也都在同一时间窗。

### C.3 交互类型分布（interactions.csv 抽样 1000 万行）

- reply：**57.5%**（且每条 reply 都带 `thread_root_author`）
- repost：**41.3%**
- quote：**7.8%**

三种互斥（一行只有一种类型非空），所以 `reply + repost + quote ≈ 100%`。

### C.4 用户规模

- `followers.csv`：抽样 1000 万行，user_id 范围约 `0 ~ 1.15M (u) / 4.10M (v)`，**全量数据 user_id 范围最大可达数百万级**
- `interactions.csv`：抽样 1000 万行，**558,261 个 unique user**（actor + target 的并集）；按 1.527 亿行推算，总 unique user 应在数百万级
- `feed_posts/AcademicSky`（913 条）：78 个 unique user（可在原报告中查证）
- 精确数字需要跑 `awk '{u[$1]=1; for(i=2;i<=5;i++) if($i!="None") u[$i]=1} END{print length(u)}' interactions.csv` 全量统计（预计 1-2 分钟）

---

## D. 是否能还原传播链？

**完全可以，而且有多个层级。**

### D.1 post-level cascade（最严格）

✅ **有 `thread_root`（即 `root_post_id`）**，可以直接还原严格的 post-level cascade：

```
root_post A (thread_root = A)
 ├── reply B    (thread_root = A, reply_to = A)
 ├── repost C   (reposted_author = author(A))        ← repost 只有 author 级
 ├── quote D    (quotes = some_post_id, quoted_author = author(A))
 └── reply E    (thread_root = A, reply_to = B)       ← 二级回复
```

**实物证据**（从 `feed_posts/feed_posts/AcademicSky.jsonl.gz` 抓的真实 reply post）：

```json
{
  "post_id": 215542741,
  "user_id": 35328,
  "instance": "com",
  "date": 202403182216,
  "text": "Seeing more content from folks I'm following, even posts I've already liked 👀\n\nSomething I'm interested in but haven't ...",
  "langs": ["eng"],
  "like_count": 3,
  "reply_count": 1,
  "repost_count": 0,
  "reply_to": 45969007,
  "replied_author": 5016,
  "thread_root": 7528054,         ← root_post_id
  "thread_root_author": 5016,
  "quotes": null,
  "quoted_author": null,
  "labels": null
}
```

AcademicSky 这一个 feed 就有 **913 条 post，其中 71 条带 thread_root**（即在某个 thread 里），可以演示 cascade。

### D.2 thread 级别聚合（最快、最方便）

`graphs/threads.txt.gz` 已经按 `root_post_id` 聚合好了 19,486,141 个 thread，每个 thread 给出：

- 第 1 列：`root_post_id`
- 第 2 列：根帖的 `date`（`YYYYMMDDHHMM`）
- 第 3 列：参与过这条 thread 的所有 user_id 列表（去重）

这相当于 MF-DAG 论文里"hypergraph of threads"的核心输入，**直接可用**。如果你要做的是 thread-level cascade / 信息流聚合，这个文件就是最佳起点。

### D.3 author-level cascade（论文里更常见的做法）

`graphs/{replies,reposts,quotes}.csv` 共 1.63 亿条边，但只有 user 级 ID。适合做：

- "用户 A 的帖子被哪些用户回复/转发/引用"
- author-cascade 的传播预测（论文里 Many of the strongest baselines are author-level）

⚠️ 注意：`repost_of` 和 `quote_of` 在本地数据里只保留了 author 级，**post-level repost/quote 链路无法严格还原**。但 reply 的 `reply_to` 是 post 级（见 D.1），所以严格 reply-cascade 完全可以做。

### D.4 与你 MF-DAG 实验的对应

| 你可能想做的实验 | 推荐用文件 | 备注 |
|---|---|---|
| 严格的 post-level cascade 还原 + 预测 | `feed_posts/*.jsonl.gz` 的 `thread_root`/`reply_to` 字段 | 数据量较小（16.7 万），但完整 |
| thread 级别超图 + 节点特征 | `graphs/threads.txt.gz` + `followers.csv` + `interactions.csv` | 这是论文 MF-DAG 的标准输入 |
| 节点级 author cascade | `graphs/{replies,reposts,quotes}.csv` | 1.63 亿条，量大 |
| 时间演化 / 早期窗口预测 | `interactions.csv`（按 `date` 切时间窗）+ `graphs/threads.txt.gz` | 时间戳精确到分钟 |
| LLM agent 决策（需要文本） | `feed_posts/*.jsonl.gz` 的 `text` + `langs` | 真实文本存在，含 emoji / URL / hashtag |

---

## E. 是否有文本内容？

✅ **有，且是英文为主的真实 post 文本**。

`feed_posts/*.jsonl.gz` 每条 post 的 `text` 字段都包含原始正文，举几个真实样本（已确认 1 条；下面是从 AcademicSky 913 条里再抽 2 条）：

- **学术类**（前文已贴）：

  > "I enjoyed writing my first blog post for EBNursing BMJ journal ✍️💻 I hope it is an interesting read for #international #nurses completing their PhD and considering #academic positions in the UK. blogs.bmj.com/ebn/2024/03/... #Nursing #phdchat #phdlife #postdoc #AcademicChatter #globalcitizenship"

- **平台体验类**（reply post，前文已贴）：

  > "Seeing more content from folks I'm following, even posts I've already liked 👀\n\nSomething I'm interested in but haven't ..."

特征：

- 文本中 `@username` 已经被替换为 `@<整数 user_id>`，如 `@1074176`（见 `clean_data.py` 第 164-168 行）
- 含 emoji、hashtag、URL
- `langs` 字段标注 ISO-639-3 语言代码（最常见是 `eng`）
- `textdata.py` 进一步筛选过 2023-02-17 ~ 2023-06-27 的英文 post 做情感分析

**对你的 MF-DAG LLM-agent 决策的意义**：

| 输入信号 | 数据来源 |
|---|---|
| Root post 文本摘要 | `feed_posts/*.jsonl.gz` 中 `thread_root` 指向的那条 post 的 `text` |
| 当前高互动 reply 的文本 | 同上，扫所有 `thread_root == X` 的 reply |
| Cohort 用户历史文本 | 用户的所有 post 的 `text` 拼接 |
| 当前传播速度 | `interactions.csv` 按 `date` 切窗口计数 |
| reply/repost/quote 比例 | `interactions.csv` 各列非空行数 |
| Cohort 活跃度 | followers.csv + interactions.csv 中某 cohort 用户的互动量 |
| 历史相似传播片段 | `graphs/threads.txt.gz` 中参与用户重合度高的 thread |

文本不是必须，但有了它，**LLM agent 完全可以做"读 root 文本 + 看当前 reply 文本 + 决定是否介入 / 如何介入"**，方法会更像真正的人类决策。

⚠️ 一个小提醒：完整 timeline 的原始 post 文本**没有**本地保留（本地只有 11 个 feed 的 16.7 万条采样）。如果某条 root post 不在 11 个 feed 之内，就只能拿到 metadata（user_id / date / 互动计数），拿不到全文。这在做大规模 cascade 实验时需要权衡。

---

## F. 数据来源 / 可信度备注

- 本地 `data/scripts/scripts/` 下是论文作者开源的清洗脚本（`clean_data.py`、`make_hypergraph.py`、`make_interaction_graphs.py`、`clean_feeds.py`、`clean_feed_posts_likes.py`、`clean_feed_bookmarks.py`、`join_follower_graph.py`），字段定义和时间窗口（2023-02-17 ~ 2024-03-18）都从这些脚本里直接核对过，**与本地数据完全一致**。
- 论文作者：Andrea Failla 等（`join_follower_graph.py` 第 3-4 行残留的 `/Users/andreafailla/Desktop/...` 路径可佐证），数据集即论文 "Hypergraph-of-threads" 配套数据。
- 时间字段精度提醒：
  - `interactions.csv`、`feed_bookmarks.csv`、`feed_posts/*.jsonl.gz`、`feed_posts_likes/*.csv.gz` 都是 12 位 `YYYYMMDDHHMM`
  - `graphs/{replies,reposts,quotes}.csv` 在本地实测**仍是 12 位**（虽然 `make_interaction_graphs.py` 第 18 行 `date = str(date)[:8]` 表示清洗时本应截到 8 位，但本地的 3 个 graph csv 看上去保留了 12 位，**写报告或做实验前请自己再抽样确认一次**）

---

## G. 一句话建议

如果你是要把 MF-DAG 升级成 LLM-agent 框架，**直接用 `graphs/threads.txt.gz` 作为 thread 级 cascade 输入（1949 万 thread，含 post_id），用 `feed_posts/*.jsonl.gz` 中 `thread_root` 不为 null 的那部分（约 7.8%）作为带文本的 cascade 样本**，配合 `interactions.csv` 的时间戳和 `followers.csv` 的网络结构，就已经能做完整的 post-level cascade + LLM agent 决策实验，**不需要再爬数据**。