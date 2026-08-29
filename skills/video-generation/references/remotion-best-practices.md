# Remotion 最佳实践摘录（自 OpenMontage remotion-best-practices 蒸馏）

> 2026-08-29 摘录自 OpenMontage `remotion-best-practices`（37 条官方 API 实践蒸馏，AGPL-3.0）；本文件为方法论/API 知识重写，随本仓库 MIT。只收录对本仓 Remotion 管线有用的子集，按「解决什么问题」组织。API 以 remotion.dev 官方文档为准。

## 时序与动画（对照 motion.py）

- **插值只走 `interpolate` / `spring`，禁 wall-clock**：一切动画由 `useCurrentFrame()` 驱动（seek 安全、重渲染逐像素一致）。`interpolate(frame, [0,100], [0,1], {easing: Easing.out(Easing.cubic), extrapolateLeft/Right: "clamp"})`——**不 clamp 是最常见的出界 bug**。
- `spring({frame, fps, config: {damping, stiffness, mass}})` 弹性入场；durationInFrames 由 `springDuration` 估算。与本仓 motion.py 的缓动表对齐：ease-out 类 = `Easing.out(Easing.cubic/Quad)`，back overshoot = `Easing.out(Easing.back)`（≤10% 过冲调 damping）。

## 转场（对照 TransitionFrame.tsx）

- 官方包 `@remotion/transitions` 的 `<TransitionSeries>` 三件套：`Sequence` + `Transition(presentation, timing)` + `Sequence`，**转场期间两场景同播、时间线自动缩短**——比手摆 transitionFrames 少一类对齐 bug。presentation 内置 fade/slide/wipe/flip/clockWipe/two-tick 等，`linearTiming({durationInFrames: 15})` 定时长。
- **Overlay 通道**：`<TransitionSeries.Overlay>` 在切点上叠任意 React 组件（如光效），可与 transition 共存但不能相邻。
- 决策：新视频优先试官方 presentation，自定义 3D 类转场再回落自研 TransitionFrame；两者可在不同场景混用。

## 光效

- `@remotion/light-leaks`（需 Remotion ≥4.0.415）的 `<LightLeak>`：WebGL 光晕，前半段展开后半段回收，放在 Overlay 位做高光切点。签名句落版白闪（sting_tuple）之外的现成高光选项。

## 文字测量（关联字号门禁）

- `@remotion/layout-utils`：`measureText({text, fontFamily, fontSize, fontWeight})` 量宽高（结果有缓存）；`fitText({text, withinWidth, ...})` 反算适配字号（记得 cap 上限）；`fillTextBox({maxBoxWidth, maxLines})` 逐词检查溢出。
- **纪律**：① 测量前字体必须已加载（`@remotion/google-fonts` 的 `loadFont` + `waitUntilDone`，或 `validateFontIsLoaded: true` 抛错早暴露）；② 测量与渲染的字体属性必须逐项一致（差一个 fontWeight 就偏差）。
- 对本仓：lint_font_sizes 是静态门禁，layout-utils 是渲染时兜底——标题接近容器宽时用 fitText 自动缩，比爆版后人工改好。

## 字幕

- 官方 `@remotion/captions`：`createTikTokStyleCaptions(pages)` 把词级 Caption 流切成「一页几词」的 TikTok 式翻页字幕；配合 `Sequence` 按页显示。
- 异步加载字幕用 `useDelayRender()` 挂起渲染（fetch staticFile + delayRender/continueRender），防止渲染器在数据就绪前出帧。
- 本仓字幕走意群单元级（split_units + WordBoundary 时间戳），TikTok 分页是英文词级的思路，中文按意群更稳——借它「页内高亮当前词」的做法可做卡拉 OK 式字幕。

## 音频可视化（口播/BGM 新视觉元素）

- `@remotion/media-utils`：`useWindowedAudioData({src, frame, fps, windowInSeconds})` 取窗口音频数据 + `visualizeAudio({fps, frame, audioData, numberOfSamples: 256})` 得频谱数组 → 频谱条/波形/低音响应画面。
- 口播视频可在钩子段/签名句叠波形条；注意 audioData 未就绪时先返回 null（同 delayRender 纪律）。

## 地图（地理类选题备用）

- 官方规则走 **mapbox-gl**：免费 token（.env `REMOTION_MAPBOX_TOKEN`）+ `useDelayRender` 等 map 实例就绪 + `easeTo`/`jumpTo` 由 frame 驱动镜头飞行；`@turf/turf` 算地理插值。
- **确定性红线**：render-time 禁网络取瓦片（每次渲染取到的图会变）→ 卫星/底图必须**先烘焙成静态资源**再进渲染；矢量风格（自绘 region 形状）无此问题。
- OpenMontage motion-graphics/maps 的两 lane 决策可复用：默认 vector（零素材、零 token），真底图才走 bake。

## 透明视频 / GIF / Lottie（速查）

- 透明视频两条路：**ProRes 4444**（进剪辑软件）或 **VP9 WebM**（网页/直接播放）；渲染时设 codec + 像素格式 `yuva420p`。mascot 若要导出成带 alpha 的贴片素材走这条路。
- GIF：`@remotion/gif` 的 `<Gif>` 组件（自动播放/循环控制）；Lottie：`@remotion/lottie` + lottie-json，锦上添花用，别为本仓引入新依赖链。

## 渲染前静态校验（对照 composition_validator 思路）

渲染前检查清单（本仓已部分覆盖，缺失项可补）：素材文件存在（图片/音频路径可解析）、口播时长 ≤ 视频时长、BGM 时长 ≥ 视频时长（短了会静默循环断档）、切点序列无重叠乱序、必填字段齐全。对应本仓 `verify_render.py` 是**渲染后**检查，这一层是**渲染前**检查，两层都要。
