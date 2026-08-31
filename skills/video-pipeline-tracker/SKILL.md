---
name: video-pipeline-tracker
description: 视频生产全生命周期状态台账。单一事实源 state.json 记录每部视频从写作到归档的 stage（backlog/drafting/article_done/article_published/narration/synthesizing/rendered/scheduled/published/archived + blocked 标志）、各平台定时与状态、history 追溯；vpt CLI 四命令（stage/queue/sync/report）维护并自动重生成 Markdown 看板（进行中/发布队列含每日一篇冲突标记/归档近况/平台数据）。多任务窗口共享同一文件。用户说「视频状态/排期看板/队列/台账/更新状态」时调用。
---

# Video Pipeline Tracker — 视频生产状态台账

**SSOT**：`data/video-pipeline/state.json`（进 git，多窗口共享）；**呈现**：`data/video-pipeline/dashboard.md`（每次变更自动重生成）。本 skill 只**记录与呈现**——发布走 video-generation 的 publish 链、数据采集走 video-analytics、渲染走 video-generation；台账在流程节点被调用。发布在途/风控冷却由 blog-src `scripts.pub.pub_guard` 登记制维护（`publish-jobs.json` + `publish-log.jsonl`，2026-08-31 起），本台账 **queue/report 只读呈现、绝不回写**。

## 何时用

- 视频流程推进到节点（文章完成/口播确认/合成/渲染完成/挂定时/出片/归档）→ `stage` 记录
- 「现在队列里有什么、排到哪天、有没有撞档」→ `queue`（含发布在途/风控冷却一行摘要）
- 「有没有别的会话正在发布、平台风控冷却中」→ `make pub-status`（blog-src，pub_guard 看板，纯本地）
- 怀疑台账与现实漂移 → `sync`（从目录/link-map/analytics 快照推导并入，只读外部源）；日循环发布后收尾直接 `make reconcile`（blog-src，批量 sync + 复算 make next）
- 看全貌 → `report` 或直接打开 `data/video-pipeline/dashboard.md`

## 用法

```bash
cd skills/video-pipeline-tracker/scripts   # 或 Makefile: make vpt-queue / vpt-report
py -3.11 vpt.py stage <slug> rendered --note "四道门禁全过"     # 推进状态
py -3.11 vpt.py stage <slug> scheduled --schedule douyin=2026-08-29\ 20:00 --schedule kuaishou=2026-08-29\ 20:00
py -3.11 vpt.py stage <slug> synthesizing --block "合成任务僵死，重跑中"   # 阻塞标注
py -3.11 vpt.py queue                                          # 排队视图（同日多条标 ⚠️CONFLICT）
py -3.11 vpt.py sync <slug>                                    # 现实源推导并入（--all 全量）

sync 实据口径（2026-08-30，openspec pipeline-reconcile）：发布实据 = link-map `pub_video.results.*.ok`——`published_at` 单独不算（失败的单平台尝试也会盖章）；`results.ok` 优先于 schedule（已发布平台不可能还有未来定时，有则是残留卡，晋升时清理）；published 晋升档已补齐（发布未归档不再卡 scheduled）。
py -3.11 vpt.py report                                         # 重生成 dashboard
```

## stage 枚举（有序）

`backlog → drafting → article_done → article_published → narration → synthesizing → rendered → scheduled → published → archived`

- 任意 stage 可叠加 blocked（`--block 原因`），stage 不变；解除用 `--unblock`。
- `scheduled` 必须带 `--schedule 平台=时间`（四平台齐才算挂好，每日一篇原则：同日只许一条）。

## 与其他 skill 的边界

| 资产 | 关系 |
|------|------|
| `content/link-map.json` | 发布证据源，`sync` 只读并入，**不回写**（单向数据流，根治覆盖事故） |
| `data/analytics/snapshots/` | 数据源（video-analytics 采集），dashboard 数据列引用最新值 |
| `data/video-pipeline/publish-jobs.json` + `risk-backoff.json` | 发布在途登记/平台风控冷却，`scripts.pub.pub_guard` 与 `scripts.pub.backoff`（blog-src）独占写，queue/report **只读呈现** |
| `video-generation` build/archive 目录 | stage 下限证据（sync 推导）；其 SKILL.md 流程节点含 vpt 调用示例 |

## 工程约束

- 写入原子（tmp + os.replace）；stage 枚举/必备键校验，坏数据拒写。
- 并发 last-write-wins：不同 slug 互不影响；同 slug 同时推进以 history + `sync` 恢复。
- dashboard.md 进 git（人机共读、可 diff）；`state.json` 同样进 git。
