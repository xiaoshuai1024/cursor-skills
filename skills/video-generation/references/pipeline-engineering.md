# 渲染管线工程细则（pipeline-engineering）

> 拆分自 SKILL.md（2026-08-30，openspec video-generation-skill-split），内容逐字保留；声音素材标准另见 sound-design.md，BGM 卡点另见 beat-cut.md。

### 管线能力缺口清单（规则先行，能力补齐前先验证再依赖）

上述规则里这几项目前管线**未完整支持**，生成视频遇到时先核对/补齐，不要当成现成能力用：

| 规则 | 缺口 | 位置 |
|------|------|------|
| 代码动态高亮 | `CodeBlock` 行级高亮未验证是否支持逐行 active 态 | `remotion/src/primitives/CodeBlock` |
| 错误场景视觉预警 | `terminal` 卡无 error 态样式（红色/闪烁/⚠️） | `scripts/video/screencast.py` |
| 迷你进度条常驻 | 各模式均无角落进度条组件 | courseware/graph/Remotion 均缺 |
| 术语比喻配图示 | 无现成比喻示意组件，需新原语或 Excalidraw 素材 | Remotion primitives |
| 结尾问题视觉卡片 | `cta` 卡可承载，但无「问题卡片」专用样式 | `screencast.py` `_CONTENT.cta` |
| 换态强调动效（swap/stamp/sting/grow） | 数学已入库 `motion.py`（2026-08-26，单测 `python -m video.test_motion`），courseware/Remotion 模板尚未接消费点——用到哪张卡再接哪张，接时按 motion-patterns.md B 节落法 | `scripts/video/motion.py` + `references/motion-patterns.md` |

已确认支持：graph 连线扫描 / Remotion 卡片逐张浮现（动态流程）、courseware `sub_points`（概念卡片）、`LeaderboardChart`/`DataReveal`（数据图表）、realshot hotspots + `.hot.active`（视觉锚点）、screencast 顶部步骤条 / Remotion 阶段导航（进度导航）、`ComparisonTable3D`/`cost` 卡（对比）、`active_idx` 逐条揭示（防信息过载）、**BGM 垫底 + 三档 SFX + 15 种场景转场**（2026-08-23 接线，全管线自动，见「声音层与转场」）、**courseware/screencast 左下角 mascot 伴随层**（2026-08-25 补齐：`courseware.py::_mascot_html` 对 tool/tutorial/普通卡统一注入，样式全内联防 CSS 丢失，cue 出生 8 帧落地反应 + 窗口外静止保 PNG 复用——Playwright 管线不做循环动画是铁律）。
### 外部素材与 BGM 卡点（stock-footage / beat-cut，2026-08-29 接入，openspec openmontage-knowledge-port）

按场景触发，不是默认启用——遇到下列画面需求才调用，平时不改变现行管线：

- **实拍空镜 B-roll**（调 `stock-footage` skill）：① 概念比喻段（压缩/缓存/token 账等抽象概念插 1-2 条实拍空镜换质感）；② 事故/案例复盘开头 3-5 秒实拍+旁白起手；③ 评测对比类选题的产品实拍；④ 封面底图（公有领域图）。素材带溯源三件套（provider/素材页/license），进成片一律静音、随 archive 登记。免 key 直接可用，境外源不通时设 HTTP_PROXY/HTTPS_PROXY
- **BGM 卡点（beat-cut，段落级）**：① 片头钩子段（前 3-5 秒提问式开头，鼓点+快切）；② 榜单盘点类快剪段（top-N 倒数段）；③ 签名句收尾 sting。**全片不卡点**——课件讲解节奏由口播驱动。启用：config 加 `beat` 字段（audiomap 路径 + 策略），先跑 `scripts/video/beatgrid.py` 出 audiomap，方法论见 `references/beat-cut.md`
- **Remotion 改版翻 `references/remotion-best-practices.md`**：官方 TransitionSeries 转场 / layout-utils 文字测量（防爆版）/ 口播波形可视化（TTS、token、账单类主题高契合）/ 地图烘焙红线
- **验收闭环（每条卡点/转场视频渲染后强制）**：`verify_render.py --transition-check <切点帧>`（切点是否生效；d2 低 = 素材死帧 WARN，改用 freezedetect 避让进片点）+ `--caption-check <帧A> <帧B>`（字幕活性 + 对比双峰判据）。实战记录见 `video-generation/build/beatcut-demo/README.md`
### 画面
- **横屏 16:9，1920×1080**（知识/教学视频标准）
- **courseware**：左栏（标题+要点三态）+ 右栏（知识卡片 sub_points 或 flow 流程图）+ 底部字幕带 + 进度条；全元素帧驱动动画 + 主锚联动（`point_births` 出生帧驱动，动画窗口外静止保 PNG 复用，见「动画与特效强制规范」）
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
  - **平台合规（强制）**：口播 + 画面**禁止「评论区扣XX / 关注我」类诱导 CTA**（抖音违规诱导，限流/下架）；结尾用中性价值钩子（「零基础四分钟装好 · 不用注册官方账号」）**或开放式提问/选择题**（「你站哪边？」「你卡在哪一步？评论区聊聊」——B站/快手/视频号口径；**抖音全链路无「评论区」三字**，点赞/收藏动作引导见「互动与转化引导」矩阵，见「黄金 2 秒与互动设计」）。禁止自问自答设问句（「key哪来」）——**画面里也不能出现**（反例：`terminal` 曾硬编码「← 还是官方模型？」自问句）
  - **tool 卡内容全透传**：`build.py::normalize_card` 必须 `dict(raw)` 透传 tool 卡全部字段（big/mats/cta/items/req/resp/hotspots/lines 等），否则 builder 落默认值（老 bug）。**新增可配内容不要硬编码进 builder**（反例：`terminal` 曾硬编码旧视频「Claude Opus 5」内容），一律走卡字段
### 声音层与转场（BGM/音效/转场全管线自动，2026-08-23 接线定规）

> 2026-08-23 复盘：声音规范（sound-design.md）、素材（gen-sfx.py）、组件（TransitionFrame）在 08-20 就已存在，但 types/VideoComposition/render/build 的**接线代码从未落地**，openspec 归档勾选失真——导致 17 个成片里 15 个无 BGM、最新 6 集无转场。现已接线：**所有管线零配置自动带 BGM + 音效 + 转场**。

- **Remotion（默认）**：`VideoComposition` 内建 `SoundLayer` **原生渲染**（合成内 `<Audio>` 层，非成片后混）：
  - BGM `bgm-bed.wav` 整片循环垫底，淡入 1s / 尾部淡出 2s；开场音 @0；转场音按场景头稀疏触发（默认每 4 场景一次，场景 0 只开场音）；提问音走 `questionFrames` 手工点帧（全片 2~4 个）
  - `config.sfx` 未声明**自动套默认值**（新视频零配置即有）；声明了按字段浅覆盖；`sfx: { enabled: false }` 整层关闭。字段全表见 `core/types.ts` 的 `SfxConfig`
  - 转场默认开启：`transitionFrames` 未设 = 16（约 0.27s，rotate3d，与存量视频视觉一致）；`config.transitionType` 全局 / `scenes[].transitionType` 逐场景覆盖，15 种见 `transitions/TransitionFrame.tsx`；显式 `0` = 硬切
- **courseware/graph/screencast**：`make video` 在 xfade/acrossfade **同一条 FFmpeg filter_complex** 里混入 BGM + 开场音 + 每 4 段转场音（`render.audio_overlay_chain`，单 pass 出片，无中间文件、无成片二次后混）。素材缺失自动降级并在收尾打印 `✗`
- **素材自愈**：Remotion 渲染前 `render.ts` 自动检查 16 个关键 BGM/SFX 文件，缺失自动重跑 `gen-sfx.py`（纯 stdlib 确定性合成，重跑一致）
- **素材位置**：`video-generation/narration/`（= Remotion public/，**BGM 8 轨 + SFX 25 个**，2026-08-26 补 error/hook 场景）；选曲/变体/音量标定依据 `references/sound-design.md`（口播片 BGM 0.3–0.4、SFX 0.4，能量靠 BGM 不靠音效）
- **内容感知选曲（2026-08-24）**：BGM 不再固定 calm——
  - courseware/graph/screencast：`make video` 按口播关键词**自动选情绪档**（收尾打印 `BGM <mood>`）
  - Remotion：config.ts 里 `import { suggestBgmMood, autoQuestionFrames, keywordFrames } from "@skill-src/core/sound-points"`，`sfx: { bgmMood: suggestBgmMood(U.map(u=>u.text)), questionFrames: autoQuestionFrames(U) }`；关键词规则两边同源（`config.py::BGM_MOOD_RULES` ↔ `sound-points.ts::MOOD_RULES`），改一边必须同步另一边

  | 情绪档 | 文件 | 适用内容 |
  |--------|------|---------|
  | calm（默认） | bgm-light-calm | 沉稳科普，任何讲解都安全 |
  | walk | bgm-light-walk | 轻快带节奏：教程/步骤/上手 |
  | focus | bgm-light-focus | 极简专注：深度解析/长讲解 |
  | bright | bgm-light-bright | 明亮进取：新发布/技巧/效率 |
  | tense | bgm-tense | 悬疑脉冲（抖音悬疑解说味）：源码内幕/揭秘/踩坑 |
  | epic | bgm-epic | 史诗推进（热血盘点味）：对决/评测/跑分 |
  | chiptune | bgm-chiptune | 8-bit 方波：程序员梗/终端/装机 |
  | lofi | bgm-lofi | Lo-fi 七和弦：温和长教程/随笔体验 |

- **SFX 场景×氛围矩阵（2026-08-26，openspec video-sfx-scenario-palette）**：SFX 与 BGM 共用 mood 轴，**按视频氛围自动选变体**（悬疑片 glitch 转场 + question-down 提问音，轻快教程 pop/swoosh + question-up）。12 语义场景（opening/question/transition/emphasis/reveal/milestone/error/typing/countdown/suspense/hook/outro）× 备选池，全表见 `references/sound-design.md` §五（文档 SSOT）：
  - courseware/graph **零配置自动**：槽位变体 + cue 定点（提问/报错/成功/揭晓关键词扫口播，每类 ≤2、总数 ≤8）+ 尾卡签名句 outro 和弦；渲染收尾打印矩阵选择与点位表
  - Remotion opt-in：`sfx: { ...suggestSfxSet(N.audio, U.map(u=>u.text)) }` 一行整套；单场景 `suggestSfx("transition", "tense")`
  - 双源纪律：`config.py::SFX_SCENARIO_MATRIX` ↔ `sound-points.ts::SFX_SCENARIOS` 同源镜像，`make video-lint` 的 `check_sfx_matrix` 机检漂移
- **SFX 选配速查**（手动微调用；自动选择走上面的矩阵）：悬念切断 `sfx-transition-tapestop`（磁带急停）、倒计时 `sfx-ticktock`、紧张铺垫 `sfx-heartbeat`、钩子埋点 `sfx-hook-riser`（上扬悬置）、报错/翻车 `sfx-error-buzz`（三全音下行）、代码逐行 `sfx-typewriter`——其余场景（转场/强调/揭晓/里程碑/收尾）优先让矩阵按 mood 选，别手锁一个变体
- **验收（强制）**：`python scripts/verify_render.py <mp4> <fps> <起帧:名>...`——frame-diff 查场景动画 + volumedetect 查混音健康（mean −20~−30dB、max 不贴 0dB）。发布前抽听开场 1s（应有 chime）与中段任意 5s（应有 BGM 底垫）。增补两检查（2026-08-29，openspec openmontage-knowledge-port 第二批）：`--caption-check <帧A> <帧B>`（字幕活性 + 主题无关对比双峰判据）、`--transition-check <切点帧>...`（切点两侧画面变化检出；切点帧来自 config 的 transitionFrames）
- **BGM 卡点（可选增强，2026-08-28 接入，openspec openmontage-knowledge-port）**：情绪档管「选哪首」，卡点管「画面跟不跟拍」。`scripts/video/beatgrid.py`（librosa 节拍网格/能量叙事/短语层，唯一音乐时间事实源）把 BGM 转成确定性 `audiomap.json`，画面按信任边界分帧卡点（beat_cut 逐拍硬切 / phrase_flow 短语流动）。**缺省不启用**：config 加 `beat` 字段才走卡点，不写完全走本节老路；动效只许复用 motion.py 既有缓动。信任边界/分帧法/素材三处理/接线方式见 `references/beat-cut.md`（beatgrid.py 搬运自 OpenMontage，AGPL-3.0 单独许可）
- **Remotion 官方实践参考**：`references/remotion-best-practices.md`（2026-08-29 摘录自 OpenMontage，TransitionSeries 官方转场/layout-utils 文字测量/音频可视化/地图烘焙红线/字幕分页等，新视频优先试官方 presentation 再回落自研）
- 教训沉淀：**归档变更前必须 grep 实际代码确认接线存在**（渲染端 import/调用点），不能只看 tasks 勾选——本次 5 项 `[x]` 任务里 4 项接线实际不存在
### 形象伴随层（机器人 mascot，2026-08-24 接线，video-mascot-narration）

> 与声音层同款零配置哲学：`config.mascot` 未声明**自动启用**，右下角常驻终端小子（封面同款形象），跟讲解随动。

- **组件**：`src/primitives/MascotFigure.tsx`（mascot.svg 几何的 JSX 转写，6 表情/3 姿态/讲话态 props 驱动）+ `MascotCompanion.tsx`（装配层：待机 sin 浮动 + 天线辉光脉冲 + 段边界反应点头/摆头/微跳按段索引 %3 轮换 + 表情切换 12 帧弹跳）
- **表情自动推断**：`src/core/mascot-mood.ts` 关键词表按 `config.subtitles` 逐段推断——疑问(huh)/算钱(money)/崩溃(dead)/惊讶(wow)/无语(meh)，**命中才切、未命中保持**（段内不闪切）。词表按真实讲解词校准过（「怎么」「省得多」「沉默」是 2026-08-24 校准补的），新视频发现误命中/漏命中直接改 `MOOD_KEYWORDS`
- **手工覆盖**：`mascot: { moodTimeline: [{ frame: 540, mood: "wow" }, ...] }`——手工点后到下一手工点之间自动推断挂起；`autoMood: false` 全程 smile
- **强调联动**：命中 `sfx.emphasisFrames` 的段自动切 point 姿态 1s（`sfx: { enabled: false }` 时不联动）；字幕含「记住/重点/关键是/结论」等词的段也 point
- **关闭**：`mascot: { enabled: false }` 一键关；旧 config 无 mascot 段照常渲染（已回归验证：差异仅在形象区）
- **遮挡调优（2026-08-25 换边定规，openspec video-mascot-placement）**：默认 `position: "bottom-left"` + `height: 240`，形象区约 left 48/bottom 36 起（含头顶符号带约 280×400）。依据：抖音/快手/视频号信息流右侧竖排互动栏（头像/关注/赞/评/转）直接覆盖横屏视频右缘（2026-08-25 实测机器人被抖音头像挡住），底部文案栏另占底缘——左下是四平台一致净空角，与「右缘避让 180px」门禁同源。240 为左侧净空区标定（右侧旧标定 210 的「240 抢戏」判定不迁移）；场景左下有核心内容（SkillStage 左栏末张要点卡）时单视频降 210，禁超 270。字幕 pill 居中不冲突；B站横屏播放互动在右下，左下同样安全
- **验收（强制）**：`python scripts/verify_render.py <mp4> 60 --mascot-check <说话帧> <静默帧> [--mood <表情A帧> <表情B帧>]`——形象区帧差 ≥0.5%（讲话面板+浮动）、表情带 ≥0.3%；本 change 实测讲话 13.41%/表情带 68.70%/段边界反应 15.48%
- **双份同步约束**：封面 `scripts/video/assets/mascot.svg` 与 `MascotFigure.tsx` 是同一形象两份实现，改几何必须两边同步（两文件头部注释互指）
- **迭代参考（非定规）**：`references/mascot-pose-rig.md`（2026-08-29 摘录）——姿态库三分类盘点（现 6 表情/3 姿态缺 attention 类朝向：看代码/看图表联动感提升点）、pose JSON 只声明变化部件的数据包模式；部件超 ~10 个或有朝向需求时再重构
### 关键经验（这条管线踩坑沉淀）
- **口播去 AI 味（强制，2026-08-03 踩坑）**：口播稿不是文章，是「讲给人听的」。诊断信号：① 同一个口号（「全量国产/切一次不回官方」）在多个场景重复 3 遍——**口号全文只说一次**（放结论场景）；② 教学腔开头「先理解一件事/算笔账/新手最容易」——删掉直接说；③ 升华句「把 X 从 A 变成 B」——删；④ 排比对仗工整。正确做法：动词驱动（「装」「粘」「切」）、具体数字（$5/$0.028/178 倍）、长短句混用、金句收尾。参照 `narrate_after_million_loc.py` 口播（全 agent、零口号重复）。**改口播 = 重跑 narrate → narration.ts 单元索引全变 → config.ts 的 span/cardsFor 必须跟着重写。**
- **场景密度对齐借鉴视频**：借鉴视频（after-million-loc）8 个内容场景、每场景 4-5 卡、总 28 卡，节奏快。教程/步骤型文章不要把所有步骤挤进一个场景——**每步一个场景**（如 ccswitch 拆「装/加供应商/切换验证」3 个场景），每场景卡片随口播逐张浮现。画面「死板」的根因是场景少 + 卡少 + 停留长。
- **内容 > 抽象 3D**：技术科普要真实素材（截图/代码/真实数据图表）+ 标注，不是抽象粒子/玻璃。调研结论：B站/抖音主流是「录屏 + 标注」，纯 3D 抽象动画只适合片头。
- **数据可视化用真实图表**：排行榜用横向条形图（`LeaderboardChart`），高亮主角（品牌色 + 发光 + 标注）；跃升用前后双柱（`GrowthChart`）。数据从文章/榜单抓取，**不编造**。
- **真实性红线**：数据必须来自真实来源（文章/官方榜单）。矛盾信息（如"是否多模态"）以用户确认为准，未经证实的不写进视频。
- **背景全局层**：科技背景（电路板网格 `TechBackground`）做全局底层，场景根背景透明露出；不要每个场景各画。
- **字幕安全带**：底部固定预留（~170px），场景内容避让；`Cover` 用 flex 流 + opacity 占位（不要用 `position:absolute` 的 `TimedLayer`，多个会互相覆盖导致重叠）。
- **DataReveal 小数**：数字递增动画要保留 number 的小数位（`toFixed(decimals)`），否则 `8.9` 被 `Math.round` 成 `9`。

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
### 课件批量生产与后台渲染事故清单（2026-08-29 复盘沉淀，强制）

#### 资产门禁（deck/narrations authoring）
- **deck 卡数必须 === narrations 卡数**（逐句卡一一对应，禁止两张口播卡合并一张 deck 卡）：数量不等 render 门禁直接拒（实录 14≠15、12≠13 两集渲染被拒）。deck 拆卡时 eyebrow/points 同步补齐。
- **metadata.txt 必须在链路前写入** `build/<slug>/metadata.txt`（至少 `标题:` 行）：cover_video 从中取标题，缺失时封面步骤静默跳过（`|| true` 吞掉），成片无封面。 серии六集实录：五集封面全缺即此因。
- **narrations JSON 零污染**（2026-08-29 实录）：从口播稿 md 提取逐句卡时，节边界必须切到「下一个 `## ` 标题」，禁止用后置章节名当切点（章节顺序一变就把分镜表/梗清单整段吞进最后一张卡）。发合成前机检：所有卡不得含 `|`、`→`、换行——TTS 会把表格当口播念出来（IndexTTS 报 unknown tokens `|` 即此症）。
- `sync_check.py` 是 **Remotion 管线专用**（依赖 remotion-videos/<slug>/narration.ts）；courseware 模式不适用，音画对位由 `_align_shots.py`（真实句边界重排镜头切点）+ 人工抽帧承担，别对课件跑它。

#### 后台/子环境渲染五坑（gpuq/后台任务实录，全部已修）
1. **gpuq/子进程 PATH 被裁剪**：链脚本内禁裸调 `wsl`/`py`/`make`——一律绝对路径（`/c/Windows/System32/wsl.exe`、`/c/Windows/py.exe`、或直接 `python.exe -m video.build` 内联绕开 make）。模板级修法见 `_run_eng_series_chain.sh` 开头的 Git Bash 重执行守卫（检测 `MSYSTEM`，WSL bash 环境自动 exec 到 Git Bash；守卫变量引用用 `${VAR:-}` 防 set -u 报 unbound）。
2. **python 文本模式补丁 .sh 会写出 CRLF** → bash 报 `invalid option`/`$'
': command not found` 拒跑。补丁脚本写文件必须 `io.open(p,'w',encoding='utf-8',newline='
')`（同 blog-writing「drawio 禁 heredoc」坑族）。
3. **gpuq 锁内再嵌 gpuq = 自锁死锁**（外层 holder=自己，内层 WAIT 自己，ttl 到期互踢）。正确姿势：后台直接 `bash 链脚本 <slug…>`，外层循环自行逐集 gpuq；给 gpuq 传的 --episode 子命令只含单集步骤。
4. **pgrep -f 自匹配**：`wsl bash -c "pgrep -f 'synth_indextts.py'"` 会匹配到自身命令行 → 永远「gpu busy」死循环。模式加括号技巧 `'[s]ynth_indextts.py'`。
5. **SLF 混写路径**：gpuq 子 bash 里 `$SELF` 若为 D:/ 风格路径，WSL bash 打不开（No such file）；统一 MSYS 风格 /d/... 并在重执行前 `cd /mnt/d/codes/blog-src` 锚定 cwd。

#### 统一服务合并（2026-08-29，看板+详情站同端口）
- `board.py serve`（默认 8765，被占自动 +1 重试并打印实际 URL）现为**唯一服务入口**：`/board.html`（生产看板，页头有入口链接）+ `/site/*`（video-detail-site 详情站）+ `/build/*`（成片 mp4/封面）。Windows 下 `_Server.allow_reuse_address = False`（NT 的 SO_REUSEADDR 允许同端口双绑定 = 多实例静默叠加、请求随机路由，正是「服务冲突」的根因）；双绑定改为显式报错走端口回退链。
- 自写 Handler 分支的事故实录：`send_response/send_header` 只写缓冲，**漏 `self.end_headers()` = 客户端收到无状态行的裸 body**（curl 报 HTTP/0.9）。新增响应分支必须 `end_headers()` 后再写 body。另：do_GET/do_HEAD 绑定要跟 Handler 同在（清理死代码时曾连坐删掉 → 全站 501）。

#### 左侧白板概述轮播（2026-08-29 用户定规，模板已实现）
- **定规**：课件左画布（镜头舞台）不得长时间空白——卡片开场先播「本步概述」：本卡要点逐条大字居中轮换（编号徽章 + 浮入/上升出场，每条 ~1s），轮播结束镜头接棒（镜头出生帧整体后移 max(birth, ov_frames)，不吞入场帧）。
- **镜头内容必须填充画布**：term/quote/stat 加 width:94% + min-height:62% + 字号升档（引言 56px/终端 36px/大数字 170px），禁止小盒子浮在大白面上（修前实录：141s 成片 121s 左画布内容占比 <6%）。
- **定量验收方法**（改模板后必跑）：`ffmpeg fps=1` 抽全片帧 → PIL 裁左画布区（~x65-1140, y105-925 @1080p）→ 统计非白(<235)像素占比，**<6% 连续 ≥3s 即不合格**。EP08 修前 121/141s 不合格，修后仅代码卡外时段达标。
- render-only 复用：改模板/重渲画面无需重合成——audio/sent/align 产物全复用，直接 `video.build`（每集 ~4-6 min）；六集批量用 `bash scripts/video/_run_eng_series_direct.sh`（v2 直跑链，无 gpuq 嵌套）。

---

## 附录：二批搬运（2026-08-30 拆分 pass2）——脚本职责表 / narrate.py 用法 / Windows 实测经验

   **Windows 实测经验（2026-08-17 deepseek-harness-desktop-cli 沉淀）**：
   - **进程名不带 .exe**：`screenshot_app.py --process "cmd"`（`Get-Process` 的 Name 是 `cmd`，传 `cmd.exe` 匹配不到直接 "no window"）
   - **窗口被遮挡是最大坑**：矩形截取用 `CopyFromScreen` 抓屏面上该区域，若目标窗口被编辑器/ZCode 等盖住，截到的是一张**静止黑屏/别人界面**——两帧 diff 为 None 就是截错信号（`ImageChops.difference` bbox）。截前先 `ShowWindow(SW_MINIMIZE)` 移开竞争窗口 + `SetForegroundWindow` 并核对 `GetForegroundWindow()==MainWindowHandle`，截图后两帧 diff 确认画面在变
   - **UIA 自动化（Electron/NSIS 通用）**：按钮常不支持 `InvokePattern` → 用 `BoundingRectangle` 中心 + `mouse_event` 物理点击；文本输入用 `ValuePattern.SetValue`（Electron 输入框可用，比 SendKeys 中文可靠）；`SetValue` 需在 UIA 树按 Name 定位（如「描述你想要构建的内容」）
   - **PS1 脚本用 python 写文件**（`open(...,'w',encoding='utf-8-sig')`），中文要么用 `[char]0x4F60` 十六进制拼接（`-join ([char[]]@(0x4F60,...))`），要么直接 UTF-8 内容——**bash heredoc 写中文 + 引号必被吞**，踩了 3 次
   - **NSIS 安装向导**：`/S` 静默安装在部分环境会卡死不动；交互向导 + 快捷键更稳（Alt+I 开始安装、Alt+N 下一步），每页截图就是教程素材
   - **WinRT OCR 间歇 `Wait` 异常**：转换 `SoftwareBitmap.Convert(Bgra8)` 后重试；小字号终端字体 OCR 读不出是正常的，配合像素 diff / 区域放大验证
   - **教程类「真机实拍」验收（强制）**：装完必须**真配置（填 key）+ 发真实请求（如「你是谁」）等回答后再截图**，不截空壳欢迎页；回答内容（会话标题/token 统计）就是最好的"能用"证据。key 这类敏感信息本机测试可临时用，视频里只教官方申请路径
   - **自动化产物不算真实坑**：TUI 黑屏/窗口不渲染这类由脚本或环境变量引发的现象，要么如实归因（「部分终端环境黑屏，换终端试试」），要么不放——**不许把自动化事故包装成用户会遇到的坑**
脚本已封装进本 skill 目录。`make video` 内部 `cd` 到 `scripts/` 跑 `python -m video.build`。

| 文件 | 职责 |
|------|------|
| `build.py` | 主入口，courseware/graph/legacy 分发，graph 的 acrossfade 音频合并 |
| `palette.py` | 权威画面色板 SSOT（token + 弱化态值 + 对比度配对声明 + 封面 :root 注入源 + 拟物豁免表，openspec video-color-retention）|
| `lint_colors.py` | 色彩机检（对比度分级判定 + 色板外漂移扫描 + Remotion 同步；并入 `make video-lint`）|
| `test_palette.py` | palette/lint_colors 单测（对比度计算/升档回归守卫/封面注入）|
| `courseware.py` | 课件 HTML 模板（`render_frame`；全元素动画编排 + 对 `card["type"]=="tool"` 分发到 screencast）|
| `flowchart.py` | flow 流程图原语（节点弹出/连线生长/跑线扫光/逐字标签，`point_births` 逐节点驱动）|
| `motion.py` | 帧驱动动画数学库（缓动/count-up/typewriter/shimmer + 编舞助手 enter_tuple/settle_dip/glow_mult）|
| `screencast.py` | 屏录感工具界面渲染（`_CONTENT` 各 tool builder + `render_frame`，自带 `python -m video.screencast` 自测出预览）|
| `capture_shots.py` | 抓真实网页截图 + 热点百分比坐标（`realshot` 素材源，产物 `assets/<slug>/`）|
| `cover_vscode.py` | 拟物化 VSCode 封面（复用 `_vscode` 窗口做主体，教程类封面）|
| `graph.py` | 节点图 HTML 模板（`render_frame`，dark/light 主题 + 动效）|
| `timeline.py` | WordBoundary → 分句 + 要点时间轴 + 字幕去标点 |
| `frames.py` | Playwright 逐帧渲染 + 段合成 |
| `tts.py` | edge-tts 合成 + 重试退避 + `normalize_for_tts`（缩写逐字母白名单，见「发音」）|
| `narrate.py` | **通用口播生成**：`split_units` 智能断句 + `generate_narration`（concat filter 拼接，无漂移）+ 单元级时间戳 JSON。任何渲染后端（Remotion/Playwright/FFmpeg）可复用 |
| `render.py` | FFmpeg xfade 视频拼接 + BGM/音效同图混入（`audio_overlay_chain`，单 pass 装配） |
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
