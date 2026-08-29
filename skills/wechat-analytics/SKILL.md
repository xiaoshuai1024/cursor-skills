---
name: wechat-analytics
description: 公众号数据分析——mp 后台只读采集（单篇列表/发表记录/详情 cgiData/账号级趋势）成增量快照，标准化后做转化五级漏斗诊断（送达→打开→读完→互动→关注与原文导流）、打开/完读/转化三层分开归因、因子分桶对比与选题反哺建议。发布文章满 48h 回看、复盘公众号表现、决定文章优化方向或选题时调用。
---

# wechat-analytics 公众号数据分析

把公众号发出去的文章数据收回来，变成可执行的优化建议。是公众号管线的**反馈环**：
写作（blog-writing / wechat-retention 规范）→ 同步（wechat-publishing）→ **表现回流（本 skill）** → 反哺下一篇的标题/首屏/节奏与选题方向。

**核心目标 = 转化与留存**：完读率第一考核指标（<30% 终止 / ≥50% 进池 / >65% 加推），
关注转化（阅读后关注）与收藏是质量信号，消息打开率对标大盘（1.9% 均值 / 4% 优秀）。

## 快速用法

```bash
make wechat-analytics         # mp 后台只读采集（日频手动跑一次）
make wechat-analytics-report  # 身份映射 → 标准化 → 诊断 → 报告
make wechat-analytics-probe   # 端点健康检查（改版/登录态失效时定位哪条通道断了）
make wechat-analytics-test    # fixtures 单测（不依赖登录态）
```

登录态失效（probe 报 token/ticket 拿不到）→ `make wechat-auth` 扫码恢复后重跑。

**48h 回看纪律**（openspec wechat-retention）：文章发布满 48h → 跑上面前两条命令 →
看该篇诊断卡核对结论 → 结论一句话写 `content/link-map.json` 该 slug 的 `weixin` 备注。

## 数据通道（2026-08-29 spike 实证）

| 端点 | 拿到什么 | 备注 |
|------|---------|------|
| `appmsganalysis?action=get_article_list` | 单篇 msg_id/标题/群发日/阅读/30 天趋势 | 直连 GET，无需 fingerprint |
| `cgi-bin/appmsgpublish?sub=list` | 群发时间 + 送达数 + appmsg_info（appmsgid 与统计 msg_id 同域） | 每页固定 20 条，需翻页 |
| `appmsganalysis?action=detailpage` | **HTML 内嵌 cgiData JSON**：完读率/新增关注/在看/收藏/留言/平均阅读时长/跳转/逐日×场景/用户画像 | 服务端渲染，免轮询；仅发表后 30 天内 |
| `appmsganalysis?action=get_article_stat_tendency_and_source` | 账号级日趋势×场景（scene 6=推荐）+ 收藏 | 直连 GET |
| `datacubequery` tmpl=28 | 5% 节点留存曲线等深度数据 | 服务端异步，delay:true 当日缺失，日频重试自然收敛 |

风控承诺：全部只读；请求间随机 sleep 3-8s；同日详情去重；单接口失败降级不阻塞；
**不触碰任何写端点**（与 publish_mp 的写通道物理分离）。

## 数据与产物

数据落 `data/wechat-analytics/`（**进 git**，时间序列历史不可再生）：
`snapshots/articles.jsonl`（list/detail 增量快照）+ `snapshots/account.jsonl`（账号级+发表记录）
+ `identity.json`（msg_id↔slug 映射）+ `metrics.json` + `diagnosis.json` + `errors.json`。

报告落 `.wechat-analytics/reports/`（生成物，git 忽略）：

| 文件 | 内容 |
|------|------|
| `YYYY-MM-DD-per-article/<slug>.md` | 单篇诊断卡：五级漏斗评级 + 留存曲线流失节点 + 证据→诊断→动作 |
| `overview-YYYY-MM-DD.md` | 账号总览：近 7 天来源结构 / 单篇排行 / 因子分桶（样本 <3 禁结论） |
| `feedback-topics.md` | 选题反哺：样本 <5 篇降级观察清单，≥5 篇出加权 diff（人工确认后才写回） |
| `report.json` | 机器可读全量诊断（link-map 48h 备注可直接引用） |

## 身份映射（msg_id ↔ slug）

三层匹配，静默猜测禁止：① `data/wechat-analytics/identity-overrides.json` 人工指定
（`{"msgid": "slug"}`，48h 回看时顺手登记）；② 标题精确匹配（归一化）；③ 最长公共子串
≥12 字且唯一。剩余列 `identity.json` 的 unresolved 供人工确认。
平台标题是手写变体（与源稿 `wechat_title` 常完全不同），精确匹配命中率天然偏低，
overrides 是常态通道。

## 已知口径与坑

- **平台标题≠源稿标题**：手写变体，别指望标题全对上。
- **人日近似口径**：detailpage 只给日粒度 read_user，来源构成与消息打开率是逐日累加
  近似，跨日重复阅读会偏高（>100% 即此情况），看趋势不看绝对值。
- **mp 侧数据延迟**：新发文章的统计行可能整体延迟数天才进 `get_article_list`
  （tmpl=28 同理）；collect 会打印「N 篇统计行缺失」，日频重采自然收敛，不要重试轰炸。
- **read_uv_ratio ≠ 打开率**：它是「阅读人数占比」（分母=期间总阅读人数）；真打开率 =
  阅读/送达（含推荐口径，可 >100%）+ 消息列表打开（对标基准的可比口径）。
- **detailpage 只统计发表后 30 天内数据**，老文章详情拿不到（诚实缺失）。
- scene→来源标签映射经 UI 图例校准（2026-08-29：推荐 85.6% = scene 6 主导），
  若微信调整再校准 `common.SCENE_LABELS`。
