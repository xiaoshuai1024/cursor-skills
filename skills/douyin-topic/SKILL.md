---
name: douyin-topic
description: 抖音选题 + 对标拆解。免登录热榜真实数据把热门话题筛成符合博客方向的选题（🔥热度/📈涨粉双系列），定位代表视频，拆解爆款（钩子/结构/热评/转写）产出可抄大纲与仿写脚本。两阶段：先选题确认，再深挖。
---

# Douyin Topic Skill — 抖音选题 + 对标拆解

把抖音当前热门话题（**真实数据**）筛成符合本博客「前端 → 全栈 → AI 开发」方向的选题，分 🔥热度 / 📈涨粉 双系列，定位确切代表视频，拆解爆款（钩子/结构/热评/转写），产出**详细到可抄**的大纲 + 映射博客资产的仿写脚本。

## 何时用

- 不知道该做什么视频 / 下一篇写什么 → 跑 `make topic` 拿选题清单（Phase 1，不下载）
- 想快速涨粉 → 优先看 📈涨粉系列（垂直话题），结合原片拆解做差异化原创
- 想蹭热点 → 优先看 🔥热度系列（热榜 ∩ 方向关键词），跟得快有流量
- 在 `topics.md` / `rough_outlines/` 看中某条 → `make topic-deep id=<group_id>` 确认后深挖（Phase 2）

## 数据源（免登录公开 API，已实测）

| 源 | 通道 | 内容 |
|----|------|------|
| A | 抖音搜索热榜 API（免登录免签名） | 51 热搜词（主榜）+ 5 上升热点（rising），`group_id` 覆盖率 98% |

- 主榜供 🔥热度系列，上升榜供 📈涨粉系列；结果缓存 10 分钟
- 零登录依赖：无需任何账号绑定或第三方查询通道，断网外因只影响拉取本身

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
make topic                 # 热榜拉取 → 双系列评分 → Top 候选「假设大纲」
                           # 产物: .douyin-topic/topics.md + rough_outlines/
# 参数: make topic top=8   # 假设大纲候选条数（默认 5）

# ── Phase 2 深挖（确认模仿后）──
make topic-deep id=<group_id>          # 下载原片 → 转写 → 拆解 → 可抄大纲
make topic-deep id=<id> skip-fetch=yes # 复用已下载目录（已有逐字稿/拆解自动跳过）

# 底层命令（不经过 pipeline，单独跑某步）
py -3.11 -m scripts.fetch_sources --out .douyin-topic/latest.json
py -3.11 -m scripts.filter_score --in .douyin-topic/latest.json
py -3.11 -m scripts.fetch_video --group-id <id>
py -3.11 -m scripts.transcribe --audio .douyin-topic/videos/<id>/audio.mp4
py -3.11 -m scripts.analyze --dir .douyin-topic/videos/<id>/
py -3.11 -m scripts.outline --rough <topic.json>   # Phase 1 假设大纲
py -3.11 -m scripts.outline --deep <analysis.json> # Phase 2 可抄大纲
```

**两阶段分工**：
- **Phase 1 选题**：拿 `topics.md` + `rough_outlines/` 的假设大纲，判断「本次模仿哪条」——不看原片，纯靠话题信息 + 方向经验 + 本站素材映射
- **Phase 2 深挖**：对确认的 `group_id` 下载原片 → 本地转写 → 拆解真实钩子/结构/热评/关键帧 → 生成**逐行可抄**的仿写脚本

产物统一落 `.douyin-topic/`（git 忽略）：`topics.json`（选题清单）、`rough_outlines/`（假设大纲）、`videos/<group_id>/`（原片/截图/转写稿/拆解）、`deep_outline.json`（可抄大纲）。

## 双系列与评分

| 系列 | 信号 | 运营目标 | 评分侧重 |
|------|------|---------|---------|
| 🔥 热度 | 热榜 ∩ 方向关键词 | 蹭热点求播放 | 热度增速 + 垂直匹配 |
| 📈 涨粉 | 上升榜 ∩ 方向搜索词 | 垂直建定位求关注 | 垂直匹配 + 竞争度 |

潜力分 = `0.4×热度增速 + 0.3×垂直匹配 + 0.2×竞争度(反向) + 0.1×互动潜力`。规则详见 `references/scoring-guide.md`。热榜无命中时**诚实输出「今日无方向命中」**，不硬凑。

## 大纲：假设（Phase 1）→ 可抄（Phase 2）

- **Phase 1 假设大纲**（`outline.py --rough`，不下载）：按系列给「钩子/讲现象/拆本质/给方案/互动」或「钩子/建信任/给步骤/给判断/求关注」结构先猜一拍，映射本站存量文章为内容素材——用来**决定模仿哪条**
- **Phase 2 可抄大纲**（`outline.py --deep`）：下载原片 → faster-whisper 转写逐字稿 → 拆解（钩子前 5 秒 / 段落时间轴 / 热评词频 / 关键帧）→ 输出**逐行可抄**仿写脚本（同结构换内容，原片仅作结构参考）
  - 有匹配存量博客文章 → 从文章结构派生（正文素材真实可用）
  - 无匹配 → 按热度速跟 / 垂直教学两套模板生成（`references/outline-templates.md`）
  - **精选对标（2026-08-27，openspec douyin-featured-selection）**：除热榜爆款外，另一类拆解对象是**已入选精选的知识类案例**（DeepSeek 实用技巧 / 自制硬件 / 三维建模类，档案见 `references/jingxuan-benchmarks.md`）——拆解维度比热榜多两层：选题结构（实用技巧清单 / 反常识机制揭秘 / 官方没说的细节三型）与**获得感密度分布**（每多少秒落一个可带走知识点）、时长形态；仿写角度优先「专业到极限」（单工具单机制源码深挖）

可抄大纲逐行可投产（口播骨架 + 画面提示 + 差异化角度），直接可喂 `video-generation` 的 deck/口播。

**仿写脚本强制视频三要素**（2026-08-24 用户定规，与 `video-generation` skill 的「视频三要素」同源，产稿时逐条对照）：① 提问式开头——引导语固定用「问你一个问题」或「你有没有想过」二选一（频道签名），问题主体 ≤20 字且须在正文中被回答；② 钩子设计且必须消费——稿附「钩子 → 回收」映射表（埋点 + 回收时间码 + **15s 兑现位**列，openspec douyin-featured-selection），无回收点的钩子不许埋；③ 分镜含 BGM 情绪档 / 音效触发点 / 转场类型三列（转场 15 种、音效至少含开场音 + 提问音 + 转场音 + 关键动作音）。**冲精选追加两条**（2026-08-27，openspec douyin-featured-selection）：④ **选题三问**——获得感（观众带走什么）/ 惊喜感（哪里超预期）/ 共鸣感（哪里想到自己），三问全空换选题；**获得感密度**——每 30s 一个可带走知识点，口播稿逐段自检；⑤ **时长预算 ≤120s**（口播 340-380 字；>150s 需拆系列论证，发布门禁拦）。另守签名定规：开头不放自我介绍，结尾最后一句固定签名「我是1024工程笔记，越基础的东西，越值得讲透。」（2026-08-26 定稿；签名句前允许合规求关注，见 video-generation skill），视觉品牌由右下角伴随机器人承担、不加水印。

## 目录结构

```
本 skill 目录（见 SKILL.md「产物与目录」）
├── SKILL.md
├── topic_keywords.json        方向关键词表（可编辑）
├── scripts/
│   ├── pipeline.py            两阶段编排（phase1 选题 / phase2 深挖）
│   ├── fetch_sources.py       免登录热榜拉取（主榜+上升榜，含缓存）
│   ├── filter_score.py        方向过滤 + 双系列 + 潜力分
│   ├── fetch_video.py         Playwright+msedge 拉代表视频/截图
│   ├── transcribe.py          faster-whisper 转写
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

- **UA 池**：请求用 `UA_POOL` 随机取，禁止硬编码单一 UA（`fetch_sources.py` 定义，`fetch_video.py` 复用）
- **请求间隔**：失败重试指数退避 + `random.uniform` 抖动
- **浏览器行为**（`fetch_video.py` 的 `_humanize`）：滚动次数/步长/间隔全随机、~25% 概率回滚、随机鼠标移动；视口尺寸每次会话随机（1410–1536 × 860–940）；页面等待 10s ± 3s 抖动
- **节奏纪律**：一次会话不要连续多次导航；触发验证码后停止，等用户手动完成或等 10 分钟再试
- 改动后跑 `py -3.11 -m py_compile scripts/fetch_sources.py scripts/fetch_video.py` 确认语法
