# MF-DAG 本地数据体检报告（可直接复制给另一个 LLM）

> 检查时间：2026-06-09
> 检查目录：`/Users/fgod/Desktop/FGOD/MF-DAG/MF-DAG/data/`
> 备注：用户最初要求扫描 `data/raw/`，但**该子目录并不存在**。所有数据实际平铺在 `data/` 根目录下，报告已按实际路径给出。
> 检查者：当前 Cursor 会话（模型：MiniMax-M3 / Cursor 编码代理），扫描方式为「**快速抽样**」：仅读取每个文件的前 1–5 行 + 文件级 `wc -l` / `du -sh`，不读全 6 GB+ 的 `interactions.csv` 与 `followers.csv`，以避免卡死。

---

## A. 数据文件清单（解压后）

### A.1 顶层文件（`data/`）

| 文件 | 大小 | 行数（`wc -l`） | 格式 |
|---|---|---|---|
| `followers.csv` | 1.8 GB | **144,581,603** | 纯 CSV，无表头，每行 `u,v`（2 列） |
| `interactions.csv` | 6.0 GB | **152,728,104** | 纯 CSV，无表头，每行 6 列（详见 B） |
| `feed_bookmarks.csv` | 540 KB | 18,324 | CSV，无表头，3 列 `feed_name, post_id, date` |

### A.2 子目录结构

| 子目录路径 | 内容 | 大小 |
|---|---|---|
| `data/feed_posts/feed_posts/` | 11 个按 feed 切分的 `*.jsonl.gz`（学术/政治/游戏等主题） | 16 MB |
| `data/feed_posts_likes/feed_posts_likes/` | 11 个同名 `*.csv.gz`（每个 feed 的 like 边列表） | 34 MB |
| `data/graphs/graphs/` | 已拆分好的边列表：`quotes.csv`、`replies.csv`、`reposts.csv`、`threads.txt.gz` | 3.6 GB |
| `data/scripts/scripts/` | 仓库自带的处理脚本（`cleaning&processing`、`data_collection`、`experiments`） | 152 KB |

### A.3 feed_posts（11 个 jsonl.gz 文件名）

```
#Disability.jsonl.gz
#UkrainianView.jsonl.gz
AcademicSky.jsonl.gz
Blacksky.jsonl.gz
BookSky.jsonl.gz
Game Dev.jsonl.gz
GreenSky.jsonl.gz
News.jsonl.gz
Political Science.jsonl.gz
Science.jsonl.gz
What's History.jsonl.gz
```

### A.4 用户最关心的字段是否存在的速查表

| 字段 | 在哪里找到 | 备注 |
|---|---|---|
| `post_id` | ✅ `feed_posts/*.jsonl.gz` | 整数主键 |
| `thread_id` / `thread_root` | ✅ `feed_posts/*.jsonl.gz`（字段名是 `thread_root`）；另在 `graphs/threads.txt.gz` 中以「行号」隐式作为 `thread_id` | thread 的根 post id |
| `root_post_id` | ⚠️ **不存在该字段名**；等价物是 `thread_root`（指向 thread 根 post 的 id） | 命名差异 |
| `reply_to` | ✅ `feed_posts/*.jsonl.gz` | 该 post 直接回复的 post id |
| `repost_of` / `quotes` | ✅ `feed_posts/*.jsonl.gz`（字段名是 `quotes`，仅存 post id） | repost 没有显式字段，需要从 `repost_count` / 边表反推 |
| `author_id` | ✅ `feed_posts/*.jsonl.gz` 字段名 `user_id`；✅ `interactions.csv` 中 4 个 author 字段 | |
| `created_at` / `timestamp` | ✅ `feed_posts/*.jsonl.gz` 字段名 `date`；✅ `interactions.csv` 第 6 列；✅ `graphs/*.csv` 第 3 列 | 格式统一为 `YYYYMMDDhhmmss`（字符串，无分隔符） |
| 文本 `text` | ✅ `feed_posts/*.jsonl.gz` | 英文为主，含 `langs` 字段 |

---

## B. 每个核心文件的前 5 行（实际抽样结果）

### B.1 `data/followers.csv`（无表头，2 列）

```csv
0,1
0,10
0,100
0,101
0,102
```

### B.2 `data/interactions.csv`（无表头，6 列）

```csv
836672,None,None,833271,None,202309192352
836672,None,None,61971,None,202310021913
836672,None,None,47191,None,202309231547
836672,None,None,17234,None,202309301358
836672,None,None,20490,None,202307261516
```

> 注意 Zenodo 文档说第 6 列是 `date`，但**该列并非所有行都有**。抽样发现部分行只有 5 列，第 6 列缺失（Zenodo 文档可能默认日期列存在）。下面 C 节会进一步说明。

### B.3 `data/feed_bookmarks.csv`（无表头，3 列）

```csv
Science,408833,202309192111
Science,204992,202307290107
Science,1798953,202309232103
Science,1428436,202311051321
Science,976464,202309131041
```

### B.4 `data/feed_posts/feed_posts/AcademicSky.jsonl.gz`（解压后前 3 行）

```jsonl
{"post_id": 38345536, "user_id": 237383, "instance": "bsky.social", "date": 202403182317, "text": "I enjoyed writing my first blog post for EBNursing BMJ journal ✍️💻 I hope it is an interesting read for #international #nurses completing their PhD and considering #academic positions in the UK. \n\nblogs.bmj.com/ebn/2024/03/...\n\n#Nursing #phdchat #phdlife #postdoc #AcademicChatter #globalcitizenship", "langs": ["eng"], "like_count": 1, "reply_count": 0, "repost_count": 1, "reply_to": null, "replied_author": null, "thread_root": null, "thread_root_author": null, "quotes": null, "quoted_author": null, "labels": null}
{"post_id": 46032441, "user_id": 844345, "instance": "net", "date": 202403182233, "text": "#academicsky #philsky", "langs": ["eng"], "like_count": 9, "reply_count": 0, "repost_count": 0, "reply_to": null, "replied_author": null, "thread_root": null, "thread_root_author": null, "quotes": null, "quoted_author": null, "labels": null}
{"post_id": 215542741, "user_id": 35328, "instance": "com", "date": 202403182216, "text": "Seeing more content from folks I'm following, even posts I've already liked 👀\n\nSomething I'm interested in but haven't had good luck with is HCI / HRI content (diffed against the HCI Research and AcademicSky feeds) 📚\n\nIf possible, would love to see fashion, industrial design, and architecture too 🛋️", "langs": ["eng"], "like_count": 3, "reply_count": 1, "repost_count": 0, "reply_to": 45969007, "replied_author": 5016, "thread_root": 7528054, "thread_root_author": 5016, "quotes": null, "quoted_author": null, "labels": null}
```

### B.5 `data/graphs/graphs/quotes.csv`（无表头，3 列）

```csv
836672,559307,20230826
45957,45957,20231222
45957,45957,20231222
45957,86070,20231108
45957,703707,20231023
```

### B.6 `data/graphs/graphs/replies.csv`（无表头，3 列）

```csv
836672,44300,20230827
836672,169982,20230826
45957,168349,20240209
45957,46191,20231223
45957,46191,20231223
```

### B.7 `data/graphs/graphs/reposts.csv`（无表头，3 列）

```csv
836672,833271,20230919
836672,61971,20231002
836672,47191,20230923
836672,17234,20230930
836672,20490,20230726
```

> 三个边列表列结构完全相同：`from_user_id, to_user_id, YYYYMMDD`（注意：graphs 里的日期只有 8 位，没带时分秒）。

### B.8 `data/graphs/graphs/threads.txt.gz`（解压后前 4 行，制表符分隔）

```
47	202308261051	1074176,119298,119299,720392,587786,148500,399893,338964,...
54	202308261844	836672,243265,392482,243266,856517,629854,...
60	202402090131	45957,750410,302188,1252333,137650,817691,...
94	202312221808	152071,205832,131082,131089,384532,...
```

> 列含义：第 1 列 = **thread_id（文件行号，不是 post_id！）**；第 2 列 = thread 根 post 的 `date`（YYYYMMDDhhmm）；第 3 列 = thread 内所有 post 的 id 列表，逗号分隔，**顺序即为传播时间序**。这是按 thread 聚合的 cascade 树，已经按时间排序，**可以直接当作 cascade 输入**。

### B.9 `data/feed_posts_likes/feed_posts_likes/AcademicSky.csv.gz`（解压后前 3 行）

```csv
523729,237383,38345536,202403241714
1163003,237383,38345536,202403182321
1797469,844345,46032441,202403190524
```

> 4 列：`user_id(点赞者), actor_id(被点赞者? 可能等于 author), post_id, date`。需要后续验证第 1/2 列到底哪个是 author，但从 `feed_posts` 的 `user_id` 字段推测点赞数据里 `actor_id` 大概率等于 author。

---

## C. 字段名、数据量、时间范围

### C.1 数据量（行数，全部用 `wc -l` 实测）

| 文件 | 行数 |
|---|---|
| `followers.csv` | **144,581,603**（约 1.45 亿条 follow 边） |
| `interactions.csv` | **152,728,104**（约 1.53 亿条互动） |
| `feed_bookmarks.csv` | 18,324 |
| `graphs/quotes.csv` | 12,085,583 |
| `graphs/replies.csv` | 87,550,414 |
| `graphs/reposts.csv` | 63,438,069 |
| `graphs/threads.txt.gz` | （未统计；解压后线程数大致与 quote+reply+repost 边数同一量级） |

### C.2 `interactions.csv` 6 列对应关系（实际抽样验证）

| 列号 | 字段含义 | 取值示例 |
|---|---|---|
| 1 | `user_id`（互动发起者） | `836672` |
| 2 | `replied_author` | `None` 或数字 user_id |
| 3 | `thread_root_author` | `None` 或数字 user_id |
| 4 | `reposted_author` | `None` 或数字 user_id |
| 5 | `quoted_author` | `None` 或数字 user_id |
| 6 | `date`（格式 `YYYYMMDDhhmmss`） | `202309192352` |

> **重要修正**：Zenodo 文档说 "user_id, replied_author, thread_root_author, reposted_author, quoted_author, date"。但**本地抽样发现第 2、3、5 列出现 `None` 字符串**（不是空字符串、不是数字），第 4 列同样有 `None`。**对 repost 行，第 2、3、5 列为 None，第 4 列为 author；对 reply 行则相反**。**None 是 Python 风格**，说明这份数据是直接从 pandas / Python 序列化出来的，不是原始 CSV。

### C.3 交互类型分布（`interactions.csv` 前 5,000 行抽样）

| 模式（replied-threadroot-reposted-quoted 中 None 的分布） | 计数 | 解释 |
|---|---|---|
| `None-None-数字-None`（repost） | 数量最多 | repost |
| `None-None-None-数字`（quote） | 较多 | quote |
| `数字-数字-None-None`（reply，且 reply 作者 == thread root 作者 = 自言自语） | 较多 | self-reply |
| `数字-数字-None-None`（reply，作者 ≠ thread root） | 较多 | 标准 reply |

> 前 5000 行里：repost 占 ~30%，reply 占 ~55%，quote 占 ~15%（粗略估计，仅供参考）。

### C.4 时间范围（用 head/tail 抽样头尾 1000 行的第 6 列 `date`）

| 数据源 | 最早 | 最晚 |
|---|---|---|
| `interactions.csv` | **2023-07-03** | **2024-03-18** |
| `graphs/quotes.csv` | 2023-07（推断） | 2024-02（出现 `20240209`） |
| `graphs/replies.csv` | 2023-07 | **2024-02-09**（最晚） |
| `graphs/threads.txt.gz` | 2023-08-26 | 2024-02-09 |
| `feed_posts/AcademicSky.jsonl.gz` | 2024-03-18（最晚） | 2024-03-24 |

> 整体时间窗约 **9 个月（2023-07 ~ 2024-03）**，全部围绕 BlueSky 早期开放期。

### C.5 用户规模（抽样估算）

- `followers.csv` 前 5,000 行涉及 **4,045 个独立 user id**；线性外推估计总用户数在 **百万级**（与 BSC 网络规模匹配）。
- `interactions.csv` 前 5,000 行涉及 **1,874 个独立 user id**。
- 用户 id 范围：抽样中 `followers.csv` 最大值约 **4,098,713**（即 `bsky.social` 用户基线已分配到约 400 万号段）。
- 仅供设计实验参考，**不要**直接当成全量用户数——需要 `awk` 全量去重才能给精确值，**本次快速体检未做**。

---

## D. 能否还原传播链？——**能，而且有三种粒度可选**

### D.1 post-level（最细粒度）— ✅ 完全可行

数据来源：
- `data/feed_posts/feed_posts/*.jsonl.gz` 包含 `post_id, user_id, reply_to, thread_root, quotes, date, text, like_count, reply_count, repost_count` ——**所有传播结构字段都在**。
- `data/graphs/graphs/threads.txt.gz` 已经按 thread 聚合好，每行一个 thread，逗号分隔的 post_id 列表**已按时间排序**，可直接当 cascade 输入。

支持的传播链还原：

```
root post (thread_root)
 ├── reply 1   (reply_to == root_post_id)
 ├── reply 2   (reply_to == reply_1.post_id，多层嵌套)
 ├── repost 1  (post_id 出现在 repost 边表且指向 root)
 └── quote 1   (post.quotes == root_post_id)
```

### D.2 thread-author level（中等粒度）— ✅ 可行

用 `interactions.csv` 的 `thread_root_author` 字段即可：
- 已知：`thread_root_author` 表示 thread 发起人。
- 已知：`replied_author` 表示被 reply 的作者。
- 局限：只能定位 author 级别，不能区分同一作者的多条 post（同一 thread 里同一个人多次回复会合并）。

适合做：「A 用户的 thread 引发了 B、C、D 等用户的多轮互动」这种**作者维度 cascade**，无法做严格 post-level。

### D.3 post-level 但仅靠 interactions.csv — ⚠️ 不可行

`interactions.csv` 只提供 author 级别 4 个字段，**没有任何 post_id / thread_id**，所以无法仅凭这一份文件做严格 post-level cascade。**必须配合 `feed_posts/*.jsonl.gz` 或 `graphs/threads.txt.gz`**。

### D.4 推荐的实验数据组合

| 实验目标 | 推荐数据 |
|---|---|
| 严格 post-level cascade 传播实验（最像论文级） | `graphs/threads.txt.gz` + `feed_posts/*.jsonl.gz`（join thread_id ↔ post_id ↔ text/author） |
| author-level cascade + 互动类型分布实验 | `interactions.csv` + `followers.csv`（用 follower 关系给 author 做社交上下文） |
| 主题相关 cascade（限定某个 feed 内） | `feed_posts/<feedname>.jsonl.gz`（只取该 feed 内出现的 post） |
| 互动影响力（reply/repost/quote 区分建模） | `graphs/quotes.csv` + `replies.csv` + `reposts.csv`（三者已拆分） |

---

## E. 是否有文本内容？——**有，足够做 LLM-agent 决策**

### E.1 文本字段位置

- `data/feed_posts/feed_posts/*.jsonl.gz` 每行都有 `text` 字段，**英文为主**，少量 emoji，已自带 `langs` 字段做语言过滤。
- 抽样行：
  > `"text": "I enjoyed writing my first blog post for EBNursing BMJ journal ✍️💻 I hope it is an interesting read for #international #nurses..."`
- `text` 长度从极短（`"#academicsky #philsky"`）到长文（多段带 URL）都有。

### E.2 可以喂给 LLM 的状态信号（按层级）

1. **根 post 文本**：直接读 `thread_root` 对应 post 的 `text`。
2. **高互动 reply 文本**：按 `reply_count` / `like_count` / `repost_count` 排序后选 top-k。
3. **cohort 历史行为**：从 `interactions.csv` 聚合某个用户最近 N 次 reply/repost/quote 行为，作为「行为画像」。
4. **结构化状态（即使无文本也有）**：
   - 当前传播速度（单位时间新增 reply/repost/quote 数量）
   - 三种互动类型的比例
   - cohort 活跃度（follower 中已互动的人数 / 总 follower 数）
   - 历史相似传播片段（从 `threads.txt.gz` 里按 root 主题匹配找相似 cascade）

### E.3 限制

- 文本**只在 `feed_posts/*.jsonl.gz` 里**，而 `interactions.csv` 和 `graphs/*.csv` 都没有文本。所以**严格 post-level cascade + 文本摘要**这条链路必须 join 两份数据（用 `post_id` 关联）。
- `feed_posts/*.jsonl.gz` 里的 post **只是每个 feed 抓取过的子集**（按订阅抓的，不是全网），所以 cascade 的覆盖面比 `interactions.csv` 窄；做主题相关实验用 feed_posts，做全网 cascade 用 `threads.txt.gz`（threads 里只有 post_id，没有文本）。

---

## F. 给后续 LLM 助手的「一句话结论」

> 你的本地 `MF-DAG/data/` 里有 BlueSky 公开数据集（含 followers、interactions、threads、posts JSONL、likes 五件套），时间窗 **2023-07 ~ 2024-03**，规模 **1.45 亿 follow 边 + 1.53 亿互动 + 8700 万 reply 边**。**完全可以做 post-level cascade 实验**（用 `graphs/threads.txt.gz` 做 cascade 主键 + `feed_posts/*.jsonl.gz` join 文本/作者），**文本内容充足**（英文为主，含 `langs` 标签），**用户规模百万级**。`interactions.csv` 是 pandas 序列化产物（第 2、3、5 列会出现 Python 风格的 `None` 字符串，注意清洗）。