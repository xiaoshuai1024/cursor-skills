---
name: douyin-topic
description: 抖音选题 + 对标拆解。免登录热榜 + 抖音指数（原热点宝）实时/飙升热点 + 创作者中心个性化垂类推荐三源真实数据，把热门话题筛成符合博客方向的选题（🔥热度/📈涨粉/💥低粉爆款代理三榜），定位代表视频，拆解爆款（钩子/结构/热评/转写）产出可抄大纲与仿写脚本。两阶段：先选题确认，再深挖。
---

# Douyin Topic Skill — 抖音选题 + 对标拆解

把抖音当前热门话题（**真实数据**）筛成符合本博客「前端 → 全栈 → AI 开发」方向的选题，分 🔥热度 / 📈涨粉 双系列 + 💥低粉爆款代理榜，定位确切代表视频，拆解爆款（钩子/结构/热评/转写），产出**详细到可抄**的大纲 + 映射博客资产的仿写脚本。

## 何时用

- 不知道该做什么视频 / 下一篇写什么 → 跑 `make topic` 拿选题清单（Phase 1，不下载）
- 想快速涨粉 → 优先看 📈涨粉系列（垂直话题 + 飙升热点 + 个性化垂类），结合原片拆解做差异化原创
- 小号想吃流量 → 看 💥低粉爆款代理榜（飙升快 × 竞争低的话题，低粉号有机会）
- 想蹭热点 → 优先看 🔥热度系列（热榜 ∩ 方向关键词），跟得快有流量
- 在 `topics.md` / `rough_outlines/` 看中某条 → `make topic-deep id=<group_id>` 确认后深挖（Phase 2）

## 数据源（免登录 + 登录态公开页，2026-08-30 实测）

| 源 | 通道 | 登录 | 内容 |
|----|------|------|------|
| A | 抖音搜索热榜 API（免登录免签名） | ❌ | 51 热搜词（主榜）+ 5 上升热点（rising），`group_id` 覆盖率 98% |
| B | **抖音指数**（原热点宝，2026-01 升级接入创作者中心）双板 | ✅ douyin 登录态 | 实时热点 + 飙升热点各 30 条（10 条/页 × ≤3 页），含热点指数；飙升板即话题上升信号 |
| C | 创作者中心首页「猜你喜欢·热门话题」 | ✅ 同上 | 按账号垂类个性化的方向内话题 Top5（带热度），免关键词直入涨粉系列 |

- 主榜/实时板供 🔥热度系列；上升榜/飙升板/C 垂类供 📈涨粉系列；A/B/C 三源按话题词归一合并，结果缓存 10 分钟
- **登录态双回退**（B/C 源）：`.douyin-topic/profile-douyin/` 持久 profile（与作品搜索共享，`make topic-works --login` 扫码一次）→ 注入 `scripts/pub/cookies/douyin.json`（发布管线 cookie）→ 都没有则自动降级仅 A 源并记 note
- **B/C 源只走 Playwright+DOM 解析**：指数页 API 全带 msToken/X-Bogus 签名，不做逆向（签名轮换不影响 DOM 通道）
- **三方平台边界**：蝉妈妈/飞瓜/新榜等三方榜单全为登录墙，且定规禁第三方数据 SaaS CLI——**不自动接**；需要视频级低粉爆款/达人涨粉明细时人工浏览（蝉妈妈 chanmama.com / 飞瓜 feigua.cn / 新榜 newrank.cn），不进管线
- **升级位**：抖音指数的话题详情页（关联视频/视频级低粉爆款）需 trendinsight 独立 SSO（douyin cookie 不覆盖，实测 `has_login:false`）——未来独立扫码一次即可解锁，本期未接

## ⚠️ 合规边界（强制，违反即错）

- 下载的原片 / 截图**仅作分析素材**（转写、拆钩子、截关键帧、拆结构），**禁止直接发布**
- 产出是「同结构、换内容」的**差异化原创脚本**：内容来自真实经历 / 存量博客，不复制原片文案逐字发布
- 搬运原片违反抖音原创声明 / 查重机制 → 限流删号；发布管线已有 AI 生成声明（`declaration=3`）

## 依赖

| 依赖 | 用途 | 安装 |
|------|------|------|
| Python 3.11（全局，含 playwright） | 全部脚本解释器（对齐 video/wechat 管线） | 已装 |
| playwright + msedge | 打开视频页拦截 mp4 / 截图 | 已装（wechat 管线复用） |
| faster-whisper | 原片本地中文转写 | `py -3.11 -m pip install faster-whisper` |

## 运行（两阶段：先选题，确认后再深挖）

**默认先跑 Phase 1 选题**（不下载原片，快）；看到想模仿的代表视频后，**用户确认**再跑 Phase 2 下载拆解。

```bash
# ── Phase 1 选题（不下载）──
make topic                 # 三源拉取(A热榜+B指数+C垂类) → 双系列+低粉代理榜评分 → Top 候选「假设大纲」
                           # 产物: .douyin-topic/topics.md + rough_outlines/
# 参数: make topic top=8        # 假设大纲候选条数（默认 5）
#       pipeline phase1 --no-trend  # 跳过 B/C 源（登录态不可用时的快速路径，仅 A 热榜）

# ── Phase 2 深挖（确认模仿后）──
make topic-deep id=<group_id>          # 下载原片 → 转写 → 拆解 → 可抄大纲
make topic-deep id=<id> skip-fetch=yes # 复用已下载目录（已有逐字稿/拆解自动跳过）
# B/C 源条目无 group_id: 先 make topic-works keywords="<话题词>" 定位作品，取 aweme_id 当 id 深挖

# 底层命令（不经过 pipeline，单独跑某步）
py -3.11 -m scripts.fetch_sources --out .douyin-topic/latest.json
py -3.11 -m scripts.fetch_trend --out .douyin-topic/trend.json   # B/C 源（登录态；--login 扫码 / --no-cache 强刷）
py -3.11 -m scripts.filter_score --in .douyin-topic/latest.json --trend .douyin-topic/trend.json
py -3.11 -m scripts.fetch_video --group-id <id>
py -3.11 -m scripts.transcribe --audio .douyin-topic/videos/<id>/audio.mp4
py -3.11 -m scripts.understand_video .douyin-topic/videos/<id>/video.mp4 --max-frames 12 -o .douyin-topic/videos/<id>/teardown.json   # 镜头级拆解帧表（零依赖，whisper 不需要）
py -3.11 -m scripts.analyze --dir .douyin-topic/videos/<id>/
py -3.11 -m scripts.outline --rough <topic.json>   # Phase 1 假设大纲
py -3.11 -m scripts.outline --deep <analysis.json> # Phase 2 可抄大纲
```

**两阶段分工**：
- **Phase 1 选题**：拿 `topics.md` + `rough_outlines/` 的假设大纲，判断「本次模仿哪条」——不看原片，纯靠话题信息 + 方向经验 + 本站素材映射
- **Phase 2 深挖**：对确认的 `group_id` 下载原片 → 本地转写 → 拆解真实钩子/结构/热评/关键帧 → 生成**逐行可抄**的仿写脚本。转写之外加**镜头级拆解**（`understand_video.py`，2026-08-28 增补，搬运自 OpenMontage video-understand，AGPL-3.0）：ffmpeg 场景切分 + 关键帧帧表（JSON 落 `videos/<id>/teardown.json`，帧图落 `video_frames/`），回答「怎么拍」——镜头数/切点节奏/钩子出现在第几个镜头/每个镜头 hold 多久；与转写文本（「说什么」）构成双证据链，缺一不算拆完。纯 ffmpeg 零第三方依赖，whisper 转写不归它管（走 transcribe.py）

产物统一落 `.douyin-topic/`（git 忽略）：`topics.json`（选题清单）、`trend.json`（B/C 源原始数据）、`rough_outlines/`（假设大纲）、`videos/<group_id>/`（原片/截图/转写稿/拆解）、`deep_outline.json`（可抄大纲）。

## 双系列 + 低粉代理与评分

| 系列 | 信号 | 运营目标 | 评分侧重 |
|------|------|---------|---------|
| 🔥 热度 | A 主榜 + B 实时热点 ∩ 方向关键词 | 蹭热点求播放 | 热度增速 + 垂直匹配 |
| 📈 涨粉 | A 上升榜 + B 飙升热点 ∩ 方向搜索词 + **C 个性化垂类免关键词直入** | 垂直建定位求关注 | 垂直匹配 + 竞争度 |
| 💥 低粉爆款代理 | rising 板证据 × 低竞争（`lowfan = 0.5×热度 + 0.5×竞争度反向`） | 小号吃流量 | 独立展示维度，**不改潜力分公式** |

- 潜力分 = `0.4×热度增速 + 0.3×垂直匹配 + 0.2×竞争度(反向) + 0.1×互动潜力`；三源合并后热度一律**系列内归一化**（B 指数与 A 热榜量级不同，跨源不直比）。规则详见 `references/scoring-guide.md`
- 💥榜是代理信号（官方低粉爆款榜已随巨量算数 2026-01 升级下线）：飙升快=话题上升期新内容有机会，竞争低=低粉号有机会；要视频级低粉爆款明细走三方人工清单（见数据源一节）
- 热榜无命中时**诚实输出「今日无方向命中」**，不硬凑；B/C 源任一失败自动降级仅 A 源（备注栏写明原因）

## 大纲：假设（Phase 1）→ 可抄（Phase 2）

- **Phase 1 假设大纲**（`outline.py --rough`，不下载）：按系列给「钩子/讲现象/拆本质/给方案/互动」或「钩子/建信任/给步骤/给判断/求关注」结构先猜一拍，映射本站存量文章为内容素材——用来**决定模仿哪条**
- **Phase 2 可抄大纲**（`outline.py --deep`）：下载原片 → faster-whisper 转写逐字稿 → 拆解（钩子前 5 秒 / 段落时间轴 / 热评词频 / 关键帧）→ 输出**逐行可抄**仿写脚本（同结构换内容，原片仅作结构参考）
  - 有匹配存量博客文章 → 从文章结构派生（正文素材真实可用）
  - 无匹配 → 按热度速跟 / 垂直教学两套模板生成（`references/outline-templates.md`）
  - **精选对标（2026-08-27，openspec douyin-featured-selection）**：除热榜爆款外，另一类拆解对象是**已入选精选的知识类案例**（DeepSeek 实用技巧 / 自制硬件 / 三维建模类，档案见 `references/jingxuan-benchmarks.md`）——拆解维度比热榜多两层：选题结构（实用技巧清单 / 反常识机制揭秘 / 官方没说的细节三型）与**获得感密度分布**（每多少秒落一个可带走知识点）、时长形态；仿写角度优先「专业到极限」（单工具单机制源码深挖）

可抄大纲逐行可投产（口播骨架 + 画面提示 + 差异化角度），直接可喂 `video-generation` 的 deck/口播。有镜头级拆解帧表时，仿写脚本的画面提示列 SHALL 对齐原片镜头节奏证据（钩子镜头时长/切点密度），不凭空编画面。

**仿写脚本强制视频三要素**（2026-08-24 用户定规，与 `video-generation` skill 的「视频三要素」同源，产稿时逐条对照）：① 提问式开头——引导语固定用「问你一个问题」或「你有没有想过」二选一（频道签名），问题主体 ≤20 字且须在正文中被回答；② 钩子设计且必须消费——稿附「钩子 → 回收」映射表（埋点 + 回收时间码 + **15s 兑现位**列，openspec douyin-featured-selection），无回收点的钩子不许埋；③ 分镜含 BGM 情绪档 / 音效触发点 / 转场类型三列（转场 15 种、音效至少含开场音 + 提问音 + 转场音 + 关键动作音）。**冲精选追加两条**（2026-08-27，openspec douyin-featured-selection）：④ **选题三问**——获得感（观众带走什么）/ 惊喜感（哪里超预期）/ 共鸣感（哪里想到自己），三问全空换选题；**获得感密度**——每 30s 一个可带走知识点，口播稿逐段自检；⑤ **时长预算 ≤120s**（口播 340-380 字；>150s 需拆系列论证，发布门禁拦）。另守签名定规：开头不放自我介绍，结尾最后一句固定签名「我是1024工程笔记，越基础的东西，越值得讲透。」（2026-08-26 定稿；签名句前允许合规求关注，见 video-generation skill），视觉品牌由右下角伴随机器人承担、不加水印。

## 目录结构

```
本 skill 目录（见 SKILL.md「产物与目录」）
├── SKILL.md
├── topic_keywords.json        方向关键词表（可编辑）；含 weights/series_keywords 反哺块（video-analytics 涨粉口径 → 选题分缩放，2026-08-29 接入）
├── scripts/
│   ├── pipeline.py            两阶段编排（phase1 选题 / phase2 深挖）
│   ├── fetch_sources.py       免登录热榜拉取（A 源：主榜+上升榜，含缓存）
│   ├── fetch_trend.py         B/C 源拉取（抖音指数实时/飙升双板 + 创作者中心垂类，登录态 DOM 采集，含缓存）
│   ├── filter_score.py        方向过滤 + 双系列 + 潜力分 + 低粉爆款代理榜（三源 word 归一合并）
│   ├── fetch_video.py         Playwright+msedge 拉代表视频/截图
│   ├── transcribe.py          faster-whisper 转写
│   ├── understand_video.py    镜头级拆解（ffmpeg 场景切分+关键帧帧表，搬运自 OpenMontage，转写不归它管）
│   ├── analyze.py             拆解（钩子/结构/热评/关键帧）
│   └── outline.py             大纲（--rough 假设 / --deep 可抄）+ 资产映射
└── references/
    ├── scoring-guide.md
    ├── outline-templates.md
    └── jingxuan-benchmarks.md  # 精选对标档案（已入选知识类案例 + 拆解框架，openspec douyin-featured-selection）
```

## 工程约束

- Windows 编码：文件 I/O 显式 `encoding="utf-8"`，子进程 `PYTHONIOENCODING=utf-8`
- 变量命名避开内置构造器（URL/name/status/data）
- 接口调用先读 Schema 再构造 payload，检查响应体每字段（不只 status 200）
- Playwright 反检测：`--disable-blink-features=AutomationControlled` + 真实 UA + msedge channel

### 反风控扰动（改爬取/下载逻辑前必读）

抖音对「固定节奏 + 固定指纹」的自动化识别很严（实测：高频导航会弹滑块验证码）。脚本已内置扰动，**新增任何对 douyin.com / CDN 的请求或浏览器动作，必须保持以下随机性**：

- **UA 池**：请求用 `UA_POOL` 随机取，禁止硬编码单一 UA（`fetch_sources.py` 定义，`fetch_video.py`/`fetch_trend.py` 复用）
- **请求间隔**：失败重试指数退避 + `random.uniform` 抖动
- **浏览器行为**（`fetch_video.py` 的 `_humanize`）：滚动次数/步长/间隔全随机、~25% 概率回滚、随机鼠标移动；视口尺寸每次会话随机（1410–1536 × 860–940）；页面等待 10s ± 3s 抖动。`fetch_trend.py` 同构：随机滚动 + 随机等待 + 弹窗自动关闭，**单会话只导航 2 个页面**（指数页 + 创作者中心首页），解析为空单次重试一次
- **节奏纪律**：一次会话不要连续多次导航；触发验证码后停止，等用户手动完成或等 10 分钟再试
- 改动后跑 `py -3.11 -m py_compile scripts/fetch_sources.py scripts/fetch_trend.py scripts/fetch_video.py` 确认语法
