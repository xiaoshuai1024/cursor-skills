# video-generation

把技术博客文章 / 选题生成为横屏 16:9 知识视频的 skill —— **内容配置驱动，全本地零收费**：数据可视化 + 真实素材 Remotion 渲染、课件逐帧动画、知识图谱三种形态，配音（edge-tts + IndexTTS-2 声音克隆双链）、BGM/音效/转场/伴随形象全自动，成片直接接抖音/快手/B站/视频号四平台发布。

完整规则与踩坑沉淀在 [`SKILL.md`](./SKILL.md)（本仓库最大的单文件，agent 执行时按节读取）；本 README 是人类阅读入口。

## 能力总览

### 四种视频模式

| 模式 | 适用内容 | 渲染方式 |
|------|----------|----------|
| **remotion**（默认） | 数据可视化 / 清单对比 / 教程步骤 / 真实素材 | React + Three.js，`remotion-videos/<id>/` config 驱动 |
| **courseware** | 线性课件讲解 | Playwright 逐帧 + FFmpeg xfade 拼接 |
| **courseware → screencast** | 教程/操作/选型，对齐抖音「录屏+标注」爆款 | courseware 子模式，`type:"tool"` 卡渲染工具界面 |
| **graph** | 概念关系 / 知识体系 / 架构拓扑 | 节点图布局 + 联动高亮 |

选型一句话：默认 remotion；讲「关系」用 graph；讲「步骤」用 courseware；讲「操作」用 screencast。

### 声音管线（三层，全部零配置自动）

- **配音**：缺省 edge-tts（免费，词级时间戳）；正式发布走 **IndexTTS-2 声音克隆链**（WSL 环境，逐句合成 + best-of-N 门禁选优 + 严格标点断句手术 + 发布五步混音链）
- **BGM/音效/转场**：所有管线自动带——BGM 按口播关键词自动选情绪档（calm/walk/focus/bright/tense/epic/chiptune/lofi），SFX 走 12 语义场景 × 氛围矩阵，转场 15 种；`make video-lint` 机检双端规则漂移
- **伴随形象**：右下角终端小子 mascot（6 表情/3 姿态），表情按字幕关键词自动推断，默认左下避让平台互动栏
- **BGM 卡点（可选增强，缺省关）**：`beatgrid.py` 把 BGM 转成确定性节拍图（audiomap.json），画面按信任边界分帧跟拍（beat_cut 逐拍硬切 / phrase_flow 短语流动）。config 加 `beat` 字段才启用，详见 [`references/beat-cut.md`](./references/beat-cut.md)

### 发布（配套能力）

成片落 `build/<slug>/` 后接四平台定时发布（抖音/快手/B站/视频号）、封面自动化、发布后逐平台状态核验与数据回看——发布链路细则在 SKILL.md「全平台发布与逐平台状态确认」，状态台账见 [`video-pipeline-tracker`](../video-pipeline-tracker/)。

## 快速开始

作为 agent skill 使用（推荐）：对 agent 说「把这篇文章生成视频」/「用 courseware 模式出片」，skill 按三要素（提问式开头/钩子设计/BGM 音效转场）走完整工作流；渲染前有强制用户确认门禁。

命令行直用（在博客项目根）：

```bash
make video slug=<slug> [mode=courseware|graph] [theme=dark|light]   # 主入口
make video-preview                                                   # 本地预览
make video-lint                                                      # 字号/SFX 矩阵等静态门禁
make video-remotion                                                  # Remotion 管线渲染
make video-cover slug=<slug> && make video-cover-check               # 封面生成与在列核验
```

## 目录结构（skill 存代码，产物落项目根）

```
.agents/skills/video-generation/     ← skill：只放可复用代码
├── SKILL.md                         完整规则手册（agent 按节读）
├── references/                      motion-patterns（动效配方）/ sound-design（声音规范）/ beat-cut（BGM 卡点）
├── remotion/                        Remotion 管线（core 框架 / primitives / scenes / render.ts）
└── scripts/video/                   Playwright 管线 + 声音链（build/narrate/timeline/frames/render/tts/
                                     screencast/motion/palette/beatgrid.py 等 30+ 模块）

video-generation/                    ← 项目根：内容配置 + 渲染产物（git 忽略）
├── narrations/ deck/ narration/     口播文案 / 课件卡定义 / Remotion 口播
├── remotion-videos/<id>/            Remotion 视频实例（config.ts）
├── build/<slug>/                    成片统一目录（mp4 + 封面 + metadata）
├── archive/<slug>/                  已发布归档（只进不出）
└── sent/ probe/                     口播分句库 / 发音探针
```

## 依赖

| 依赖 | 用途 |
|------|------|
| Python 3.10+ + edge-tts + Playwright(chromium) | 缺省配音与逐帧渲染 |
| Node.js + Remotion | remotion 模式（`remotion/` 内 npm install） |
| FFmpeg / ffprobe | 音视频合成与探针 |
| （可选）WSL + IndexTTS-2 | 正式发布的声音克隆链；缺失自动回退 edge-tts |
| （可选）librosa + numpy + soundfile | beatgrid.py 节拍分析（仅卡点功能需要） |

## 内置硬规则（agent 侧强制，完整版见 SKILL.md）

- **视频三要素**：提问式开头（「问你一个问题」/「你有没有想过」）+ 钩子设计且逐一消费 + BGM/音效/转场
- **渲染前用户确认门禁**：完整口播稿 + 分镜呈用户审阅确认后才能渲染
- **严禁无封面发布**：封面失败阻断发布或编辑页补图，禁止跳过
- **色彩可读性门禁**：正文/字幕 ≥4.5:1，主青只作强调用途，`make video-lint` 机检
- **全元素动画联动**：讲解节拍 ≥3 元素、反馈 ≤3 帧、全程缓动
- **发布确认一律工具核验**：上传器日志不可信，逐平台扫后台为准

## 文档地图（SKILL.md 按需读哪节）

| 要做什么 | 读哪节 |
|----------|--------|
| 新视频选模式/搭结构 | 「内容驱动设计」「新文章复用」 |
| 口播/断句/声音克隆 | 「默认口播配置：IndexTTS-2 克隆 + 严格标点断句」 |
| 调 BGM/音效/转场/卡点 | 「声音层与转场」+ `references/sound-design.md` / `references/beat-cut.md` |
| 写动效 | `references/motion-patterns.md` + 「动画与特效强制规范」 |
| 配色/字号 | 「色彩可读性」+ `palette.py` |
| 发布与核验 | 「全平台发布与逐平台状态确认」「严禁无封面发布」 |
| 渲染事故排查 | 「音画同步与渲染事故清单」 |

## 第三方组件与许可

本 skill 主体按仓库 [MIT](../../LICENSE) 许可。例外：

- [`scripts/video/beatgrid.py`](./scripts/video/beatgrid.py) 搬运自 [OpenMontage](https://github.com/calesthio/OpenMontage)（music-to-video 的节拍分析器），按 **AGPL-3.0-only 单独许可**（文件头有 SPDX 标注）；对应方法论 [`references/beat-cut.md`](./references/beat-cut.md) 为本仓重写，随 MIT。再分发 beatgrid.py 须遵循 AGPL-3.0。

## See also

- [`SKILL.md`](./SKILL.md)：完整规则手册（agent 执行入口）
- [`video-pipeline-tracker`](../video-pipeline-tracker/)：视频生产全生命周期状态台账
- [`douyin-topic`](../douyin-topic/)：选题与对标拆解（含镜头级帧表拆解）
- [`metadata-optimizer`](../metadata-optimizer/)：标题/简介/话题生成
- [仓库根 README](../../README.md)：全 skill 全景与安装
