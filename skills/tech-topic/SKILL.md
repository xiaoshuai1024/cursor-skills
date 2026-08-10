---
name: tech-topic
description: 技术文章选题。掘金近期高互动文章（匿名/登录态接口）→ 方向过滤（前端/后端/AI）→ 🔥热度/🎯垂直 双视角 → 选题清单 + 假设大纲。深挖做原文保存 + 结构分析（仿写交写博客 skill）。不知道下一篇写什么时调用。
---

# Tech Topic Skill — 技术文章选题

把掘金当前高互动技术文章（**真实数据**）筛成符合本博客「前端 → 全栈 → AI 开发」方向的选题参考，分 🔥热度（category 命中 + 高互动）/ 🎯垂直（关键词精准命中）双视角，定位代表文章。深挖只做**原文保存 + 结构分析**（标题树/钩子/段落骨架/字数/代码块/配图），**仿写交给写博客 skill**（skill 间独立，不互引）。

## 何时用

- 不知道下一篇写什么 → 跑 `make tech-topic` 拿近期选题清单 + 假设大纲（Phase 1，不拉正文）
- 想蹭技术热点 → 看 🔥热度视角（高互动广覆盖）
- 想写垂直深度 → 看 🎯垂直视角（关键词精准命中）

## 数据源（多源，已实测验证）

掘金三源 + CSDN/InfoQ/知乎（`tech-topic-multi-source` 扩展，全部免费公开接口、免 self-host）：

| 源 | 通道 | 登录 | 互动字段 | 状态 |
|----|------|------|----------|------|
| 掘金 A | `recommend_api/v1/article/recommend_all_feed` | 免登录 | digg/view/collect/comment/hot_rank | ✅ |
| 掘金 B | `search_api/v1/search?query=…` | 登录态（`make tech-topic-login`）| 跨全文相关度 | ✅ |
| **CSDN** | `blog.csdn.net/phoenix/web/blog/hot-rank` | 免登录 | viewCount/favorCount/commentCount/hotRankScore | ✅ |
| **InfoQ** | `infoq.cn/feed`（RSS）| 免登录 | 无浏览量（getList 拿不到近期）→ 仅近期信号 | ✅ |
| **知乎** | `api.zhihu.com/topstory/hot-list` | 免登录 | 热度值；**关键词过滤**（全站热榜泛话题，只留技术向）| ✅ |
| DailyHotApi / 今日头条 | — | — | 需 self-host / 无技术信号 | ❌ 不接 |

- **方向映射**：掘金 `category_id` / InfoQ `topic` 标签 / CSDN/知乎 标题关键词（`sources.json` 配置）。
- **评分**：分源互动归一（× 源权重）+ 绝对 log 归一 混合，避免高量级源（CSDN👍千 / InfoQ views 万）淹没低量级源（掘金👍几十）；CSDN 标题不命中技术关键词的水文过滤掉。
- **输出格式**：topics.md「🔥 热门（每平台 Top N，按来源聚合）」+「🎯 垂直视角」**均为 markdown 表格**（`| 分 | 文章 | 方向 | 互动 |`）。N 由 `sources.json` 的 `per_source_top`（默认 **10**）控制。
- 掘金 B 源用 **GET + `query`**（非 POST+keyword）；首次 `make tech-topic-login` 登录后 headless 复用，未登录降级纯 A 源。掘金 category_id：前端 `6809637767543259144` / 后端 `6809637769959178254` / 人工智能 `6809637773935378440`（`category_map.json`）。

## 运行（两阶段：先选题，确认后再深挖）

```bash
# ── 首次：登录掘金（弹窗一次，cookie 持久化，之后免登录）──
make tech-topic-login

# ── Phase 1 选题（不拉正文）──  A+B 双源（B 需先登录；未登录自动降级纯 A）
make tech-topic                      # 默认 top=5, pages=2
make tech-topic top=8 pages=3        # 可调 Top 数与翻页
make tech-topic no-search=1          # 纯 A 源（更快，不启浏览器）
# 产物: .tech-topic/topics.md (人读) + topics.json (机读) + rough_outlines/ (假设大纲)
```

看到想对标的文章后，取其 `article_id`：

```bash
# ── Phase 2 深挖（拉原文保存 + 结构分析，不生成仿写）──
make tech-topic-deep id=<article_id>
# 产物: .tech-topic/articles/<id>/  article.html / article.txt / screenshot.png / meta.json / analysis.md
# 拿 analysis.md + 原文 → 用写博客 skill 仿写
```

## 评分（潜力分）

```
潜力分 = 0.45×互动量(归一) + 0.30×方向命中 + 0.15×时效(rtime 衰减) + 0.10×原创度
```
- 互动量以 `digg_count` 为主（+ collect×0.5 + comment×0.3）；`view_count` 口径模糊，仅展示不入分。
- 时效：**30 天硬过滤**（超出直接剔除，过滤掉远古爆款；实测剔除 113/140 篇）。
- 两视角各自系列内归一化、分开排名。

## ⚠️ 合规边界（强制，违反即错）

- 抓取的文章**正文仅作分析素材**（拆钩子 / 提结构 / 量化）。
- 本 skill 只到「原文保存 + 结构分析」，**不生成仿写内容**；仿写由写博客 skill 独立完成（差异化原创，禁止逐字搬运）。
- **禁止逐字照搬**原文发布（掘金有原创机制，搬运会被限流）。
- 控制抓取量级（选题研究用，不做大规模商业采集）。

## 配置（可编辑）

- `topic_keywords.json`：方向 → 关键词表（title/tags 命中 → 🎯垂直视角）。
- `category_map.json`：方向 → 掘金 category_id 映射。

## 依赖

| 依赖 | 用途 | 说明 |
|------|------|------|
| Python 3（stdlib） | A 源拉取（urllib，零依赖） | 已装 |
| playwright + chrome/msedge | B 源登录态搜索 / Phase 2 原文渲染 | macOS chrome、Windows msedge；skill 独立不互引 |

## 产物（`.tech-topic/`，git 忽略）

```
.tech-topic/
├── latest.json              A+B 原始结果（缓存 10 分钟）
├── topics.json / topics.md  双视角选题清单（机/人读）
├── rough_outlines/          Phase 1 假设大纲（Top N + INDEX.md）
├── msedge-profile/          B 源登录态（cookie 持久化）
└── articles/<article_id>/   Phase 2：article.html/.txt + screenshot.png + meta.json + analysis.md
```

## 工程约束

- 文件 I/O 显式 utf-8，子进程 `PYTHONIOENCODING=utf-8`。
- 变量名避开内置构造器（URL/name/status/data）。
- 接口先读响应 schema 再构造 payload，校验 `err_no` 与每字段（不只 HTTP 200）。
- 无方向命中诚实输出「近期无方向命中」+ 已试关键词，不硬凑。
