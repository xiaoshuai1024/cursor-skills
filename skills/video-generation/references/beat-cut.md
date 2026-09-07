# Beat-Cut — BGM 卡点（节拍驱动剪辑）

> 方法论搬运自 OpenMontage music-to-video（AGPL-3.0），接线方式重写为本仓 Remotion/config 驱动管线。**缺省不启用**：视频 config 不写 `beat` 字段时，BGM 照走情绪档铺底链路，本文件描述的代码路径完全不被触达。
>
> 许可：`scripts/video/beatgrid.py` 搬运自 OpenMontage，按 **AGPL-3.0-only 单独许可**（区别于本仓库 MIT，文件头有 SPDX 标注）；本文件为方法论重写，随仓库 MIT。

## 它解决什么问题

现行 BGM 是「情绪档铺底」：选一首情绪对的音乐垫底，画面节奏与音乐零联动。卡点 = 把音乐的内部结构（节拍/能量/短语）变成画面的剪辑时间轴——鼓点落点切镜头、能量爆发给强动效、平缓段给慢推。`scripts/video/beatgrid.py` 把任意 BGM 确定性地转成 `audiomap.json`，这是**唯一的音乐时间事实源**。

## 信任边界（最重要的一节）

`audiomap.json` 是分析器的输出，不是真理。字段分两档：

| 永远可信 | 仅在音乐真有节拍时可信 |
|----------|------------------------|
| `energy_phases[]`（level/energy/density/feel）、`events[]` + `onset_rate`、`rolls[]`（及其缺失）、`silences[]`、`hard_stops[]`、`key_moments[]`、`phrases[]`、`audio.duration_sec` | `tempo.bpm`、`grid.beats_sec` / `downbeats_sec` 的**精度** |

- **网格可信**：rolls 存在 / 密集相位 / 高 onset_rate 且网格稳 → 逐拍硬切可以锚在 beats 上
- **网格是幻觉**：rolls≈0 / 大多 sparse / 低 onset_rate——平缓音乐上节拍追踪器会**强加**一个节拍器网格（常倍频翻倍，格点比真实 onset 还多）→ **禁止逐拍硬切**，改按 `phrases[]` + 能量包络走

判断属于哪档，是每帧 `pacing` 的判定（下文）。

## 分帧方法论（先分帧，再填内容）

1. **切帧**：在音乐真实换状态处切——`hard_stops[]`、SURGE/DROP 类 `key_moments[]`、一段 `rolls[]` 的首尾、onset 空窗（`events[]` 长空白）、能量档跳变。相邻同质相位合并成一个手势。**期望 1-6 帧**，短曲可能就一帧；禁止每拍一帧。
2. **边界吸附**：帧边界吸附到最近的 audiomap 锚点；网格可信时再吸附到最近 `beats_sec`（容差 ≤ ½ 拍），不可信时吸到 `phrases[]`/能量相位边缘。
3. **帧平铺**：首帧起于 0、末帧止于 `duration_sec`，无重叠无缝隙。
4. **每帧四件套**：`span_sec`（轨道秒）、`pacing`（beat_cut / phrase_flow）、`mood`（warm/dark/hype/elegant/glitch/cinematic/playful/tense/dreamy/aggressive 选 1-3）、`feel`（一句大白话音乐态势，如「onset 流加速进一个被按住的强拍」）。

## 素材/画面处理三式

| 式 | 适用帧 | 做法 |
|----|--------|------|
| **beat_cut** | 仅 `beat_cut` 帧 | 每个锚切一条素材/换一个画面态；淡出止于下一锚后**立即硬关**（opacity 归零 + 硬 set 成对出现，防 seek 残帧）；强锚切大画面，hero 素材落在 key_moment/强拍上 |
| **ken_burns** | `phrase_flow` 帧 | 单素材跨整段慢推（scale 1.0→1.08 + 小位移），按帧而非按拍缓动，帧边缘交叉淡化；网格不可信时的正确姿势 |
| **bg_under_text** | 任意 | 素材压暗 30-50% 垫底，前景课件/文字层照常；文本锚仍挂 audiomap 锚点 |

硬规则：视频素材**一律静音入片**（BGM/口播是唯一音轨）；逐 onset 硬切只许出现在 `beat_cut` 帧。

## 与本仓管线的接线

- **消费方**：Remotion 管线（config 驱动）。config 增加显式 `beat` 字段才启用：
  ```yaml
  beat:
    audiomap: assets/<slug>/audiomap.json   # beatgrid.py 的产物
    strategy: beat_cut | phrase_flow        # 或按帧声明
    frames: [...]                            # 可选手工分帧覆盖自动分帧
  ```
- **流程**：`python scripts/video/beatgrid.py assets/<slug>/bgm.mp3 -o assets/<slug>/audiomap.json` → 分帧（自动 + 人审）→ Remotion 侧按 audiomap 锚点排动画窗。
- **动画纪律不变**：卡点只决定**时间轴**（何时切/何时强调），动效实现一律复用 `motion.py` 既有缓动与动画窗规则、门禁五条照跑；不新造第三套动效体系。
- **与现有声音层共存**：BGM 选曲/情绪档/音效触发点照旧；卡点只是在其上增加「画面跟随」的时间映射。
- **确定性**：同一 BGM 永远同一张 audiomap（beatgrid.py 保证）；改稿换曲必重跑 beatgrid 并重审分帧。

## 运行环境

依赖 `ffmpeg/ffprobe` + `librosa/numpy/soundfile`。Windows 主 Python 缺包时 `pip install librosa numpy soundfile`（或建专用音频 env）。缺包时脚本给出可执行提示而非裸 traceback。
