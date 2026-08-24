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
```

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
| 视频号 | patchright | `channels.weixin.qq.com/.../post_list` | 登录态敏感，失效时报错降级（重新扫码恢复）|

单平台失败不阻塞其他平台，错误记 `errors.json`、报告标注缺失。

## 身份映射（join key）

`link-map.json` 的 `pub_video.{platform}_id` 是全部分析的连接键。回填两级匹配（`va/fetch_uid.py`）：

1. **标题 LCP≥12**：期望标题 = metadata.txt `标题_平台` override，否则 `crop_title(标题, title_max)`；与平台标题最长公共前缀 ≥12（容忍发布后改标题后半段）
2. **时长 ±1.5s + 发布日 ±1 天**：ffprobe 本地 mp4（缓存 `duration_cache.json`）——快手 title 常为空的主通道；**换声重渲会漂移**，重渲过的视频匹配不到就走人工

全局认领登记：一个平台 item 只能归属一个 slug（防系列视频时长接近互相抢）。手写平台标题（与 metadata 无公共前缀）→ 人工确认后直接编辑 link-map。

## 诊断口径

- **双基准**：自身历史分位数 P25/P50/P75（n≥5 启用，第一基准）→ 行业阈值兜底（`references/metrics-benchmark.md`）；n<5 强制标「样本不足仅供参考」
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
