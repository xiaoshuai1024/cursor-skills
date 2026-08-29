# Mascot 姿态库与数据驱动 Rig 参考（自 OpenMontage 角色三件套蒸馏）

> 2026-08-29 摘录自 OpenMontage `pose-library-design` / `character-rigging` / `svg-character-animation`（AGPL-3.0）；本文件为方法论重写，随本仓库 MIT。供 mascot（MascotFigure.tsx / MascotCompanion.tsx / mascot-mood.ts）下次迭代参考，不是现行定规。

## 现状与差距

现行 mascot：6 表情（smile/huh/money/dead/wow/meh）+ 3 姿态 + 讲话态，表情由 mascot-mood.ts 关键词表推断，姿态硬编码在 JSX。三份蒸馏知识给出的升级方向：**姿态库分类法**（覆盖面有体系可查）与**数据驱动 rig**（角色=数据包，运行时代码通用）。

## 姿态库分类法（pose taxonomy）

设计新表情/姿态时按三类盘点，避免「想加一个加一个」的碎片化：

| 类目 | 内容 | mascot 对应 |
|------|------|-------------|
| **Neutral 中性** | idle / breathe / listening | 现有待机浮动 + sin 呼吸 |
| **Attention 注意** | look_up / look_down / look_left / look_right | 现无——「看代码/看标题/看向上升图表」类朝向可做成 4 姿态 |
| **Emotion 情绪** | happy / sad / surprised / worried / determined | 现 6 表情（money/dead/wow/meh…），盘点缺口：worried（翻车前兆）/ determined（跑分冲刺） |

姿态数据结构（数据驱动核心）：**只声明相对默认 rig 变化的部件**，未声明的从 rig 默认继承——

```json
{ "pose": "surprised",
  "parts": { "head": {"rotation": -6, "y": -4},
             "pupil_left": {"x": 4, "y": -6},
             "mouth": "small_o" },
  "hold_frames": 18, "transition": "back.out" }
```

## 数据驱动 Rig 模式

把 mascot 从「一份 JSX 硬编码」拆成「通用渲染器 + 角色数据包」：

- **parts[]**：每个可动部件声明 `id / kind / layer（绘制层级）/ parent（层级约束）`
- **joints{}**：每个部件的 `pivot`（显式 SVG 坐标，别依赖浏览器 transform-origin 的坐标空间行为；GSAP 用 `svgOrigin`）+ 旋转限位区间（如 head [-20°, 20°]）
- **嘴形、眼/瞳、道具必须是独立部件**（gaze 变化要单独动瞳孔；嘴形是独立 path 组）
- 质检清单：每个会动的部件有 pivot；有层级意义的部件标了 parent；渲染帧抽样能看到有意义的差量（不是冻住）

## Remotion 帧驱动纪律（与现有实现一致，守好别破）

- GSAP timeline 在 Remotion 里**必须由帧驱动**：`timeline.progress(useCurrentFrame() / durationInFrames)`，禁 requestAnimationFrame / wall-clock（渲染器随机 seek）
- 变换只动 transform（x/y/scale/rotation），不动 layout 属性
- 动作节拍用 timeline 排（多部件连动可读）；姿态 hold 要够长（hold_frames）让情绪读得出来
- 眨眼/视线/嘴形三者独立到「帧抽样能分别检出」的程度

## 迭代建议（下次动 mascot 时）

1. 先把现 6 表情 + 3 姿态重排进三类盘点表，找缺口（attention 类大概率全空）
2. 新表情按「只声明变化部件」的 pose JSON 加，进 `moodTimeline` 手工通道验收后再考虑进关键词表
3. 若部件数超过 ~10 个或出现朝向类需求，再考虑数据包化重构——现在 6 表景规模 JSX 还扛得住，别为模式而模式
