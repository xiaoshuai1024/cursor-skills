# 元素动效配方库（motion-patterns）

> 来源：HeyGen 开源的 [HyperFrames](https://github.com/heygen-com/hyperframes)（Apache-2.0）catalog 实测提炼。
> 2026-08-26 用 52s demo（HyperFrames 原生渲染）逐配方验证后入库；场景级转场（whipPan/glitch/flash/lightLeak 等 15 种）已于 2026-08-23 移植进 `remotion/src/transitions/TransitionFrame.tsx`，本文件管**场景内元素级动效**——入场/出场之外的第三类动词「换态强调」。
> 数学实现一律在 `scripts/video/motion.py`（双管线共用），**不自造曲线**（SKILL.md「动画与特效强制规范」第 3 条）。分镜动画列直接写本文件配方名。

## A. 缓动总表（GSAP 名 → motion.py → Remotion）

| motion.py | GSAP/HyperFrames 名 | Remotion 等价 | 用途 |
|-----------|--------------------|---------------|------|
| `ease_out_cubic` | power2.out | `Easing.out(Easing.cubic)` | 常规入场（默认） |
| `ease_in_cubic` | power2.in | `Easing.in(Easing.cubic)` | 出场加速（M3 退场） |
| `ease_out_back` | back.out(1.7) | `Easing.out(Easing.back)` | 弹出（overshoot ≤10%） |
| `ease_in_out_sine` | sine.inOut | `Easing.inOut(Easing.sin)` | 连线生长/进度类 |
| `ease_out_expo` | expo.out | `Easing.out(Easing.exp)` | **落定**：砸入/印章/落版（前段速后段骤停） |
| `ease_out_quart` | power4.out | `Easing.bezier(0.25,1,0.5,1)` | **换词入场**：猛进缓收 |
| `ease_in_quart` | power4.in | `Easing.bezier(0.895,0.03,0.685,0.22)` | **换词出场**：蓄力整段甩出 |

选型口径：入场 cubic 起步，要「拍上去」的感觉升 expo，要弹性用 back，换词一进一出配 quart 对。

## B. 配方目录

规范帧率基准 24fps（ms÷~42=帧）。已入库配方（motion.py 有数学）标 ⚙，deck 占位符可零配置用的标 @@。

### B1. 槽内换词（kinetic-type-swap）⚙
**效果**：同一个槽位里旧词整体上甩出、新词从下方顶入，重叠极短——观众感知是「替换」不是「先后」。
**参数**：`swap_pair(age, dur=10)`（≈420ms）；旧词 `ease_in_quart` 甩至 -112%（自身高度），60% 拍点后新词 `ease_out_quart` 顶入。两词同槽绝对定位叠放、外层 overflow 裁切。
**用在哪**：口播讲身份/状态演变——「前端 → 全栈 → AI 开发」「手动 → 脚本 → 全自动」；比连续三张卡省屏且节奏感强。
**Remotion**：`interpolate(frame, [cut, dur], [112, 0], {easing: Easing.bezier(0.25,1,0.5,1)})`，旧词对称取负。

### B2. 词组 slam 交替入场（caption-kinetic-slam）⚙（enter_tuple + 编排约定）
**效果**：一句话按词拆开逐个砸入，相邻词入场方向交替（上弹/左入/右入/缩放四式轮换），比统一方向 stagger 更「kinetic」。
**参数**：每词 `enter_tuple(age, 10, dy=±140 或 scale_from=0.6, ease=ease_out_back)`，词间 stagger 2-3 帧（既有 50-100ms 规范）；方向表 `[dy:-140 ↑, dx:-90 ←, dx:90 →, scale:0.55 ⤢]` 按 index%4 轮换。
**用在哪**：提问式开头的大字钩子、结论句；关键词用 ACCENT 色（限强调，色彩规约）。

### B3. 数字滚动（count-up）⚙@@ 
**效果**：`0 → 9,603` 滚动落地，sine.inOut 全程缓。
**用法**：deck 写 `@@countup:9603@@`，卡 `anim: {"type":"countup","start_frame":N,"frames":12}`；落地拍可再叠 `settle_dip` 微缩脉冲。窗口外显示终值（静止保 PNG 复用）。
**用在哪**：star 数/价格/百分比/时长——一切有冲击力的数字。

### B4. 打字机（typewriter）⚙@@
`@@typewriter:文本@@`，逐字 reveal，窗口外全文。终端卡/代码卡专用，正文标题禁用（全片最多一两处，多了腻）。

### B5. 流光扫字（shimmer-sweep）⚙@@
`@@shimmer:文本@@`：高光带从 -20% → 120% 扫过字面（background-clip:text）。单程不 repeat 默认；repeat=true 时**仅 Remotion 管线可用**（Playwright 禁循环铁律）。用在哪：片头标题、奖杯位关键词。

### B6. 划线 / 标记带生长（strike & highlight band）⚙
**效果**：删除线/下划线从左划出；或高亮标记带在文字**后面**生长出来（字不动、底色长）。
**参数**：`grow_scale(age, dur=8)`（≈330ms，sine.inOut——生长类两端缓，**禁 back**会倒缩出负长度）。
**落法**：删除线 → `transform: scaleX(p); transform-origin:left`；标记带 → `background-size: p*100% 100%`（渐变 ACCENT→ACCENT_DEEP），跨行加 `box-decoration-break: clone`。
**用在哪**：口播「不再是 X」划掉旧说法、「记住这一点」高亮标记带——讲解纠偏/强调节拍的标配。

### B7. 印章拍落（stamp）⚙
**效果**：结论卡/口号从 1.25 缩到 1 落定、带 ≤2-3° 微旋转——「盖章」感。
**参数**：`stamp_tuple(age, 13, scale_from=1.25, rotate=2.0)`，expo.out；opacity 提前到位（1.6 倍速）。
**用在哪**：一段讲完的「锤一下」结论拍、验证戳（✓/✗ 配状态双通道）。

### B8. 落版白闪（logo/签名句 sting）⚙
**效果**：收尾定帧三拍：字标 1.15→1 expo.out 落定 → **单帧白闪** → ACCENT 辉光环 0.34→2.4 扩散淡出。
**参数**：`sting_tuple(age, land_dur=16, flash_at=8, ring_dur=22)`；白闪**恰 1 帧**（多帧廉价）、ring 用 ACCENT 描边圆环（同屏辉光 ≤2 个，色彩规约）。
**用在哪**：签名句「我是1024工程笔记…」落版、品牌 outro。全片一次。

### B9. 辉光脉冲 / 凹陷过渡（既有，联动反馈专用）⚙
`glow_mult`（主拍后 0-6 帧关联元素 box-shadow 增量）+ `settle_dip`（类切换时透明度微凹）——配合 B1-B8 的主元素做「一次节拍 ≥3 元素响应」联动（动画规范第 2 条）。

### B10. 循环漂移背景（aurora-drift，仅 Remotion）
**效果**：2-3 个大模糊 ACCENT 色块缓慢漂移的无缝循环背景。
**实现**：相位走完恰好 2π 归一（t=0 与 t=D 姿态一致）：
```ts
const phase = (frame / loopFrames) % 1;           // 归一相位
const x = Math.sin(2 * Math.PI * phase) * amp;    // 正弦往返，端点相接
```
**⚠ Playwright 管线禁用**（帧驱动铁律：循环/呼吸类不进逐帧管线；课件底静深色即可，动感交给 B1-B8）。

## C. 编舞约定

- **信封（envelope）**：每个动效 `IN → HOLD → OUT` 三段；**卡时长不足时按比例压缩 IN/OUT、HOLD 优先保**，禁整体 timeScale 加速（会改变缓动性格）。与既有「动画有界窗口、窗口外静止」同源。
- **出场快于入场**（既有 M3 规则）：OUT 4-5 帧 ease-in，**位移优先于纯淡出**——纯 opacity 淡出的中途帧会掉对比度（见 E2 坑）。
- **先退后进**：换卡/换场景时旧元素先完成退场（或位移出画面），新元素再入场——两团文字同屏重叠 = 返工（E1 坑）。
- slam 方向轮换表见 B2；stagger 既有 50-100ms/项规范不变。

## D. 确定性守则（HyperFrames 契约，已并入帧驱动铁律）

1. **显式两端初态**：任何动画首帧前元素必须有明确初始态（opacity 0 藏在出生位），不依赖浏览器默认加载序。
2. **预烘焙帧表**：count-up/打字机类按帧表取值（`count_up_table`），不做逐帧浮点重算——同输入同输出，重渲一致。
3. **有界窗口**：窗口外一律终态且不输出 inline style（PNG 复用优化的前提，见 frames.py）。

## E. 渲染质量门禁（2026-08-26 demo 实测抓到的坑，候选并入 make video-lint）

| # | 规则 | 实测坑 | 建议检法 |
|---|------|--------|---------|
| E1 | 文字块重叠禁令 | 印章卡压住流水线节点文字 304 帧才被采样器抓出 | 渲染前抽帧对同屏文本框做相交检测 |
| E2 | 淡出中途对比度 | 元素纯 opacity 淡出途中实测 1.02:1（门禁 3:1） | 退场位移+≤5 帧；对比度采样覆盖淡出中途帧 |
| E3 | 同元素同属性动画窗冲突 | opacity 入场窗未关又开出场窗 → 跳变 | 静态扫动画时间表：同元素同属性窗口不得重叠 |
| E4 | 字体显式声明 | headless 渲染字体回退换字形 | Playwright/Remotion 字体清单与 @font-face 对账 |
| E5 | media 元素稳定 id | 无 id 的音轨渲染时静默静音 | 渲染前置检查：音/视元素必须有 id 且素材存在 |

## F. 待移植 backlog（需要时再动，勿提前实现）

- **shader 转场**：HyperFrames `@hyperframes/shader-transitions` 14 个 GLSL（whip-pan/glitch/flash-through-white/light-leak 四星已有 CSS 近似版在 TransitionFrame；shader 版质感更强，代价是 WebGL 进 Remotion）
- bar-chart-race（排名交换动画）、camera-dolly-zoom（视差焦距解算）、beat-freeze-cut（拍点定格硬切）
- HyperFrames catalog 全量：`docs/catalog/components/`（219）/`blocks/`（154），mdx 内含可复制源码
