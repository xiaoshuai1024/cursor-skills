---
name: video-generation
description: 把一篇技术博客文章或技术主题生成为横屏 16:9 讲解视频。三种程序化模式 courseware(课件式)/graph(知识图谱)/remotion(数据可视化)，edge-tts 配音 + Playwright 逐帧渲染 + FFmpeg 合成，全本地零收费。Use when the user wants to 把文章/主题转成讲解视频、生成知识培训视频、B站知识区风格视频。
---

# Video Generation Skill

把一篇技术博客文章 / 一个技术主题生成为**横屏 16:9 视频**。三种程序化模式：

> **打包范围**：本 skill 目录只打包 Playwright 管线的引擎脚本（`scripts/video/*.py`，覆盖 courseware/graph + 通用口播 `narrate.py`）。下文出现的 `demo/`（Remotion 数据可视化管线）、`.douyin-build/`、`narrations/<slug>.json` 属于使用方项目里的内容/产物，不在本 skill 内，按各自项目结构准备。

- **courseware（默认）**：课件式——左栏要点逐条浮现 + 右栏知识卡片 + 底部字幕带（Playwright 管线）
- **graph**：节点图/知识图谱——中心辐射布局，节点逐个高亮 + 连线生长，适合概念关系/体系架构（Playwright 管线）
- **remotion**：数据可视化 + 真实素材——排行榜/对比/代码/截图标注，适合发布速报、性能对比（Remotion 管线，`demo/` 目录）

三种模式共用 TTS/断句/字幕规则（`narrate.py`）。数据 → edge-tts 配音 + 程序化画面渲染 + FFmpeg 合成。零收费、全本地。

## 何时用

- 把博客文章转成横屏知识/培训讲解视频（B站知识区、YouTube、在线课程风格）
- 线性步骤讲解 → **courseware**；概念关系/知识体系/架构拓扑 → **graph**
- 需要「讲到哪、信息跟到哪」的跟随感（非静态卡片轮播）

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

### 发音（重要决策，多次试听迭代确认）
- edge-tts 中文语音**不支持 SSML 音素控制**（标签会被当文本读出）
- **缩写逐字母 vs 单词音的权衡**（核心经验）：
  - 逐字母（DOM→`D O M`）读得准，但每个字母停顿 ~197ms，**慢且不自然**
  - 单词音（API→/æpi/、GLM→/gælm/）**自然流畅**，虽不完全符合中文技术圈逐字母习惯，但可识别
  - ✅ **结论**：`normalize_for_tts` 白名单**只留会被读成"无法识别中文错音"的词**（如 DOM→"多姆"），其他缩写当单词读。当前白名单 = `{DOM}`。
  - ❌ 不要靠整体提速（rate +20%）补偿字母停顿——会让中文语调变机械。英文慢的根因是加空格，不是语速。
- **rate 用 `+8%`**（自然区间，验证过）。男声 `zh-CN-YunxiNeural`（科普/技术默认），女声 `zh-CN-XiaoxiaoNeural`（培训）。
- ❌ 不要用中文谐音替换（如 "AI"→"诶爱"）：实测反而切成两个独立词

### 断句（`narrate.split_units`，避免误切）
- 先按中文标点（`，。、：；`）拆意群——这步永远对
- 超长才字数硬切，阈值 **24**（接近字幕单行容量）。❌ 不要用 18，会把 "DeepSeek发布V4 Flash正式版"(20字) 切成两半
- 英文词块**整体切**（`computed style` 不可断成 `computed`+`style`）
- **尾部短词(<6字)回并上一句**——避免 "正式版" 这类尾巴单独成句、断句不自然

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

### 工程
- **全本地零收费**：仅 edge-tts + Playwright + FFmpeg
- **Windows 编码**：文件 I/O 显式 `encoding="utf-8"`，子进程 `PYTHONIOENCODING=utf-8`
- **edge-tts 间歇 NoAudioReceived**：`synth_with_boundaries` 必须带指数退避重试（服务端间歇抽风，非代码问题）
- **变量命名**：避开 JS/Python 内置（不用 URL/name/status/data）
- **去 AI 味**：口播文案写作去套话水词（参见 blog-writing skill）

## 工作流

```
deck.json / deck-graph.json（内容）+ narrations/<slug>.json（口播 cards[]）
        ↓ make video slug=<slug> [mode=courseware|graph] [theme=dark|light]
[TTS+WordBoundary] → [timeline 分句+字幕去标点]
        → [Playwright 逐帧渲染] → [xfade 视频拼接 + acrossfade 音频合并]
        ↓
.video-build/<slug>/<slug>_<theme>.mp4（1920×1080）
```

## 新文章复用

### courseware（默认）
1. `.douyin-build/<slug>/deck.json`（含 points + sub_points + footer）
2. 口播 `scripts/video/narrations/<slug>.json`，格式 `{voice, rate, outline:[论点], cards:[文案]}`
3. `make video slug=<slug>`

### graph
1. `.douyin-build/<slug>/deck-graph.json`，格式：
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
2. 口播 `narrations/<slug>.json`（同 courseware）
3. `make video slug=<slug> mode=graph theme=light`

## 脚本位置（.agents/skills/video-generation/scripts/video/）

脚本已封装进本 skill 目录。`make video` 内部 `cd` 到 `scripts/` 跑 `python -m video.build`。

| 文件 | 职责 |
|------|------|
| `build.py` | 主入口，courseware/graph/legacy 分发，graph 的 acrossfade 音频合并 |
| `courseware.py` | 课件 HTML 模板（`render_frame`）|
| `graph.py` | 节点图 HTML 模板（`render_frame`，dark/light 主题 + 动效）|
| `timeline.py` | WordBoundary → 分句 + 要点时间轴 + 字幕去标点 |
| `frames.py` | Playwright 逐帧渲染 + 段合成 |
| `tts.py` | edge-tts 合成 + 重试退避 + `normalize_for_tts`（缩写逐字母白名单，见「发音」）|
| `narrate.py` | **通用口播生成**：`split_units` 智能断句 + `generate_narration`（concat filter 拼接，无漂移）+ 单元级时间戳 JSON。任何渲染后端（Remotion/Playwright/FFmpeg）可复用 |
| `render.py` | FFmpeg xfade 视频拼接 / 混 BGM |
| `config.py` | 尺寸/编码配置 |

### narrate.py 用法（通用口播，跨管线复用）

```python
from video.narrate import generate_narration_from_sentences

mp3, json_path = generate_narration_from_sentences(
    sentences=["第一句完整话。", "第二句。"],
    out_dir=Path("out"),
    voice="zh-CN-YunxiNeural",   # 男声；培训用 zh-CN-XiaoxiaoNeural
    rate="+8%",                   # 自然语速
    fps=60,
    audio_name="narration.mp3",
)
# → out/narration.mp3（整段口播）+ out/narration.json（segments 单元级时间戳）
```
命令行：`python -m video.narrate --text-file units.txt --out-dir out/`（每行一句完整话，自动 `split_units`）

## Remotion 数据可视化视频（第三种模式）

除 courseware/graph（Playwright 管线）外，还有 **Remotion 管线**（`demo/` 目录，React + Three.js），适合「数据可视化 + 真实素材」的发布/科普视频（如模型榜单、性能对比）。**口播/字幕/断句规则与本 skill 通用，复用 `narrate.py`。**

### 关键经验（这条管线踩坑沉淀）
- **内容 > 抽象 3D**：技术科普要真实素材（截图/代码/真实数据图表）+ 标注，不是抽象粒子/玻璃。调研结论：B站/抖音主流是「录屏 + 标注」，纯 3D 抽象动画只适合片头。
- **数据可视化用真实图表**：排行榜用横向条形图（`LeaderboardChart`），高亮主角（品牌色 + 发光 + 标注）；跃升用前后双柱（`GrowthChart`）。数据从文章/榜单抓取，**不编造**。
- **真实性红线**：数据必须来自真实来源（文章/官方榜单）。矛盾信息（如"是否多模态"）以用户确认为准，未经证实的不写进视频。
- **背景全局层**：科技背景（电路板网格 `TechBackground`）做全局底层，场景根背景透明露出；不要每个场景各画。
- **字幕安全带**：底部固定预留（~170px），场景内容避让；`Cover` 用 flex 流 + opacity 占位（不要用 `position:absolute` 的 `TimedLayer`，多个会互相覆盖导致重叠）。
- **DataReveal 小数**：数字递增动画要保留 number 的小数位（`toFixed(decimals)`），否则 `8.9` 被 `Math.round` 成 `9`。

### 三层架构（配置驱动，加视频 = 加 config）
```
demo/src/
  core/         框架（VideoConfig/VideoComposition/SubtitleOverlay/theme）—— 跨视频稳定
  primitives/   视觉原语（TechBackground/CodeBlock/MockScreen/标注/图表基础）
  scenes/       通用场景（Cover/LeaderboardChart/GrowthChart/DataReveal/Outro...）
  videos/<id>/  视频实例（config.ts + narration.ts + 口播生成脚本）
```
加新视频：`videos/<new>/config.ts`（选场景 + 传 props + 字幕从 narration 派生）+ 在 Root.tsx 注册。场景时长用 `span(unitA, unitB)` 从 narration 时间戳动态算，不手拍帧。

## 性能

graph 模式约 1-2 分钟渲染（5 段 ~1800 帧），courseware 约 10-12 分钟。Remotion 管线 50-100s 视频约 1-3 分钟。若频繁迭代，可降帧率到 30fps 或用 `--scale=0.5` 草稿模式。
