# 全 Feed × threads Join 覆盖率检查报告

生成时间：2026-06-09 14:45:59

## 1. 检查目标

为 MF-DAG 第一版主实验筛选最适合的 feed/topic：基于 `threads.txt` 的 post-level thread sequence propagation，目标 500–2000 threads、200 agents。

## 2. 数据路径

- 数据根目录：`/Users/fgod/Desktop/FGOD/MF-DAG/MF-DAG/data`
- feed_posts：`/Users/fgod/Desktop/FGOD/MF-DAG/MF-DAG/data/feed_posts/feed_posts`
- threads：`/Users/fgod/Desktop/FGOD/MF-DAG/MF-DAG/data/graphs/graphs/threads.txt`
- 扫描 thread 总数：19,486,141

## 3. 单 Feed 统计摘要

| feed | posts | users | join% | cond2 threads | cond2 users | cond3 threads | cond3 users | 200 agents |
|---|---|---|---|---|---|---|---|---|
| Blacksky | 86,299 | 1,564 | 2.17% | 988 | 119 | 839 | 116 | 否 |
| News | 41,685 | 75 | 3.15% | 677 | 25 | 539 | 24 | 否 |
| Science | 33,491 | 1,716 | 2.69% | 419 | 89 | 403 | 86 | 否 |
| #UkrainianView | 2,097 | 172 | 8.39% | 11 | 3 | 11 | 3 | 否 |
| What's History | 161 | 71 | 3.11% | 0 | 0 | 0 | 0 | 否 |
| GreenSky | 658 | 190 | 2.43% | 0 | 0 | 0 | 0 | 否 |
| #Disability | 566 | 411 | 1.06% | 0 | 0 | 0 | 0 | 否 |
| BookSky | 638 | 275 | 0.94% | 0 | 0 | 0 | 0 | 否 |
| Political Science | 357 | 46 | 0.84% | 0 | 0 | 0 | 0 | 否 |
| Game Dev | 635 | 504 | 0.79% | 0 | 0 | 0 | 0 | 否 |
| AcademicSky | 913 | 352 | 0.44% | 0 | 0 | 0 | 0 | 否 |

## 4. Feed 排名

| rank | feed | condition | threads | users | join | reason |
|------|------|-----------|---------|-------|------|--------|
| 1 | Blacksky | condition_2 | 988 | 119 | 2.17% | users=119<200; threads>=500; join=2.17% |
| 2 | News | condition_2 | 677 | 25 | 3.15% | users=25<200; threads>=500; join=3.15% |
| 3 | Science | condition_2 | 419 | 89 | 2.69% | users=89<200; threads=419<500; join=2.69% |
| 4 | #UkrainianView | condition_2 | 11 | 3 | 8.39% | users=3<200; threads=11<500; join=8.39% |
| 5 | What's History | condition_2 | 0 | 0 | 3.11% | users=0<200; threads=0<500; join=3.11% |
| 6 | GreenSky | condition_2 | 0 | 0 | 2.43% | users=0<200; threads=0<500; join=2.43% |
| 7 | #Disability | condition_2 | 0 | 0 | 1.06% | users=0<200; threads=0<500; join=1.06% |
| 8 | BookSky | condition_2 | 0 | 0 | 0.94% | users=0<200; threads=0<500; join=0.94% |
| 9 | Political Science | condition_2 | 0 | 0 | 0.84% | users=0<200; threads=0<500; join=0.84% |
| 10 | Game Dev | condition_2 | 0 | 0 | 0.79% | users=0<200; threads=0<500; join=0.79% |
| 11 | AcademicSky | condition_2 | 0 | 0 | 0.44% | users=0<200; threads=0<500; join=0.44% |

## 5. 合并 Feed 可行性

| 方案 | posts | users | join% | cond2 threads | cond2 users | 200 agents | 500 threads |
|---|---|---|---|---|---|---|---|
| Science + AcademicSky | 34,369 | 2,024 | 0.0263 | 419 | 89 | 否 | 否 |
| Science + News | 75,148 | 1,789 | 0.0294 | 1,575 | 137 | 否 | 是 |
| AcademicSky + Science + News | 76,026 | 2,097 | 0.0291 | 1,575 | 137 | 否 | 是 |
| Blacksky | 86,299 | 1,564 | 0.0217 | 988 | 119 | 否 | 是 |
| All feeds merged | 167,368 | 5,237 | 0.0257 | 4,009 | 308 | 是 | 是 |

## 6. 推荐主实验 Feed

- **最推荐（合并）**：`All feeds merged`
- **最佳单 feed（未达 200 agents）**：`Blacksky`
- **无单 feed 同时满足** condition_2/3 下 threads>=500 且 users>=200
- **备选**：News, Science, #UkrainianView
- **不推荐**：#UkrainianView, What's History, GreenSky, #Disability, BookSky, Political Science, Game Dev, AcademicSky
- **最佳合并方案**：`All feeds merged`

## 7. MF-DAG 主实验可行性结论

- 单 feed 可行：**否**
- 合并 feed 可行：**是**
- 总体可行：**是**

## 8. 退路方案

- 无单 feed 在 condition_2/3 下同时满足 200 agents + 500 threads。
- 最佳单 feed 为 Blacksky（cond2: 988 threads, 119 users），需合并其他 feed 或扩展 user 池。
- 推荐合并方案：All feeds merged（cond2: 4009 threads, 308 users）。