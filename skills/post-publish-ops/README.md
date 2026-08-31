# post-publish-ops 视频发布后运营

视频在四平台（抖音/快手/B站/视频号）发布完成**之后**的全部运营动作，沉淀成一个 skill——发布不是终点，是流量的起点。

Agent 工作流入口见 [SKILL.md](SKILL.md)；本 README 是给人看的能力说明。

## 解决什么问题

发布完成（link-map 四平台齐全）之后，各平台后台还有一整面可操作的运营位：置顶作品、动态、弹幕、私信、官方活动、公众号联动……这些入口此前在仓内**零档案**，新运营点全靠偶遇。本 skill 把它们盘成一张矩阵，并给出发布后的统一时间线。

## 覆盖能力

**发布后时间线**（t = 发布时刻）：

| 时点 | 动作 |
|------|------|
| t+20-30min | 四平台状态复查首查（`make pub-audit`） |
| t+1h | 置顶评论（挂抖音粉丝群链接，`ops pin`） |
| t+24h | 状态二查 + 数据回流启动 |
| t+24-96h | 评论承接（`make comment-reply`，逐条确认） |
| t+44-96h | 深度回看对照基线 + 系列健康度 |
| t+7-12d | 转化/系列判断（≥5000 播放评估加拍） |
| 随时 | 置顶作品位轮换 / B站动态 / 私信承接（新运营位） |
| 活动窗口 | 平台免费官方活动/任务（有截止日进 ASK） |
| 每次发文 | 视频号×公众号联动 |

**新运营位矩阵**（2026-08-31 四平台只读实查结论，详见 SKILL.md）：

- ✅ 直接可用：抖音主页置顶作品位（已在用）、抖音发布后编辑、B站稿件编辑（补 fix-cover 缺口）、视频号发布后编辑、四平台活动/任务入口
- ⚠️ 有条件：B站评论管理含「待精选评论」+弹幕管理、视频号互动管理三件套（评论/弹幕/私信）、快手权益恢复（当前降级 V1）
- ❌ 不做（定规）：**直播、一切付费加热**（DOU+/粉条/必火推广/视频号加热）

## 硬定规

1. **不做直播**（2026-08-31 用户定规，永久排除）。
2. **不投流**：一切付费加热零预算；平台**免费**活动/任务不受此限。
3. 其余运营点全做；缺工具走 `ops` 表登记（platform-ops-toolkit 定规），禁止另起新脚本。
4. 只读先行：新运营位先截图+XHR 留证实查，写操作逐个立项、必问门禁后才实改。
5. 手动触发、一次一平台、先看 `make pub-status` 避风控冷却；永不挂无人值守定时。

## 怎么用

对 Agent 说「**发布后运营**」「**置顶作品**」「**发个动态**」「**看看平台活动**」等即触发（详见 SKILL.md description）。

探查脚本（只读 dry-run，产出截图+XHR 留证）：

```bash
py -3.11 scripts/pub/post_publish_explore.py [douyin|kuaishou|bilibili|shipinhao|all]
# 留证: scripts/pub/vendor/logs/post_publish_explore/<plat>/
```

## 与其他 skill 的分工

| 事项 | 归属 |
|------|------|
| 评论承接（分诊/回复/置顶评论） | comment-auto-reply（本 skill 只索引） |
| 发布中链路（七字段矩阵/风控/audit） | video-generation publishing.md |
| 合集转化与合集数据 | video-generation publishing.md「合集数据与转化定规」 |
| 数据回流/回看/变现 | video-analytics / wechat-analytics / monetize 链 |
| 作品管理操作（delete/status/find） | `ops` 统一入口（platform-ops-toolkit） |
| **本 skill 拥有** | 置顶作品位、动态、弹幕、私信、免费活动、公众号联动、发布后时间线总览 |

## 环境要求

- Python 3.11 + patchright；四平台登录态 `scripts/pub/cookies/{douyin,kuaishou,bilibili,shipinhao}.json`
- 运营节拍类（make next）纯本地零平台请求；实查/写操作需登录态且手动触发

## 来源

openspec `post-publish-ops-explore`（2026-08-31 调研决策：直播/投流不做、其余全做，落地载体=本 skill）。活动/话题信息有时效性，投稿前重进活动页核对截止日与规则。
