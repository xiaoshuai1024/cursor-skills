---
name: video-generation
description: 把技术博客文章/主题生成为横屏 16:9 视频。三种模式：remotion（默认，数据可视化+真实素材）、courseware（课件，含 screencast 屏录感工具界面子模式）、graph（知识图谱）。edge-tts 配音 + Playwright/Remotion 渲染 + FFmpeg 合成，全本地零收费。含多平台发布（抖音/快手/视频号/B站，头条经抖音同步）。
---

# Video Generation Skill

把一篇技术博客文章 / 一个技术主题生成为**横屏 16:9 视频**。三种程序化模式：

- **remotion（默认）**：数据可视化 + 真实素材——深色科技网格底 + 真实数据图表 + 素材标注，适合发布速报、性能对比、教程步骤（Remotion 管线，`remotion/` 目录）。**默认主题，参照 `after-million-loc-my-skills.mp4`**
- **courseware**：课件式——左栏要点逐条浮现 + 右栏知识卡片（或 flow 流程图逐节点动画）+ 底部字幕带（Playwright 管线）。**全元素动画 + 主锚联动零配置自动带**（2026-08-25 起，见「动画与特效强制规范」）：口播分句驱动每个元素的出生帧，要点弹入/知识卡 spring/标题条与进度条脉冲/字幕上滑同拍联动，flow 卡的节点弹出+连线生长+跑线扫光+逐字标签讲到哪步动到哪步
- **screencast（courseware 子模式）**：屏录感工具界面——**浏览器真实网页截图打底 + 箭头标注是主角**（`realshot`：任何能在浏览器里呈现的步骤都截图，官网 / 市场 / GitHub / 控制台 / 在线编辑器都行），CSS 仿真窗口（VSCode mockup / 终端）只在浏览器截不到时才兜底（本地桌面应用、需登录态的真实界面）。标题栏下方**顶部常显步骤条**（全部步骤：done/active/future 三态），`active_idx` 高亮当前操作 + 光标箭头，对标抖音「录屏+标注」爆款（Ai小白Lab 26.2 万赞）。deck 卡 `type:"tool"` 即触发
- **graph**：节点图/知识图谱——中心辐射布局，节点逐个高亮 + 连线生长，适合概念关系/体系架构（Playwright 管线）

三种模式共用 TTS/断句/字幕规则（`narrate.py`）。数据 → 程序化画面渲染 + FFmpeg 合成。零收费、全本地。配音分两档：**发布视频默认 IndexTTS-2 克隆声（严格标点断句管线，见「默认口播配置：IndexTTS-2 克隆 + 严格标点断句」）**；edge-tts 为快速预览与 fallback。

## 规范文件地图（references 索引，2026-08-30 拆分）

SKILL.md 是工作流骨架；细则按域拆在 references/，章节存根保留原名可检索：

| 文件 | 承接内容 |
|------|---------|
| `references/content-rules.md` | 三要素细则/签名品牌/互动合规矩阵/黄金2秒/抖音红线/精选冲选/完播纪律/讲解呈现/三原则/内容覆盖 |
| `references/animation-shots.md` | 动画与特效七条硬规全文 / 卡内分镜 shots（deck 字段/节奏门禁/_align_shots） |
| `references/tts-narration.md` | 发音/断句/音频同步逐条经验 / 音色标定表 |
| `references/pipeline-engineering.md` | 画面规格/声音层矩阵/mascot 配置/能力缺口/Remotion 关键经验/两份事故清单 |
| `references/cover-metadata.md` | 封面 v2-v4 全规格与像素阈值 / 标题简介话题正反例 / metadata.txt 字段模板 |
| `references/publishing.md` | 七字段矩阵/合规口径/快手v2/B站/全平台确认/挂定时复核/复查闭环/违规清理/成片生命周期 |
| `references/motion-patterns.md` `sound-design.md` `beat-cut.md` `remotion-best-practices.md` `mascot-pose-rig.md` | 动效配方 / 声音设计 / BGM 卡点 / Remotion 官方实践 / mascot 姿态（既有） |

## 目录结构（skill 存代码，产物落项目根）

skill 目录只放可复用代码/脚本/模板。**所有内容配置、渲染产物、临时文件**落在项目根的 `video-generation/`（git 忽略），通过路径自动解析（skill 根向上找 `hugo.toml`/`.git` 定位项目根）。

```
.agents/skills/video-generation/          ← skill：只放可复用代码
├── SKILL.md
├── remotion/                             Remotion 管线（React + Three.js）
│   ├── src/core/                         框架（VideoConfig/VideoComposition/theme）
│   ├── src/primitives/                   视觉原语
│   ├── src/scenes/                       通用场景组件
│   ├── src/videos/                       示例/测试 video configs（dummy/showcase）
│   ├── remotion.config.ts                webpack alias @videos + @skill-src
│   └── scripts/render.ts                 渲染入口
├── scripts/video/                        Playwright 管线核心模块
│   ├── config.py                         OUTPUT_ROOT = 项目根/video-generation
│   ├── build/courseware/graph/...        build/narrate/timeline/frames/render/tts
│   ├── screencast.py                     屏录感工具界面渲染（courseware `type:"tool"` 分发）
│   ├── narrate.py                        通用口播生成
│   ├── assets/                           skill 内素材（预留）；BGM/SFX 素材在项目根 video-generation/narration/（gen-sfx.py 生成）
│   ├── narrate_*.py                      各 Remotion 视频口播生成
│   └── probe_*.py                        TTS 发音探针

video-generation/                        ← 项目根：所有内容配置 + 渲染产物
├── narrations/<slug>.json                口播文案（voice/rate/cards[]）
├── deck/<slug>/deck.json                 Playwright 课件卡片定义
├── deck/<slug>/deck-graph.json           Playwright 节点图定义
├── narration/                            Remotion 口播 mp3 + 时间戳 json
├── remotion-videos/<id>/                 Remotion 内容视频实例（config.ts + narration.ts）
├── build/<slug>/                         成片统一目录：<slug>.mp4 + 同目录 <slug>_cover.png + metadata + 音视频分段（out / covers 已弃用）；只放待发布与在售视频
├── archive/<slug>/                       已发布视频归档（只进不出，登记见 archive/README.md）
├── sent/<slug>/                          已交付口播分句库（cXX_sYY.wav/.txt + meta.json）
└── probe/                                TTS 发音探针输出
```

## 何时用

- 把博客文章转成横屏知识/培训讲解视频（B站知识区、YouTube、在线课程风格）
- **默认 remotion**（数据可视化 + 真实素材）；概念关系/知识体系/架构拓扑 → **graph**；线性课件讲解 → **courseware**
- **教程/操作/选型类要对齐抖音「录屏+标注」爆款** → **screencast**（courseware 子模式，`type:"tool"` 卡）
- 需要「讲到哪、信息跟到哪」的跟随感（非静态卡片轮播）

## 内容驱动设计（强制，先于管线选型）

**先判定文章内容类型，再选管线/结构，禁止默认套模板。** 结构由内容派生，不是由管线决定：

| 内容类型 | 判定信号 | 推荐结构 |
|---------|---------|---------|
| 清单 + 流程 | 按阶段/顺序逐组列举实体（如「研发生命周期 6 组 skill」） | **阶段递进**：阶段导航 + 组内条目卡片，按流程主线逐阶段推进 |
| 榜单 / 排行 | 有可量化排序（GitHub Star、性能分） | 排行榜（LeaderboardChart）+ 逐条卡片 |
| 对比 / 选型 | 两两对照、决策树 | 对比表 / 选型原则 |
| 概念 / 体系 | 概念关系、心智模型 | 概念图 / 中心辐射（graph） |
| 教程 / 步骤 | 线性操作步骤 | **screencast**（`type:"tool"` 卡）：拟物化真实截图/工具窗口 + 箭头标注，对齐抖音「录屏+标注」|

- **判定方法**：读文章标题 + 章节大纲 + 主体结构（`##` 标题怎么组织），判断主线是「顺序推进」还是「并列概念」还是「量化排序」
- **配图密度**：随篇幅分档（2000-4000 字 ≥2 张图），但视频不套用此配额——视频按场景数保证信息密度
- **反例（本 skill 踩坑）**：清单+流程型文章（百万行 Skill 分组）被套 graph 中心辐射模板，阶段被降为并列卫星节点、每条 skill 的「管什么」无承载。修复：阶段递进布局 + 每阶段 skill 卡片（`SkillStage` 场景）

## 内容创作规范：开头 · 呈现 · 互动（数据驱动，2026-08-17 定规）

### 视频三要素（2026-08-24 用户定规，每条视频强制，优先级高于本节其余技巧）

① **提问式开头**（引导语固定「问你一个问题」/「你有没有想过」二选一，问题 ≤20 字、正文必回答）② **钩子设计且必须消费**（钩子→回收映射表，无回收点的钩子不许埋）③ **BGM + 音效 + 转场**（六情绪档/四类音效/15 种转场，管线零配置自动带）。开拍前先对照 `make analytics-report` 产出的运营 directives。**三要素逐条展开与 directive 自查法见 `references/content-rules.md`。**
**每支视频成片前 checklist（2026-08-24 定规，⑧⑨ 为发布前门禁；任一不过先改稿/改 config）**：

- [ ] **① 提问式开头**：第一句口播 = 固定引导语（「问你一个问题」/「你有没有想过」二选一）+ ≤20 字问句（痛点/反常识，无「凭什么」）；该问题在正文有明确回答（记下回答的时间码）
- [ ] **② 钩子已埋**：钩子→回收映射表已附（编号 + 埋点时间码），含标题暗示的隐性钩子也入表；表为空 = 重写开头；**「15s 兑现位」列非空**（前 15 秒内兑现的硬信息位置——数字/结论/对比至少其一，openspec douyin-featured-selection）
- [ ] **③ 钩子已消费**：映射表每行的回收时间码非空——没回收点的钩子不许埋；每个回收时刻有视觉强调（字卡 / 高亮 / 专属音效至少其一）
- [ ] **④ BGM**：分镜表 BGM 列逐场景非空，情绪档在六档内（tense/walk/focus/bright/epic/calm）；章节换档处标了情绪切换点
- [ ] **⑤ 音效**：开场音、提问音（`questionFrames` 全片 2~4 个）、章节转场音、关键动作音（安装成功/报错/打字等）四类全覆盖，config 的 `sfx` 段落齐全
- [ ] **⑥ 转场**：分镜表转场列逐场景有类型（15 种之内），章节边界必设；同章节内不滥用（硬切省预算）
- [ ] **⑦ 内容动画**：deck 卡片入场 / 代码高亮 / 图表数字生长 / 字卡弹出至少覆盖主要场景，无 >10s 纯静态画面（对齐 M1：每 5-10 秒一个视觉变化）；「内容动画继续」= 动画在内容推进全程持续，不许只做片头。**全元素 + 联动硬规**（2026-08-25）：每个内容元素有动画（入场/换态/强调至少其一），每次讲解节拍联动 ≥3 元素、反馈 ≤3 帧，流程图框线文字三件套同拍——细则见「动画与特效强制规范」
- [ ] **⑧ Metadata（标题/简介/话题，发布前查）**：
  - **标题**：过 metadata-optimizer 7 项清单（可识别实体/真实数字/清晰动词/后果人群/标点转折/权威钩子/概念包装）**≥4 合格**；事实边界——素材里没有的事实（刚刚/首个/第一/榜单数字）不得出现；平台变体（`标题_抖音` 等）不超该平台 title_max（抖音 30 / 快手 50 / B站 80 字）
  - **简介**：首句三拍（当前不适 → 更好愿景 → 行动路径）；结尾含互动问题；公众号 digest ≤129 字
  - **话题**：用 topic_suggest 推荐后再定（不拍脑袋），各平台数量不超配额（抖音 4 / 快手 3 / B站 6 / 视频号 10）
  - **门禁**：`make metadata-lint slug=<slug>` 跑到绿（FAIL 项必修：硬截断/词中断/结构红线；WARN 酌情）；发布文案再过 platform-compliance 违禁词扫描
- [ ] **⑨ 互动引导（发布前查，openspec video-engagement-cta）**：主 CTA 已按内容类型选定（教程/工具/避坑→收藏、观点/拆解→点赞、B站→三连）；结尾四段结构就位（单动作引导在签名句之前、价值锚定 ≤15 字、互动段 ≤10s、**CTA 句字幕默认在场**）；平台变体过「平台 × 露出面」矩阵（抖音全链路无「评论区」三字、无「点赞关注」连用、简介无动作指令词；视频号无转发引导）；置顶评论文案已备稿（发布后 1h 内发）
- [ ] **⑩ 完播纪律（冲精选，openspec douyin-featured-selection）**：选题三问有档（获得感/惊喜感/共鸣感，全空 = 重做选题）；成片 ≤120s（120-150s lint WARN、>150s 无「豁免_时长」**FAIL 拒发**，豁免填拆系列论证）；前 15s 硬信息兑现位在钩子映射表有标注（见 ②）

> 执行时机：①-③ 口播稿定稿时查，④-⑥ 分镜/config 定稿时查，⑦ 渲染前 deck 检查，⑧-⑩ 发布前查（⑩ 的选题三问在定稿时查、时长在成片后查）；与 directives 自查同批做。自查通过 ≠ 可渲染——checklist 全过后还须过「渲染前用户确认」门禁（完整稿呈用户审阅，见「规则约束 → 渲染前用户确认」）。

> **发布窗口（2026-08-26 用户定规）**：视频一律 **晚上 20:00 发布**，不再中午发（渲染/自查可在白天完成，定时任务挂 20:00 出片）。黄金档依据：晚 8 点是各平台流量峰，中午发完播数据持续偏低。**定时用平台侧 `--schedule`**：`py -3.11 -m scripts.pub.publish --slug <slug> --platforms douyin --confirm --schedule "YYYY-MM-DD 20:00"`（抖音服务器定时发布，电脑休眠/会话结束不影响；白天挂好晚上自动出片——不要用本地 cron/长等待方案）。注意本机 PATH 的 `python` 指向 hermes venv（无 patchright），发布一律 `py -3.11`。**发布流程 = 白天挂定时 → 20:00 出片 → 归档**（2026-08-26 补定规）：**四平台挂全才算「定时挂好」**（2026-08-27 定规：抖音/快手/B站/视频号一个不少、不分先后，收尾自检见「全平台发布与逐平台状态确认」，只挂了部分平台不许归档收尾）；定时挂好即归档本视频相关、tasks 已全勾的 openspec 变更（移入 `openspec/changes/archive/YYYY-MM-DD-<name>/`），不留尾巴。

> **状态台账（2026-08-28 起，video-pipeline-tracker skill）**：流程节点必须用 `vpt` 记录状态（SSOT `data/video-pipeline/state.json`，多任务窗口共享，看板 `data/video-pipeline/dashboard.md` 自动重生）——渲染完成过门禁 → `make vpt-` 前置 `cd .agents/skills/video-pipeline-tracker/scripts && py -3.11 vpt.py stage <slug> rendered`；四平台定时挂好 → `vpt.py stage <slug> scheduled --schedule douyin=YYYY-MM-DD\ 20:00 --schedule kuaishou=... --schedule bilibili=... --schedule shipinhao=...`；出片（平台侧回读确认）→ `vpt.py stage <slug> published`；归档 → `vpt.py stage <slug> archived`；任何卡点 → `vpt.py stage <slug> <当前stage> --block "原因"`。台账与现实漂移时 `vpt.py sync <slug>` 从目录/link-map/快照推导校正。

> **每日一篇原则（2026-08-27 用户定规，优先级最高）**：**每天 20:00 只发布一个视频**；已有定时排队的视频，新片往后排队到第二天 20:00。定时挂好前先查队列（抖音创作中心「定时发布」tab 有无当日卡）；发布冲突时用「修改定时」顺延旧卡（比删除重传温和——不用 build 目录来回搬），删除/取消定时后再归档的走 README 变更日志登记。**实战教训（同日沉淀）**：① 抖音定时卡会重复积累（同一视频多次提交各占一卡），撤卡后必须用只读清单复核到 0 才算撤干净；② **上传器日志虚报实锤两处**——`douyin_delete_scheduled.py` 报「删除成功」实际没删（DOM 匹配失效）、publish 报 `ok:true` 但快手卡没挂上——**一切以平台侧回读为准**：抖音用 check_status、快手/B站/视频号进管理页实读卡片与「定时发布中」标记；③ `publish.py` 的结果回收是**整条覆盖** link-map（单平台补发会冲掉其他平台历史记录，已人工修复一次）——补发后核对 results 完整性，待修合并逻辑；④ B站验证双轨：网页 cookie（`bilibili.json`，会过期）与 biliup 登录态（`biliup login` 写入的 cookie_info 格式，SESSDATA 长效）是两套——网页跳扫码页 ≠ 投稿失败；用 biliup cookie_info 的 SESSDATA 提取后以完整属性（domain 缺省 .bilibili.com、secure、sameSite）挂浏览器进管理页实读即免扫码核验；B站公开搜索（标题+发布时间+播放数）是无登录旁证；⑤ 无 TTY 环境（后台任务）跑 `biliup login` 直接退出且二维码不可见——B站重新登录必须真实终端前台跑 `~\.social-auto-upload	oolsiliup\windows-x86_64iliup.exe -u scripts\pub\cookiesilibili.json login`（PATH 里的 pip 同名 biliup 是另一个包，勿用）。

### 签名与品牌露出（2026-08-24 用户定规，与三要素配套执行）

开头不放自我介绍；结尾最后一句固定 **「我是1024工程笔记，越基础的东西，越值得讲透。」**（「1024」= 逐位「一零二四」，读法已固化进配音链）；签名句前允许平台合规求关注（B站可硬 / 抖音快手价值锚定软表达且禁与点赞连用 / 视频号禁转发）；品牌由右下角伴随机器人承担、**不加常驻文字水印**。完整定规见 `references/content-rules.md`。

### 互动与转化引导（合规矩阵，2026-08-24 定规，openspec video-engagement-cta）

结尾四段结构「价值兑现 → 互动问题 → 单动作引导 → 签名句」，一次只引导一个动作、互动段 ≤10s；主 CTA 按内容类型轮换（教程/工具/避坑→收藏、观点/拆解→点赞、B站→三连）；**抖音全链路禁「评论区」三字、禁「点赞关注」连用、简介禁一切外链**；动作引导句默认带字幕（敏感期 `〖无字幕〗` 标记降险）；发布后 1h 置顶评论 + 24h 承接。**私域承接（2026-08-30 定规）**：抖音置顶评论挂**粉丝群站内链接**——账号级常量 `scripts/pub/config.py::DOUYIN_FAN_GROUP_URL`（从抖音 App 群分享页复制），`douyin_pin_comment.py` 发置顶评论时自动挂尾（留空不挂、文案已含不重复）；站内链接不是外链，不触简介外链红线，其余平台暂无私域承接。**平台 × 露出面矩阵、话术对照、〖无字幕〗管线支持、`简介_平台`/`置顶评论` 字段与资料型互动合规写法见 `references/content-rules.md`。**

### 开头：抓住黄金 2 秒（强制）

禁静态标题页开场；痛点前置 / 提问+数据反差 / 结果前置三选一；「问题-答案」结构贯穿全片；第一句 ≤20 字含具体钩子。**首帧三件套（2026-08-25 定规，强制）**：① intro 卡禁纯标题（首帧必须有动态元素）；② 首帧与封面同源；③ 钩子词 2.5s 内出口。句式与数据依据见 `references/content-rules.md`。

### 抖音审核红线（2026-08-17 事故沉淀，强制）

「评论区 + 指令动词（报/扣/发/搜）」结构口播/字幕/封面/简介/metadata 全链路硬禁，引导互动改选择题/站队句；极限词（第一/最强/暴涨/天花板）技术语境也避；**胜负宣言 + 挑衅反问点名竞品是引战风险源**（用数据陈述代替胜负判决）；被判违规走创作者服务中心申诉。细则见 `references/content-rules.md`。

### 抖音精选冲选（2026-08-27 调研定规，openspec douyin-featured-selection）

官方标准只有**惊喜感 / 获得感 / 共鸣感**三维度（无量化门槛，不臆造）；**原创是硬门槛**；选题三问全空重做选题；完播是入场券；AI 规范标注（2026-08-30 双声明）不影响精选。细则见 `references/content-rules.md`。

### 完播率优化：价值钩子前置 + 结论先行（2026-08-17 专家建议，强制）

前 3 秒放最精彩的（❌ 禁过程性开场）；结论先行（开头给 3 个核心收获清单）；首句即价值承诺；30 秒点题检查。**冲精选期完播纪律**（H1 答案半句前置 / H5 删第 2-3 句过渡 / 15s 硬信息兑现位）与**时长分档**（主力精选档 120-180s 缺省 / 深度长档 ≤240s 硬顶 / **>240s 禁止单片**；lint >150s 无「豁免_时长」FAIL）见 `references/content-rules.md`。

### 讲解呈现：把抽象变具象（强制）

代码动态高亮（优先做）/ 流程图必须动起来（❌ 整图一次铺出）/ 概念卡片化 / 术语翻译成人话 + 类比配图示 / 数据图表化（数字必须真实来源）/ 错误场景视觉预警 / 对比呈现落到怎么选 / 故事化场景代替干讲 / 进度条 + 章节导航 / 视觉锚点 / 结尾问题做成视觉卡片 / 防信息过载与单调背景。逐条细则见 `references/content-rules.md`。

### 讲解逻辑三原则（课件呈现的底层依据，2026-08-25 调研定规）

**问题先行**（卡片标题优先写问题句，答案作揭示）/ **信号原则**（同一时刻只高亮当前讲解点，future/done 降权）/ **时间接近原则**（口播分句驱动动画出生帧，讲到哪动到哪）。依据与落法见 `references/content-rules.md`。

### 动画与特效强制规范（全内容类型，2026-08-25 定规，openspec courseware-motion-linkage）

1. **全元素动画（硬性）**：每个内容元素必有入场/换态/强调至少其一，>10s 纯静态 = 违规返工
2. **联动（硬性）**：一次讲解节拍同时驱动 ≥3 元素、反馈 ≤3 帧；流程图框/线/文字三件套同拍
3. **缓动（硬性）**：一切动画带缓动曲线，一律从 `motion.py` 取（入场 ease-out 300-450ms、出场 ease-in 更快、stagger 50-100ms），禁自造曲线
4. **帧驱动铁律**：禁 CSS animation / @keyframes / wall-clock，一切由 `state["frame"]` 插值、窗口外静止
5. **课件零配置**：courseware 口播分句自动生成出生帧；新增内容元素必须同步接入场+出场动画（`motion.py::enter_tuple/exit_tuple` + 编舞表登记）
6. **换态强调配方**（swap/countup/typewriter/shimmer/grow/stamp/sting）参数见 `references/motion-patterns.md`；编舞三条（禁整体加速/位移优先于淡出/换卡先退后进）与渲染门禁五条同文件
7. **flow 字段格式与实现细则见 `references/animation-shots.md`。**

### 卡内分镜 shots（2026-08-26 定规，openspec card-shots，每张非 intro 卡强制）

每张非 intro 卡必配 `shots` 镜头序列（`code/tree/term/stat/table/quote/flow` 七种）；**任何镜头停留 ≤15s**（卡 >25s ≥3 镜头、15-25s ≥2 镜头）；`from_s` 必须对齐口播句边界——**合成后必须跑 `_align_shots.py <slug>` 贴真实边界，禁拿估算值直接渲染**；code/term 素材必须真实可溯源；占位框禁止出现在成片。deck 字段格式、节奏门禁与实现见 `references/animation-shots.md`。

### 价值与互动：可带走 + 留讨论钩子（强制）

可带走价值**外链分平台**（B站简介可附原文链接；抖音/快手/视频号简介禁外链，改纯内容表述）；结尾选择题引导站队；内容埋点留思考题；提问要具体 + 给回应承诺（24h 内兑现）；动作引导合规边界见「互动与转化引导」。细则见 `references/content-rules.md`。

### 管线能力缺口清单（规则先行，能力补齐前先验证再依赖）

部分规则管线未完整支持（代码逐行高亮/错误态样式/迷你进度条/比喻图示/问题卡片/换态动效接点）——用到先核对，不要当现成能力；已确认支持能力清单同见 `references/pipeline-engineering.md`。

### 外部素材与 BGM 卡点（stock-footage / beat-cut，2026-08-29 接入，openspec openmontage-knowledge-port）

按场景触发、不是默认启用：实拍空镜 B-roll 调 stock-footage skill（溯源三件套、进片静音）；BGM 卡点（片头钩子/榜单快剪/签名句 sting，**全片不卡点**）走 `beatgrid.py` 出 audiomap、config 加 `beat` 字段才启用；验收 `verify_render.py --transition-check / --caption-check` 强制。触发场景与红线见 `references/pipeline-engineering.md`、方法论见 `references/beat-cut.md`。

### 内容覆盖（强制，文章→视频的完整性）

视频必须覆盖**文章提及的所有条目/插件/skill/关键实体**——每个条目的「它是什么/能做什么」必须出现，光在榜单里一行闪过不算；判定方法 = 关键实体清单逐条核对。反例与排行类完整结构见 `references/content-rules.md`。

### 效果验证

新视频发布后观察：**2s 跳出率 < 40%**、**评论率**相对前 10 条均值提升；未达标先复查第一卡是否静态、结尾是否缺提问（归因顺序见 `references/content-rules.md`）。

## 依赖

| 依赖 | 用途 | 安装 |
|------|------|------|
| edge-tts | 免费 TTS（Azure 同源中文声音）+ 词级时间戳 | `pip install edge-tts` |
| Playwright | 程序化画面逐帧渲染 | `pip install playwright`（chromium 本机已有）|
| FFmpeg | 音视频合成 | 已装 |

## 规则约束（强制，违反即错）

### 渲染前用户确认（强制门禁，2026-08-25 定规）

- **门禁时点**：分镜脚本（deck.json / deck-graph.json / config.ts 的场景与动画设计）与口播稿（narrations/<slug>.json / narrate_<slug>.py）**完整成稿后、执行任何合成与渲染命令之前**（`synth_indextts.py` 长耗时克隆合成、`make video` / `make video-remotion` / `pnpm render` 等全部算），必须把两份**完整内容**呈给用户审阅：
  - **完整口播稿**：逐句全文（含开头问句、钩子/回收/SFX/BGM/转场内联标记、结尾四段），不是摘要或大纲
  - **完整分镜脚本**：逐卡/逐场景列出（画面内容与要点、动画设计、BGM 情绪档、音效触发点、转场类型三列）
- **确认后才渲染**：用户明确回复确认后才能开合成/渲染；用户提修改 → 改完**重新呈完整稿复审**，循环直到确认。IndexTTS 克隆合成耗时长且改稿即作废，务必在确认后跑。
- **整批授权口径（2026-08-28 补充）**：用户对一批视频给出明确的「依次产出/写完直接渲染」指令时，视同该批的确认门禁通过，不再逐支停下来等审；但批内任何一集的口播或分镜在此之后发生内容改动，该集仍按完整复审规则重来。
- **❌ 禁止**：跳过确认直接渲染；只呈摘要/要点清单就当已确认；先渲染后补审；把 checklist 自查通过当作用户确认。
- **例外（免复审）**：渲染技术失败重试、管线/代码 bug 修复、内容零变更的重渲（如纯补封面）无需重新确认；但口播或分镜**改了任何一处内容**，必须重新过审再渲染。

### 画面

横屏 16:9 1920×1080；courseware/graph/screencast 版式与 dark/light 主题规格；**拟物化方向（教程类强制）**：能浏览器截图的一律 `realshot` 截真实网页，CSS 仿真只兜底；**内容事实校验**（star 查 GitHub API / 包名 `npm view` / 下载地址必须写进画面）；官网截图 `wait_until="commit"` 兜底；平台合规（禁自问自答设问句，画面里也不能出现）；tool 卡内容全透传、新增内容不硬编码进 builder。**完整版式规格与踩坑实录见 `references/pipeline-engineering.md`。**

### 色彩可读性（2026-08-25 定规，openspec video-color-retention）

- **色板单一来源**：全部颜色以 `scripts/video/palette.py`（SSOT）为准——品牌主青 `ACCENT #22d3ee`、深底 `BG_DARK #0a0e1a`、课件中明度底 `BG_COURSEWARE #1e293b`（抗强光既定设计）、亮色系 `LIGHT_ACCENT #2563eb` / `LIGHT_MUTED #64748b`、副色紫/橙/红/黄沿封面主次制。Remotion `theme.ts` 默认值与 palette 逐项对齐（旧默认青 `#00d9ff` 已退役，全 src 禁残留）；封面横竖模板 `:root` 由 `cover.py` 构建期从 `palette.cover_root_css()` 注入，**禁手改模板色值**。
- **对比度分级下限**（`make video-lint` 机检，声明在 `palette.PAIRS`）：正文/字幕 ≥4.5:1；≥24px 大字与**弱化态**（未讲/未来/注释）≥3.0:1。弱化态「未讲 ≠ 不可见」——户外强光下低对比文字最先消失（2026-08-25 实测升档：课件未讲 ≈1.9→5.5:1、图谱 future ≈2.1→4.4:1、代码注释 4.0→7.4:1），升档值与正常态保持 ≥2:1 主次比，层次不丢。
- **强调色用量规约（防刺眼，管用量不改色值）**：主青限强调用途（高亮态/边框/图表系列色/进度条），**禁做正文长文本色、禁大面积实填充（单屏 ≤15%）、同屏辉光元素 ≤2 个**；面板底一律用深底/白 alpha，主色只画边框与状态标记。
- **状态双通道（色盲安全）**：错误红/成功绿不许仅靠颜色传义，必配 ✗/✓ 或形状差异（CodeBlock token/hardcoded 行自带 ✓/✗ 前缀，CodeAuditScan/Annotation/AntiPatternWall/教程步骤条已达标——新增状态场景照此办）。
- **新增颜色流程**：先登记 `palette.py`（品牌色进 token 区 / 拟物仿真色进 `EXEMPT` 写明理由），文字色同步进 `PAIRS` 声明配对与阈值，再进模板——`lint_colors.py` 对四个 Python 模板 + 封面模板做「色板外漂移」扫描，未登记色值直接 FAIL；palette 改 token 后模板旧字面量也会失配被拦下。单测 `python -m video.test_palette`。

### 发音（重要决策，多次试听迭代确认）

> ⚠️ **默认口播 = IndexTTS-2 用户声克隆，不是 edge-tts（2026-08-25 定规，违者返工）**：正式视频一律走克隆链（`synth_indextts.py --emo dyn` → assemble → shrink，全节见下「默认口播配置」）；edge-tts **仅是克隆链不可用时的 fallback，必须先向用户说明并获准**。`narrations` 的 voice/rate 只在 fallback 生效——渲染前 checklist 必查：**口播是否为用户克隆声**。

- 缩写读音：`normalize_for_tts` 白名单只留错音词（当前 `{DOM, AI}`，AI 必须逐字母 "A I"）；TUI 大小写通吃、探针必须用口播原文；**量词「行」克隆声误读 xíng——写稿期一律改「条」或删量词**，定稿前 grep `那行|一行|通知行|多少行` 自查；❌ 不靠整体提速补偿、❌ 不用中文谐音替换
- rate 用 `+8%`；逐条权衡经验见 `references/tts-narration.md`

### 断句（`narrate.split_units`，避免误切）

标点拆意群（永远对）→ 超长才字数硬切，阈值 **24**（❌ 不要 18）→ 英文词块整体切 → 尾部短词(<6字)回并上一句。**写稿源头保证每个标点分句 ≤24 字**（英文词块含空格计数），避免硬切破词。经验与踩坑见 `references/tts-narration.md`。

### 音频同步（架构约束，违反即错）

narrate 管线：逐意群合成 + ffmpeg **concat filter**（❌ 禁 demuxer `-c copy`——encoder padding 累计漂移；❌ 禁两次合成）；courseware/graph：**xfade + acrossfade 一一对应**（总时长 = sum(dur) − (n−1)×0.8；❌ 禁 concat + `-shortest`——字幕早 0.8s 踩过）。验收标准（偏差 <0.01s）见 `references/tts-narration.md`。
  - ❌ 简单 concat 音频 + `-shortest` mux：字幕比声音早 0.8s，逐段累计（已踩坑）

### 声音层与转场（BGM/音效/转场全管线自动，2026-08-23 接线定规）

**所有管线零配置自动带 BGM + 音效 + 转场**；BGM 按口播关键词自动选情绪档（八档：calm/walk/focus/bright/tense/epic/chiptune/lofi）；SFX 场景×氛围矩阵按 mood 自动选变体——**双源纪律 `config.py::SFX_SCENARIO_MATRIX` ↔ `sound-points.ts::SFX_SCENARIOS`，`make video-lint` 机检漂移**；素材缺失自动重跑 `gen-sfx.py`；验收 `verify_render.py`（混音 mean −20~−30dB + 字幕活性 + 切点检查）。**八档情绪表、12 语义场景矩阵、选配速查与教训沉淀（归档前必须 grep 实际代码确认接线）见 `references/pipeline-engineering.md` 与 `references/sound-design.md`。**

### 形象伴随层（机器人 mascot，2026-08-24 接线，video-mascot-narration）

零配置自动启用（`config.mascot` 未声明即开），右下角常驻终端小子；表情按字幕关键词自动推断（命中才切、段内不闪切，手工 `moodTimeline` 可覆盖）；**默认 `position: "bottom-left"` + `height: 240`**（四平台信息流右缘被互动栏覆盖，左下是净空角——2026-08-25 换边定规；场景左下有核心内容降 210，禁超 270）；验收 `verify_render.py --mascot-check`；封面 `mascot.svg` 与 `MascotFigure.tsx` 双份同步约束。配置项、遮挡调优与迭代参考见 `references/pipeline-engineering.md` 与 `references/mascot-pose-rig.md`。

### 字幕
- **意群单元级**（不是句级）：`split_units` 拆成的短意群，每次显示一个完整短句，按单元时间戳跟随口播
- **单行**：去中文标点，不截断、不加省略号；超屏的句子应在 `split_units` 阶段拆短，不在渲染时截断
- ❌ 不要整段铺开、不要句级长字幕（超屏）

> 文章→视频的内容完整性规则（关键实体全覆盖）见 `references/content-rules.md`「内容覆盖」。

### 工程
- **全本地零收费**：仅 edge-tts + Playwright + FFmpeg
- **GPU 渲染排队（2026-08-28 重做，Redisson 式看门狗锁，openspec gpu-queue-lock-watchdog）**：任何视频生产批（`synth_indextts.py` 合成、`make video` 渲染链）开工前必须**整链包裹**进排队器——`PYTHONIOENCODING=utf-8 py -3.11 scripts/video/_gpu_queue.py run <owner> -- <整条命令>`（生产链脚本已内置 exec 自包裹，直接跑脚本即可），**禁止一次性 `acquire` 后裸跑**。机制：锁目录 `video-generation/.chain/gpu.lock`（临时目录写齐 token/lease_ts 后 rename 原子落位）+ 持锁进程内看门狗线程每 60s 续写租约（TTL 180s，自我守护）+ **停摆过期接管**（进程死→看门狗随死→最长约 3 分钟内等待者接管；接管前强制过 WSL 合成探测门槛——死 holder 的孤儿合成仍在占卡时不许抢；rename 独占+证据留痕）+ token 令牌化释放（错令牌 RELEASE-SKIP，误删不了新锁）；续期连续 3 次失败或 token 易主 → LEASE-LOST fail-closed 终止工作链。队列账本 `.chain/queue.jsonl`（WAIT/WAIT-STILL/ACQUIRE/RELEASE/STEAL/RENEW-FAIL/LEASE-LOST/RESTORE 全程留痕）；`gpuq status` 随时查持锁者与租约剩余；`acquire/renew/release` 仅手动调试用（租约=单 TTL，超时未续约会被接管）。对不走锁的外部合成任务 WSL pgrep 探测避让不变（先来先服务；探测连续 3 个周期失败按放行降级）。**事故存档 2026-08-27**：本链 ep3 与另一会话 token-saving-skills 合成同挤一张 8GB 卡，迭代从 6s/it 飙到 22s/it 后 WSL 整体重启双杀两任务——多批次并行前一律进队。**事故存档 2026-08-28（v4 判活失效→重做根因）**：tasklist 判活解析方向反了（有匹配时输出反不含 `: `）+ 一次性 acquire 拿锁即退致 owner.pid 恒死，「45 分钟死锁自救」退化成 45 分钟最大租约（账本实锤：humor-pilot 07:39:40 ACQUIRE → 08:24:50 被 STEAL），render 阶段无探测兜底可复刻 ep3 挤卡——遂重做为看门狗锁；锁语义自测 `py -3.11 scripts/video/test_gpu_queue.py`（隔离临时目录，不碰真实锁）。
- **批量生产链（2026-08-28 沉淀）**：多支视频串行产出一律走 `bash scripts/video/_run_series_chain.sh`（slug 列表在脚本头，按需改）——每支自动执行 synth(WSL)→assemble→shrink→align→render→cover→covercheck，全程状态落 `video-generation/.chain/status.jsonl`，失败不阻塞后续（标 failed 继续跑完），配合排队器天然与外部任务共存。单支重跑照抄链内 run_step 顺序即可。
- **视频生产看板（2026-08-28 定规，openspec video-board）**：`data/video-pipeline/board.html` 实时看板——GPU 队列横幅（持锁者/租约剩余/等待者/近 24h STEAL·LEASE-LOST 告警）、渲染中卡片（7 步骤链状态点 + synth 句进度/render 段进度 + 步骤耗时）、排队/阻塞、已渲染库存、20:00 排期（同日冲突标记）+ 四平台状态、近两日播放/涨粉/完播数据（timeseries.db）、归档表；机器读同目录 `board.json`。**实时**（2026-08-29 端口合并）：看板页由 8901 全生命周期控制台承载——`make video-preview-serve` 起一个端口，`/board`（看板页，请求前惰性重生成 board.py）+ `/board.json`（数据）+ `/console`（控制台首页含 GPU 队列/渲染进度横幅）+ `/v/<slug>` + `/narration-console/`；原 `make video-board-serve`（8765）退役，调用时提示并自动起 8901。链步骤与 gpuq 锁事件仍各自触发重生成（事件后感知 ≤5s）；直开 file:// 退化为 5s 整页重载兜底，手动一次性出板 `make video-board`。看板是旁路：单源缺失降级不炸板、钩子异常不阻塞生产链，`GPUQ_NO_BOARD_HOOK=1` 可禁重生成钩子（自测用）。
- **字数→时长系数（2026-08-28 实测标定）**：成片秒数 ≈ 口播中文字数 ÷5.5 × **1.25–1.31**（含 TTS 停顿垫、句间 0.24s、xfade 折算）；预算 120–180s 主力档 ⇒ 口播 **620–950 字**。合成前后偏差实测 ±3%，**门禁以 ffprobe 实测成片时长为准**（metadata-lint 直读 mp4），字数只是预算工具。
- **Windows 编码**：文件 I/O 显式 `encoding="utf-8"`，子进程 `PYTHONIOENCODING=utf-8`
- **edge-tts 间歇 NoAudioReceived**：`synth_with_boundaries` 必须带指数退避重试（服务端间歇抽风，非代码问题）。整批失败（make video Error 1）多为同一时段服务抽风——**直接重跑 make，一般 2-3 次内过**，先别怀疑内容
- **Makefile video target 用 `$(PYTHON_PW)` 不是 `$(PYTHON)`**（2026-08-17 修）：`.venv` 无 playwright/edge-tts，Windows 用本机 Python311（`PYTHON_PW`），否则 `ModuleNotFoundError`
- **变量命名**：避开 JS/Python 内置（不用 URL/name/status/data）
- **去 AI 味**：口播文案写作去套话水词（参见 **de-ai-smell skill**，唯一权威）；**禁词（2026-08-03 定规）：兜底、铁证、说白了、先说、根子、扎眼**——口播一律不出现，写完整稿后跑 `make check-ai-smell path=...` 扫一遍

## 工作流

```
deck.json / deck-graph.json（内容）+ narrations/<slug>.json（口播 cards[]）
        ↓ 【用户确认门禁】完整口播稿 + 分镜脚本呈用户审阅，明确确认后才能进入合成/渲染
          （见「规则约束 → 渲染前用户确认」）
        ↓ make video slug=<slug> [mode=courseware|graph] [theme=dark|light]
[TTS+WordBoundary] → [timeline 分句+字幕去标点]
        → [Playwright 逐帧渲染] → [xfade 视频拼接 + acrossfade 音频合并 + BGM/音效同图混入]
        ↓
video-generation/build/<slug>/<slug>_<theme>.mp4（1920×1080）
```

## 新文章复用

### courseware
1. `video-generation/deck/<slug>/deck.json`（含 points + sub_points + footer；流程类内容用 `flow` 字段替代 sub_points，见「动画与特效强制规范」第 6 条——节点/连线/跑线/逐字标签按口播分句自动逐节点动画）
2. 口播 `video-generation/narrations/<slug>.json`，格式 `{voice, rate, outline:[论点], cards:[文案]}`
3. `make video slug=<slug>`（动画零配置：分句时间轴自动生成每元素出生帧，无需任何 anim 配置）

### screencast（屏录感教程：对齐抖音「录屏+标注」爆款）
1. `video-generation/deck/<slug>/deck.json`，每卡 `type:"tool"`：
   ```json
   {"type": "tool", "tool": "hook", "title": "主标题", "subtitle": "窗口标题",
    "points": ["第1步", "第2步", "第3步"]}
   ```
2. 口播 `video-generation/narrations/<slug>.json`（**cards 数量必须 = deck cards 数量**，逐段对应；`points` 长度驱动每段内的步骤揭示）
3. `make video slug=<slug>`（courseware 模式默认）
4. 逐卡预览：`cd .agents/skills/video-generation/scripts && PYTHONIOENCODING=utf-8 python -m video.screencast` → `video-generation/probe/screencast_preview/cardNN_stepM.png`

**拟物化步骤（教程类，2026-08-03 定规）**：
1. **能浏览器截图的步骤 → 全部浏览器截图（主原则）**：`cd scripts && PYTHONIOENCODING=utf-8 python -m video.capture_shots --slug <slug>` → `video-generation/assets/<slug>/<key>.png` + `manifest.json`（Playwright 抓官网实拍 1600×900，热点框坐标记百分比）。`Shot._locate` 支持 `{sel}`（精确选择器）或 `{text, after_heading}`（README 段内文本定位）。**任何能在浏览器呈现的 UI 都截**——官网 / 市场 / GitHub / 控制台 / 在线编辑器（如 vscode.dev），不限于下载页
2. **deck 加 realshot 卡**：`{"type":"tool","tool":"realshot","slug":<slug>,"shot":"<key>","points":[...],"hotspots":[null,{x,y,w,h,label},...]}`——`hotspots` 数组按 `points` 索引对齐，`null` 表示该步无箭头
3. **CSS 仿真窗口只兜底**：浏览器截不到的本地桌面应用 / 登录态界面，才用 `tool:"vscode"`（拟物化 VSCode）等 mockup，卡字段 `req`/`resp`/`points` 驱动
4. **封面**：`make video-cover slug=<slug>` 生成横竖双封面（cover.py v3/v4 hero 体系；`ensure_covers` 对早于 metadata.txt 的旧封面强制重生成——2026-08-30 新鲜度定规，`cover_vscode` 模块已不存在、死引用已清除）→ `make video-cover-check slug=<slug>` 过验收
5. **本地桌面应用窗口截图**：浏览器截不到的本地应用（Codex / CcSwitch / 客户端等）优先**真实窗口截图**而不是 CSS 仿真——用 `scripts/screenshot_app.py` 只截应用窗口（跨平台：macOS Quartz / Windows 调 .ps1，不截全屏）：
   ```bash
   python skills/app-screenshot/scripts/screenshot_app.py --process "Codex" --title "Codex" --output video-generation/assets/<slug>/01.png
   ```
   截图后如无法目视验证（模型不支持看图），用 `skills/app-screenshot/scripts/ocr.py`(app-screenshot skill)（macOS Vision / Windows WinRT）核对窗口文字，确保截到了目标界面而非误截。
   **Windows 实测经验**（进程名不带 .exe / 窗口遮挡是最大坑——两帧 diff 验证 / UIA 自动化 / PS1 中文写文件 / NSIS 交互向导 / WinRT OCR 重试 / 教程类「真机实拍」验收强制 / 自动化产物不算真实坑）：逐条见 `references/pipeline-engineering.md`。

`tool` 现有实现（`screencast.py` 的 `_CONTENT` 注册表）：
`hook` 痛点+材料+前置 CTA ｜ `realshot` 真实截图打底 + 箭头热点（拟物化步骤卡）｜
`vscode` 拟物化 VSCode 窗口（插件使用流程）｜ `install` GitHub Releases ｜ `terminal` 终端验证（内容用 `lines` 字段驱动）｜
`ccswitch` Provider 列表 ｜ `settings` settings.json env 段 ｜ `rank` 能力排行榜（真实分数条形）｜
`map` 国产阵营分工 ｜ `cost` 成本对比（old/new/badge）｜ `cta` 结语+订阅钩
新增工具：在 `screencast.py` 加 builder 函数 + 注册进 `_CONTENT` + 补对应 CSS（`_CSS`）。

### graph
1. `video-generation/deck/<slug>/deck-graph.json`，格式：
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
2. 口播 `video-generation/narrations/<slug>.json`（同 courseware）
3. `make video slug=<slug> mode=graph theme=light`

### remotion（默认：清单/榜单/对比/数据可视化/教程步骤）
1. 口播脚本 `.agents/skills/video-generation/scripts/narrate_<slug>.py`（参照 `narrate_ccswitch.py` / `narrate_after_million_loc.py`）：写口播句子 → 复用 `video.narrate` 生成 mp3 + `narration.ts` 到 `video-generation/remotion-videos/<slug>/`
2. `video-generation/remotion-videos/<slug>/config.ts`：按内容类型选场景（`SkillStage` 阶段递进 / `LeaderboardChart` 榜单 / `ComparisonTable3D` 对比 / `DataReveal` 成本账），`span(from,to)` 从 narration 时间戳算每场景时长；字幕用 **`U.filter(s => !s.no_subtitle).map(...)`**（口播句首 `〖无字幕〗` 标记的单元不进字幕——CTA 句敏感期降险开关，见「互动与转化引导 → 管线支持」）
3. Root.tsx 注册：`import { xxxConfig } from "@videos/<slug>/config"` + 加入 `allConfigs`
4. `make video-remotion slug=<slug>`（内部 `cd remotion && VIDEO_ID=<slug> pnpm render`）→ 产物 `video-generation/build/<slug>/<slug>.mp4`，封面自动生成到**同目录** `video-generation/build/<slug>/<slug>_cover.png`

> 新增场景组件放 `remotion/src/scenes/content/` + 在 `content/index.ts` 注册（参照 `SkillStage.tsx`：flex 布局 + 字幕安全带 paddingBottom 60px + 卡片按场景帧逐张浮现）。

## 口播稿审稿台（narration-console，2026-08-29 增补，与成片预览合并）

口播稿成稿后（talkshow 炸场档或普通档），跑 `make narration-console` 生成 **web 审稿控制台**——首页（稿件卡：字数/时长@1.06/卡数/台账 stage/对标摘要 + **全线生产排期表**）+ 每支**详情页**。产物 `video-generation/build/narration-console/`（index.html + `<slug>.html`，生成器 `scripts/video/narration_console.py`）。

- **静态区**（file:// 也能看）：对标档案表（原片/作者/四维数据/时长发布/原片本质/钩子结构/仿写角度）、钩子→回收映射（15s 兑现位列）、禁区条、选题三问、分卡口播（BGM·音效·转场 chips + 大字号照读 + 每卡字数）、梗工作台 ≥3 版对照（默认展开）、字数时长实测声明、台账 stage、关联文章
- **动态能力（已被 /v/<slug> 全生命周期页承接）**：排期/平台状态/封面/成片/发布数据在 `/console` 与 `/v/<slug>` 服务端渲染，深审页只管稿件内容
- **全生命周期控制台（同服务，2026-08-29）**：`make video-preview-serve`（8901）→ `http://<局域网IP>:8901/console`——`console_pages.py` **服务端动态渲染**（七源每次请求现读：state/board/diagnosis/posts/稿/build）：首页全视频卡+**搜索框**（标题/slug/阶段/平台状态客户端过滤）+阶段 chips；**每视频一个稳定 URL `/v/<slug>`**，详情页含八阶段时间线（选题→文章→口播→合成→成片→定时→发布→复盘）、排期与四平台状态、文章卡、口播稿卡（链深审页）、对标档案、成片播放+封面+metadata、发布数据、**数据复盘**（diagnosis.json 各平台漏斗指标+findings 诊断结论）、台账变更历史；board/diagnosis 有但台账无的 slug 以「台账外」区展示。审稿台深审页（`/narration-console/`）专注稿件内容（对标/钩子/分卡/梗工作台），与 `/v/<slug>` 互链。
- **稿件 md 结构段约定**：`「slug」`档位行、`## 对标档案`（表格七行）、`## 钩子 → 回收映射`、`## 禁区`、`## 选题三问`、`### 卡N｜`、`## 梗工作台`、`## 字数与时长`（**必须写实测字数**，口径=卡内汉字、语速 3.2 字/s、atempo 1.06 折算成片时长，对照 EP08 验收基准 141s）
- 改稿后重跑 `make narration-console` 即更新；`ARGS="其他稿.md"` 可接任意新稿

## 脚本位置（.agents/skills/video-generation/scripts/video/）

脚本已封装进本 skill 目录。`make video` 内部 `cd` 到 `scripts/` 跑 `python -m video.build`。**各脚本职责表见 `references/pipeline-engineering.md`。**

### narrate.py 用法（通用口播，跨管线复用）

Python 调用（`generate_narration_from_sentences`）与 CLI（`python -m video.narrate --text-file units.txt --out-dir out/`）示例见 `references/pipeline-engineering.md`。

### 音色选择（2026-08-18 实测标定）

正式视频一律克隆声（见「发音」顶部定规）；下表仅限**用户批准的 fallback** 查用——解说/深度/悬疑默认 `zh-CN-YunjianNeural`（F0med 132Hz 最接近对标）、轻快教程 `zh-CN-YunxiNeural`、新闻播报 `zh-CN-YunyangNeural`、培训女声 `zh-CN-XiaoxiaoNeural`，rate `+8%`。标定方法与完整对照表见 `references/tts-narration.md`。

## 默认口播配置：IndexTTS-2 克隆 + 严格标点断句（2026-08-25 定稿）

发布视频（codex/claude 系列）的默认声音 = **IndexTTS-2 发布配置克隆**；edge-tts 降级为快速预览与 fallback。断句定规 = **只在逗号和句号停顿**，由管线强制，不依赖模型自觉。

### 声音配置（与发布系列逐项一致，来源 video-pipeline-6-skills 定稿）

| 项 | 值 |
|---|---|
| 参考音 | `~/refaudio/my_voice_seg.wav`（WSL） |
| 情绪 | 逐句角色向量 `--emo dyn`（2026-08-28 定档 D，openspec tts-emotion-dynamics）：幅值表烙在 `scripts/video/emotion_map.py`——hook 好奇上扬 / punch 金句小得意 / reveal 揭底兴奋 / body 贴原声 / settle 收尾温和；负向维度（angry/sad/afraid/disgusted/melancholic）恒 0，calm 仅 ≤0.05 微量；**scale 1.0 全值经盲听判「起伏过大」已弃用，发布档不得高于定档 D**，`--emo-scale` 只许 ±0.1 微调；`--emo none`（纯随参考音）为平淡旧口径，仅探针对照用 |
| interval_silence | 250 |
| 后处理 | assemble 发布五步链：120ms 呼吸垫 → RMS -18dB → treble g=2 → deesser → alimiter 0.7 + -1dB |
| 整体提速 | `tts_speed_shrink.py` atempo 1.06（时间戳等比缩放） |

### 断句档位（三级分明，全部落在标点上）

| 档 | 时长 | 机制 |
|---|---|---|
| 非标点位置 | >0.11s 一律手术清到 0.05s（听感连续） | pause_audit 手术 |
| 逗号 `，、；：` | 原生 0.4-0.6s（参考音停顿习惯被克隆）→ 0.18s 档 | pause_audit 手术 |
| 句号（句间） | 0.24s（120ms 垫×2，atempo 后 ~0.2s） | assemble 垫 |

语速：合成期 best-of-N 按窗口 [4.6, 6.2] 字/s 优选（<12 字短句软窗 ≤7.5），发布链零变速 DSP。

### 断句根源定论（实证存档，防止再走调参弯路）

句内停顿由 **AR 随机采样**决定——`interval_silence` 对单段句子不生效、`do_sample=True` 硬编码、同句重采停顿必变、上游 issue #572 未修：**参数修不动，只能管线强制（门禁选优 + 手术）**。实证细节见 `references/tts-narration.md`。

### 命令链

```bash
# ① 合成 + 门禁选优 + 手术（WSL indextts env，项目根 /mnt/d/codes/blog-src）
#   产物 sent/<slug>/（c{i}_s{j}.wav/.txt/.tts.txt/meta.json）+ pause_audit.json 审计表
PYTHONIOENCODING=utf-8 python scripts/video/synth_indextts.py <slug> [--attempts 4] [--limit N]
# ② 发布五步链拼装（Windows，产物 audio/<slug>/audio_XX.mp3 + boundaries_XX.json）
PYTHONIOENCODING=utf-8 python scripts/video/tts_pipeline/assemble.py \
  video-generation/narrations/<slug>.json video-generation/sent/<slug> video-generation/audio/<slug>
# ③ 整体提速 1.06（Windows，产物 audio/<slug>_t/，时间戳等比）
python scripts/video/tts_speed_shrink.py <slug>
# ④ 独立复审（WSL 或有 faster-whisper 的环境，可单独跑）
python scripts/video/pause_audit.py video-generation/sent/<slug>
```

### 改稿必清缓存（2026-08-28 事故定规，最高优先级）

**synth 的续跑幂等检查只看「产物在不在」，不看「文字变没变」**：改完 narrations 直接重跑，旧 sent 目录会让它整体跳过重合成，assemble 拿旧音频配新分镜——实测产出过一支 380s 的错误成片（新稿 774 字）。改口播后必须先清产物再进链：

```bash
rm -rf video-generation/sent/<slug> video-generation/audio/<slug> video-generation/audio/<slug>_t
```

改稿即作废（定规）在此落实为：**清缓存是改稿流程的一部分**，不是可选步骤。

### 已知坑

`use_cuda_kernel=False` 必须显式传（默认 True 触发 BigVGAN JIT，8GB 卡 >13min 无产出）；fp16 = 8GB 卡默认档；GPU 并行只影响速度不影响停顿位置；whisper 对齐失败自动退化字数比例映射；续跑自动复核旧产物。全文见 `references/tts-narration.md`。

## Remotion 数据可视化视频（第三种模式）

除 courseware/graph（Playwright 管线）外，还有 **Remotion 管线**（`remotion/` 目录，React + Three.js），适合「数据可视化 + 真实素材」的发布/科普视频（如模型榜单、性能对比），**是默认视频风格**。**口播/字幕/断句规则与本 skill 通用，复用 `narrate.py`。** 渲染产物落在 `video-generation/build/<id>/<id>.mp4`（成片统一目录，`out/` 已弃用），封面自动生成到**同目录** `video-generation/build/<id>/<id>_cover.png`；口播 mp3 落在 `video-generation/narration/`（即 Remotion public 目录，`remotion.config.ts` 已指好）。内容视频实例（config.ts + narration.ts）放在 `video-generation/remotion-videos/<id>/`，通过 webpack alias `@videos/` 引用。

### 关键经验（这条管线踩坑沉淀）

口播去 AI 味（口号全文只说一次 / 动词驱动 + 具体数字 / **改口播 = 重跑 narrate → config.ts 的 span/cardsFor 必须重写**）、场景密度对齐借鉴视频（每步一个场景）、内容 > 抽象 3D、数据可视化用真实图表（不编造）、真实性红线、背景全局层、字幕安全带（~170px）、DataReveal 小数位（`toFixed(decimals)`）。逐条见 `references/pipeline-engineering.md`。
### 三层架构（配置驱动，加视频 = 加 config）
```
remotion/src/             ← skill 内：框架 + 场景 + 示例
  core/                   框架（VideoConfig/VideoComposition/SubtitleOverlay/theme）—— 跨视频稳定
  primitives/             视觉原语（TechBackground/CodeBlock/MockScreen/标注/图表基础）
  scenes/                 通用场景（Cover/LeaderboardChart/GrowthChart/DataReveal/Outro...）
  videos/<id>/            示例/测试视频（dummy-test/showcase 等）
video-generation/
  remotion-videos/<id>/   内容视频实例（config.ts + narration.ts）—— 项目专属
```
加新内容视频：`video-generation/remotion-videos/<new>/config.ts`（import 类型用 `@skill-src/core/types`，选场景 + 传 props）+ 在 Root.tsx 用 `import { xxxConfig } from "@videos/<new>/config"` 注册。场景时长用 `span(unitA, unitB)` 从 narration 时间戳动态算，不手拍帧。

**运行**：`make video-remotion slug=<id>`（自动执行渲染 + 封面）。手工：`cd remotion && pnpm install && python ../scripts/narrate_<video>.py && VIDEO_ID=<id> pnpm render`。narration.ts 由 narrate 脚本生成到 `video-generation/remotion-videos/<id>/`，mp3 自动进 `video-generation/narration/`。

> **项目根注入**：技能库外置为独立仓 + `.agents/skills` 是 junction/symlink 时，向上探测会落到 skills 仓自身。项目根一律优先读 `VIDEO_PROJECT_ROOT` 环境变量（blog-src 的 Makefile 已传 `$(CURDIR)`），TS（render/sync/remotion.config）与 Python（config.py）同规则；未传时才走向上探测 + 同级 blog-src 兜底。手动跑渲染前先 `export VIDEO_PROJECT_ROOT=<项目根>`。
>
> **依赖版本**：remotion 固定 **4.0.517**（2026-08-26 codewalk-probe 实测升级：Node 24 无头渲染正常；4.0.8 报 `spawn UNKNOWN` 的老坑不复现）。⚠️ 4.0.517 下 `Easing.bezier()`/`Easing.out()` 工厂产物喂 `interpolate` 报 "easing.length undefined"——缓动一律用纯函数 `(t:number)=>number` 封装。

## 产出完整性（2026-08-17 定规，强制）

**每个视频的一次完整产出 = 成片 mp4 + 横屏封面 `_cover.png` + 竖屏封面 `_cover_v.png` + `metadata.txt`，四者缺一即产出不完整。**

- `make video-remotion` / `make video` 渲染完成后，必须立即跟：`make video-cover slug=<slug>`（横竖双封面）+ 在 `video-generation/build/<slug>/` 写入 `metadata.txt`（标题/系列/期数/封面标题或关键词/标签/简介/话题，简介含结尾互动问题；**通用简介不放外链**，博客链接只进 `简介_B站` 变体——抖音走回退继承，2026-08-26 事故）。
- **封面必须按 v3/v4 规范全字段生成（2026-08-25 定规；字段名 2026-08-27 勘误，每条视频强制）**：metadata.txt 封面字段齐填——**合法键是 `封面hero`**（word/screenshot/number 三态，见上「封面必带大字强调」定规）+ `封面hero内容` + `封面效果`（burst/marker/glitch）+ `形象表情` + `封面关键词组`（dense 轰炸层 3-8 词，三色主次制）+ `封面要点`（✓ 信息行 ≤4 条，取自简介不编造）。⚠️ 本条目早期版本写的 `封面主角*`/`封面表情` 是无效键、静默丢弃，勿再照抄（DSH 六期与 transformer-matrix 中招实录见上）。hero + 特效 + 轰炸层是 2026-08-24 封面优化的定型组合，缺一即不符合要求；**所有封面必须有 hero 大字强调**（DSH「官方故意的」式断言大字），cover-check 对无 hero 封面直接 FAIL。❌ **禁止用降级手段过 cover-check**（删 hero 改纯标题、砍关键词组、绕过 hero 板）——竖版字形覆盖不足时按 v3 补字段（关键词组/要点行/hero 板）调参，不削特性；「cover-check 通过」不等于「封面合规」，两项都要过。发布前 checklist 增查一项：封面按 v3 规范生成（字段齐 + 双版 PASS）。
- 渲染管线如中途失败/被取消，恢复后要确认没有残留僵尸渲染进程（node/ffmpeg）锁住输出文件——曾因此 Permission denied 连环失败。清场：`taskkill /F /IM node.exe` 后单实例重渲。
- **口播声音来源验收（2026-08-25 定规，第一道）**：成片口播必须是用户克隆声——确认 `video-generation/audio/<slug>_t/audio_*.mp3 + boundaries_*.json` 在场、make video 日志出现「换声旁路」字样。edge-tts 声（narrations voice 字段生效、日志只有 edge-tts WordBoundary）= 未走默认链，**返工**（用户明示批准的 fallback 除外）。
- 封面过 `make video-cover-check`，metadata 过 platform-compliance（标题/简介/话题），**音频过 `verify_render.py`**（BGM 底垫在场 + 混音不削波，见「声音层与转场」），三项都绿才算产出闭环。
- **严禁无封面发布（2026-08-28 用户定规，最高优先，覆盖一切降级路径）**：任何平台、任何形式的发布（立即/定时/跨平台补发）必须有**自定封面在片**作为发布前置条件。封面生成失败、封面弹窗打不开、上传器报「封面设置失败跳过」一律**视同发布失败阻断流程**——禁止「跳过封面继续发布」「交给推荐封面兜底」类降级（推荐封面常取片头暗帧 = 实际无封面，历史上多个视频因此裸奔上线）。封面设置失败的视频：重试上传；仍失败则发布后**立即**用编辑页补图（`douyin_fix_cover.py` / `kuaishou_fix_cover.py`），平台侧复核到封面在列才算该平台发布完成。
- **metadata-lint 机检（2026-08-24 定规，三检之后的第四道）**：`make metadata-lint slug=<slug>`——硬截断/词中断/结构红线（凭什么/打赢类）FAIL，最优长度/话题配比/断句丢钩子 WARN。发布管线 `--confirm` 时自动跑同一 lint，FAIL 拒发（`--force` 逃生留痕）。依据：`openspec/changes/metadata-optimization`。
- **可读性双检（2026-08-24 定规，强制）**：发布前过 `make video-lint`（模板字号基准 + Remotion 场景字号 + **色彩对比度/色板登记机检**（2026-08-25 并入，见「色彩可读性」），非零退出）+ `make video-preview slug=<slug>`（抖音信息流模拟图：黑边 + 右侧图标列 + 底部文案叠加，缩 390px 宽），模拟图里**正文层文字「一眼可读」**才发布。新 deck 要点密度过 `video-lint --deck <slug>`（≤3 条/卡、≤14 字/条；存量 deck 超限渲染时只警告）。基准与依据：`openspec/changes/video-landscape-readability`（正文 ≥48px/画面高 4.4%、标题 ≥72px、右缘避让 180px、crf 18、screencast 热点 1.6× 特写取景）。

## 成片生命周期：build → archive（2026-08-24 定规，强制）

**build/ 只放待发布与在售视频**：平台发布完成后 `mv build/<slug> archive/<slug>` 并在 `archive/README.md` 登记归档证据（平台 item_id）；**archive/ 只进不出**（重发/重渲先在 README 变更日志登记）；测试/demo 成片验证完即删；判定依据 = `data/analytics/snapshots/` 快照按标题对到条目。细则见 `references/publishing.md`。

## 音画同步与渲染事故清单（2026-08-17 复盘沉淀，强制）

**span 公式**：场景时长 = `U[to+1] ? U[to].end_frame : 末单元 end_frame` − `U[from].start_frame`（❌ 旧公式把下一句首单元算进来，累计漂移 27s）；验收 = 场景时长总和 === 末单元 end_frame === 音频总长，三者一致才许渲染。改 config 必跑 `sync-content-videos.ts`；异常渲染先杀僵尸 node/ffmpeg；缓存删 `remotion/node_modules/.cache`；开源项目类内容必须实拍仓库主页 + 星数 GitHub API 验证。**全文见 `references/pipeline-engineering.md`。**

### 课件批量生产与后台渲染事故清单（2026-08-29 复盘沉淀，强制）

**资产门禁**：deck 卡数必须 === narrations 卡数（不等 render 拒）；metadata.txt 必须在链路前写入（缺 `标题:` 行封面静默跳过）；narrations JSON 零污染（卡内禁 `|`/`→`/换行，TTS 会念表格）；`sync_check.py` 仅 Remotion 管线适用。**后台渲染五坑**（PATH 裁剪绝对路径/`.sh` 写 CRLF 拒跑/gpuq 嵌套自锁/pgrep -f 自匹配加括号技巧/`$SELF` 路径混写）；统一服务合并（8901 一个端口 `/console` `/board` `/v/<slug>`；Windows 禁 SO_REUSEADDR 双绑定）；**左侧白板概述轮播**（课件左画布不得长时间空白，`ffmpeg fps=1` 抽帧统计非白像素 **<6% 连续 ≥3s 不合格**）。**全文见 `references/pipeline-engineering.md`。**

## 性能

graph 模式约 1-2 分钟渲染（5 段 ~1800 帧），courseware 约 10-12 分钟，screencast（courseware 子模式）9 段约 10-15 分钟。Remotion 管线 50-100s 视频约 1-3 分钟。若频繁迭代，可降帧率到 30fps 或用 `--scale=0.5` 草稿模式。

## 封面(cover)

发布**不截视频帧**，专门生成标准封面（1920×1080），统一标准以 `after-million-loc-my-skills` 为基准。**封面必带 hero 大字强调（2026-08-27 升格强制）**：所有封面必须产出 hero 大字槽（3-5 字 punchline / 关键数字 / 态度词，禁中性描述词），无 hero 直接 FAIL、**禁用降级手段过 cover-check**；metadata 字段名以 `meta.py::FIELD_ALIASES` 为准（`封面hero`/`封面hero内容`/`封面效果`/`形象表情`/`封面关键词组`/`封面要点`——历史废名 `封面主角*`/`封面表情` 会静默丢弃）。v3 hero 三态 + 轰炸层、v4 一图一主角五条铁律、横竖双版必出、8 占位符、标题三档来源、**像素验收阈值表**（青色 ≥0.8%/字形覆盖 ≥2%/hero ROI ≥1%/惊吓色分档）——**全表见 `references/cover-metadata.md`**；`make video-cover-check slug=<slug>` 门禁不变。

## 标题 / 简介 / 话题标签规范（2026-08-17 定规，写入 metadata.txt）

标题：痛点前置禁流水账、认知反差禁说明书、「你」代入禁「我」陈述，**钩子必须落在平台裁剪后的前半段**（超短上限平台补 `标题_抖音` 等变体）；简介：前置核心收获 + 行动指令 + 结尾互动问题，**B站简介可附原文链接，抖音/快手/视频号禁外链**；话题：核心词 + 场景词组合、精选 3-5 个禁堆砌。逐条正反例见 `references/cover-metadata.md`。

## 发布元信息 metadata.txt（2026-08-05 起取代 metadata.json）

每个视频目录 `build/<slug>/metadata.txt` 存发布口径元信息（UTF-8）：`标题`/`简介`/`话题` 必填；`#` 顶格为注释、缩进行为上一字段续行；平台变体（`简介_抖音`/`简介_B站` 等）、`置顶评论`、`豁免_时长` 与封面 v3 字段齐备。**完整字段模板与解析规则见 `references/cover-metadata.md`**；读取统一走 `scripts/pub/meta.py::load_meta()`（txt → 旧 json → front matter 兜底）；发布描述 = 简介 + `\n\n` + 话题。

## 发布到多平台（自建管线，2026-08-23 七字段定规）

发布 = **抖音/快手/视频号/B站四平台全发**（小红书已移除，头条经抖音同步）。

```bash
# 默认全平台 dry-run(发布页全字段填完+预览截图)
make pub-video slug=xxx
# 正式发布（定时）
make pub-video slug=xxx platforms=douyin confirm=yes schedule="2026-08-25 20:00"
```

**七字段矩阵**（标题/简介/话题/封面/定时/合集/原创-AI 声明，每平台全过一遍）与**合规口径（2026-08-30 定规最高优先：AI 生成声明 + 原创（自制/禁转载）双声明，声明失败一律阻断禁裸发；快手绝不能选「素材来源于网络」；B站 `creation_statement` 只认对象形态传整数报 21001）**；快手现役 v2 通道与 desc 清空 bug 闭环；B站 biliup 601/21566 频控；**「视窗跟随定规」**（vendor 上传器 headful 统一 `--start-maximized` + `no_viewport=not headless`，单加参数会视口裁切，工具 `scripts/pub/viewport_probe.py`/`viewport_window_demo.py`）；**「全平台发布与逐平台状态确认」与「发布成功确认」**（四平台缺省全发、上传器日志不可信逐平台工具实查、严禁只有话题没有标题/简介的作品上线、抖音简介乱码治理与话题策展公式、封面在列确认、收尾 link-map 四平台齐全）；**「挂定时后必须复核实际状态」**（视频号定时控件曾静默回退，schtasks 兜底）；**「发布后复查闭环」**（20-30 分钟首查/24h 二查、元信息层/内容层/追罚类三层处置、复查写 link-map `pub_video.review`）；**违规视频必须清理**（四平台删除工具与快手/B站坑位）——**全集见 `references/publishing.md`**。⚠️ link-map 无文件锁，多平台并行会互相覆盖，串行发布或事后核对。
