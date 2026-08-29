---
name: stock-footage
description: 免费实拍/档案素材检索——16 个免登录或免费注册素材源（NASA/Wikimedia/Archive.org/LOC/NARA/Mixkit/Pexels/Pixabay 等）统一搜索、下载、溯源清单。做实拍混剪、纪录片感、空镜 B-roll 类视频需要真实素材时调用；也可为文章配图找公有领域图。只收免费/自由许可源，与「数据通道只用免登录公开源」定规同构。
---

# Stock Footage Skill — 免费素材统一检索

把 16 个免费素材源收敛成一条命令：**搜索 → 带溯源的候选清单 → 按需下载**。方法与源适配器搬运自 [OpenMontage](https://github.com/calesthio/OpenMontage)（AGPL-3.0；`scripts/stock_sources/` 按 AGPL-3.0-only 单独许可，其余部分随本仓库 MIT，协议边界见文末）。

## 何时用

- 视频选题需要**实拍感/档案感**素材：太空、机械、自然、城市空镜、年代影像——现行合成课件管线做不出的画面
- 做混剪类内容（纪录片蒙太奇、卡点混剪——卡点侧配 video-generation 的 beat-cut）
- 文章需要公有领域配图（NASA/Wikimedia 的图）
- 对标拆解需要参考素材风格

**不适用**：现行合成课件/Remotion 数据可视化视频不需要实拍素材时，不用本 skill。

## 快速开始

```bash
cd .agents/skills/stock-footage/scripts

# ① 看哪些源可用（零配置：免 key 源直接亮）
python stock_search.py sources

# ② 搜索（返回带溯源的 JSON 候选清单）
python stock_search.py search "earth timelapse from space" --per-source 4 --orientation landscape --min-width 1280

# ③ 边搜边下载（快路径，每源按序取前 N 条）
python stock_search.py search "rain city neon night" --download-dir assets/stock --download-limit 6
```

结果 JSON 每条候选强制携带 `provider / source_url（素材页）/ license` 溯源三件套 + `download_url / thumbnail_url / duration`。缺溯源的候选自动过滤进 warnings，不进 results。

## 源决策树（先选源再写查询）

```
需要什么画面？
├─ 太空/航天/地球/科学装置 → nasa（免key，本机直连可达，慢、结果niche，单独小批量跑）
├─ 年代档案感（vintage，如"九十年代机房"）→ archive_org + wikimedia + loc + nara
│   （archive_org 的 Prelinger 深翻很慢：单独成批，别和现代源混跑）
├─ 现代 HD 实拍空镜/自然/城市 → mixkit、coverr（免key）→ pexels、pixabay_video（免key注册）
├─ 童话/儿童向 fantasy 风格 → 只用 pixabay_video（AI 生成 fantasy 集中地，风格一致性 > 单条分数，别混真实 footage）
├─ 历史/科普图（文章配图）→ wikimedia + loc + nasa 的 image kind
└─ 极限运动/游戏资产 → dareful（4K/360°，需 requests+bs4）
```

源分四档（`python stock_search.py sources` 实时显示可用状态）：

| 档 | 源 | 条件 |
|----|----|------|
| 免 key·纯 stdlib | archive_org, wikimedia, nasa, nara, loc, pond5_pd, coverr | 零安装 |
| 免 key·需解析库 | mixkit, esa, noaa, dareful, jaxa | `pip install requests beautifulsoup4` |
| 免费注册 key | pexels, pixabay_video, unsplash, videvo | 环境变量 `PEXELS_API_KEY` / `PIXABAY_API_KEY` / `UNSPLASH_ACCESS_KEY` / `VIDEOVO_API_KEY`（coverr 可选 `COVERR_API_KEY` 提额） |
| key 可选提额 | nara, nasa（DEMO_KEY 兜底） | 不配也能跑 |

**网络注意**：本机直连部分境外源不通（wikimedia/archive.org 实测被墙、loc 返回 403 需浏览器 UA、nasa/mixkit 直连可达）。适配器走 `requests`，自动吃标准 `HTTP_PROXY/HTTPS_PROXY` 环境变量——直连失败的源，开代理后设好环境变量再跑。

## 检索纪律（详见 references/retrieval-discipline.md）

- **query 写具体名词 + 视觉特征**（`raindrop on asphalt slow motion`），禁抽象概念词直搜（`time passes`）；弱结果按「换具体名词 → 加视觉限定 → 换同义词」改写，**每槽最多两轮，仍无匹配就标 unfilled 上报，不许硬凑**
- `--per-source` 经验值 4-8；候选总量按「槽位数 × 8-12 倍」配比
- **相邻镜头去重**：两条候选画面高度相似只留一条；每条素材只归属一个槽位
- **年代向**：sources 收敛到 archive_org,wikimedia,loc,nara 且单独成批
- 择片靠人看（缩略图/候选页），不唯时长分辨率论；**license 不明即弃**

## 许可红线

- 只收公有领域 / CC0 / 自由许可（NASA 公有领域、Wikimedia 逐文件核、Pexels/Mixkit 自有自由许可）
- license 字段不明或含商业限制 → 直接丢弃，不留人工兜底
- 素材进成片时，溯源三件套随素材登记进项目 archive 记录（可查证）

## 与其他 skill 的关系

- **video-generation**：本 skill 只管素材供给，不带渲染。素材清单供 remotion/courseware 管线的 B-roll 位与未来混剪模板消费；BGM 卡点侧见 video-generation `references/beat-cut.md`
- **douyin-topic**：对标拆解若需参考素材风格，用本 skill 找同类免费素材做差异化原创

## 协议边界

`scripts/stock_sources/` 适配器包与检索方法论搬运自 OpenMontage（AGPL-3.0），目录内有独立 LICENSE：

- **`scripts/stock_sources/`（18 个文件）按 AGPL-3.0-only 单独许可**，不适用本仓库 MIT——再分发须遵循 AGPL-3.0（保留声明 + 提供源码，网络服务使用同样适用）
- 上层 CLI `stock_search.py`、SKILL.md、references/ 为本仓新写/方法论重写，按仓库 MIT
- 若把本 skill 整体引入你的项目：AGPL 义务只随 `stock_sources/` 目录传导，其余部分照 MIT 用
