# 真实成稿案例库（real-world examples）

以下 16 个 `.excalidraw` 文件全部来自本博客**已发布文章的真实配图**（源文件同款出 SVG 到站上），不是教学演示稿。写新图前先在这里找同型参考——布局坐标、留白密度、箭头走线都是验证过能出片的，比从零手排坐标快得多。

## 按图型检索

| 文件 | 图型 | 学什么 |
|------|------|--------|
| `glm-5-3-release-timeline.excalidraw` | 时间线 | 横向里程碑排布，日期标签用自由文本不装箱 |
| `ai-agent-engineering-evolution-cognition.excalidraw` | 演进/阶段 | 少量节点讲清「认知升级」类抽象主题 |
| `deepseek-harness-evolution.excalidraw` | 演进/阶段 | 三段式演进，文字多框少的排版密度 |
| `arch-decay-excalidraw.excalidraw` | 架构腐化 | diamond 判定节点 + 长箭头回环的走线 |
| `e2e-registry-gate.excalidraw` | 门禁/判定 | diamond 做闸门、两条分支走线的标准画法 |
| `ai-buzzwords-one-line-mental-model.excalidraw` | 心智模型 | 概念类比图：6 框 5 箭头承载 14 段文字的密度上限 |
| `ai-buzzwords-one-line-agent-compare.excalidraw` | 对比 | 极简双栏对比（7 个元素讲清两个主体的差异） |
| `ai-buzzwords-one-line-advanced-ladder.excalidraw` | 阶梯/进阶 | 阶梯式升维排布，线 + 框混用 |
| `ai-buzzwords-one-line-skill-structure.excalidraw` | 结构拆解 | 树状拆解一个概念的组成 |
| `spec-lifecycle.excalidraw` | 生命周期/环 | ellipse 做起止态、闭环回边的画法 |
| `spec-positions.excalidraw` | 定位/坐标 | 多主体在坐标系里的相对位置表达 |
| `rag-recall-tuning-1.excalidraw` | 流水线 | 检索链路直排流水线（7 框 2 箭头的克制版） |
| `rag-recall-tuning-3.excalidraw` | 流水线 | 同一链路加强版（12 框 10 箭头），对照 -1 看「加细节」怎么加 |
| `claude-code-ccswitch-domestic-models-2.excalidraw` | 渐进组图·简 | 同一主题第一张：只画主干 |
| `claude-code-ccswitch-domestic-models-3.excalidraw` | 渐进组图·中 | 第二张：补分支 |
| `claude-code-ccswitch-domestic-models-4.excalidraw` | 渐进组图·繁 | 第三张：补完整拓扑——「一图一讲」的拆图节奏 |

## 使用方式

```bash
# 直接以某个案例为骨架改
cp references/examples/real-world/spec-lifecycle.excalidraw /tmp/my-diagram.excalidraw
python3 scripts/check_alignment.py /tmp/my-diagram.excalidraw
python3 scripts/render.py /tmp/my-diagram.excalidraw
```

注意：这些成稿的 `seed` 字段多为具体值（出片时定死的）。复用骨架后记得把 `seed` 清回 `null`，让渲染器重新注入随机抖动，否则手绘质感会发死。
