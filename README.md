# xiaoshuai skills

技术内容创作与多平台运营 Agent Skills 集合 —— 把「选题 → 写作 → 配图 → 发布 → 视频 → 发布后运营 → 评论承接 → 数据回看」全链路沉淀成 24 个可复用的 skill。

所有 skill 兼容 [Agent Skills 规范](https://agentskills.io)，可在 Claude Code、Codex、Cursor、Gemini CLI 等编码 Agent 里通用。

> 本仓只收**自研** skill。这套 skill 的特点是带着真实运营定规：不是「教你写」的方法论，而是每天真实产出文章/视频沉淀下来的机检门禁、平台红线与数据回看闭环。

## 安装

### 一键全量

```bash
npx skills add xiaoshuai1024/skills
```

安装后 skill 出现在你项目的 `.claude/skills/` 目录，Agent 自动发现。不需要的全部忽略即可，装全量不影响性能——skill 只在被触发时加载。

### 按场景选装（装哪些）

`npx skills add` 会装全部 24 个；真正的「选装」是**配置**——只有配了登录态/密钥的 skill 才能跑通完整链路，其余 skill 纯本地即可用：

| 你要做的事 | 必装（自动发现即用） | 需要额外配置才能跑满 |
|-----------|---------------------|---------------------|
| 只写技术博客 | blog-writing、drawio、excalidraw、de-ai-smell、app-screenshot、article-quality-check | 无（全本地） |
| + 选题 | tech-topic、douyin-topic、mstodo-topic | mstodo-topic 需 Microsoft 登录态；douyin-topic 深挖需 patchright + 浏览器 |
| + 标题与合规 | metadata-optimizer、platform-compliance、media-review | 无（词表+脚本自包含） |
| + 公众号 | wechat-publishing、wechat-analytics | wechat-publishing/analytics 需 mp 后台登录态 + `.env.local`（见下） |
| + 视频 | video-generation、stock-footage、video-detail-site | 视频发布需四平台登录态（cookies/）；IndexTTS-2 克隆链需 WSL 环境（可降级 edge-tts） |
| + 全平台运营闭环 | comment-auto-reply、video-analytics、video-pipeline-tracker、post-publish-ops | 需各平台创作者登录态；B站全链路走 web UI 通道 |
| 写口播稿/文章加梗 | talkshow | 无（口播按题材触发或点名，文章点名触发；联网搜热梗需网络） |
| 爬虫 / 文档 | crawl、code-doc-maker | 无 |

### 作为 submodule 接入你自己的项目（进阶）

如果你的项目本身就是这套 skill 的「运行场」（比如本仓作者的个人博客），推荐 submodule + junction 方式消费，保持 skill 单一归属：

```bash
git submodule add git@github.com:xiaoshuai1024/skills.git .skills
# Windows 本地接线（管理员或开发者模式）：
cmd /c mklink /J .agents\skills\<name> ..\.skills\skills\<name>
```

---

## 给 Agent 的场景提示词（复制即用）

> 用法：装好对应场景的 skill 后，把提示词整段粘给 Agent，替换 `【】` 里的内容。每条提示词都写明了 Agent 该按什么顺序调用哪些 skill、走哪些门禁——这是本仓的推荐用法，Agent 自由发挥不如按流程走。

### 场景 1：写一篇技术博客

需要：blog-writing、drawio、excalidraw、de-ai-smell、app-screenshot、article-quality-check（终检）、metadata-optimizer（标题打分）

```
用 blog-writing skill 写一篇《【主题】》的技术文章。要求：
1. 先做选题自检，定主导类型（教程/深度/踩坑/最佳实践/观点/随笔，只选一个）；
2. 开头用一个来自源码/实操的反直觉发现做钩子，正文必须回收；
3. 标题走 metadata-optimizer：fact card → 多档候选 → score_title.py 打分（≥4 分才给我选）；
4. 配图按字数配额执行（max(2, 字数÷1800) 张）：架构图用 drawio、概念图用 excalidraw
   （先看 excalidraw skill 的 references/examples/real-world/ 找同型骨架改）；
5. 写完跑 de-ai-smell 扫描（make check-ai-smell），L1 禁词清零、整句重写标红段；
6. 跑 article-quality-check 终检：机检门禁（relref/段落长度/标题数字兑现/重复片段）全绿后，
   按六大编辑终检组（润色/AI 味复判/趣味/流畅/合理/技术深度）过一遍，问题修完复跑到无阻断；
7. 最后 hugo build 验证再交稿。
```

### 场景 2：公众号文章（写作 → 发布 → 48h 回看）

需要：场景 1 全部 + wechat-publishing、wechat-analytics

```
把《【文章标题】》同步到公众号：
1. 先过 blog-writing 的 wechat-retention.md 留存清单：标题/摘要出独立变体
   （wechat_title ≤25 字含 1 个可搜关键词、摘要前 40 字含痛点或硬数字）；
2. 做公众号版长度决策：>4000 字默认压缩变体，≤2500 直发；
3. 走 wechat-publishing 存草稿（封面自动取首图、代码高亮、原文链接、内链替换），
   发布配置四查：作者非空/合集挂对/原创声明/广告开关；
4. 定时群发落 20:00-21:00 窗口；
5. 发满 48h 后跑 wechat-analytics 出单篇诊断卡，对照完读率 30/50/65 基线给结论。
```

### 场景 3：短视频生产（选题 → 口播稿 → 成片）

需要：douyin-topic 或 mstodo-topic、blog-writing、talkshow（可选）、video-generation、stock-footage、metadata-optimizer、platform-compliance、media-review

```
把《【文章/主题】》做成横屏视频：
1. 口播稿以文章为底，遵守视频三要素：提问式开头（「问你一个问题」/「你有没有想过」二选一）、
   钩子逐一消费（稿附钩子→回收映射表）、BGM+音效+转场分镜三列；
2. 结尾四段：价值兑现→互动问题→单动作引导→签名句（「我是1024工程笔记，越基础的东西，越值得讲透。」）；
3. 用 video-generation 渲染（remotion/courseware/graph 三选一），IndexTTS-2 克隆链配音，
   断句只认逗号句号，best-of-N 门禁选优；
4. 需要实拍素材时用 stock-footage 找免费源，产出溯源清单；
5. metadata-optimizer 出四平台标题/简介变体（抖音 ≤30 字、简介无外链），
   platform-compliance 扫违禁词，HIGH 命中即改稿；
6. 成片过 media-review 转化评审（P0-P3 问题三轮清零）+ 四道机检门禁（video-lint），
   封面必须自定，产出四件套。
```

### 场景 4：短视频日常运营（发布 → 评论 → 数据 → 反哺）★核心运营场景

需要：video-generation（发布链）、video-pipeline-tracker、comment-auto-reply、video-analytics、douyin-topic

```
进入日常运营节拍：
1. 发布：用 video-generation 的发布链把《【视频名】》挂四平台（抖音/快手/B站/视频号）
   定时，今天只发晚上 20:00 黄金档（一天最多一个视频，全平台同日同步同一条）；
   挂定时后必须逐平台回读核验（上传器日志不可信），封面在列确认，link-map 四平台齐全才算发布完成；
2. 台账：video-pipeline-tracker 记 stage（vpt stage/queue/sync），dashboard 看板更新，
   冲突用「修改定时」顺延，撤卡后平台侧复核到 0；
3. 评论：发后 1h 用 comment-auto-reply 采集未回复一级评论 → 分诊 → 技术提问出 LLM 草稿
   逐条确认发送，负面/求资源转人工；
4. 数据：发布满 48h 跑 video-analytics 采集四平台快照，出漏斗诊断（3s 退出/完播/CTR/
   涨粉），横向对比找最弱一环，给「证据→诊断→动作」；
5. 反哺：把诊断结论写回 link-map 备注， douyin-topic 用表现最好的钩子型找下一批对标。
```

### 场景 5：从一条待办到全平台的全链路

需要：以上全部 + code-doc-maker（无需）、mstodo-topic 起点版

```
我的待办清单里有选题「【待办内容】」。完整走一遍：
mstodo-topic 拉清单分析（三维：仿写价值/潜力/方向匹配）→ 出报告写回备注并标记完成
→ 场景 1 写文章 → 场景 2 同步公众号（用户确认草稿后）
→ 场景 3 做视频 → 场景 4 发布与运营
全程用 video-pipeline-tracker 记录 stage，任何一步不达标停给我看，别带病闯关。
```

---

## 全景：24 个 skill 按场景选用（渐进叠加）

这些 skill 设计为**配合使用**，按内容运营需求分层叠加。每一层独立可用，装到哪层用哪层：

```
                        博客   +选题   +合规   +公众号   +视频   +全平台运营
                        ────   ─────   ──────   ──────   ─────   ──────────
blog-writing             ✅     ✅       ✅       ✅       ✅        ✅
drawio / excalidraw      ✅     ✅       ✅       ✅       ✅        ✅
de-ai-smell              ✅     ✅       ✅       ✅       ✅        ✅
app-screenshot           ✅     ✅       ✅       ✅       ✅        ✅
article-quality-check    ✅     ✅       ✅       ✅       ✅        ✅
talkshow                 ✅     ✅       ✅       ✅       ✅        ✅
tech-topic                      ✅       ✅       ✅       ✅        ✅
platform-compliance                      ✅       ✅       ✅        ✅
metadata-optimizer                       ✅       ✅       ✅        ✅
media-review                             ✅       ✅       ✅        ✅
wechat-publishing                                ✅       ✅        ✅
wechat-analytics                                 ✅       ✅        ✅
video-generation                                          ✅        ✅
stock-footage                                             ✅        ✅
video-detail-site                                         ✅        ✅
douyin-topic                                                        ✅
mstodo-topic                                                        ✅
comment-auto-reply                                                  ✅
video-analytics                                                     ✅
video-pipeline-tracker                                              ✅
post-publish-ops                                                    ✅
```

---

### Level 1 — 博客写作（基础）

**你能做什么**：写技术博客文章（选题自检→定类型→搭骨架→写正文→配图→润色→验证），画架构图和手绘概念图，去 AI 味，截应用窗口图，口播稿/文章加梗。

| Skill | 作用 |
|-------|------|
| [blog-writing](skills/blog-writing/) | 写作全流程 9 步工作流（标题走 metadata-optimizer 候选→打分→人选定稿）+ 去 AI 味手册 + 分类型规范 + 公众号留存层（留存清单/长度决策三档/90 秒规则） |
| [drawio](skills/drawio/) | draw.io 架构图（禁止 mermaid），mxGraph XML + SVG 导出，去 AI 味配色硬规则 |
| [excalidraw](skills/excalidraw/) | 手绘风概念图/流程图/心智模型，真实 Excalidraw 引擎渲染；**附 16 张已发布文章的真实成稿案例库**（时间线/心智模型/阶梯/流水线/门禁，按图型索引，直接拿骨架改） |
| [de-ai-smell](skills/de-ai-smell/) | 去 AI 味扫描（L1 无例外禁词 + L2 慎用词 + 风格量化检查脚本），全站唯一权威词表 |
| [app-screenshot](skills/app-screenshot/) | 桌面应用窗口截图 + OCR（跨平台 macOS Vision / Windows WinRT），真实截图拿不到时 Playwright 复刻兜底 |
| [talkshow](skills/talkshow/) | 脱口秀式改写（**口播按题材触发或点名；文章仍点名制**）：写梗管线（态度先行→包袱先行→多版本竞争→六维诊断修梗）+ 联网搜梗引擎 + 密度门禁；同时覆盖口播稿与文章两条链路 |
| [article-quality-check](skills/article-quality-check/) | 文章定稿前质量终检统一收口：机检门禁（relref 断链/段落超长/标题数字兑现/代码块行数/收尾形态/重复片段/配图引用）+ 六大编辑终检组（润色复查/AI 味复判/趣味密度/流畅性/合理性/技术深度）+ 多篇隔离检查；编排 de-ai-smell/compliance/talkshow 的终检，不改它们的规则 |

**依赖**：Python 3（de-ai-smell、app-screenshot）；draw.io CLI（drawio）；Node + Playwright（excalidraw 首次渲染）。

---

### Level 2 — + 选题

**新增能力**：选题不再靠刷——外部信号（掘金/CSDN/InfoQ/知乎热榜、抖音热榜、你的 Microsoft To Do 待办收件箱）拉进来统一筛选，产出带大纲/口播分镜的选题报告。

| 新增 Skill | 作用 |
|------------|------|
| [tech-topic](skills/tech-topic/) | 四源技术选题（掘金推荐流+热榜 / CSDN 热榜 / InfoQ RSS / 知乎关键词过滤）→ 方向过滤 → 分源归一评分 → 每平台 Top 10 → 假设大纲 → 深挖原文保存+结构分析。全部匿名 API，stdlib 零依赖 |
| [douyin-topic](skills/douyin-topic/) | 抖音选题+对标拆解：免登录热榜 API（🔥热度/📈涨粉双系列）→ 作品搜索通道 → 下载原片 → faster-whisper 转写 → 拆钩子/结构/热评 → 可抄大纲+仿写脚本；含抖音精选对标档案 |
| [mstodo-topic](skills/mstodo-topic/) | **微软待办选题收件箱**：浏览器登录态打开 To Do 网页版，拉指定清单最新待办 → 三维分析（仿写价值/潜力/方向匹配度）出报告 → 备注追加+标记完成写回 → 编排写作/发布/视频 skill 走「文章(用户确认)→发布→视频→发布」生产链 |

**依赖**：Python 3（stdlib 为主）；mstodo-topic 与 douyin-topic 深挖需 Playwright（patchright 优先）+ msedge/chrome。

---

### Level 3 — + 合规与元信息（发布前三道闸）

**新增能力**：标题/简介/话题有方法论（fact card → 分档候选 → 7 项清单打分 → 平台变体），违禁词有词库机检，内容转化潜力有六维预估评审（选题期 1 万线门禁 + 发布前最后一道内容关）——发布前的质量、安全、转化三闸。

| 新增 Skill | 作用 |
|------------|------|
| [metadata-optimizer](skills/metadata-optimizer/) | 标题/简介/话题优化：素材提 fact card → 5 档位候选（数字/问句/反差/后果/克制）→ `score_title.py` 7 项清单打分（≥4 合格）→ 人选定稿 → 平台变体（抖音 ≤30 字 / B站含关键词 / 公众号 ≤25 字钩子前移）→ `metadata-lint` 机检收口；含本地话题推荐（大词+长尾，零外部查询） |
| [platform-compliance](skills/platform-compliance/) | 多平台违禁词与敏感词检查——广告法极限词、夸大宣传、诱导引流、权威冒用，及抖音/快手/小红书/视频号各自红线；发布视频/口播/标题/封面/简介前扫描，HIGH 命中即拦 |
| [media-review](skills/media-review/) | 内容转化潜力评审（视频成片+公众号文章两条资产线）：问题分级 P0-P3 + 三轮清零退出、选题期 1 万线预测门禁（六维预估中位 ≥10,000 才算选题完成，不达线按四杠杆迭代 ≤3 轮）、热点冲刺模式、运营配比与转化 KPI、发布后救片哨兵、封面标题 CTR 专项；砍卡撤卡有既定 SOP |

**依赖**：Python 3（纯 stdlib，词表+脚本自包含）。

---

### Level 4 — + 公众号

**新增能力**：写完文章同步到微信公众号（mp 后台 API 直推，跳过风控），含封面自动化、代码高亮、原文链接注入、定时群发、发布配置四查与 48h 完读率回看基线。

| 新增 Skill | 作用 |
|------------|------|
| [wechat-publishing](skills/wechat-publishing/) | 公众号 mp 后台 API 直推（Playwright 登录态）→ 草稿+定时群发+封面自动取首图 9:5+代码高亮（chroma→Monokai）+内链替换；发布配置四查（作者/合集/原创声明/广告开关） |
| [wechat-analytics](skills/wechat-analytics/) | 公众号数据分析：mp 后台只读采集（单篇/详情/趋势）→ 增量快照 → 转化五级漏斗诊断（送达→打开→读完→互动→关注导流）→ 打开/完读/转化三层归因 → 48h 回看对照 30/50/65 完读基线出结论 |

**依赖**：Python 3 + playwright + bs4 + Pillow。配置 `.env.local`（见 [`.env.local.example`](skills/wechat-publishing/.env.local.example)）：站点 URL、作者名、合集 ID、masssend 指纹。

---

### Level 5 — + 视频生成

**新增能力**：把博客文章生成为横屏 16:9 视频（remotion 数据可视化 / courseware 课件含屏录感 / graph 知识图谱三种模式），IndexTTS-2 声音克隆配音（edge-tts 为 fallback）+ FFmpeg 合成，全本地零收费；产出四件套（成片+横竖封面+metadata）过四道机检门禁。

| 新增 Skill | 作用 |
|------------|------|
| [video-generation](skills/video-generation/) | 文章→视频三模式 + 视频三要素（提问式开头/钩子消费/BGM+音效+转场）+ 卡内分镜 shots（≤15s 句边界切换）+ 全元素动画联动 + IndexTTS-2 克隆链（best-of-N 门禁+标点断句手术）+ 四平台定时发布（每日两窗口原则+队列管理+平台侧回读验证+严禁无封面）+ build→archive 生命周期 |
| [stock-footage](skills/stock-footage/) | 免费实拍/档案素材检索：16 个免登录或免费注册素材源（NASA/Wikimedia/Archive.org/Mixkit/Pexels 等）统一搜索下载，产出溯源清单；只收免费/自由许可源 |
| [video-detail-site](skills/video-detail-site/) | 视频详情预览站：扫描全部成片生成本地静态站点（列表页+每支视频独立 URL 详情页：播放器/meta/口播稿全文/分镜脚本），浏览器直接看成片 |

**依赖**：Python 3 + patchright/playwright + FFmpeg（系统安装）；Node + pnpm（remotion 渲染）；IndexTTS-2（WSL 环境，可选，fallback 到 edge-tts 需说明）。

---

### Level 6 — + 多平台运营闭环

**新增能力**：视频四平台（抖音/快手/B站/视频号）一键定时发布、发布后运营位（置顶作品/动态/私信/免费活动）、评论区自动承接、数据回看反哺选题——运营从手动变成闭环。

| 新增 Skill | 作用 |
|------------|------|
| [comment-auto-reply](skills/comment-auto-reply/) | 评论承接（手动单命令）：采集 B站/抖音近 14 天未回复一级评论 → 规则分诊（无信息量跳过/技术提问 LLM 草稿/负面转人工）→ 逐条确认 → 自建通道发送（B站公开 API / 抖音评论管理页 DOM）+ 回读验证；配套置顶评论发布器 |
| [video-analytics](skills/video-analytics/) | 多平台运营数据分析：四平台创作者后台只读采集 → 增量快照 + SQLite 时间序列库 → 单视频漏斗诊断（3s 退出/完播/CTR/涨粉）→ 横向因子对比 → 「证据→诊断→动作」建议 → 选题关键词反哺 |
| [video-pipeline-tracker](skills/video-pipeline-tracker/) | 视频生产全生命周期状态台账：单一事实源 state.json（10 态 stage + blocked 标志 + history 追溯）+ vpt CLI（stage/queue/sync/report）+ 自动重生 Markdown 看板（进行中/队列日历含冲突标记/归档近况/平台数据），多任务窗口共享 |
| [post-publish-ops](skills/post-publish-ops/) | 视频发布后运营统一入口：发布后时间线（复查→置顶评论→承接→回看→转化判断）+ 新运营位（抖音主页置顶作品/B站稿件编辑与弹幕/视频号评论弹幕私信三件套/四平台免费活动与话题借势/视频号×公众号联动）；硬定规=不做直播、不投流；只读实查 SOP + 留证 |

**依赖**：Python 3 + patchright/playwright；各平台登录态（cookie 持久化，扫码一次长期复用；B站全链路走 web UI 通道）。

---

### 独立工具（按需，不属于上述管线）

| Skill | 作用 | 何时用 |
|-------|------|--------|
| [crawl](skills/crawl/) | 爬虫反检测最佳实践（浏览器策略/平台技巧/速率/captcha） | 写/改爬虫脚本时 |
| [code-doc-maker](skills/code-doc-maker/) | 仓库 Markdown 文档治理（README 结构/面试笔记整理） | 补齐/整理仓库文档时 |

## 典型工作流示例

**从一条待办到四个平台的完整闭环**（全部 skill 协作的真实路径）：

```
mstodo-topic 拉待办清单 → 三维分析出报告（合适项附大纲/口播分镜）→ 写回待办
  → blog-writing 写文章（标题走 metadata-optimizer 打分）
  → drawio 配图 + excalidraw 手绘图 + app-screenshot 实拍
  → de-ai-smell 扫描 + article-quality-check 终检 + hugo 构建门禁
  → 用户确认草稿 → deploy 发布 + wechat-publishing 同步公众号
  → video-generation 出视频（口播稿/分镜 → IndexTTS-2 克隆 → 渲染 → 四道门禁）
  → stock-footage 补实拍素材（需要时）→ video-detail-site 本地预览验收
  → metadata-optimizer 出平台标题变体 → platform-compliance 扫违禁词 → media-review 转化评审
  → 四平台定时发布（每日一条 20:00 黄金档，全平台同日同步）→ 归档
  → comment-auto-reply 置顶评论 + 24h 回评
  → video-pipeline-tracker 全程记录 stage
  → video-analytics / wechat-analytics 48h 数据回看 → 结论反哺下一轮选题
```

## 配置约定

| 配置 | 说明 | 适用 skill |
|------|------|-----------|
| `.env.local`（gitignore） | 站点 URL / 作者名 / 合集 ID / masssend 指纹 | wechat-publishing / wechat-analytics |
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
- **只收自研**：本仓不收第三方开源 skill；第三方工具以依赖形式引入，不以 skill 形式入库。

## License

MIT
