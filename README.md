# xiaoshuai skills

技术内容创作与多平台运营 Agent Skills 集合 —— 把「选题 → 写作 → 配图 → 发布 → 视频 → 评论承接 → 数据回看」全链路沉淀成可复用的 skill。

所有 skill 兼容 [Agent Skills 规范](https://agentskills.io)，可在 Claude Code、Cursor、Codex、Gemini CLI 等编码 Agent 里通用。

## 安装

```bash
npx skills add xiaoshuai1024/skills
```

安装后，在你的项目 `.claude/skills/` 目录下即可发现所有 skill。按需使用，不需要的全部忽略即可。

## 全景：18 个 skill 按场景选用（渐进叠加）

这些 skill 设计为**配合使用**，按你的内容运营需求分层叠加。每一层都独立可用，装到哪层用哪层：

```
                        博客   +选题   +合规   +公众号   +视频   +全平台运营
                        ────   ─────   ──────   ──────   ─────   ──────────
blog-writing             ✅     ✅       ✅       ✅       ✅        ✅
drawio / excalidraw      ✅     ✅       ✅       ✅       ✅        ✅
de-ai-smell              ✅     ✅       ✅       ✅       ✅        ✅
app-screenshot           ✅     ✅       ✅       ✅       ✅        ✅
tech-topic                      ✅       ✅       ✅       ✅        ✅
platform-compliance                      ✅       ✅       ✅        ✅
metadata-optimizer                       ✅       ✅       ✅        ✅
wechat-publishing                                ✅       ✅        ✅
image-text-cards                                 ✅       ✅        ✅
video-generation                                          ✅        ✅
douyin-topic                                                        ✅
mstodo-topic                                                        ✅
comment-auto-reply                                                  ✅
video-analytics                                                     ✅
video-pipeline-tracker                                              ✅
```

---

### Level 1 — 博客写作（基础）

**你能做什么**：写技术博客文章（选题自检→定类型→搭骨架→写正文→配图→润色→验证），画架构图和手绘概念图，去 AI 味，截应用窗口图。

| Skill | 作用 |
|-------|------|
| [blog-writing](skills/blog-writing/) | 写作全流程 9 步工作流（标题走 metadata-optimizer 候选→打分→人选定稿）+ 去 AI 味手册 + 分类型规范 + 公众号留存层；踩坑库含 date 未来时间静默跳过、drawio 书写方式等 |
| [drawio](skills/drawio/) | draw.io 架构图（禁止 mermaid），mxGraph XML + SVG 导出，去 AI 味配色硬规则 |
| [excalidraw](skills/excalidraw/) | 手绘风概念图/流程图/心智模型，Excalidraw 风格 |
| [de-ai-smell](skills/de-ai-smell/) | 去 AI 味扫描（L1 无例外禁词 + L2 慎用词 + 风格量化检查脚本），全站唯一权威词表 |
| [app-screenshot](skills/app-screenshot/) | 桌面应用窗口截图 + OCR（跨平台 macOS Vision / Windows WinRT），真实截图拿不到时 Playwright 复刻兜底 |

**依赖**：Python 3（de-ai-smell、app-screenshot）；draw.io CLI（drawio）；Node（excalidraw）。

---

### Level 2 — + 选题

**新增能力**：选题不再靠刷——外部信号（掘金/CSDN/InfoQ/知乎热榜、抖音热榜、你的 Microsoft To Do 待办收件箱）拉进来统一筛选，产出带大纲/口播分镜的选题报告。

| 新增 Skill | 作用 |
|------------|------|
| [tech-topic](skills/tech-topic/) | 四源技术选题（掘金推荐流+热榜 / CSDN 热榜 / InfoQ RSS / 知乎关键词过滤）→ 方向过滤 → 分源归一评分 → 每平台 Top 10 → 假设大纲 → 深挖原文保存+结构分析。全部匿名 API，stdlib 零依赖 |
| [douyin-topic](skills/douyin-topic/) | 抖音选题+对标拆解：免登录热榜 API（🔥热度/📈涨粉双系列）→ 作品搜索通道 → 下载原片 → faster-whisper 转写 → 拆钩子/结构/热评 → 可抄大纲+仿写脚本；含抖音精选对标档案 |
| [mstodo-topic](skills/mstodo-topic/) | **微软待办选题收件箱**：浏览器登录态打开 To Do 网页版，拉指定清单最新待办 → 三维分析（仿写价值/潜力/方向匹配度）出报告（合适项给文章大纲或口播稿+分镜）→ 备注追加+标记完成写回 → 编排写作/发布/视频 skill 走「文章(用户确认)→发布→视频→发布」生产链。浏览器通道自建（patchright + 静默 SSO + Bearer 会话提取），零第三方依赖 |

**依赖**：Python 3（stdlib 为主）；mstodo-topic 与 douyin-topic 深挖需 Playwright（patchright 优先）+ msedge/chrome。

---

### Level 3 — + 合规与元信息（发布前两道闸）

**新增能力**：标题/简介/话题有方法论（fact card → 分档候选 → 7 项清单打分 → 平台变体），违禁词有词库机检——发布前的质量与安全双闸。

| 新增 Skill | 作用 |
|------------|------|
| [metadata-optimizer](skills/metadata-optimizer/) | 标题/简介/话题优化：素材提 fact card → 5 档位候选（数字/问句/反差/后果/克制）→ `score_title.py` 7 项清单打分（≥4 合格）→ 人选定稿 → 平台变体（抖音 ≤30 字 / B站含关键词 / 公众号 ≤25 字钩子前移）→ `metadata-lint` 机检收口；含 `topic_suggest` 本地话题推荐（大词+长尾，零外部查询） |
| [platform-compliance](skills/platform-compliance/) | 多平台违禁词与敏感词检查——广告法极限词、夸大宣传、诱导引流、权威冒用，及抖音/快手/小红书/视频号各自红线；发布视频/口播/标题/封面/简介前扫描，HIGH 命中即拦 |

**依赖**：Python 3（纯 stdlib，词表+脚本自包含）。

---

### Level 4 — + 公众号同步

**新增能力**：写完文章一键同步到微信公众号（mp 后台 API 直推，跳过风控），含封面自动化、代码高亮、原文链接注入、定时群发、发布配置四查与 48h 完读率回看基线。

| 新增 Skill | 作用 |
|------------|------|
| [wechat-publishing](skills/wechat-publishing/) | 公众号 mp 后台 API 直推（Playwright 登录态）→ 草稿+定时群发+封面自动取首图 9:5+代码高亮（chroma→Monokai）+内链替换；发布配置四查（作者/合集/原创声明/广告开关） |
| [image-text-cards](skills/image-text-cards/) | 公众号/小红书图文笔记卡片设计（卡片秒抓眼球 + 正文深度展开，对比驱动与去术语化原则） |

**依赖**：Python 3 + playwright + bs4 + Pillow。配置 `.env.local`（见 [`.env.local.example`](skills/wechat-publishing/.env.local.example)）：站点 URL、作者名、合集 ID、masssend 指纹。

---

### Level 5 — + 视频生成

**新增能力**：把博客文章生成为横屏 16:9 视频（remotion 数据可视化 / courseware 课件含屏录感 / graph 知识图谱三种模式），IndexTTS-2 声音克隆配音（edge-tts 为 fallback）+ FFmpeg 合成，全本地零收费；产出四件套（成片+横竖封面+metadata）过四道机检门禁。

| 新增 Skill | 作用 |
|------------|------|
| [video-generation](skills/video-generation/) | 文章→视频三模式 + 视频三要素（提问式开头/钩子消费/BGM+音效+转场）+ 卡内分镜 shots（≤15s 句边界切换）+ 全元素动画联动 + 伴随机器人 + IndexTTS-2 克隆链（best-of-N 门禁+标点断句手术）+ 多平台定时发布（每日一篇原则+队列管理+平台侧回读验证）+ build→archive 生命周期 |

**依赖**：Python 3 + patchright/playwright + FFmpeg（系统安装）；Node + pnpm（remotion 渲染）；IndexTTS-2（WSL 环境，可选，fallback 到 edge-tts 需说明）。

---

### Level 6 — + 多平台运营闭环

**新增能力**：视频四平台（抖音/快手/B站/视频号）一键定时发布、评论区自动承接、数据回看反哺选题——运营从手动变成闭环。

| 新增 Skill | 作用 |
|------------|------|
| [comment-auto-reply](skills/comment-auto-reply/) | 评论承接（手动单命令）：采集 B站/抖音近 14 天未回复一级评论 → 规则分诊（无信息量跳过/技术提问 LLM 草稿/负面转人工）→ 逐条确认 → 自建通道发送（B站公开 API / 抖音评论管理页 DOM）+ 回读验证；配套置顶评论发布器（一级评论发送+合规闸+截图留证） |
| [video-analytics](skills/video-analytics/) | 多平台运营数据分析：四平台创作者后台只读采集 → 增量快照 → 单视频漏斗诊断 → 横向因子对比 → 「证据→诊断→动作」建议 → 选题关键词反哺 |
| [video-pipeline-tracker](skills/video-pipeline-tracker/) | 视频生产全生命周期状态台账：单一事实源 state.json（10 态 stage + blocked 标志 + history 追溯）+ vpt CLI（stage/queue/sync/report）+ 自动重生 Markdown 看板（进行中/队列日历含每日一篇冲突标记/归档近况/平台数据），多任务窗口共享 |

**依赖**：Python 3 + patchright/playwright；各平台登录态（cookie 持久化，扫码一次长期复用；B站走 biliup-rs 双轨）。

---

### 独立工具（按需，不属于上述管线）

| Skill | 作用 | 何时用 |
|-------|------|--------|
| [pua](skills/pua/) | 高绩效文化教练 skill——15 种大厂方法论按任务类型路由（Debug→RCA、新功能→Musk 五步、审查→减法优先），三条可判定红线 + 降压协议 + 失败计数持久化；实装样本见仓库博文 | Agent 躺平/糊弄/提前放弃时 |
| [crawl](skills/crawl/) | 爬虫反检测最佳实践（浏览器策略/平台技巧/速率/captcha） | 写/改爬虫脚本时 |
| [code-doc-maker](skills/code-doc-maker/) | 仓库 Markdown 文档治理（README 结构/面试笔记整理） | 补齐/整理仓库文档时 |

## 典型工作流示例

**从一条待办到四个平台的完整闭环**（全部 skill 协作的真实路径）：

```
mstodo-topic 拉待办清单 → 三维分析出报告（合适项附大纲/口播分镜）→ 写回待办
  → blog-writing 写文章（标题走 metadata-optimizer 打分）
  → drawio 配图 + app-screenshot 实拍
  → de-ai-smell 扫描 + hugo 构建门禁
  → 用户确认草稿 → deploy 发布 + wechat-publishing 同步公众号
  → video-generation 出视频（口播稿/分镜 → IndexTTS-2 克隆 → 渲染 → 四道门禁）
  → metadata-optimizer 出平台标题变体 → platform-compliance 扫违禁词
  → 四平台定时发布（每日一篇 20:00）→ 归档
  → comment-auto-reply 置顶评论 + 24h 回评
  → video-pipeline-tracker 全程记录 stage（看板 data/video-pipeline/dashboard.md）
  → video-analytics 48h 数据回看 → 结论反哺下一轮选题
```

## 配置约定

| 配置 | 说明 | 适用 skill |
|------|------|-----------|
| `.env.local`（gitignore） | 站点 URL / 作者名 / 合集 ID / masssend 指纹 | wechat-publishing |
| `topic_keywords.json` | 方向关键词表（**示例配置，按你的内容方向修改**） | tech-topic / douyin-topic |
| `category_map.json` | 掘金 category_id → 方向映射 | tech-topic |
| `.mstodo-topic/`（gitignore） | endpoints.json 接口固化 / 待办快照 / 分析报告 | mstodo-topic |
| `cookies/`（gitignore） | 各平台登录态（douyin/kuaishou/bilibili/shipinhao） | video-generation 发布 / comment-auto-reply |
| `data/analytics/` | 平台数据增量快照（进 git）/ 口播转写 wav（不进） | video-analytics |

## 设计原则

- **skill 自包含**：脚本在 skill 目录内，不引用外部路径；产物落项目根约定目录。
- **项目信息脱敏**：账号/域名/指纹/登录态通过环境变量与 gitignore 配置，不硬编码。
- **差异化原创**：所有涉及原文/原片的 skill 遵守「仅分析素材、产出差异化原创、禁止照搬」。
- **通道自建**：发布与数据采集一律 patchright/官方 API 直连，不引入第三方 SaaS 及其 CLI。
- **日志不可信**：一切发布/删除动作以平台侧回读验证为准（上传器返回值仅作参考）。
- **私有数据本地处理**：待办/登录态/数据快照不进 git、不出本机。

## License

MIT
