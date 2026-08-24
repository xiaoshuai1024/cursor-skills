# 音效与转场设计规范（参考「老张 · Agent 的 7 种架构」）

> 2026-08-20 基于对参考片（224s，抖音 6.41 老张作品）的程序化拆解得出，不是拍脑袋。
> 适用：Remotion 视频管线（`VideoConfig.sfx` + `TransitionFrame` + 场景原语）与 Playwright 管线共用同一套听觉/剪辑语言。

## 一、参考片拆解证据（先看事实，再看设计）

### 音频侧（m4a 224s，谱分析）
| 指标 | 数值 | 结论 |
|------|------|------|
| 5s 段能量 | 全部 -44.8 ~ -46.7 dB，几乎不落 | 全程连续 BGM，无停顿 |
| 谱质心 | 1400–2900Hz，高频占比 3–13% | 明亮、有节奏的电子/流行 BGM |
| 强瞬态事件 | **224s 内只有 1 个**（t=213s 结尾处） | **几乎没有离散音效**（无 ding / whoosh / riser） |

**关键结论**：参考片的「轻快感」不是靠离散音效堆出来的，而是靠**一条全程不落、响度均匀的 BGM** 承载的。它的剪辑节奏在换画面，但听觉始终是音乐在带。

### 视频侧（1080p 224s，切点检测 2fps）
| 指标 | 数值 | 结论 |
|------|------|------|
| 场景数 / 节奏 | 89 个场景，**中位 2.5s**（min 0.5 / max 5.8） | 快剪节奏，2.5s 一换 |
| 动画转场 | ~19 个（约 0.5s 一个），平均每 5 场景出现一次（约 8–12s 一次） | 动画转场**稀疏**，不追求每场都换 |
| 转场类型 | 逐帧判别：crossfade / 软 wipe 系（wipeH/wipeV 残差几乎持平），**slide 系残差是前者的 2–3 倍** | 用**融合式转场**（淡入淡出/软划像），不用滑动推镜 |
| 场景内变化 | 大量「内容变化」（单帧 diff 2.3–3.4，原地换字/换图）+ 若干硬切（diff>7） | 节奏主要靠**场景内原地换内容**，不是靠转场 |

## 二、设计原则

1. **能量靠 BGM，不靠音效**：先配 BGM 垫底（`bgm-bed.wav`，整片循环低音量），再在上面点缀 SFX。SFX 是强调，不是主力。
2. **音效要稀疏**：参考片零离散音效。我们的三档 SFX（开场/转场/提问）是**增量优化**，用法上要克制——转场音只在动画转场上放，不逐场堆。
3. **转场用融合系，节奏用原地换内容**：`fade` / `wipe` / `wipeUp` / `iris` 优先；`slide` / `rotate3d` 是炫技项，用于重点强调场景，不做默认。动画转场约每 5 场景一次。
4. **口播类视频 BGM 更小**：参考片是快剪（大概率无口播或口播稀疏），BGM 可以顶到接近响度主载。我们的技术视频普遍有密集口播——**口播密度越高，BGM 越小**（`bgmVolume` 0.3–0.4），否则压人声。

## 三、参考片 → 本管线映射

| 参考片做法 | 本管线实现 | 参数 |
|-----------|-----------|------|
| 全程连续 BGM | `sfx.bgm: "bgm-bed.wav"` + `bgmVolume`（默认 0.35） | 无口播快剪可提到 0.6，口播视频 0.3–0.4 |
| 2.5s 快剪节奏 | 场景 `durationInFrames` 收紧到 2.5–4s（60fps 即 150–240 帧）；慢速深度视频仍可用 5s+ | 快剪优先内容原语原地动（KineticText/CountUp/HighlightBand） |
| 融合式转场 | `TransitionFrame`：`fade` / `wipe` / `wipeUp` / `iris`，时长 12–24 帧 | `transitionType` 场景级覆盖；动画转场约每 5 场景一次 |
| 原地换内容 | `PrimitiveDemo` + 动画原语（数字滚动/流光/标记带），场景内高帧动 | 快剪每场景给 1 个原语 |
| 硬切强调 | 直接换场景 + 无转场（`transitionFrames: 0`）或 `pushCut` | 用于章节开头的强调句 |
| 结尾唯一一次音效 | 开场音（`sfx.opening`）移到开头抓注意——参考片把唯一的音放在结尾，我们做成「开场引子」 | 第 0 帧，~0.5–0.9s |

## 四、三档 SFX 用法细则（`VideoConfig.sfx`）

```ts
sfx: {
  opening: "sfx-opening.wav",        // 开场 3 选 1:扫频+钟声(旧)/ -chime(更柔)/ -riser(缓升落地)
  transition: "sfx-transition.wav",  // 转场 3 选 1:二阶低通 whoosh(旧)/ -swoosh(更透气)/ -pop(快节奏)
  question: "sfx-question.wav",      // 提问 3 选 1:双音上行(旧)/ -up(更轻快)/ -down(收束反思)
  questionFrames: [285, 885, 1665],  // 提问绝对帧号,避开转场帧
  volume: 0.4,                       // 声音小一点(2026-08-20: 0.7→0.5→0.4,SFX 只点缀不抢耳)
  bgm: "bgm-bed.wav",                // BGM 垫底:轻音乐 4 轨循环(calm/walk/focus/bright)
  bgmVolume: 0.35,
}
```

- **开场音**：所有视频加。0.5–1.0s 完成「引子 + 落点」，最抓注意。轻讲解选 `-chime`（无扫频噪声更柔），钩子型选 `sfx-opening.wav`。
- **转场音**：只配给用动画转场的场景，且**不要每场都响**——用 `transitionEvery` 控制稀疏度。参考片快剪约每 5 场景一次动画转场且无转场音；口播快剪设 `transitionEvery: 3~5`，只让重点场景切换带 whoosh。
- **提问音**：只放真·提问句（口播里问句对应的字幕帧），`questionFrames` 手工点帧。**数量克制**：一篇视频 2–4 个提问音足够，多了成电子琴乱弹。反思/收束句用 `-down`。
- **强调/揭示音**（`sfx-emphasis` / `sfx-emphasis-tick` / `sfx-reveal` / `sfx-reveal-bloom`）：给关键词落地、数字滚动、图表/结论出现配点缀，同样走 `questionFrames` 那套帧定位，音量 0.4 以下。
- **音量**：SFX `volume` **0.4**（口播片，2026-08-20 降档）；BGM `bgmVolume` 0.3–0.5（口播）或 0.6（无口播快剪）。所有提示音都要低于口播人声，新 10 个变体内置幅度更小（RMS 比旧款低 3~10dB）。
- **BGM 选曲**（本地 8 轨，30-53s 循环，见 `gen-sfx.py`）：calm=沉稳科普 / walk=轻快带节奏 / focus=极简专注 / bright=明亮进取 + **tense=悬疑脉冲 / epic=史诗推进 / chiptune=8-bit / lofi=Lo-fi 七和弦**（2026-08-24 对齐抖音科技/知识区扩充）；口播片默认 calm 或 focus，快剪默认 bright。情绪档由**内容感知自动选**：courseware/graph 按口播关键词（`config.py::BGM_MOOD_RULES`），Remotion 用 `core/sound-points.ts::suggestBgmMood`——两边规则同源，改一边必须同步另一边。
- **帧定位铁律**：SFX 全部用 `<Sequence from={帧号}>` 定位，禁用 wall-clock。转场音必须和转场窗口对齐（`sceneStarts` 已自动对齐场景头）。提问帧可 `autoQuestionFrames(U)` 自动算（问句单元起始帧，≤4 个），关键词落点 `keywordFrames(U, [...])`。

## 四点五、2026-08-24 扩充：抖音风格 SFX（10 个）

按抖音科技/知识区高频音效类型合成（继续确定性、零版权、轻声幅度纪律）：

| 音效 | 用途 |
|------|------|
| sfx-transition-glitch | 数字故障抖动，配 glitch 转场 |
| sfx-transition-tapestop | 磁带急停（音高下坠），悬念切断 |
| sfx-impact | 低频重击，硬切强调/重点结论 |
| sfx-coin | 金属双音，数字/收益/成本落地 |
| sfx-ticktock | 时钟滴答，倒计时/时间线 |
| sfx-heartbeat | 低频心跳，悬念/紧张铺垫 |
| sfx-harp-gliss | 竖琴上行刮奏，揭晓/揭秘 |
| sfx-ding | 清亮叮，里程碑/通知 |
| sfx-typewriter | 打字机咔嗒，代码逐行/字幕 |
| sfx-outro-chord | 终止式软和弦（G→C），收尾定格 |

用法：Remotion `sfx.emphasis/reveal` 槽 + `emphasisFrames/revealFrames`（`keywordFrames` 算帧）；数量纪律不变——全片点缀总数 ≤8，多了成电子琴。

## 五、素材再生成

```bash
# 在 blog 仓(VIDEO_PROJECT_ROOT 决定输出到 public 目录 video-generation/narration/)
cd .agents/skills/video-generation/remotion
VIDEO_PROJECT_ROOT=$PWD/../../../.. PYTHONIOENCODING=utf-8 python scripts/gen-sfx.py
# 产物: 短音效 23 个 + BGM 8 轨 + bgm-bed 别名
# 全部纯 stdlib 确定性合成,无版权风险,重跑结果一致
```

## 六、复盘（为什么这套设计是对的）

- 参考片能量=连续 BGM，不是音效——所以**先有 BGM 垫底**，否则视频听感空洞（目前管线默认无 BGM）。
- 参考片 2.5s 一换场景——我们的默认 5s 场景配多原语动画，**信息密度不比它低**，但纯视觉验证片（motion-showcase）用它验证「动画+转场+音效」三件套。
- 转场融合系而非滑动系——因为 89 个场景里 19 个动画转场全是融合式，硬切负责强调。照抄即得参考片的顺滑感。
- 验收锚点：渲染后用 RMS 轮廓检查（开场 0–0.8s 峰值、BGM 持续底垫、转场帧小尖峰、提问帧双音）——**不靠听，靠数据**。
