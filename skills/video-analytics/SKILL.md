---
name: video-analytics
description: 多平台运营数据分析——四平台(B站API/抖音·快手XHR拦截/视频号)只读采集自己创作者后台的作品表现数据成增量快照，标准化后做单视频漏斗诊断、抖音流量池落位、横向因子对比、跨平台矩阵，产出「证据→诊断→动作」优化建议与选题关键词反哺 diff。发布视频后看表现、复盘、决定优化方向时调用。
---

# video-analytics 多平台运营数据分析

把发布管线（`scripts/pub`）发出去的视频表现数据收回来，变成可执行的优化建议。定位是管线的**反馈环**：选题（douyin-topic）→ 制作（video-generation）→ 发布 → **表现回流（本 skill）** → 反哺选题权重。

**核心目标 = 涨粉**：反哺与 Top/Bottom 排序以涨粉口径为主（单视频涨粉数、播转粉率），播放量作参考；账号级日涨粉/掉粉序列随 `make analytics` 每日采集。

## 快速用法

```bash
make analytics                    # 采集四平台快照 + 回填平台作品 ID（日频手动跑一次）
make analytics platform=bilibili  # 单平台（douyin,kuaishou,bilibili,shipinhao 逗号分隔）
make analytics-deep               # 深度过程采集（完播率/平均时长/3s退出/涨粉）+ whisper 留存对齐
make analytics-deep slugs=a,b     # 只跑指定 slug（转写有缓存）
make analytics-report             # 标准化 → 诊断 → 报告
make analytics-revenue            # 平台收益只读采集 + 变现门槛进度表（monetize-tracking）
make fans-insight                 # 粉丝画像/活跃时段采集 + 发布档校准建议（fans-insight）
make experiment ARGS="list"       # 实验台账：假设→落地→验证闭环（ops-hardening）
```

**冲精选期采集纪律**（2026-08-27，openspec douyin-featured-selection）：① deep 采集对**新发视频默认全量跑**（历史仅 4/25 覆盖，回验样本不足）；② 每条视频发布满 **48h** 跑一次 `analytics-deep + analytics-report`，对照「精选自查基准线」写进 directives；③ **月度精选复盘**——每月 18-20 日（官方发上月精选作者榜单）跑一次 report，对照榜单记录本号差距与可仿写点，同步更新 `douyin-topic/references/jingxuan-benchmarks.md` 案例档案；④ 20:00 发布窗口回测——累计 10 支 20:00 档后与中午档历史对比完播/池级，结论回写 video-generation skill「发布窗口」节；⑤ **结论沉淀**（2026-08-29）——48h 回验与月度复盘的账号级结论追加 `references/findings-log.md`（`reports/` 与 `.video-analytics/` 均 gitignore 不进 git，跨期结论只认 references 落盘；新结论与旧结论冲突时并列保留并标注修订）。

报告落 `.video-analytics/reports/`：

| 文件 | 内容 |
|------|------|
| `YYYY-MM-DD-per-video/<slug>.md` | 单视频诊断卡：播放/互动漏斗 + 流量池落位 + **过程分析（停留句定位 + 段落表）** + 三段式建议（含转粉器标注） |
| `overview-YYYY-MM-DD.md` | 总览：**涨粉看板（粉丝总数/日涨掉序列/涨粉效率 Top/发布日拉动）**、Top/Bottom、跨平台矩阵、留存深度排行、因子分桶、动作清单 |
| `feedback-keywords.md` | 选题反哺：**涨粉口径** Top/Bottom 系列的 weight 调整 diff（涨粉锚点 <3 支回退播放口径并标注；人工确认后应用） |
| `directives.md` | **创作指导（写下一支脚本前必读）**：账号数据 × playbook 技巧装配的优先级清单，每条带证据/动作/验证指标；video-generation 已接线消费 |
| `report.json` | 机器可读全量诊断 |

数据落 `data/analytics/`（**进 git**，时间序列历史不可再生）：`snapshots/{platform}.jsonl`（列表快照）+ `snapshots/deep/{platform}.jsonl`（过程锚点）+ `snapshots/fans/{platform}.jsonl`（账号级日涨掉序列）+ `transcripts/<slug>.json`（句级转写缓存）+ `metrics.json` + `diagnosis.json` + `retention.json` + `errors.json`。

## 涨粉数据通道

| 平台 | 通道 | 数据 |
|------|------|------|
| 抖音 | `overview/all`（janus 裸 fetch，随 `make analytics` 每日）| 粉丝总数、每日涨粉/掉粉、每日播放/赞评转/主页访问序列 |
| 抖音 | `summarize`（单视频，随 `make analytics-deep`）| 单视频涨粉数、播转粉率 |
| B站 | 公开 `relation/stat`（免登录）+ 日快照差分 | 粉丝总数、净增（无掉粉明细则不造数） |
| B站 | `archive_diagnose`（单视频）| 涨粉、播转粉率（含同类 UP 主对照，not_ready 时置空） |
| 视频号 | `statistic/fans_trend`（首页裸 fetch，随 `make analytics` 每日，2026-08-29 接入）| 粉丝总数、7 日涨/掉/净增序列、涨粉来源拆解（推荐/主页/分享…）；单视频涨粉走列表 `follow_count` |
| 快手 | cp.kuaishou.com 被动 XHR 拦截 + fan/follower 关键字深挖（随 `make analytics`，2026-08-30 接入）| 粉丝总数（快照差分得净增；端点带签名，落空时降级留痕） |

## 粉丝画像与发布档校准（fans-insight，2026-08-30）

`make fans-insight`：四平台创作者中心粉丝画像 XHR 宽匹配拦截 + 原始证据落盘（`snapshots/fans_insight_raw/`，gitignore）+ 关键字/name/value 双路深挖。**当前覆盖**：视频号全量画像（年龄/性别/地域/设备，`statistic/fans_portrait` respJson 解包）；抖音/快手的活跃时段直方图端点未固化（raw 证据在手，待人工抓包迭代）；B站随登录恢复后接入。产出 `data/analytics/fans_insight.json`（含 F1 发布档校准 directive：活跃峰值 vs 现行 8/12/20 档）+ `reports/fans-insight.md`。校准是建议不是自动改档——双窗口定规不动。

## 变现数据（monetize-tracking，2026-08-30）

- `make analytics-revenue` = `va.revenue_collect`（B站/视频号收益页 XHR 宽匹配拦截，原始证据 `snapshots/revenue_raw/`）+ `va.monetize`（门槛进度表）。快照落 `snapshots/revenue/<platform>.jsonl`（进 git）。
- `data/analytics/monetize-report.md`（进 git）：各平台变现门槛进度（现状/差距/近7日净增/按速度外推达标日）+ 收益摘要。门槛数值在 `monetize-thresholds.json` 维护（含来源注记，以后台页面为准）。
- 已知缺口（2026-08-30 首采）：视频号 141 粉后台无收益中心入口（未达开通条件，属预期）；B站浏览器登录态失效（archives HTTP API 仍活），收益端点待登录恢复后抓包固化。

## 实验台账（ops-hardening，2026-08-30）

directives 提出假设，`va.experiment` 补验证闭环：`add`（登记 directive/假设/落地 slug/验证指标）→ 观察期 → `verify <id> --note "结论"`（自动拉 timeseries.db 最新指标辅助，结论必须人写——平台无对照流量不硬造 A/B）。台账 `data/analytics/experiments.jsonl`（进 git）；`make analytics-report` 的总览与 `experiments.md` 均渲染进行中/最近已验证实验。

## 播放过程分析（锚点推断法）

平台 web 端不开放秒级留存曲线（已实测：抖音 `video_data/detail`/`play_curve` 均 url doesn't match），过程分析用**真实锚点 × 句级时间轴**：

- **锚点**（`va/deep_collect.py`）：抖音 `summarize`（完播率/平均播放时长/封面点击/主页访问/涨粉 + 逐小时播放）、B站 `archive_diagnose`（完播比/3s退出率/封标点击/播转粉；`not_ready_field` 诚实置空）
- **时间轴**（`va/retention.py`）：faster-whisper `small` 本地转写 → 句级时间戳（缓存复用，`initial_prompt` 偏置技术词）
- **对齐产出**：「平均观众停在第 N 句（时间码、深度%）」+ ≤6 段落表（时间码/内容摘要/留存提示），报告明确标注为锚点推断非全量曲线
- 诊断分支：深度 <10% → 开头 30 秒流失主导；完播 <1% 且 ≥3min → 拆系列；3s 退出 ≥40%（B站）→ 钩子/封面承诺不匹配；封面点击 <3% → 换封面版式

## 数据通道（全部只读、全部复用发布登录态）

| 平台 | 通道 | 端点 | 深度指标 |
|------|------|------|---------|
| B站 | HTTP API + SESSDATA（免浏览器）| `member.bilibili.com/x2/creative/web/archives/sp` | 播放/赞/币/藏/弹幕/评/转；观看时长 P2 |
| 抖音 | patchright + 页内 fetch 翻页 | `creator.douyin.com/janus/douyin/creator/pc/work_list`（GET+max_cursor）| 播放/赞/评/藏/转/时长；完播率/CTR 走「导出 Excel」通道 P2 |
| 快手 | patchright 滚动加载 XHR 拦截 | `cp.kuaishou.com/rest/cp/works/v2/video/pc/photo/list`（带 `__NS_sig3` 签名不可直连）| 播放/赞/评/时长；定时件发布后才有 workId |
| 视频号 | patchright | 首页点「内容管理」→ 页内 fetch POST `micro/content/cgi-bin/mmfinderassistant-bin/post/post_list`（2026-08-29 接口改版迁移，旧 `mmfinderassistant-bin/post_list` 404；列表 UI 是按钮翻页滚动无效，页内 fetch pageSize=20 数页拉全量；**列表级自带播放/互动/完播率/平均观看秒/单视频涨粉**）| 登录态敏感，失效时报错降级（重新扫码恢复）|

单平台失败不阻塞其他平台，错误记 `errors.json`、报告标注缺失。

## 身份映射（join key）

`link-map.json` 的 `pub_video.{platform}_id` 是全部分析的连接键。回填两级匹配（`va/fetch_uid.py`）：

1. **标题 LCP≥12**：期望标题 = metadata.txt `标题_平台` override，否则 `crop_title(标题, title_max)`；与平台标题最长公共前缀 ≥12（容忍发布后改标题后半段）
2. **时长 ±1.5s + 发布日 ±1 天**：ffprobe 本地 mp4（缓存 `duration_cache.json`）——快手 title 常为空的主通道；**换声重渲会漂移**，重渲过的视频匹配不到就走人工

全局认领登记：一个平台 item 只能归属一个 slug（防系列视频时长接近互相抢）。手写平台标题（与 metadata 无公共前缀）→ 人工确认后直接编辑 link-map。

## 诊断口径

- **双基准**：自身历史分位数 P25/P50/P75（n≥5 启用，第一基准）→ 行业阈值兜底（`references/metrics-benchmark.md`）；n<5 强制标「样本不足仅供参考」
- **精选自查基准线（2026-08-27，openspec douyin-featured-selection）**：48h 回看——平均观看时长 >30s 且完播 >5% 为**达标**、>10% 为**强信号**；未达标自动归因到 directives（时长超标 → 豁免门禁口径；前段流失 → 15s 硬信息/H1/H5 指令）。⚠️ 这是**内部自查线非官方门槛**——官方无任何量化口径，精选按惊喜感/获得感/共鸣感定性评选，此线只用于迭代完播
- **数据成熟**：发布满 24h 且播放 ≥50 才算率值；未满 24h 标「数据未熟」
- **抖音流量池**：72h 播放对照梯度 [300 / 3k / 2w / 10w / 50w]，落位 + 差多少 + 晋级指标
- **诊断树**：卡第 1 级=冷启动问题（封面/标题/发布时间）；播放过千互动率 <5%=流量承接弱（压时长提密度）；单项率低=对应 CTA 缺失
- **已知边界**：秒级留存曲线平台 web 端不开放，过程分析为锚点推断（`make analytics-deep`）；快手深度指标 P2；5s 留存无（用平均时长深度 + B站 3s 退出率近似定位钩子问题）

## 反哺闭环

`feedback-keywords.md` 输出 Top/Bottom 系列的 weight 调整 diff（+0.5/-0.5），**不自动改** `douyin-topic/topic_keywords.json`——人工确认后编辑。样本 <3 时不建议调整。

## 风控承诺

只读自己创作者后台（不点任何写操作按钮）、手动日频（不建 cron）、平台间 sleep、登录态与发布共用（`scripts/pub/cookies/`，不新开）。视频号/快手 cookie 失效时先 `python -m scripts.pub.login <platform>` 重新扫码。

## 环境要求

- 浏览器平台：`PYTHON_PW`（Python311 + patchright，Makefile 已配）
- B站：任意 Python（stdlib urllib）
- ffprobe（时长兜底匹配用）
- Windows：`PYTHONIOENCODING=utf-8`（Makefile 已带）

## 时间序列库（2026-08-28 定规，analytics-timeseries-db）

**每日采集后跑 `make analytics-ts`**：snapshots JSONL → SQLite（`data/analytics/timeseries.db`，gitignore）UPSERT 每日一行/视频/平台 → 生成 `timeseries-report.md`（进 git：最近 5 条视频今日 vs 昨日 Δ + 发布以来趋势，含播放/点赞/评论/涨粉/完播率/3 秒跳出）。
- `py -m va.ts_db import` 幂等（同日重跑覆盖）；deep/fans 子目录快照并入（涨粉/跳出率来源）。
- 趋势判断纪律：累积 ≥7 个采集日后做趋势结论；`py -m va.ts_db query "SELECT ..."` 只读 SQL 逃生舱。
