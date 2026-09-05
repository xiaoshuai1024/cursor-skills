# 动画与卡内分镜细则（animation-shots）

> 拆分自 SKILL.md（2026-08-30，openspec video-generation-skill-split），内容逐字保留；动效配方参数另见 motion-patterns.md。

### 动画与特效强制规范（全内容类型，2026-08-25 定规，openspec courseware-motion-linkage）

> 适用于**所有模式的所有内容元素**——不只流程图。courseware 原生元素与 flow 流程图已由管线**零配置自动保障**；其他模式沿用各自动画能力（graph 连线扫描/节点脉冲、Remotion 动画原语+15 种转场、screencast 步骤条+热点三态），分镜阶段按本规范 + checklist ⑦ 自查，缺动画的场景先补能力再拍。

1. **全元素动画（硬性）**：画面中每个内容元素——标题/副标题/标题条/要点/知识卡/流程图节点与连线/代码高亮/图表数字/字幕/进度条/封面 outline——都必须有**入场、换态、强调三类动画至少其一**；任何 >10s 纯静态画面 = 违规返工。静态信息轮播是反例（2s 跳出率 >45% 的根因之一）。
2. **联动（硬性）**：一次讲解节拍（口播分句/要点亮起）必须**同时驱动 ≥3 个元素响应**——主元素（要点弹入）+ 关联元素微反馈（知识卡/流程节点弹出、标题条与进度条辉光脉冲、字幕上滑），反馈在主拍后 0-3 帧内（100-200ms，NN/g 联动窗口）。流程图必须「框、线、文字」三件套同拍：节点弹出（ease-out-back）+ 连线生长 + 跑线扫光 + 标签逐字浮现，讲到哪步动到哪步。
3. **缓动（硬性）**：一切位移/缩放动画必须带缓动曲线，禁止线性硬动。规范值（24fps）：入场 ease-out cubic 300-450ms（7-11 帧）；弹出 ease-out back，overshoot ≤10%；连线生长 ease-in-out sine；**出场 ease-in cubic 加速、150-250ms（4-5 帧），快于入场**（M3 退场规范）；stagger 错峰 50-100ms/项（2-3 帧）。缓动一律从 `motion.py` 取（`ease_out_cubic/ease_out_back/ease_in_out_sine/ease_in_cubic` + 落定/换词档 `ease_out_expo/ease_out_quart/ease_in_quart` + 编舞助手 `enter_tuple/exit_tuple/settle_dip/glow_mult/type_chars`），不自造曲线；选型口径见 `references/motion-patterns.md` A 表。
4. **帧驱动铁律（既有，不可违反）**：禁 CSS animation / @keyframes / wall-clock；一切动画由 `state["frame"]` + 出生帧数学插值（Remotion 侧 `useCurrentFrame`），动画**有界窗口**、窗口外静止（PNG 复用优化）。循环/呼吸类持续动画不进 Playwright 管线。
5. **课件动画写法（零配置）**：courseware 模式的 deck 不需要任何动画配置——口播分句时间轴自动生成每元素出生帧（`frames.py::point_births/cue_birth`），渲染自动带全元素动画；**卡尾 8 帧自动错峰出场**（`out_at` 锚：eyebrow/footer→标题/条→要点/卡片/流程节点→字幕带，ease-in 加速），分句字幕结束自动 4 帧退场（`cue_out`）。**新增内容元素时必须同步接入场+出场动画**（`motion.py::enter_tuple/exit_tuple`），在 `courseware.py`/`flowchart.py` 编舞表登记，不接动画的新元素不许合入。
6. **元素动效配方库（换态强调类，2026-08-26 定规，源 HyperFrames catalog）**：入场/出场之外的第三类动词，数学全部入库 `motion.py`，参数/双管线落法/适用场景见 **`references/motion-patterns.md`**（分镜动画列直接写配方名）——**槽内换词** `swap_pair`（「前端→全栈→AI」身份演变）、**词组 slam 交替入场**（enter_tuple+方向轮换，钩子/结论句）、**数字滚动** `@@countup@@`、**打字机** `@@typewriter@@`、**流光扫字** `@@shimmer@@`、**划线/标记带生长** `grow_scale`（纠偏划旧说法、强调标记带）、**印章拍落** `stamp_tuple`（结论「锤一下」）、**落版白闪** `sting_tuple`（签名句/品牌 outro，白闪恰 1 帧、全片一次）。编舞三条：信封 IN→HOLD→OUT 时长不足按比例压缩 IN/OUT 禁整体加速；出场**位移优先于纯淡出**（纯 opacity 淡出中途帧实测掉到 1.02:1，对比度门禁 3:1 必炸）；换卡**先退后进**（两团文字同屏重叠=返工）。渲染质量门禁五条（文字重叠采样/淡出对比度/动画窗冲突/字体声明/media id）见 motion-patterns.md E 表，候选并入 `make video-lint`。
7. **flow 流程图字段**（insight 卡，与 sub_points 互斥、flow 优先）：
   ```json
   {"type": "insight", "title": "...", "points": ["步骤一", "步骤二", "步骤三"],
    "flow": {"nodes": [{"id":"n1","label":"口播断句"}, {"id":"n2","label":"帧号驱动"}],
             "edges": [["n1","n2"]]}, "footer": "..."}
   ```
   nodes 与 points 一一对应（第 k 拍亮第 k 个节点 + 长出指向它的连线）；未讲到的节点保持虚线幽灵态，已讲节点降权实线——信号原则的流程图落法。`motion.py`（缓动/帧表/编舞助手 `enter_tuple/settle_dip/glow_mult/type_chars`）是两条管线共用的动画数学库，新动画一律从这取缓动，不自造曲线。
### 卡内分镜 shots（2026-08-26 定规，openspec card-shots，每张非 intro 卡强制）

> 病根（本片实测）：单卡口播 15-50s 只有一组一次性入场动画，主画面随后长时间零变化；无流程图的卡主内容区只剩空占位框（约 40% 画面空白挂整卡）。**解法：每张卡按口播句边界切 2-5 个镜头轮换，主内容区永远有实料。**

1. **deck 字段**：每张卡必填 `shots` 数组（**2026-09-05 用户定规取代旧「intro 不加」口径**：intro 卡也要带 2-3 个镜头并给 `points`——`points` 为空会触发 `is_cover` 剥离全部 shots，首屏沦为纯标题静态画面，GPT-6 片首屏 23s 静态实录）：
   ```json
   "shots": [
     {"from_s": 0.0, "kind": "flow"},
     {"from_s": 13.1, "kind": "code", "data": {"title": "文件名", "lines": ["..."], "hl": 1},
      "hl_steps": [[17.8, 7], [21.0, 8]]},
     {"from_s": 23.9, "kind": "quote", "data": {"text": "...", "source": "..."}}
   ]
   ```
2. **7 种镜头**：`code` 源码卡（行号 + 高亮行随讲解推进，`hl_steps` 讲到哪行亮哪行）/ `tree` 文件树 / `term` 终端演示（cmd/out/ok/err/dim 五色行）/ `stat` 大数字卡 / `table` 对比表（首列 `*` 标高亮行）/ `quote` 引文金句卡 / `flow` 流程图（降级为镜头之一，不再独占整卡）。
3. **节奏门禁（硬规则）**：任何镜头停留 **≤15s**；卡 >25s ≥3 镜头、15-25s ≥2 镜头、<15s 1-2 镜头；`from_s` 必须对齐该卡口播**句边界**（`boundaries_*.json` 的 start_ms），禁止句中切；占位符（「讲解中…」）禁止出现在成片。写 deck 后跑节奏自检（镜头 span + 数量下限）。
4. **素材真实性**：code/term 镜头素材必须来自真实仓库文件（如 DSH 片用本地 deepseek-harness 仓的 AGENTS.md、agent.cordis.yml、包名清单），分镜表备注溯源路径；终端演示可重构命令序列但机制必须真实存在，不得虚构源码行。
5. **写 deck 流程步**：每卡产出「分镜表」（时间轴 | kind | 素材内容 | 对应口播句），随 deck.json 一起交付。
6. **实现**：`prism.py::_shots_stage/_shot_html`（prism 白色主管线，2026-09-05 起默认；镜头切换为 slideleft 主流向——新镜头右缘推入、旧镜头左移退场）+ `tutorial.py::_shots_stage/_shot_content`（tutorial 存量管线）+ `frames.py`（每帧算 `shot_idx/shot_birth/shot_t_ms`）。动画：新镜头 8 帧浮入 + 前镜头 6 帧淡出 + 行级 2 帧/行 stagger，帧驱动铁律不变，静止段 HTML 等值（PNG 复用优化保持）。⚠️ 原深色系渲染器随 2026-09-05 管线换代删除（openspec prism-motion-pipeline，用户定规），`courseware.py` 只剩调度器 + mascot 外壳。
7. **from_s 两段式（2026-08-28 定规，配 `_align_shots.py`）**：写稿时 from_s 用「卡内逐句累计 ÷5.5 字/秒」估算即可；**合成后必须跑** `PYTHONIOENCODING=utf-8 py -3.11 scripts/video/_align_shots.py <slug>`，把每卡镜头切点贴到真实句边界（读 `audio/<slug>_t/boundaries_XX.json`，找离估算最近且不早于前一镜 +0.8s 的起点）。禁止拿估算值直接渲染——估算与真实边界偏差实测 0.1-0.5s/句。
