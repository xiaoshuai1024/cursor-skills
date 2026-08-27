---
name: comment-auto-reply
description: 评论自动回复（手动单命令）。采集 B站/抖音近 14 天作品的未回复一级评论 → 规则分诊（A 无信息量跳过 / B 技术提问 LLM 草稿 / C 负面·求资源·观点转人工队列）→ 逐条交互确认 → 自建通道发送（B站公开 API / 抖音评论管理页 DOM）+ 回读验证。用户说「回复评论/评论承接/跑一下评论」时调用。
---

# comment-auto-reply 评论自动回复

video-engagement-cta「24h 回复承接」的自动化实现。**单命令手动触发**（2026-08-27 用户定规：不挂 schtasks 定时，用户自己跑）。

## 用法

```bash
make comment-reply                      # 全流程（B站+抖音 → 分诊 → 逐条确认 → 发送）
make comment-reply args="--dry"         # 演练：走到发送前留截图，不实发
make comment-reply args="--platform douyin --no-llm"
```

**定向回复单条**（用户贴来一条评论要回时，不跑整轮）：

```bash
make comment-reply args='--locate 本源之外'        # 采集两平台按昵称/正文搜，命中落 work/locate.json
# 确认稿子后（≤120 字，见下方写稿纪律）：
make comment-reply args='--reply douyin:<video_id>:<comment_id> --text "回复正文"'
```

`--reply` 走与整轮一致的纪律：合规门禁、配额、账本幂等（已 sent 拦截）、回读验证、kill switch。2026-08-27 首次实发并回读验证通过。

**撤回自己已发的楼中楼回复**（仅抖音；默认演练——点到「确定要删除吗」弹窗即自动取消，不实删，用于走通路子）：

```bash
make comment-reply args='--delete douyin:<video_id>:<comment_id>'          # 演练：定位→点「删除」→弹窗截图→取消
make comment-reply args='--delete douyin:<video_id>:<comment_id> --commit' # 实删 + 回读验证（账本记 manual 防重入队）
```

`--delete` 从账本取该 key 已 sent 的 `reply_text` 定位楼中楼；`--commit` 成功后记 manual（不再进自动队列），演练不写账本。2026-08-27 演练走通到确认弹窗（截图留证 work/del_*.png）。

实现在 `scripts/comments/`（reply.py 为 CLI 入口），数据落 `data/comments/`。

## 通道（2026-08-27 spike 实证，勿走回头路）

| 环节 | B站 | 抖音 |
|------|-----|------|
| 作品源 | link-map `bilibili_id`（或 `bilibili_aid`，只有 aid 没有 bvid 的作品也要扫）→ aid | link-map `douyin_id` |
| 读评论 | 公开 API `x/v2/reply/main`（`root=0` 一级） | 评论管理页 `creator-micro/interactive/comment?item_id=` 域内无签名 fetch `comment/list/select`（一级）/`list/reply`（子回复） |
| 已回判定 | 子回复 `mid == DedeUserID` | 子回复昵称 ∈ creator_nicknames（默认「1024工程笔记」） |
| 回复 | `x/v2/reply/add`（SESSDATA+bili_jct） | 页内「回复」按钮 → contenteditable（placeholder=`回复 <昵称>：`）→ 发送 |
| 验证 | 发送后回读 `reply/reply` | 发送后回读 `list/reply` |
| 删自己的回复 | —（后台手工） | 行内「删除」（直接文本节点匹配，从正文上溯 ≤20 级找公共容器，命中后**回验同楼**再取坐标点）→「确定要删除吗」弹窗 → 回读 `list/reply` 验证消失。楼中楼先展开：「N 条回复」入口在行容器外兄弟分支，页面级按「文本长度+矩形面积最小」候选逐个试点 |

⚠️ 抖音评论管理旧路由 `comment/manage` 已重定向（2026-08-27 UI 改版），勿再用；「回复」按钮带图标子节点，DOM 匹配用直接文本节点（`childNodes` text === '回复'），不能用叶子节点过滤。

## 分诊口径（triage.py，规则不依赖 LLM）

- **A 无信息量**（纯赞/表情/打卡/超短）：不回只记账——刷回复是最强机器人信号，伤号
- **B 技术提问**（问句或技术词）：LLM 草稿（可选）→ 交互确认后发
- **C 人工队列**：负面/引战、求资源/求私联（导流风险）、观点表态、超长评论——**只展示不自动回**
- **盖楼**：默认不回；楼内纠错类 → `floor-correction` 进人工队列（必须让人看见，不回会持续误导）；高热度追问（楼内 +1≥2）→ 人工队列
- LLM 草稿**事实锚定**：注入该视频口播稿/文章（anchor.py），材料没覆盖走兜底话术，禁止现编

## 风控纪律（spec 硬性要求，勿放宽）

- 单轮单平台 ≤5 条、每日单平台 ≤15 条（账本自动算配额）
- 多条发送间隔随机 40–180s（人工确认耗时计入）
- 仅近 14 天作品；kill switch：`data/comments/DISABLED` 存在即只采集不发送
- 每次发送后回读验证（不信发送动作返回）；每步截图落 `data/comments/work/`
- 发送前过 platform-compliance 词库（HIGH 命中即拦）
- 账本 `reply-ledger.jsonl` 进 git（幂等：已 sent/manual/skipped 的不重复出队）

## LLM 配置（可选）

`data/comments/config.json`（git 忽略）：
```json
{"llm": {"base_url": "https://api.xxx/v1", "api_key": "sk-...", "model": "glm-4-flash"},
 "creator_nicknames": ["1024工程笔记", "1024 工程笔记"]}
```
未配置时 B 档全部人工写稿（`e` 直接输入），整链不依赖 LLM。

## 写稿纪律（2026-08-27 用户反馈定规，LLM 与人工写稿同守）

- **直接从答案讲起**：不设计回应评论措辞的口径化开场——观众求私下讲解时回「不用私，就在这讲」被判生硬；也不写「好问题」「问得好」类客套。观众想私下请教 = 把干货直接写进公开回复，不提私聊也不声明不私聊。
- **类比只用大白话生活类比**（记账/查账/建索引这级）：「不装海马体」这类冷门领域梗连作者本人都要问一句什么意思，评论区受众比文章读者杂，看不懂的类比不如不比。
- 事实锚定纪律不变：答案必须在锚定材料里有依据，材料没覆盖走兜底话术。
- **尊重事实（2026-08-27 定规）**：不虚构作者本人的做法——没做过的实践不能写成「我的做法是…」（编造「我锁一个稳定版跑日常」被打回撤稿）。收尾没真实个人实践可写时，直接删掉那段，改为说明该方案/做法自身存在的问题与取舍，不拿编造的经历凑收尾。

## 复盘

每周人工抽查账本里 `sent` 的回复质量（技术准确性 + 语气），翻车案例写回本 skill。首次 B站实发后确认 `verify_sent` 回读口径有效（写通道当时未实发验证）。

已沉淀案例：
- 2026-08-27 「本源之外」问 dsh 事件记忆原理：初稿「不用私，就在这讲」开场 + 「海马体」类比双双被用户打回（见写稿纪律），改为直答 + 记账类比后定向发送成功。
- 2026-08-27 「以古论今」评 dsh 本地化：初稿收尾编造「我锁一个稳定版跑日常」（作者并无此实践）→ 定规「尊重事实」（见写稿纪律），更正方向 = 删掉该段、只讲自维护分叉自身的问题（新功能要自己跟着上游升级合并、分叉越久越难合回）。同日楼主在该楼连发追问、暂缓删稿；删除通道（`--delete`/`--commit`）以演练模式实测走通到「确定要删除吗」弹窗即取消，未实删。


## 置顶评论发布器（2026-08-27 新增，`scripts/pub/douyin_comment_post.py`）

发**一级评论**（回复走 reply.py 的 send_reply，一级评论此前无工具）。三个子命令：
`find --title <关键词>`（内容管理页按标题找 item_id——**卡片 DOM 不暴露 item_id**，靠点「评论」入口从跳转 URL 抓）/ `post --item-id <id> --text-file <文案> [--dry]` / `pin`（web 端无置顶入口，抖音置顶只能在 App 长按自己评论——pin 子命令仅当页面出现按钮时可用）。

**实战坑（全已修进代码，改时别回退）**：
- async playwright 的 screenshot 必须 await——同步 lambda 调用得到未执行 coroutine，**截图全空且无报错**（只有 RuntimeWarning），留证机制静默失效；
- 评论管理页「发送」按钮是**非 `<button>` 标签**——`button:has-text()` 全不中，用直接文本节点匹配（同「回复」按钮手法）；
- 新发评论**不进管理页首屏列表**（显示「暂无更多评论」）——定位/置顶前先检测并 reload；回读 `list/select` 对新评论有延迟（total=0 是常态），回读失败时以 sent 截图为证返回，勿误报失败；
- pin 流程改动时注意 `needle = _norm(match)[:16]` 定义必须留在 reload 逻辑之后（吞过一次 NameError）。
