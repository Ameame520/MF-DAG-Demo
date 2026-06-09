# MF-DAG 本地数据体检报告（可直接复制给另一个 LLM） > 检查时间：2026-06-08 > 检查目录：/Users/fgod/Desktop/FGOD/MF-DAG/MF-DAG/data/raw > 检查者：当前 Cursor 会话（GPT-5.5）

补充说明：用户指定的 `data/raw` 目录在本地不存在；实际解压后的数据目录是 `/Users/fgod/Desktop/FGOD/MF-DAG/MF-DAG/data`。以下检查均基于这个实际存在的 `data` 目录完成。大文件使用快速扫描：对 CSV 做二进制行数统计，对字段和前几行直接读取；对超大 `interactions.csv` 只抽样解析前 200 万行的交互类型分布，不做全量字段解析。

## A. 数据文件清单

本地实际结构如下：

```text
data/
├── followers.csv                         1.95 GB
├── interactions.csv                      6.41 GB
├── feed_bookmarks.csv                    553 KB
├── feed_posts/
│   └── feed_posts/
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
│   └── feed_posts_likes/
│       ├── #Disability.csv.gz
│       ├── #UkrainianView.csv.gz
│       ├── AcademicSky.csv.gz
│       ├── Blacksky.csv.gz
│       ├── BookSky.csv.gz
│       ├── Game Dev.csv.gz
│       ├── GreenSky.csv.gz
│       ├── News.csv.gz
│       ├── Political Science.csv.gz
│       ├── Science.csv.gz
│       └── What's History.csv.gz
├── graphs/
│   └── graphs/
│       ├── replies.csv                   1.94 GB
│       ├── reposts.csv                   1.39 GB
│       ├── quotes.csv                    262 MB
│       └── threads.txt.gz                274 MB
└── scripts/
    └── scripts/                          数据采集、清洗和实验脚本
```

重点字段确认：

| 字段 | 是否存在 | 出现位置 | 备注 |
|---|---:|---|---|
| `post_id` | 有 | `feed_posts/*.jsonl.gz`, `feed_posts_likes/*.csv.gz` | feed posts 有真实 post 级 ID；likes 文件也可关联 post |
| `thread_id` | 未见明确字段 | 无 | 没有名为 `thread_id` 的字段 |
| `root_post_id` | 间接存在 | `feed_posts.thread_root`, `graphs/graphs/threads.txt.gz` 第 1 列 | `thread_root` 是 root post 的内部 ID；threads 第 1 列可视作 thread root id |
| `reply_to` | 有 | `feed_posts/*.jsonl.gz` | 但整体很稀疏，只有 5,808 / 168,463 条非空 |
| `repost_of` | 未见该字段名 | 无 | 清洗脚本里曾有 `repost_from`，但本地 feed_posts 输出字段没有保留 |
| `quote_of` | 等价字段有 | `feed_posts.quotes` | `quotes` 是被 quote 的 post_id |
| `author_id` | 等价字段有 | 多处用 `user_id`、`replied_author`、`quoted_author` 等 | 用户/作者均为整数编码 |
| `created_at` / `timestamp` | 等价字段有 | 多处用 `date` | 格式多为 `YYYYMMDDHHMM`，graphs 三个 CSV 是 `YYYYMMDD` |

Zenodo 页面说明的两个核心文件与本地一致：

- `followers.csv`：无表头，2 列 `u,v`，表示用户 `u` follow 用户 `v`。
- `interactions.csv`：无表头，6 列 `user_id,replied_author,thread_root_author,reposted_author,quoted_author,date`，覆盖 reply/comment、repost、quote 三类互动。

本地额外重要文件：

- `graphs/graphs/threads.txt.gz`：每行是一个 thread/root 的参与作者序列，非常适合做 author-level cascade 或 MF-DAG 风格超图传播。
- `feed_posts/*.jsonl.gz`：有 post 级字段和文本内容。
- `feed_posts_likes/*.csv.gz`：有 post-level like 边。

## B. 每个核心文件的前几行

### `head -n 5 followers.csv`

```text
0,1
0,10
0,100
0,101
0,102
```

字段解释：无表头，`u,v`，表示用户 `u` follow 用户 `v`。

### `head -n 5 interactions.csv`

```text
836672,None,None,833271,None,202309192352
836672,None,None,61971,None,202310021913
836672,None,None,47191,None,202309231547
836672,None,None,17234,None,202309301358
836672,None,None,20490,None,202307261536
```

字段解释：无表头，6 列依次是：

```text
user_id, replied_author, thread_root_author, reposted_author, quoted_author, date
```

其中空值用字符串 `"None"` 表示。`date` 是 12 位整数样式的时间戳：`YYYYMMDDHHMM`。

### `head -n 5 feed_bookmarks.csv`

```text
Science,408833,202309192111
Science,204992,202307290107
Science,1798953,202309232103
Science,1428436,202311051321
Science,976464,202309131041
```

字段解释：无表头，3 列：

```text
feed_name, user_id, date
```

### `head -n 3 graphs/graphs/replies.csv`

```text
836672,44300,20230827
836672,169982,20230826
45957,168349,20240209
```

字段解释：无表头，3 列：

```text
src_author_id, dst_author_id, date
```

### `head -n 3 graphs/graphs/reposts.csv`

```text
836672,833271,20230919
836672,61971,20231002
836672,47191,20230923
```

字段解释：无表头，3 列：

```text
src_author_id, dst_author_id, date
```

### `head -n 3 graphs/graphs/quotes.csv`

```text
836672,559307,20230826
45957,45957,20231222
45957,45957,20231222
```

字段解释：无表头，3 列：

```text
src_author_id, dst_author_id, date
```

### `gzip -dc graphs/graphs/threads.txt.gz | head -n 3`

```text
47	202308261051	1074176,119298,119299,720392,587786,148500,399893,338964,2210327,286233,78373,...
54	202308261844	836672,243265,392482,243266,856517,629854,102570,699309,121296,50489,169982
60	202402090131	45957,750410,302188,1252333,137650,817691,168349,198942
```

字段解释：tab 分隔，3 列：

```text
thread_root_id, root_time, participants
```

第 3 列是参与该 thread 的 `author_id` 列表，逗号分隔。根据本地样例与旧探索结论，它可视作按参与/加入顺序排列的作者序列。

### `gzip -dc feed_posts/feed_posts/Blacksky.jsonl.gz | head -n 3`

```json
{"post_id": 34631950, "user_id": 37717, "instance": "bsky.social", "date": 202403182357, "text": "I know for a fact that even were I to cast my vote for Biden, too many other Americans have said no, I cannot check a box on a ballot for a man who is committing genocide, for him to be able to be victorious at the polls in November.", "langs": ["eng"], "like_count": 9, "reply_count": 0, "repost_count": 4, "reply_to": null, "replied_author": null, "thread_root": null, "thread_root_author": null, "quotes": null, "quoted_author": null, "labels": null}
{"post_id": 194684721, "user_id": 34671, "instance": "bsky.social", "date": 202403182357, "text": "In good news I haven't messaged them in 21 days which is wholly a record for me, and I honestly may never message them again", "langs": ["eng"], "like_count": 5, "reply_count": 1, "repost_count": 0, "reply_to": null, "replied_author": null, "thread_root": null, "thread_root_author": null, "quotes": 194684722, "quoted_author": 34671, "labels": null}
{"post_id": 194684722, "user_id": 34671, "instance": "bsky.social", "date": 202403182356, "text": "Since the Discord update there's a 50/50 chance that it's going to flash random profiles of people I'm friends with at the top of my messages as it's loading in the actual account activity thing, & I hate this because it almost always flashes my ex's profile first which just makes me sad", "langs": ["eng"], "like_count": 3, "reply_count": 0, "repost_count": 0, "reply_to": null, "replied_author": null, "thread_root": null, "thread_root_author": null, "quotes": null, "quoted_author": null, "labels": null}
```

完整字段集合，共 16 个：

```text
post_id, user_id, instance, date, text, langs, like_count, reply_count, repost_count, reply_to, replied_author, thread_root, thread_root_author, quotes, quoted_author, labels
```

### `gzip -dc feed_posts_likes/feed_posts_likes/#Disability.csv.gz | head -n 5`

```text
1268471,125049,2238814,202310260410
361133,125049,2238814,202312090526
88914,125049,2238814,202307291222
59268,125049,2238814,202310170159
291703,125049,2238814,202401160447
```

字段解释：无表头，4 列：

```text
liker_user_id, post_author_id, post_id, date
```

## C. 字段名、数据量、时间范围

### 核心文件规模

| 文件 | 行数 | 字段 | 时间范围 |
|---|---:|---|---|
| `followers.csv` | 144,581,603 | `u,v` | 静态 follow 边，无时间列 |
| `interactions.csv` | 152,728,104 | `user_id,replied_author,thread_root_author,reposted_author,quoted_author,date` | 全量旧探索：约 2023-02-17 到 2024-03-18；本次前 200 万行抽样：2023-02-19 到 2024-03-18 |
| `feed_bookmarks.csv` | 18,324 | `feed_name,user_id,date` | 样例覆盖 2023-07 到 2023-11 |
| `graphs/graphs/replies.csv` | 87,550,414 | `src_author_id,dst_author_id,date` | 8 位日期，旧探索：约 2023-02 到 2024-02 |
| `graphs/graphs/reposts.csv` | 63,438,069 | `src_author_id,dst_author_id,date` | 8 位日期，旧探索：约 2023-07 到 2024-02 |
| `graphs/graphs/quotes.csv` | 12,085,583 | `src_author_id,dst_author_id,date` | 8 位日期，旧探索：约 2023-08 到 2023-09 |
| `graphs/graphs/threads.txt.gz` | 19,486,141 | `thread_root_id,root_time,participants` | 2023-02-17 00:52 到 2024-03-18 23:59 |
| `feed_posts/*.jsonl.gz` | 168,463 | 16 个 JSON 字段，含 `post_id` 和 `text` | 2023-02-20 02:27 到 2024-03-18 23:59 |
| `feed_posts_likes/*.csv.gz` | 4,895,318 | `liker_user_id,post_author_id,post_id,date` | 原始值最早 2023-05-01；最大出现 2030-10-18，疑似异常未来时间 |

### `feed_posts` 各 feed 的 post 级字段覆盖

| feed | posts | `reply_to` 非空 | `thread_root` 非空 | `quotes` 非空 | `quoted_author` 非空 | `text` 非空 | 时间范围 |
|---|---:|---:|---:|---:|---:|---:|---|
| `#Disability` | 566 | 0 | 0 | 80 | 80 | 566 | 2023-07-27 到 2024-03-18 |
| `#UkrainianView` | 2,098 | 204 | 204 | 352 | 352 | 2,097 | 2023-07-05 到 2024-03-18 |
| `AcademicSky` | 913 | 71 | 71 | 77 | 77 | 913 | 2024-02-14 到 2024-03-18 |
| `Blacksky` | 86,490 | 0 | 0 | 24,776 | 24,776 | 85,411 | 2023-09-24 到 2024-03-18 |
| `BookSky` | 638 | 57 | 57 | 71 | 71 | 638 | 2023-12-17 到 2024-03-18 |
| `Game Dev` | 635 | 106 | 106 | 21 | 21 | 635 | 2024-03-16 到 2024-03-18 |
| `GreenSky` | 662 | 288 | 288 | 59 | 59 | 662 | 2024-03-15 到 2024-03-18 |
| `News` | 42,112 | 683 | 683 | 0 | 0 | 41,639 | 2023-02-20 到 2024-03-18 |
| `Political Science` | 357 | 0 | 0 | 231 | 231 | 357 | 2023-05-01 到 2024-03-18 |
| `Science` | 33,831 | 4,399 | 4,399 | 5,063 | 5,063 | 33,831 | 2023-05-26 到 2024-03-18 |
| `What's History` | 161 | 0 | 0 | 41 | 41 | 161 | 2024-03-13 到 2024-03-18 |
| 合计 | 168,463 | 5,808 | 5,808 | 30,771 | 30,771 | 166,910 | 2023-02-20 到 2024-03-18 |

### 用户数量

本次没有对 144M follow 边做全量去重，因为这会占用较大内存。项目内已有旧探索报告给出的估计：

```text
followers.csv 用户数估计：约 1.4M 到 2.8M unique users
```

本次快速复核：

```text
interactions.csv 前 2,000,000 行抽样 unique user_id：24,704
```

这个抽样只反映文件开头局部，不代表全量用户数。

### 交互类型

`interactions.csv` 没有显式 `interaction_type` 字段，需要根据四个 author 列是否为 `"None"` 判断：

```text
replied_author != None        => reply/comment
thread_root_author != None    => 该 reply/comment 所属 thread 的 root author
reposted_author != None       => repost
quoted_author != None         => quote
```

前 2,000,000 行快速抽样结果：

| 类型 | 抽样计数 | 抽样占比 |
|---|---:|---:|
| reply/comment | 1,161,743 | 58.1% |
| thread_root_author 非空 | 1,161,743 | 58.1% |
| repost | 808,997 | 40.4% |
| quote | 156,016 | 7.8% |

注意：同一行可能同时属于多种类型，因此占比相加可以超过 100%。

## D. 是否能还原传播链

结论先说：本地数据不能稳定还原完整的严格 post-level `root post -> reply/repost/quote` 传播树；但可以很好地做 author-level cascade / thread-author propagation，也可以对 quote 和 like 做 post-level 边。

### 1. `interactions.csv` 不能直接还原 post-level cascade

`interactions.csv` 的 6 列是：

```text
user_id, replied_author, thread_root_author, reposted_author, quoted_author, date
```

这里的 `replied_author`、`thread_root_author`、`reposted_author`、`quoted_author` 都是作者 ID，不是 post ID。因此：

- 可以知道用户 A 在某时间 reply/repost/quote 了作者 B。
- 可以知道 reply 所属 thread 的 root author。
- 不能从这个文件直接知道被 reply/repost/quote 的具体 `post_id`。
- 不能从这个文件直接还原 `root_post_id -> child_post_id` 的树边。

### 2. `feed_posts` 有 post-level 字段，但 reply/thread 字段很稀疏

`feed_posts/*.jsonl.gz` 确实有：

```text
post_id, reply_to, thread_root, quotes, user_id, date, text
```

但是本次全量统计显示：

```text
总 posts：168,463
reply_to 非空：5,808
thread_root 非空：5,808
quotes 非空：30,771
```

所以：

- reply 链：可以做少量 post-level reply 链，但覆盖率只有约 3.4%，不适合作为主实验的完整 post-level cascade。
- quote 链：`quotes` 字段覆盖较多，可以比较可靠地做 post-level quote cascade。
- repost 链：本地输出没有 `repost_of` / `repost_from` 字段；repost 主要只能做到 author-level。
- like 链：`feed_posts_likes` 有 `post_id`，可以做 post-level engagement，但 like 不是传播树边。

### 3. `graphs/graphs/threads.txt.gz` 是最适合的传播链文件

`threads.txt.gz` 有 19,486,141 行，每行：

```text
thread_root_id<TAB>root_time<TAB>author_id_1,author_id_2,author_id_3,...
```

这非常适合做：

- author-level cascade
- thread-author propagation
- MF-DAG 风格超图传播
- cohort 历史行为统计
- thread 长度、参与者序列、传播速度等结构化特征

如果目标是类似下面这种严格 post-level 树：

```text
root post A
 ├── reply 1
 ├── repost 1
 ├── quote 1
 └── reply 2
```

那么本地数据只能部分支持：

| 边类型 | post-level 可还原性 | 推荐数据源 | 判断 |
|---|---|---|---|
| reply | 部分可还原，但很稀疏 | `feed_posts.reply_to`, `feed_posts.thread_root` | 不适合作为主实验 |
| quote | 可较好还原 | `feed_posts.quotes -> post_id` | 可做 quote cascade |
| repost | 不能稳定还原 post-level | `interactions.reposted_author`, `graphs/reposts.csv` | 只能做 author-level |
| like | 可还原 post-level engagement | `feed_posts_likes.post_id` | 可做参与/反馈，不是传播树 |
| thread 传播 | 可还原 author-level cascade | `graphs/graphs/threads.txt.gz` | 最推荐 |

### 4. 推荐给实验设计的判断

如果实验需要“严格 post-level cascade”，建议限定为：

```text
quote cascade + like engagement + 少量 reply_to/thread_root 可用样本
```

如果实验目标是 MF-DAG 论文风格的传播建模，建议主线使用：

```text
followers.csv
+ interactions.csv
+ graphs/graphs/threads.txt.gz
+ graphs/graphs/replies.csv/reposts.csv/quotes.csv
```

这样是 author-level / thread-author propagation，不是完整 post-level tree cascade。

## E. 是否有文本内容

有文本。`feed_posts/*.jsonl.gz` 的 `text` 字段覆盖率很高：

```text
总 posts：168,463
text 非空：166,910
文本覆盖率：約 99.1%
```

这意味着 representative LLM 可以读取：

- root post 文本摘要
- 当前高互动 reply/quote 文本摘要
- cohort 历史行为摘要
- feed/topic 相关文本

但要注意两个限制：

1. 文本主要来自 `feed_posts` 的 feed 切片，不等于 `interactions.csv` / `graphs` 中所有 13 个月互动的完整文本全集。
2. 对 reply/repost 的完整 post-level parent-child 关系不稳定；因此“高互动 reply 摘要”只能在 `reply_to/thread_root` 非空的子集上做，或者改成 author-level/结构化传播状态。

如果不使用文本，LLM-agent 仍然可以基于结构化状态决策，例如：

```text
当前传播速度
reply/repost/quote 比例
thread 参与作者序列
cohort 活跃度
历史相似传播片段
follow graph 邻居特征
author-level interaction graph 特征
post 的 like_count/reply_count/repost_count
```

## 给另一个 LLM 的一句话摘要

本地 MF-DAG 数据有 1.45 亿 follower 边、1.53 亿 interactions、1,949 万 thread-author 序列、16.8 万条带文本和 post_id 的 feed posts；`interactions.csv` 与 Zenodo 描述一致但只有 author-level 目标 ID，不能直接还原完整 post-level cascade。最稳的实验路线是用 `graphs/graphs/threads.txt.gz` 做 author-level cascade / MF-DAG 超图传播；若必须做 post-level cascade，则 quote 链和 like engagement 可用，reply 链很稀疏，repost 缺少 post_id。
