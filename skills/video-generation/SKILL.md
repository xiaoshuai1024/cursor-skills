---
name: video-generation
description: 把技术博客文章/主题生成为横屏 16:9 视频。三种模式：remotion（默认，数据可视化+真实素材）、courseware（课件，含 screencast 屏录感工具界面子模式）、graph（知识图谱）。edge-tts 配音 + Playwright/Remotion 渲染 + FFmpeg 合成，全本地零收费。含多平台发布（抖音/快手/小红书/视频号）。
---

# Video Generation Skill

把一篇技术博客文章 / 一个技术主题生成为**横屏 16:9 视频**。三种程序化模式：

- **remotion（默认）**：数据可视化 + 真实素材——深色科技网格底 + 真实数据图表 + 素材标注，适合发布速报、性能对比、教程步骤（Remotion 管线，`remotion/` 目录）。**默认主题，参照 `after-million-loc-my-skills.mp4`**
- **courseware**：课件式——左栏要点逐条浮现 + 右栏知识卡片 + 底部字幕带（Playwright 管线）
- **screencast（courseware 子模式）**：屏录感工具界面——**浏览器真实网页截图打底 + 箭头标注是主角**（`realshot`：任何能在浏览器里呈现的步骤都截图，官网 / 市场 / GitHub / 控制台 / 在线编辑器都行），CSS 仿真窗口（VSCode mockup / 终端）只在浏览器截不到时才兜底（本地桌面应用、需登录态的真实界面）。标题栏下方**顶部常显步骤条**（全部步骤：done/active/future 三态），`active_idx` 高亮当前操作 + 光标箭头，对标抖音「录屏+标注」爆款（Ai小白Lab 26.2 万赞）。deck 卡 `type:"tool"` 即触发
- **graph**：节点图/知识图谱——中心辐射布局，节点逐个高亮 + 连线生长，适合概念关系/体系架构（Playwright 管线）

三种模式共用 TTS/断句/字幕规则（`narrate.py`）。数据 → edge-tts 配音 + 程序化画面渲染 + FFmpeg 合成。零收费、全本地。

## 目录结构（skill 存代码，产物落项目根）

skill 目录只放可复用代码/脚本/模板。**所有内容配置、渲染产物、临时文件**落在项目根的 `video-generation/`（git 忽略），通过路径自动解析（skill 根向上找 `hugo.toml`/`.git` 定位项目根）。

```
.agents/skills/video-generation/          ← skill：只放可复用代码
├── SKILL.md
├── remotion/                             Remotion 管线（React + Three.js）
│   ├── src/core/                         框架（VideoConfig/VideoComposition/theme）
│   ├── src/primitives/                   视觉原语
│   ├── src/scenes/                       通用场景组件
│   ├── src/videos/                       示例/测试 video configs（dummy/showcase）
│   ├── remotion.config.ts                webpack alias @videos + @skill-src
│   └── scripts/render.ts                 渲染入口
├── scripts/video/                        Playwright 管线核心模块
│   ├── config.py                         OUTPUT_ROOT = 项目根/video-generation
│   ├── build/courseware/graph/...        build/narrate/timeline/frames/render/tts
│   ├── screencast.py                     屏录感工具界面渲染（courseware `type:"tool"` 分发）
│   ├── narrate.py                        通用口播生成
│   ├── assets/                           bgm.mp3 等可复用素材
│   ├── narrate_*.py                      各 Remotion 视频口播生成
│   └── probe_*.py                        TTS 发音探针

video-generation/                        ← 项目根：所有内容配置 + 渲染产物
├── narrations/<slug>.json                口播文案（voice/rate/cards[]）
├── deck/<slug>/deck.json                 Playwright 课件卡片定义
├── deck/<slug>/deck-graph.json           Playwright 节点图定义
├── narration/                            Remotion 口播 mp3 + 时间戳 json
├── remotion-videos/<id>/                 Remotion 内容视频实例（config.ts + narration.ts）
├── build/<slug>/                         成片统一目录：<slug>.mp4 + 同目录 <slug>_cover.png + metadata + 音视频分段（out / covers 已弃用）
└── probe/                                TTS 发音探针输出
```

## 何时用

- 把博客文章转成横屏知识/培训讲解视频（B站知识区、YouTube、在线课程风格）
- **默认 remotion**（数据可视化 + 真实素材）；概念关系/知识体系/架构拓扑 → **graph**；线性课件讲解 → **courseware**
- **教程/操作/选型类要对齐抖音「录屏+标注」爆款** → **screencast**（courseware 子模式，`type:"tool"` 卡）
- 需要「讲到哪、信息跟到哪」的跟随感（非静态卡片轮播）

## 内容驱动设计（强制，先于管线选型）

**先判定文章内容类型，再选管线/结构，禁止默认套模板。** 结构由内容派生，不是由管线决定：

| 内容类型 | 判定信号 | 推荐结构 |
|---------|---------|---------|
| 清单 + 流程 | 按阶段/顺序逐组列举实体（如「研发生命周期 6 组 skill」） | **阶段递进**：阶段导航 + 组内条目卡片，按流程主线逐阶段推进 |
| 榜单 / 排行 | 有可量化排序（GitHub Star、性能分） | 排行榜（LeaderboardChart）+ 逐条卡片 |
| 对比 / 选型 | 两两对照、决策树 | 对比表 / 选型原则 |
| 概念 / 体系 | 概念关系、心智模型 | 概念图 / 中心辐射（graph） |
| 教程 / 步骤 | 线性操作步骤 | **screencast**（`type:"tool"` 卡）：拟物化真实截图/工具窗口 + 箭头标注，对齐抖音「录屏+标注」|

- **判定方法**：读文章标题 + 章节大纲 + 主体结构（`##` 标题怎么组织），判断主线是「顺序推进」还是「并列概念」还是「量化排序」
- **配图密度**：随篇幅分档（2000-4000 字 ≥2 张图），但视频不套用此配额——视频按场景数保证信息密度
- **反例（本 skill 踩坑）**：清单+流程型文章（百万行 Skill 分组）被套 graph 中心辐射模板，阶段被降为并列卫星节点、每条 skill 的「管什么」无承载。修复：阶段递进布局 + 每阶段 skill 卡片（`SkillStage` 场景）

## 内容创作规范：开头 · 呈现 · 互动（数据驱动，2026-08-17 定规）

> 背景：近 10 个视频数据诊断——**2s 跳出率普遍 >45%**（同类均值 35%-40%），**评论率≈0**。根因：① 开头多为静态标题页，信息密度低；② 缺少激发提问/讨论的钩子。目标：新视频 2s 跳出率降到 40% 以下、评论率明显提升。以下技巧来自同赛道热门视频拆解（pi-agent 源码书 / 7 种 Agent 架构 / DeepSeek Harness 等），**开头（痛点+数据反差）和视觉呈现（代码高亮+动态流程图）是最快见效的两块**。本节在「内容驱动设计」定完结构后执行，管口播稿、deck 骨架和画面呈现。

### 开头：抓住黄金 2 秒（强制）

- **禁静态标题页开场**：视频第一卡（前 2s 画面 + 第一句口播）不允许是「标题念一遍」的封面式画面。
- **痛点前置**（问题解决类）：第一句直接戳痛点，用「惊艳反差 + 数字」句式，如「Agent 出 demo 只要一周，上线却要一年？差距就在这三个坑里」。痛点句要具体到场景和数字，不要泛泛「很多人都会遇到」。
- **提问 + 数据制造认知反差**（科普类）：先抛常见问题，再用数据指出多数人的错误认知，如「从零搭 Agent 系统，你会选什么架构？80% 的人只听过 ReAct 或 Multi-Agent」。数字是钩子的核心，没有数据支撑的反差句不写。
- **结果前置**（教程类）：开头先展示最终成功的界面/结果（真实截图/最终数据），让观众立刻看到「跟着做能成」，再回头讲步骤。
- **「问题-答案」结构贯穿全片，不只在开头**：正文每个模块都用「先抛观众可能遇到的具体问题 → 再给解法」组织，❌ 禁说明书式平铺。对比：「安装需要 Node 22.14+」是说明书；「为什么你安装总失败？因为忽略了 Node 版本这个硬门槛」是问题-答案。deck 搭骨架时每个卡片的标题优先写成问题句，答案作为揭示内容。
- 第一句口播 ≤ 20 字、含具体钩子（数字/痛点/反常识），写完稿自查：把第一句单独拿出来，问自己「刷到这条会不会停下」。
- 封面/标题同理：标题文案优先用痛点问句或结果承诺，不用平铺直叙的主题名。

### 抖音审核红线（2026-08-17 事故沉淀，强制）

- **「评论区」三字是硬违规**：口播、字幕、封面、简介、metadata 全部禁止出现「评论区 + 指令动词（报/扣/发/搜）」结构——top10 视频因此被判「不适宜公开」。引导互动改用**选择题/站队句**（「你站哪边」「聊聊你的组合」），无指令动词。
- **引导句可「有声无字幕」**：结尾讨论句留在口播里，字幕/画面文字停在此句之前（字幕是硬文本最易被扫，音频转写命中率低一档；不保证豁免，只降概率）。Outro 的 ctaText 只放中性选择题。
- **极限词连带**：「第一/最强/暴涨/天花板」等即使技术语境也会触发 2026-07 新规清洗（GLM 视频因此连带风险）。技术表述改「开源榜前列/提升 X%」。
- **胜负宣言 + 挑衅语气点名竞品是引战风险源**（2026-08-18 Pi 视频定规）：❌「Pi 凭什么打赢 Claude Code？便宜一半分数打平」——「凭什么」是挑衅反问、「打赢」是胜负宣言、再点名商业竞品，三重叠加易判「贬低竞品/引战」（封面标题「打赢 Claude Code 和 Codex」风险更大）。✅ 规避手法：**用数据陈述代替胜负宣言**——「账单差一倍」「分数打平」「7 席占 4 席」是客观数据可过，「打赢/吊打/碾压」是判决必避；竞品可以出现但只做参数对比，不做高下判决。对比类标题模板：「同一个模型换个壳，账单差一倍：Pi Agent 跑分拆解」。
- 发布描述（metadata 简介）、评论区管理（预审 + 及时删违规评论）同口径：无指令词、无导流。
- 发布后如被判违规：创作者服务中心 → 作品分析 → 申诉（原始文件），勿用第三方强开。

### 完播率优化：价值钩子前置 + 结论先行（2026-08-17 专家建议，强制）

> 数据背景：某源码解析视频 2s 跳出率 43.51%、完播率 1.46%。根因是「内容价值」与「观众预期」匹配效率低——观众要的是「我能学到什么 / 这有什么用」，不是创作者的过程铺垫。目标：2s 跳出率 < 30%，平均播放时长提升。

- **前 3 秒放最精彩的东西**：把全片最有洞察力的结论 / 看点 / 动态画面直接放到开头 3 秒（如核心流程图动起来、一句反常识结论）。❌ 禁过程性开场（「我肝了一天」「我完整读了一遍源码」）——真实但不构成观看理由。
- **结论先行（核心结构）**：先告诉观众 3 个核心收获（「看完你会得到这三个判断」），再逐一展开论据如何支撑结论。观众带着明确目标看下去，完播才立得住。适用所有讲解结构，与「问题-答案」结构叠加使用：开头给结论清单，正文每段用问题引出对应结论。
- **首句即价值承诺**：第一句口播写成「看完这条你能得到 X」或直接抛最锋利的结论，≤20 字。
- 效果验证：改版发布后盯 2s 跳出率（目标 <30%）与平均播放时长，数据说话。

### 讲解呈现：把抽象变具象（强制）

- **代码动态高亮**（优先做，技术视频专业感的最大来源）：代码画面不做静态截图——当前讲到的关键行/变量用高亮框或颜色变化突出，引导视线。
- **流程图必须「动」起来**：讲执行步骤/数据流向时，框图跟着口播一步步渐显、箭头逐段生长，❌ 禁止整图一次性静态铺出。「Agent 轮次生命周期」这类流程，讲到哪一步亮到哪一步。复杂概念（「Agent 的本质是循环」「错误回灌」）同理——讲什么概念，就让画面动什么。
- **概念卡片化**：新术语（如「Harness 工程」）不只口头说，弹出带定义 + 简图示的卡片，降低认知负荷。
- **术语翻译成人话 + 配图示**：专业术语首次出现配一个类比（如 MCP 协议 = AI 界的 USB 接口），类比要日常、具体，一个术语只用一个类比；且不能只停留在口播，配一张比喻示意图，图文同出。
- **数据图表化**：关键数字（「45 万行代码」「24 万 Star」）用柱状图/图标/数字递增动画呈现，不落在纯文字里，数据仍必须真实来源。
- **错误场景视觉预警**：演示报错/注意事项时用红色边框、闪烁、⚠️ 图标强调，不允许错误信息和普通信息同视觉权重。
- **对比呈现**：选型/优劣判断用左右分屏或前后对比，配醒目数字/颜色（绿=更优）让差异一目了然，不单独罗列。给出对比后要落到「怎么选」的判断，体现专业立场。
- **故事化场景代替干讲**：技术问题放进具体工作场景讲，如讲安全机制不说「防止危险操作」，而是「万一模型想要 delete 甚至 drop」——危险场景 + 具体命令比原理讲解印象深刻 10 倍。口播写场景，不写定义。
- **进度条 + 章节导航**：多章节视频要有清晰导航让用户知道学到哪了——screencast 的顶部步骤条（done/active/future）、Remotion 的阶段导航已是管线能力，**其他模式讲多实体时也要补编号标题卡**（如「01 单 Agent 架构」「02 ReAct 架构」），长视频角落可常驻迷你进度条。
- **视觉锚点**：录屏/界面演示时用箭头、圆圈、放大效果突出正在点击的按钮或关键区域，避免观众在复杂界面里迷失；关键步骤必须有视觉强调，不允许关键信息裸出。
- **结尾问题做成视觉卡片**：结尾互动问题不只在口播里，用醒目文字卡片定格收尾（如「你在安装时遇到了什么坑？」），口播 + 画面双露出。
- **避坑：信息过载**——一帧画面不堆满所有文字图表，分点分步展示（跟随 `active_idx` 逐条揭示）。
- **避坑：单调背景**——不用纯黑/纯白背景，用现有主题底（深蓝黑 `#0a0e1a` + 网格纹理 + 光晕 / 浅灰蓝），已有配色规范不变。

### 价值与互动：可带走 + 留讨论钩子（强制）

- **可带走的额外价值**：视频结尾或简介给出一份可下载/可访问的资料（博客原文、在线文档、配套代码/书），给用户明确的收藏理由，如「我把所有工具都放在在线文档里了」。有对应博客文章的视频，简介末尾必附原文链接。
- **结尾选择题引导互动**：收尾用开放式问题或选择题（如「你站哪边？未来 AI 产品该像 Codex 一样简单，还是像 Harness 一样开放？」），二选一比开放问答更容易让人下场站队。
- **内容埋点**：讲复杂概念/巧妙设计时，可留思考题悬念（如「这段代码为什么这么写？可以想一想」），后半段或字幕里给解答，制造「看下去 + 来评论」的双重动机。
- **提问要具体 + 给回应承诺**：❌「大家有什么想法？」（太泛，没人接）✅「你切换 Provider 时踩过哪个坑？」（具体场景才有人答）。提问后加一句回应承诺（「评论区聊聊，我来帮你看看」），让观众知道留言会被接住，显著提高下场意愿。
- ⚠️ **与平台合规的边界**（见下「规则约束 → 平台合规」）：允许**开放式提问/选择题引导讨论**；**禁止**「评论区扣 XX」「关注我看下期」类诱导 CTA。提问句式本身不带指令性动词（扣/发/搜），用「聊聊」「说说」「你站哪边」这类讨论词。
- 问题写进口播末段 + 简介文案（metadata.txt 的 `简介`），双露出。

### 管线能力缺口清单（规则先行，能力补齐前先验证再依赖）

上述规则里这几项目前管线**未完整支持**，生成视频遇到时先核对/补齐，不要当成现成能力用：

| 规则 | 缺口 | 位置 |
|------|------|------|
| 代码动态高亮 | `CodeBlock` 行级高亮未验证是否支持逐行 active 态 | `remotion/src/primitives/CodeBlock` |
| 错误场景视觉预警 | `terminal` 卡无 error 态样式（红色/闪烁/⚠️） | `scripts/video/screencast.py` |
| 迷你进度条常驻 | 各模式均无角落进度条组件 | courseware/graph/Remotion 均缺 |
| 术语比喻配图示 | 无现成比喻示意组件，需新原语或 Excalidraw 素材 | Remotion primitives |
| 结尾问题视觉卡片 | `cta` 卡可承载，但无「问题卡片」专用样式 | `screencast.py` `_CONTENT.cta` |

已确认支持：graph 连线扫描 / Remotion 卡片逐张浮现（动态流程）、courseware `sub_points`（概念卡片）、`LeaderboardChart`/`DataReveal`（数据图表）、realshot hotspots + `.hot.active`（视觉锚点）、screencast 顶部步骤条 / Remotion 阶段导航（进度导航）、`ComparisonTable3D`/`cost` 卡（对比）、`active_idx` 逐条揭示（防信息过载）。

### 内容覆盖（强制，文章→视频的完整性）

- 视频必须覆盖**文章提及的所有条目/插件/skill/关键实体**，不得遗漏重要信息。观点、论述、铺垫可以简化删减，但**每个条目的核心信息（「它是什么 / 能做什么」）必须出现**。
- 判定标准（检查清单）：把文章的关键实体（插件名 / 模型名 / 术语）列成清单，逐条确认在视频里有明确呈现（专属卡片 / 图表行 / 口播均可），缺一个就是漏。**光在榜单里一行闪过不算覆盖**。
- ❌ 反例（claude-plugins 视频踩坑）：排行文章 12 个插件，视频只给 4 个做了介绍卡片，其余 8 个只在排行榜里一闪而过——用户判定为「有遗漏」。修复：每个插件一个「能做什么」卡片（观点/选型段可缩短）。
- 排行类视频的完整结构参考：封面 → 快速过排行 → **逐个条目卡片**（每个：名字 + 星数 + 它是什么）→ 选型/观点（可简化）→ 结论 → 结尾。

### 效果验证

新视频发布后观察：**2s 跳出率 < 40%**、**评论率**相对前 10 条均值提升。未达标先复查第一卡是否静态、结尾是否缺提问，再动其他变量。

## 依赖

| 依赖 | 用途 | 安装 |
|------|------|------|
| edge-tts | 免费 TTS（Azure 同源中文声音）+ 词级时间戳 | `pip install edge-tts` |
| Playwright | 程序化画面逐帧渲染 | `pip install playwright`（chromium 本机已有）|
| FFmpeg | 音视频合成 | 已装 |

## 规则约束（强制，违反即错）

### 画面
- **横屏 16:9，1920×1080**（知识/教学视频标准）
- **courseware**：左栏（标题+要点三态）+ 右栏（知识卡片 sub_points）+ 底部字幕带 + 进度条
- **graph**：中心节点（当前主题放大发光）+ 卫星节点环绕 + 连线从中心辐射；节点三态（active 高亮 / done 半亮 / future 暗淡）
- **两种主题**：`dark`（默认，深蓝黑底 + 霓虹青 `#22d3ee`）/ `light`（亮色中性，浅灰蓝底 + 深蓝 `#2563eb`）
- **graph 动效**（帧级驱动，非 CSS animation）：节点入场缩放（0.3→1.0）、active 节点脉冲环扩散、连线扫描 dashoffset、中心节点呼吸
- **screencast（courseware `type:"tool"` 卡）**：整屏一张真实工具窗口（Mac 红绿灯 + 标题栏 + 「记录中 ●」），标题栏下**顶部步骤条常显全部步骤**（编号圆点 + 标签，done 绿色 ✓ / active 青色发光 / future 暗淡），内容按 `points` 逐条 `active_idx` 高亮 + 光标箭头；底部字幕带 + 进度条。背景：青网格（44px 间隔 + 2px 粗线 + 20px 偏移，保证线落在可见边距且 H.264 编码后仍可见——1px 细线会被压缩抹平）+ 左上青 / 右下紫双光晕。
  - 热点高亮**只加边框发光**（`.hot.active` 只设 border-color + box-shadow，`!important` 不覆盖元素自身背景/渐变）——badge / CTA / 价格色块靠自身渐变活着
  - 窗口内文案必须与文章口径一致（如本文「热重载」是禁词，settings 窗口里也不能出现）；改口播时同步改 deck 对应卡
  - 排行榜（`rank` 卡）分数必须真实来源（如 Terminal-Bench 2.1 官方实测），条形宽度 = 分数 / 榜首 折算；数据从榜单抓取，不编造
  - **拟物化方向（教程类强制，2026-08-03 定规）**：教程/操作类不用抽象 CSS 假界面、不 mockup 能真实截图的界面。**核心原则：能浏览器截图的步骤，一律用 `realshot` 截真实网页**（`capture_shots.py` 抓官网实拍 1600×900，热点坐标记百分比；渲染时 base64 内嵌 + `.shotwrap` 16:9 容器 + 热点框随 `active_idx` 三态 + 箭头标签）。**不只是下载/安装页——任何能在浏览器里呈现的 UI 都该截**：官网、应用市场、GitHub、控制台、在线编辑器（如 vscode.dev）。CSS 仿真窗口（`vscode` mockup / 终端）**只在浏览器截不到时才兜底**（本地桌面应用、需登录态才能进的真实界面）。截图不编造内容
  - **内容事实校验（强制，2026-08-17 定规）**：写进 deck/口播的**数字和命令必须先验证**——① 涉及 star 数一律查 GitHub API（`api.github.com/repos/<owner>/<repo>` 的 `stargazers_count`），文章/网页里的旧数据经常过时（实测 8.5k → 9603）；② 涉及 npm 包名一律 `npm view <pkg>` 验证存在性（文章里流传的 `@deepseek-ai/dsh-tui` 实际是 404，正确包是 `@deepseek-harness-tui/dsh-tui`）；③ 教程类**下载地址必须写进画面**（realshot 的 `url_note` / 口播报域名），不能只说「官网下载」四个字
  - **官网截图超时兜底（2026-08-17 踩坑）**：部分官网（dshdesktop.cn）对 Playwright 默认 `goto(domcontentloaded)` 直接超时，curl 却能 200——改用 `wait_until="commit"` + 长 settle（10s+）能截到；热点坐标用 `bounding_box()` 实测百分比，不目测（页面改版会漂移）
  - **平台合规（强制）**：口播 + 画面**禁止「评论区扣XX / 关注我」类诱导 CTA**（抖音违规诱导，限流/下架）；结尾用中性价值钩子（「零基础四分钟装好 · 不用注册官方账号」）**或开放式提问/选择题**（「你站哪边？」「你卡在哪一步？评论区聊聊」，见「黄金 2 秒与互动设计」）。禁止自问自答设问句（「key哪来」）——**画面里也不能出现**（反例：`terminal` 曾硬编码「← 还是官方模型？」自问句）
  - **tool 卡内容全透传**：`build.py::normalize_card` 必须 `dict(raw)` 透传 tool 卡全部字段（big/mats/cta/items/req/resp/hotspots/lines 等），否则 builder 落默认值（老 bug）。**新增可配内容不要硬编码进 builder**（反例：`terminal` 曾硬编码旧视频「Claude Opus 5」内容），一律走卡字段

### 发音（重要决策，多次试听迭代确认）
- edge-tts 中文语音**不支持 SSML 音素控制**（标签会被当文本读出）
- **缩写逐字母 vs 单词音的权衡**（核心经验）：
  - 逐字母（DOM→`D O M`）读得准，但每个字母停顿 ~197ms，**慢且不自然**
  - 单词音（API→/æpi/、GLM→/gælm/）**自然流畅**，虽不完全符合中文技术圈逐字母习惯，但可识别
  - ✅ **结论**：`normalize_for_tts` 白名单**只留会被读成"无法识别中文错音"的词**，其他缩写当单词读。当前白名单 = `{DOM, AI}`。
  - ⚠️ **AI 必须逐字母**（claude-plugins 视频踩坑，两次复发）：男声 `YunxiNeural` 实测原始 "AI" 被当单词读成拼音音"爱/哀"（不自然），"A I" 才是技术圈标准读法。故 AI 进白名单 → normalize 展开成 "A I"。**旧的"AI 自动逐字母、保持原样"结论是错的**，WordBoundary 探针已推翻。验证方法：合成后看 WordBoundary 是否把 AI 拆成 A、I 两个独立词。
  - ⚠️ **TUI 大小写通吃 + 探针必须用口播原文（2026-08-17 踩坑）**：dsh-TUI 读音错误两轮才修好——第一轮只把 `TUI` 加进白名单，但白名单正则 `[A-Z]{2,5}` 只匹配大写，而口播写的是小写 `dsh-tui`，normalize 根本没命中，用户复听仍错。**修法：normalize 里追加大小写不敏感规则（`[tT][uU][iI]` → "T U I"）**；且**探针测试必须用口播文件里的原文（含小写）**，不能只测大写形式——探针通过 ≠ 口播通过。
  - ❌ 不要靠整体提速（rate +20%）补偿字母停顿——会让中文语调变机械。英文慢的根因是加空格，不是语速。
- **rate 用 `+8%`**（自然区间，验证过）。男声 `zh-CN-YunxiNeural`（科普/技术默认），女声 `zh-CN-XiaoxiaoNeural`（培训）。
- ❌ 不要用中文谐音替换（如 "AI"→"诶爱"）：实测反而切成两个独立词

### 断句（`narrate.split_units`，避免误切）
- 先按中文标点（`，。、：；`）拆意群——这步永远对
- 超长才字数硬切，阈值 **24**（接近字幕单行容量）。❌ 不要用 18，会把 "DeepSeek发布V4 Flash正式版"(20字) 切成两半
- 英文词块**整体切**（`computed style` 不可断成 `computed`+`style`）
- **尾部短词(<6字)回并上一句**——避免 "正式版" 这类尾巴单独成句、断句不自然
- ⚠️ **超 24 字分句会硬切中文词**（claude-plugins 踩坑）：某分句 >24 字时按字符硬切，切点不看词边界，实测 "12 个按 GitHub Star 排行的必装开源插件"(28字)→"必装开|源插件"、"…结构化的无障碍快照…"(29字)→"结构|化"。**修法：写口播句子时保证每个标点分句 ≤24 字**，从源头避免触发硬切。计数注意：英文词块含空格算（"Playwright MCP"=14 字）。

### 音频同步（架构约束，违反即错）
- **narrate 管线**：逐意群单元合成 mp3 → **ffmpeg `concat` filter**（样本级精确）拼接。时间戳基于 probe 累加，与音频严格同源。
  - ❌ 不用 concat **demuxer `-c copy`**：mp3 帧间 encoder padding 会累计，时间戳和音频漂移几十~几百 ms（音画不同步的根因）
  - ❌ 不用"逐句合成拿时间戳 + 整段重合成 mp3"：两次合成，时间戳和音频来自不同合成，漂移
  - ✅ 验收标准：最后单元 end_frame/60 与音频 total_seconds 偏差 < 0.01s
- **courseware/graph 管线**：视频段用 **xfade** 转场（段间重叠 `transition_dur=0.8s`），音频**必须**用 **acrossfade** 与视频一一对应，总时长 = `sum(dur) - (n-1)*0.8`
  - ❌ 简单 concat 音频 + `-shortest` mux：字幕比声音早 0.8s，逐段累计（已踩坑）

### 字幕
- **意群单元级**（不是句级）：`split_units` 拆成的短意群，每次显示一个完整短句，按单元时间戳跟随口播
- **单行**：去中文标点，不截断、不加省略号；超屏的句子应在 `split_units` 阶段拆短，不在渲染时截断
- ❌ 不要整段铺开、不要句级长字幕（超屏）

> 文章→视频的内容完整性规则（关键实体全覆盖）见上「内容创作规范 → 内容覆盖」。

### 工程
- **全本地零收费**：仅 edge-tts + Playwright + FFmpeg
- **Windows 编码**：文件 I/O 显式 `encoding="utf-8"`，子进程 `PYTHONIOENCODING=utf-8`
- **edge-tts 间歇 NoAudioReceived**：`synth_with_boundaries` 必须带指数退避重试（服务端间歇抽风，非代码问题）。整批失败（make video Error 1）多为同一时段服务抽风——**直接重跑 make，一般 2-3 次内过**，先别怀疑内容
- **Makefile video target 用 `$(PYTHON_PW)` 不是 `$(PYTHON)`**（2026-08-17 修）：`.venv` 无 playwright/edge-tts，Windows 用本机 Python311（`PYTHON_PW`），否则 `ModuleNotFoundError`
- **变量命名**：避开 JS/Python 内置（不用 URL/name/status/data）
- **去 AI 味**：口播文案写作去套话水词（参见 **de-ai-smell skill**，唯一权威）；**禁词（2026-08-03 定规）：兜底、铁证、说白了、先说、根子、扎眼**——口播一律不出现，写完整稿后跑 `make check-ai-smell path=...` 扫一遍

## 工作流

```
deck.json / deck-graph.json（内容）+ narrations/<slug>.json（口播 cards[]）
        ↓ make video slug=<slug> [mode=courseware|graph] [theme=dark|light]
[TTS+WordBoundary] → [timeline 分句+字幕去标点]
        → [Playwright 逐帧渲染] → [xfade 视频拼接 + acrossfade 音频合并]
        ↓
video-generation/build/<slug>/<slug>_<theme>.mp4（1920×1080）
```

## 新文章复用

### courseware
1. `video-generation/deck/<slug>/deck.json`（含 points + sub_points + footer）
2. 口播 `video-generation/narrations/<slug>.json`，格式 `{voice, rate, outline:[论点], cards:[文案]}`
3. `make video slug=<slug>`

### screencast（屏录感教程：对齐抖音「录屏+标注」爆款）
1. `video-generation/deck/<slug>/deck.json`，每卡 `type:"tool"`：
   ```json
   {"type": "tool", "tool": "hook", "title": "主标题", "subtitle": "窗口标题",
    "points": ["第1步", "第2步", "第3步"]}
   ```
2. 口播 `video-generation/narrations/<slug>.json`（**cards 数量必须 = deck cards 数量**，逐段对应；`points` 长度驱动每段内的步骤揭示）
3. `make video slug=<slug>`（courseware 模式默认）
4. 逐卡预览：`cd .agents/skills/video-generation/scripts && PYTHONIOENCODING=utf-8 python -m video.screencast` → `video-generation/probe/screencast_preview/cardNN_stepM.png`

**拟物化步骤（教程类，2026-08-03 定规）**：
1. **能浏览器截图的步骤 → 全部浏览器截图（主原则）**：`cd scripts && PYTHONIOENCODING=utf-8 python -m video.capture_shots --slug <slug>` → `video-generation/assets/<slug>/<key>.png` + `manifest.json`（Playwright 抓官网实拍 1600×900，热点框坐标记百分比）。`Shot._locate` 支持 `{sel}`（精确选择器）或 `{text, after_heading}`（README 段内文本定位）。**任何能在浏览器呈现的 UI 都截**——官网 / 市场 / GitHub / 控制台 / 在线编辑器（如 vscode.dev），不限于下载页
2. **deck 加 realshot 卡**：`{"type":"tool","tool":"realshot","slug":<slug>,"shot":"<key>","points":[...],"hotspots":[null,{x,y,w,h,label},...]}`——`hotspots` 数组按 `points` 索引对齐，`null` 表示该步无箭头
3. **CSS 仿真窗口只兜底**：浏览器截不到的本地桌面应用 / 登录态界面，才用 `tool:"vscode"`（拟物化 VSCode）等 mockup，卡字段 `req`/`resp`/`points` 驱动
4. **封面**：`cd scripts && PYTHONIOENCODING=utf-8 python -m video.cover_vscode --slug <slug>` → 复用视频主体视觉做封面（realshot 截图或写实窗口），再 `make video-cover-check slug=<slug>` 过验收
5. **本地桌面应用窗口截图**：浏览器截不到的本地应用（Codex / CcSwitch / 客户端等）优先**真实窗口截图**而不是 CSS 仿真——用 `scripts/screenshot_app.py` 只截应用窗口（跨平台：macOS Quartz / Windows 调 .ps1，不截全屏）：
   ```bash
   python scripts/screenshot_app.py --process "Codex" --title "Codex" --output video-generation/assets/<slug>/01.png
   ```
   截图后如无法目视验证（模型不支持看图），用 `scripts/ocr.py`（macOS Vision / Windows WinRT）核对窗口文字，确保截到了目标界面而非误截。
   **Windows 实测经验（2026-08-17 deepseek-harness-desktop-cli 沉淀）**：
   - **进程名不带 .exe**：`screenshot_app.py --process "cmd"`（`Get-Process` 的 Name 是 `cmd`，传 `cmd.exe` 匹配不到直接 "no window"）
   - **窗口被遮挡是最大坑**：矩形截取用 `CopyFromScreen` 抓屏面上该区域，若目标窗口被编辑器/ZCode 等盖住，截到的是一张**静止黑屏/别人界面**——两帧 diff 为 None 就是截错信号（`ImageChops.difference` bbox）。截前先 `ShowWindow(SW_MINIMIZE)` 移开竞争窗口 + `SetForegroundWindow` 并核对 `GetForegroundWindow()==MainWindowHandle`，截图后两帧 diff 确认画面在变
   - **UIA 自动化（Electron/NSIS 通用）**：按钮常不支持 `InvokePattern` → 用 `BoundingRectangle` 中心 + `mouse_event` 物理点击；文本输入用 `ValuePattern.SetValue`（Electron 输入框可用，比 SendKeys 中文可靠）；`SetValue` 需在 UIA 树按 Name 定位（如「描述你想要构建的内容」）
   - **PS1 脚本用 python 写文件**（`open(...,'w',encoding='utf-8-sig')`），中文要么用 `[char]0x4F60` 十六进制拼接（`-join ([char[]]@(0x4F60,...))`），要么直接 UTF-8 内容——**bash heredoc 写中文 + 引号必被吞**，踩了 3 次
   - **NSIS 安装向导**：`/S` 静默安装在部分环境会卡死不动；交互向导 + 快捷键更稳（Alt+I 开始安装、Alt+N 下一步），每页截图就是教程素材
   - **WinRT OCR 间歇 `Wait` 异常**：转换 `SoftwareBitmap.Convert(Bgra8)` 后重试；小字号终端字体 OCR 读不出是正常的，配合像素 diff / 区域放大验证
   - **教程类「真机实拍」验收（强制）**：装完必须**真配置（填 key）+ 发真实请求（如「你是谁」）等回答后再截图**，不截空壳欢迎页；回答内容（会话标题/token 统计）就是最好的"能用"证据。key 这类敏感信息本机测试可临时用，视频里只教官方申请路径
   - **自动化产物不算真实坑**：TUI 黑屏/窗口不渲染这类由脚本或环境变量引发的现象，要么如实归因（「部分终端环境黑屏，换终端试试」），要么不放——**不许把自动化事故包装成用户会遇到的坑**

`tool` 现有实现（`screencast.py` 的 `_CONTENT` 注册表）：
`hook` 痛点+材料+前置 CTA ｜ `realshot` 真实截图打底 + 箭头热点（拟物化步骤卡）｜
`vscode` 拟物化 VSCode 窗口（插件使用流程）｜ `install` GitHub Releases ｜ `terminal` 终端验证（内容用 `lines` 字段驱动）｜
`ccswitch` Provider 列表 ｜ `settings` settings.json env 段 ｜ `rank` 能力排行榜（真实分数条形）｜
`map` 国产阵营分工 ｜ `cost` 成本对比（old/new/badge）｜ `cta` 结语+订阅钩
新增工具：在 `screencast.py` 加 builder 函数 + 注册进 `_CONTENT` + 补对应 CSS（`_CSS`）。

### graph
1. `video-generation/deck/<slug>/deck-graph.json`，格式：
   ```json
   {
     "slug": "...", "series": "AI 研发实战", "title": "...",
     "graph": {
       "center": {"label": "工程体系"},
       "nodes": [{"id": "n1", "label": "命令化"}, ...],
       "edges": [{"from": "center", "to": "n1"}, ...]
     },
     "cards": ["口播第1段", "..."]   // cards 数量必须 = narrations.cards 数量
   }
   ```
   - 口播第 1 段（cover）→ active_node=-1（只显示中心），第 2 段起 → 0,1,2...
   - edges 状态由 to 节点决定：`to` 是 active→实线高亮，done→实线，future→虚线扫描
2. 口播 `video-generation/narrations/<slug>.json`（同 courseware）
3. `make video slug=<slug> mode=graph theme=light`

### remotion（默认：清单/榜单/对比/数据可视化/教程步骤）
1. 口播脚本 `.agents/skills/video-generation/scripts/narrate_<slug>.py`（参照 `narrate_ccswitch.py` / `narrate_after_million_loc.py`）：写口播句子 → 复用 `video.narrate` 生成 mp3 + `narration.ts` 到 `video-generation/remotion-videos/<slug>/`
2. `video-generation/remotion-videos/<slug>/config.ts`：按内容类型选场景（`SkillStage` 阶段递进 / `LeaderboardChart` 榜单 / `ComparisonTable3D` 对比 / `DataReveal` 成本账），`span(from,to)` 从 narration 时间戳算每场景时长
3. Root.tsx 注册：`import { xxxConfig } from "@videos/<slug>/config"` + 加入 `allConfigs`
4. `make video-remotion slug=<slug>`（内部 `cd remotion && VIDEO_ID=<slug> pnpm render`）→ 产物 `video-generation/build/<slug>/<slug>.mp4`，封面自动生成到**同目录** `video-generation/build/<slug>/<slug>_cover.png`

> 新增场景组件放 `remotion/src/scenes/content/` + 在 `content/index.ts` 注册（参照 `SkillStage.tsx`：flex 布局 + 字幕安全带 paddingBottom 60px + 卡片按场景帧逐张浮现）。

## 脚本位置（.agents/skills/video-generation/scripts/video/）

脚本已封装进本 skill 目录。`make video` 内部 `cd` 到 `scripts/` 跑 `python -m video.build`。

| 文件 | 职责 |
|------|------|
| `build.py` | 主入口，courseware/graph/legacy 分发，graph 的 acrossfade 音频合并 |
| `courseware.py` | 课件 HTML 模板（`render_frame`；顶部对 `card["type"]=="tool"` 分发到 screencast）|
| `screencast.py` | 屏录感工具界面渲染（`_CONTENT` 各 tool builder + `render_frame`，自带 `python -m video.screencast` 自测出预览）|
| `capture_shots.py` | 抓真实网页截图 + 热点百分比坐标（`realshot` 素材源，产物 `assets/<slug>/`）|
| `cover_vscode.py` | 拟物化 VSCode 封面（复用 `_vscode` 窗口做主体，教程类封面）|
| `graph.py` | 节点图 HTML 模板（`render_frame`，dark/light 主题 + 动效）|
| `timeline.py` | WordBoundary → 分句 + 要点时间轴 + 字幕去标点 |
| `frames.py` | Playwright 逐帧渲染 + 段合成 |
| `tts.py` | edge-tts 合成 + 重试退避 + `normalize_for_tts`（缩写逐字母白名单，见「发音」）|
| `narrate.py` | **通用口播生成**：`split_units` 智能断句 + `generate_narration`（concat filter 拼接，无漂移）+ 单元级时间戳 JSON。任何渲染后端（Remotion/Playwright/FFmpeg）可复用 |
| `render.py` | FFmpeg xfade 视频拼接 / 混 BGM |
| `config.py` | 尺寸/编码配置 + `OUTPUT_ROOT`（项目根 `video-generation`） |

### narrate.py 用法（通用口播，跨管线复用）

```python
from video.narrate import generate_narration_from_sentences

mp3, json_path = generate_narration_from_sentences(
    sentences=["第一句完整话。", "第二句。"],
    out_dir=Path("out"),
    voice="zh-CN-YunjianNeural",  # 解说/深度口播默认男声（见下方「音色选择」）
    rate="+8%",                   # 自然语速
    fps=60,
    audio_name="narration.mp3",
)
# → out/narration.mp3（整段口播）+ out/narration.json（segments 单元级时间戳）
```
命令行：`python -m video.narrate --text-file units.txt --out-dir out/`（每行一句完整话，自动 `split_units`）

### 音色选择（2026-08-18 实测标定）

对标过抖音口播标杆（低沉男声解说型，F0 中位 ≈148Hz、频谱质心 ≈1kHz，偏暗），用同一句文案对 edge-tts 4 个中文男声测基频/质心对比，结论：

| 场景 | 音色 | 说明 |
|------|------|------|
| **解说/深度/悬疑叙事（默认）** | `zh-CN-YunjianNeural` | 低沉磁性男声（F0med 132Hz、质心 1205Hz，4 者中最接近对标），rate `0%`~`+8%` |
| 轻快教程/产品演示 | `zh-CN-YunxiNeural` | 阳光青年男声（F0med 186Hz），节奏快时配 `+10%`~`+15%` |
| 新闻播报式/权威口径 | `zh-CN-YunyangNeural` | 播音腔男声，音色偏亮（质心 1543Hz），科普引用数据时可切 |
| 培训/温和女声 | `zh-CN-XiaoxiaoNeural` | 女声兜底 |

- 判据可复现：`ffmpeg` 抽 wav → 30ms 帧自相关估 F0 + rFFT 质心，对比样本落点（脚本思路见 `/tmp` 一次性分析，不必沉淀）。
- 抖音头部「AI 解说」类多为剪映系音色（如解说小帅），edge-tts 无同款；**YunjianNeural 是可白嫖的最接近替代**。若对标的明显是真人配音，不做音色克隆，按上表选最近替代。

## Remotion 数据可视化视频（第三种模式）

除 courseware/graph（Playwright 管线）外，还有 **Remotion 管线**（`remotion/` 目录，React + Three.js），适合「数据可视化 + 真实素材」的发布/科普视频（如模型榜单、性能对比），**是默认视频风格**。**口播/字幕/断句规则与本 skill 通用，复用 `narrate.py`。** 渲染产物落在 `video-generation/build/<id>/<id>.mp4`（成片统一目录，`out/` 已弃用），封面自动生成到**同目录** `video-generation/build/<id>/<id>_cover.png`；口播 mp3 落在 `video-generation/narration/`（即 Remotion public 目录，`remotion.config.ts` 已指好）。内容视频实例（config.ts + narration.ts）放在 `video-generation/remotion-videos/<id>/`，通过 webpack alias `@videos/` 引用。

### 关键经验（这条管线踩坑沉淀）
- **口播去 AI 味（强制，2026-08-03 踩坑）**：口播稿不是文章，是「讲给人听的」。诊断信号：① 同一个口号（「全量国产/切一次不回官方」）在多个场景重复 3 遍——**口号全文只说一次**（放结论场景）；② 教学腔开头「先理解一件事/算笔账/新手最容易」——删掉直接说；③ 升华句「把 X 从 A 变成 B」——删；④ 排比对仗工整。正确做法：动词驱动（「装」「粘」「切」）、具体数字（$5/$0.028/178 倍）、长短句混用、金句收尾。参照 `narrate_after_million_loc.py` 口播（全 agent、零口号重复）。**改口播 = 重跑 narrate → narration.ts 单元索引全变 → config.ts 的 span/cardsFor 必须跟着重写。**
- **场景密度对齐借鉴视频**：借鉴视频（after-million-loc）8 个内容场景、每场景 4-5 卡、总 28 卡，节奏快。教程/步骤型文章不要把所有步骤挤进一个场景——**每步一个场景**（如 ccswitch 拆「装/加供应商/切换验证」3 个场景），每场景卡片随口播逐张浮现。画面「死板」的根因是场景少 + 卡少 + 停留长。
- **内容 > 抽象 3D**：技术科普要真实素材（截图/代码/真实数据图表）+ 标注，不是抽象粒子/玻璃。调研结论：B站/抖音主流是「录屏 + 标注」，纯 3D 抽象动画只适合片头。
- **数据可视化用真实图表**：排行榜用横向条形图（`LeaderboardChart`），高亮主角（品牌色 + 发光 + 标注）；跃升用前后双柱（`GrowthChart`）。数据从文章/榜单抓取，**不编造**。
- **真实性红线**：数据必须来自真实来源（文章/官方榜单）。矛盾信息（如"是否多模态"）以用户确认为准，未经证实的不写进视频。
- **背景全局层**：科技背景（电路板网格 `TechBackground`）做全局底层，场景根背景透明露出；不要每个场景各画。
- **字幕安全带**：底部固定预留（~170px），场景内容避让；`Cover` 用 flex 流 + opacity 占位（不要用 `position:absolute` 的 `TimedLayer`，多个会互相覆盖导致重叠）。
- **DataReveal 小数**：数字递增动画要保留 number 的小数位（`toFixed(decimals)`），否则 `8.9` 被 `Math.round` 成 `9`。

### 三层架构（配置驱动，加视频 = 加 config）
```
remotion/src/             ← skill 内：框架 + 场景 + 示例
  core/                   框架（VideoConfig/VideoComposition/SubtitleOverlay/theme）—— 跨视频稳定
  primitives/             视觉原语（TechBackground/CodeBlock/MockScreen/标注/图表基础）
  scenes/                 通用场景（Cover/LeaderboardChart/GrowthChart/DataReveal/Outro...）
  videos/<id>/            示例/测试视频（dummy-test/showcase 等）
video-generation/
  remotion-videos/<id>/   内容视频实例（config.ts + narration.ts）—— 项目专属
```
加新内容视频：`video-generation/remotion-videos/<new>/config.ts`（import 类型用 `@skill-src/core/types`，选场景 + 传 props）+ 在 Root.tsx 用 `import { xxxConfig } from "@videos/<new>/config"` 注册。场景时长用 `span(unitA, unitB)` 从 narration 时间戳动态算，不手拍帧。

**运行**：`make video-remotion slug=<id>`（自动执行渲染 + 封面）。手工：`cd remotion && pnpm install && python ../scripts/narrate_<video>.py && VIDEO_ID=<id> pnpm render`。narration.ts 由 narrate 脚本生成到 `video-generation/remotion-videos/<id>/`，mp3 自动进 `video-generation/narration/`。

> **项目根注入**：技能库外置为独立仓 + `.agents/skills` 是 junction/symlink 时，向上探测会落到 skills 仓自身。项目根一律优先读 `VIDEO_PROJECT_ROOT` 环境变量（blog-src 的 Makefile 已传 `$(CURDIR)`），TS（render/sync/remotion.config）与 Python（config.py）同规则；未传时才走向上探测 + 同级 blog-src 兜底。手动跑渲染前先 `export VIDEO_PROJECT_ROOT=<项目根>`。
>
> **依赖版本**：remotion 固定 **4.0.502**（Node 24 下浏览器可正常 spawn；4.0.8 会报 `spawn UNKNOWN`），勿升。

## 产出完整性（2026-08-17 定规，强制）

**每个视频的一次完整产出 = 成片 mp4 + 横屏封面 `_cover.png` + 竖屏封面 `_cover_v.png` + `metadata.txt`，四者缺一即产出不完整。**

- `make video-remotion` / `make video` 渲染完成后，必须立即跟：`make video-cover slug=<slug>`（横竖双封面）+ 在 `video-generation/build/<slug>/` 写入 `metadata.txt`（标题/系列/期数/封面标题或关键词/标签/简介/话题，简介含结尾互动问题与原文链接）。
- 渲染管线如中途失败/被取消，恢复后要确认没有残留僵尸渲染进程（node/ffmpeg）锁住输出文件——曾因此 Permission denied 连环失败。清场：`taskkill /F /IM node.exe` 后单实例重渲。
- 封面过 `make video-cover-check`，metadata 过 platform-compliance（标题/简介/话题），两项都绿才算产出闭环。

## 音画同步与渲染事故清单（2026-08-17 复盘沉淀，强制）

### 音画同步（最严重，已修）
- **span 公式**（场景时长）：❌ 旧 `U[to].end - U[from].start` 会把**下一句的第一个单元**算进本场景（to 传的是下一句首单元），逐场景错位、累计漂移（实测 159.7s 口播撑成 186.6s，画面落后口播最多 27s）。✅ 正确：`const span = (from, to) => (U[to + 1] ? U[to].start_frame : U[U.length - 1].end_frame) - U[from].start_frame;`
- **验收标准**：场景时长总和 === narration 最后单元 end_frame === 音频总长，三者一致才允许渲染。抽帧验证：取某句首单元 start_frame/60 秒处截图，画面主题、标注、字幕三方应一致。
- 口播句子相邻不要用相同开头的词（易混淆排查），场景与句子必须一一对应（gen4 生成器场景数 = 句子数）。

### 渲染工程
- **改 config 后必须重跑 `sync-content-videos.ts`**：composition 时长固化在 `remotion/src/videos/content-videos.ts` 注册表，不 sync 渲染用的还是旧时长（本次 11198 帧反复出现即此因）。
- **异常渲染先查僵尸进程**：取消的任务会残留 node/ffmpeg 锁住输出文件 → Permission denied。`taskkill /F /IM node.exe` 清场后单实例重渲。
- **缓存**：改配置/组件后仍渲染旧结果，删 `remotion/node_modules/.cache` 再试。
- edge-tts `NoAudioReceived` 是服务端间歇抽风，重跑生成器即可。

### 内容规范（开源项目类视频，强制）
- **必须实拍仓库主页**（RepoShot 场景 + `capture_shots.py`/Playwright 截图）：讲到哪个仓库画面就是哪个仓库，一句一景，禁止一个场景塞多个仓库。
- **星数必须 GitHub API 验证**（`api.github.com/repos/<owner>/<repo>` stargazers_count），口播、画面、排行榜三处用同一份已验证数字；仓库 URL 从文章提取，不要猜（猜错 = 404 截图，绝对禁止）。
- 每个仓库镜头必须带「这个仓库是什么」核心点信息条（RepoShot 的 core 字段），让观众 3 秒看懂。
- 排行榜停留时长按用户指定（默认自然句长，不要自行硬限 3 秒）。
- 结尾无静默尾巴（去掉 TAIL 余量），评论引导必须有声音有字幕，说完即收。
- 开头禁用「双持」类冷门行话（已入 de-ai-smell 禁词表，用「深度使用」）。

## 性能

graph 模式约 1-2 分钟渲染（5 段 ~1800 帧），courseware 约 10-12 分钟，screencast（courseware 子模式）9 段约 10-15 分钟。Remotion 管线 50-100s 视频约 1-3 分钟。若频繁迭代，可降帧率到 30fps 或用 `--scale=0.5` 草稿模式。

## 封面(cover)

视频发布时**不截视频帧**,而是专门生成一张标准封面(1920×1080),参考抖音知识区爆款风格(大字标题 + 高对比)。由 `scripts/yixiaoer/cover_template.html` + Playwright 截图程序化产出,全自动、可复用。

**统一标准(video-cover-standard):以 `after-million-loc-my-skills`(23-skill)封面为基准模板。** 任何视频走生成管线都必须产出同一视觉语言——大字双行主标题 + 青色关键词高亮 + 副标题 + 3 标签,不依赖人工逐张调参。封面质量可用像素签名验收(见下「像素验证」),不再凭肉眼。

> **教程/screencast 类封面变体（2026-08-03 定规）**：教程类封面跟随视频的**浏览器截图/拟物化**视觉——右侧主体用视频里的真实截图（`realshot` 素材）或写实窗口（`vscode` mockup，当前 `cover_vscode.py` 即复用 `_vscode` @ active_idx=2 工作态），左侧大字双行标题 + 实心青色关键词框（`.hlbox`）+ 副标题 + 3 标签，封面与视频画面同源。同样过 `make video-cover-check`（通过实心青色块满足青色≥0.8%，不用渐变文字——渐变只有亮端命中检测器）。标题文案/时长硬编码在 `build_cover_html`，换视频记得改。

### v2 设计规格

```
┌───────────────────────────────────────────────────────────────┐
│ [EP.06] AI 研发实战                       ● <你的品牌名>       │ ← 期数+系列 / 品牌
│                                                               │
│  { }                                              </>          │ ← 代码括号装饰(半透明)
│             ━━━ ● ━━━                                          │ ← 装饰线+圆点
│                                                               │
│            六个 Skill 怎么用                                    │ ← 主标题(关键词分色)
│        从想清楚到归档的一次完整链路                              │ ← 副标题
│                                                               │
│  // spec-driven                                    ⎇          │ ← 代码注释装饰
│                                                               │
│      [📋 规格驱动]  [🤖 AI Agent]  [⚡ 效率翻倍]              │ ← 底部标签 pill
│  — AI 研发实战 系列 —                  ▶ 看完整流程           │ ← 底栏
└───────────────────────────────────────────────────────────────┘
 1920×1080 | 背景 #0a0e1a + 网格纹理 | 主色 #22d3ee
```

| 要素 | 规格 |
|------|------|
| 背景 | `#0a0e1a` 深色 + 60px 网格纹理 + 三层光晕(右上青 / 左下紫 / 中央椭圆) |
| 主标题 | **大字双行**,96px 起步(最长行 ≤13 CJK 当量,中文/全角=1、ASCII=0.6),按行宽分档 96→72→56px,**禁止单行缩字**;关键词青色渐变高亮(`.hl`)固定在第二行(punchline 位置),其余白色 |
| 强调色 | **主强调仅青色 `#22d3ee`**;紫 `#a78bfa` 仅第 2 个标签 + 左下光晕;橙 `#f59e0b` 仅第 3 个标签 + 极小点缀;**主标题区禁用紫/橙**(`.hl-orange` 类保留仅向后兼容,默认生成不用) |
| 副标题 | 36px 浅灰 `#94a3b8`,居中;取主标题断句剩余部分,无剩余可为空 |
| 期数标签 | 左上 `EP.0X` 青色色块(斜体)+ 系列名 |
| 品牌 | 右上角 `● <你的品牌名>`(带发光圆点) |
| 装饰 | 左侧大号半透明 `{ }`、右侧 `// code` 注释、飘浮 `</>` `#` `⎇` 符号 |
| 底部标签 | 恒 3 个 pill,配色顺序固定:第 1 个青 / 第 2 个紫 / 第 3 个橙;从文章 tags 前 3 个取 + emoji 前缀,超 7 CJK 当量截断,不足补「📌 干货分享」 |
| 底栏 | 左:系列名 / 右:▶ 发光播放按钮 +「看完整流程」 |
| 安全区 | 所有文字在 `left:240 right:240`(1440px 宽,对应抖音 4:3 安全区) |

> ⚠️ **主标题必须是白色**(`color: var(--text)`,已修复)。深色背景上继承默认黑色 = 看不清,这条是踩坑换来的,改动模板时不要去掉。

### 参数化(8 个占位符)

模板用 Python 字符串替换(见 `scripts/yixiaoer/cover.py` 的 `build_cover_html`):

| 占位符 | 示例 | 来源 |
|--------|------|------|
| `{{EPISODE}}` | `EP.06` | 文章 `weight` 推导 |
| `{{SERIES}}` | `AI 研发实战` | metadata.txt 的 `系列` |
| `{{BRAND}}` | `<你的品牌名>` | 从 BRAND_NAME 环境变量读 |
| `{{MAIN_TITLE}}` | `Claude Code<br><span class="hl">换国产模型</span>` | cover_title > cover_keyword > 自动断句(`resolve_cover_title`) |
| `{{TITLE_CLASS}}` | `""`(96px)/ `long`(72px)/ `longer`(56px) | 按主标题最长行近似宽度分级(≤13 / ≤19 / 超出) |
| `{{SUB_TITLE}}` | `从想清楚到归档的一次完整链路` | 主标题断句剩余部分,可为空 |
| `{{TAG1}}`/`{{TAG2}}`/`{{TAG3}}` | `📋 规格驱动` | 文章 tags 前 3 个 + emoji 匹配(`cover.py` 的 `TAG_EMOJI_MAP`),配色顺序固定青/紫/橙 |
| `{{DECO_CODE}}` | `// spec-driven<br>// AI agent workflow` | 右侧装饰注释,可按主题换 |

### 主标题来源(三档优先级,`resolve_cover_title`)

1. **`cover_title`(人工 HTML,最高优先)**——可含 `<br>` 与 `<span class="hl">` 精控,原样插入;副标题自动取原标题剩余部分。23-skill 封面走此档
2. **`cover_keyword`(推荐入口)**——只需给关键词短语(可跨标点,如「换国产模型，月省99%」),自动包 `<span class="hl">` 青色高亮并固定在第二行(punchline 位置),关键词前内容作第一行,关键词后内容作副标题
3. **自动 fallback(无任何输入)**——标点(冒号/破折号/逗号/问号)处断句 → 主标题 + 副标题;主标题按宽度均衡断双行(中文=1、ASCII=0.6);无关键词时不强加高亮,结构仍与基准一致

> 强调色已固定(主强调青、紫/橙仅标签),**不要再往主标题塞橙色高亮**。模板里 `.hl-orange` 类保留仅向后兼容。

### 生成方式

```bash
# 发布时自动触发,无需手动
make publish-video slug=xxx
```

技术链路:`cover_video.py::load_meta()` 读 metadata.txt（新,含封面字段）+ 文章 front matter → `cover.py::generate_cover()` 读模板 → 替换 8 占位符 → Playwright 渲染 → 截图 1920×1080 → `video-generation/build/<slug>/<slug>_cover.png`（与视频同目录,渲染后自动产出）→ 发布时复用 → `yxer upload` 得 key → 按平台字段注入 payload。手动补生成单张: `make video-cover slug=<slug>`；发布管线优先取同目录 `build/<slug>/<slug>_cover.png`，缺失回退旧 `covers/` 目录（存量），都没有才现场生成到同目录。

**横竖两版（2026-08-05 定规）**：`make video-cover` 同时产出两张封面——
- `_cover.png`（1920×1080 横屏 16:9）→ 抖音 horizontalCover / 视频号 / 快手，内容在中央 4:3（左右 240px 安全区）
- `_cover_v.png`（1080×1920 竖屏 9:16，`cover_template_v.html`）→ 抖音创作平台后台手动补「竖封面」/ 主页 3:4 展示；内容全收进中央 3:4（y 240–1680），上下 240px 只放装饰，抖音按 3:4 裁切不丢内容
- 抖音开放平台 API 只认 `horizontalCover`（无 verticalCover 字段），竖封面需在后台手动传 `_cover_v.png`

> 想控制某张封面的关键词高亮,在该视频的 `metadata.txt` 填 `封面关键词: 短语`(推荐)或 `封面标题: <br><span class=hl>…</span>`(精控)。新视频默认补封面关键词。

### 像素验证(`make video-cover-check`)

封面是视觉产物,肉眼不可回归,用像素签名验收(锚点从 23-skill 封面实测标定):

```bash
make video-cover-check slug=<slug>
```

| 指标 | 阈值 | 说明 |
|------|------|------|
| 尺寸 | 1920×1080 | 不符直接报错 |
| 青色强调像素 | ≥ 0.8% | 高亮面积 = 视觉强度(基准 1.01%,弱封面仅 0.33%) |
| 字形覆盖(白+青+青渐变) | ≥ 2.0% | 大字标题存在感(基准 3.41%,弱封面 0.79%) |
| 中央区文字带 | ≥ 2 | 主标题双行(弱封面单行 = 1) |

任何新封面生成后跑一遍,FAIL 说明标题单行 / 未高亮 / 无强调色,回 `resolve_cover_title` 排查。

## 标题 / 简介 / 话题标签规范（2026-08-17 定规，写入 metadata.txt）

写 metadata.txt 时对照执行。标题抓点击、简介做价值预告、标签引精准流量，三者各司其职。

### 标题：从「记录」到「吸引」

- **痛点前置，禁流水账**：❌「我肝了一天，DeepSeek Harness 的源码解析」✅「看完你就明白它为什么比 Codex 更灵活」。标题回答「看完我能得到什么」，不是记录自己做了什么。
- **认知反差，禁说明书式平铺**：❌「Harness 工程：AI 编程从命令体系到自治体系的演进」✅「AI 编程还在玩 Prompt 工程？Harness 工程才是下一个方向」。「还在 X？Y 才是 Z」句式制造认知缺口，但结论必须有内容兑现。
- **「你」代入，禁「我」陈述**（踩坑/教程类）：❌「我肝了一天读完主线」✅「你安装 Harness 总失败？因为忽略了这 3 个源码级细节」。第二人称让读者对号入座。
- 平台字数裁剪（抖音≤30 / 小红书≤20 / 快手≤50 / 视频号≤80）由发布管线自动处理，但**钩子必须落在裁剪后的前半段**——写标题时把冲突点放前 10 字。
- 与封面规则联动：标题文案优先用痛点问句或结果承诺（见「内容创作规范 → 开头」末条）。

### 简介：从「目录」到「价值预告」

- **前置核心收获，禁罗列细节**：❌「45 万行 TypeScript、60+ 个包…」✅「帮你搞懂这 3 个核心：Agent 生命周期、工具执行管线、会话落盘机制」。第一句就是观众决定看不看的依据。
- **给行动指令，禁信息堆砌**：✅「跟着视频走，八步搞定安装。提前避开 Node 版本、插件兼容这 3 个坑」——「跟着做能得到什么 + 避开什么」双承诺。
- **结尾引导互动，禁戛然而止**：简介末段带提问 + 回应承诺（「你在安装时遇到过什么坑？评论区聊聊，我来帮你看看」），与「内容创作规范 → 价值与互动」的口播结尾呼应，双露出。
- **可带走价值**：有对应博客文章的，简介末尾附原文链接（收藏钩子，已有规则在此重申）。

### 话题标签：从「堆砌」到「精准组合」

- **核心词 + 场景词组合，禁大词堆砌**：❌`#ai编程 #程序员 #科技` ✅`#deepseek #harness #源码解析 #工具教程`。大词流量泛且竞争激烈，组合词才进得了精准流量池。
- **具体，禁宽泛**：❌`#编程` `#AI` ✅`#TypeScript编程` `#AI工具教程`。标签越具体，进来的观众越精准（完播/互动数据越好，算法加权越高）。
- **可用疑问式/避坑式标签吸精准用户**：`#AI编程避坑` `#Agent开发指南`——带场景意图的标签自带筛选。
- **精选 3-5 个，禁堆砌 8+**：标签不是越多越好，不相关标签稀释推荐精度。取「内容核心实体词 2-3 + 场景/教程词 1-2」。

## 发布元信息 metadata.txt（2026-08-05 起取代 metadata.json）

每个视频目录 `video-generation/build/<slug>/metadata.txt` 存发布口径元信息，UTF-8，格式：

```text
# 视频发布元信息（metadata.txt）
标题: ...                  # 必填
系列: ...                  # 可选，默认「AI 研发实战」
期数: 0                    # 可选，封面 EP 期数（weight）
封面标题: ...              # 可选，可含 <br> / <span class="hl"> HTML
封面关键词: ...            # 可选，自动包 <span class="hl"> 高亮
标签: a, b, c              # 可选，逗号分隔
简介: 第一行...            # 必填，缩进续行支持多段
    第二行续行...
话题: #tag1 #tag2          # 必填，空格分隔的热门话题；缩进续行
    #tag3
```

规则：`#` 顶格开头是注释；缩进（空格/制表符）开头的行是上一字段续行（简介/话题用 `\n` 连接）；`标题` / `简介` / `话题` 必填。读取统一走 `scripts/yixiaoer/meta.py::load_meta()`（txt → 旧 metadata.json → 文章 front matter 兜底）。发布描述 = 简介 + `\n\n` + 话题。

## 发布到多平台(yxer CLI)

视频渲染完成后,一条命令分发到抖音 / 快手 / 小红书 / 视频号:

```bash
# 默认 4 平台 dry-run(预览,不正式发)
make publish-video slug=xxx

# 正式发布(全平台)
make publish-video slug=xxx confirm=yes

# 只发指定平台
make publish-video slug=xxx platforms=douyin confirm=yes
```

### 抖音先行 + 后台状态门禁（2026-08-20 定规，强制）

> 背景：ccswitch 抖音审核「不符合相关法规」后，其余平台若已同时发布会造成多平台无效副本。且自动化发布的「发布成功」日志 ≠ 后台状态正确（定时发布可能变「审核未通过/仅自己可见」）。

- **流程（发布顺序强制）**：
  1. `make pub-video slug=xxx platforms=douyin confirm=yes schedule="…"` —— 只发抖音
  2. `python scripts/pub/douyin_check_status.py "<标题关键词>"` —— 后台状态检查，**必须确认「定时发布」**（无「不适宜公开/仅自己可见/未通过」标记）
  3. 状态确认后，再发其余平台：`make pub-video slug=xxx platforms=kuaishou,xiaohongshu,shipinhao,weixin confirm=yes schedule="…"`
- **门禁**：状态检查返回非 0（未找到/状态异常）→ 禁止发布其余平台，先人工处理抖音后台。
- 配套工具：`scripts/pub/douyin_delete_verified.py`（带弹窗全文安全阀+删除后验证的删除）、`scripts/pub/douyin_scan_works.py`（只读扫描）。

**发布管线**(`scripts/yixiaoer/publish_video.py`)自动处理:

- **封面生成**:自动生成标准封面(不截帧),设计规格 / 参数化 / 主标题优先级见上文「封面」章节
- **AI 生成声明**(declaration):抖音=3 / 快手=1 / 小红书=2;视频号不支持(需手动补)
- **原创标记**(createType):小红书=1 / 视频号=2
- **标题裁剪**:按平台字数限制(抖音≤30 / 小红书≤20 / 快手≤50 / 视频号≤80)
- **封面字段**:抖音/视频号用 `horizontalCover`;快手/小红书用 `cover`
- **账号动态解析**:每次发布时 `yxer accounts list` 查询,不硬编码 account_id
- **结果回收**:发布结果写入 `content/link-map.json` 的 `video` 子键

依赖:`npm install -g @yixiaoermail/cli` + `yxer config init --api-key <key>` + 蚁小二客户端在线。
