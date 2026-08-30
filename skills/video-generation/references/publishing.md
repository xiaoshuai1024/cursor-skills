# 多平台发布细则（publishing）

> 拆分自 SKILL.md「发布到多平台」「成片生命周期」（2026-08-30，openspec video-generation-skill-split），内容逐字保留；发布红线摘要仍在我 SKILL.md 存根。

## 成片生命周期：build → archive（2026-08-24 定规，强制）

- **build/ 只放待发布与在售视频**。视频在平台发布完成后（判定依据：`data/analytics/snapshots/` 的 B站/抖音/快手快照里，能按 `metadata.txt` 标题对到条目），及时 `mv build/<slug> archive/<slug>`，并在 `video-generation/archive/README.md` 归档清单登记（目录 / 归档日期 / 平台 item_id 证据）。
- **archive/ 只进不出**：不挪回 build、不改内容物；确需重发/重渲，先在 README 变更日志登记原因和日期再动手。抖音定时发布的视频（成片已传平台）本地可直接归档，不影响定时任务。
- **测试/demo 成片验证完即删**（如 motion-showcase），不留 build；发布证据核对用标题逐一比对，不做模糊匹配。
- 2026-08-24 已执行一轮：claude-codex 源码系列全 6 期 + video-pipeline-6-skills 归档；build 存量 2 支未发布正式稿（ai-buzzwords-one-line、codex-auto-video-editing）。
## 发布到多平台（自建管线，2026-08-23 七字段定规）

视频渲染完成后分发到抖音 / 快手 / 视频号 / B站（2026-08-21 定规：小红书因被风控处罚且无播放分成机制已移除；公众号流量主门槛高已放弃；头条由抖音发布页「同时发布」同步，账号默认开启）：

```bash
# 默认全平台 dry-run(发布页全字段填完+预览截图)
make pub-video slug=xxx
# 正式发布（定时）
make pub-video slug=xxx platforms=douyin confirm=yes schedule="2026-08-25 20:00"
```

### 七字段矩阵（2026-08-23 定规：标题/简介/话题/封面/定时/合集（可创建）/原创声明——每平台发布必须全过一遍）

| 字段 | 抖音 | 快手（v2 现役） | 视频号 | B站（biliup） |
|------|------|------|--------|------|
| 标题 | ✅ 裁剪≤30 | ✅（描述承载，≤50） | ✅ ≤63 | ✅ `--title` ≤80 |
| 简介 | ✅ desc | ✅ 描述 | ✅ | ✅ `--desc` |
| 话题 | ✅ 面板选择 ≤4 | ✅ 描述内 # 文本（快手解析为标签，**必须 ≤4**，超出在描述阶段裁剪） | ✅ | ✅ `--tag` ≤6 |
| 封面 | ✅ 横版 | ✅ v2 封面步骤（上传+预览等待+失败即中止） | ✅ 横竖 | ✅ `--cover` 横版 |
| 定时 | ✅ | ✅ v2 | ✅ | ✅ `--dtime`（距提交 >4h） |
| 合集 | ✅ apply_collection 选已有（下拉易被浮层拦截，先清浮层再点）；**合集本体 Web 可管理（2026-08-30 实证，推翻「Web 无入口 App 手动」旧论）：`creator.douyin.com/creator-micro/content/manage?tab=collections` → 编辑合集（标题≤20/简介≤200/封面 1080×1080 ≤5M/添加作品/拖拽排序）；添加作品抽屉必须搜索关键词触发且 headless 不渲染列表（headful + `[class*=plus-area]`）；元信息变更触发约 1h 平台审核；工具 `scripts/pub/douyin_collection_edit.py`（meta\|members\|verify）** | ✅ 合集内发布：v2 `argv[3]=collectionId`（现役合集「AI 编程实战课」=263304580，2026-08-30 由「AI 研发实战」改名、ID 不变）；合集本体编辑页只有标题(≤12)/展示设置/添加作品（无封面/简介字段，封面取首成员缩略图）；**一个作品只能在一个合集**（补挂自动迁出旧合集）；公开展示门槛=有效剧集数（6/9 集均「未公开展示」、38 集过）；工具 `scripts/pub/kuaishou_collection_edit.py` | ✅ apply_collection | ❌ 权益两级门：Lv2 仅解锁入口，创建受「合集个数」配额限（2026-08-30 API 实证 20082「您创建的合集个数太多了」而 seasons total=0，配额按粉丝量定级）；全流程 API 脚本已备好 `scripts/pub/bilibili_collection_create.py`（封面上传 `/x/vu/web/cover/up` base64 需 `data:image/png;base64,` 前缀），配额达标一键建 |
| 原创/AI 声明 | ✅ 自主声明→内容由AI生成（失败拒发） | ✅ v2 作者声明→内容为AI生成（单选下拉，失败抛错阻断） | ✅ 视频标注→含AI生成内容（strict，失败阻断） | ✅ biliup `--extra-fields` 传 creation_statement + `--copyright 1 --no-reprint 1` |

**合规口径（2026-08-30 定规，最高优先）**：四平台发布必须带 **AI 生成声明 + 原创（自制/禁转载）双声明**，声明失败一律阻断发布、禁止裸发。平台实现与坑：抖音「自主声明→内容由AI生成」；快手 v2「作者声明→内容为AI生成」（单选下拉，实测选项：内容为AI生成/演绎情节/个人观点/素材来源于网络，**绝不能选素材来源于网络=否认原创**）；视频号「视频标注→含AI生成内容」strict 模式（另有创作分成弹窗点「声明原创」保流量收益）；B站 biliup `--extra-fields` 传 `creation_statement:{"id":1,"content":"含AI生成内容"}`（**只认对象形态，传 neutral_mark 整数报 21001**；枚举同源 archive/pre）+ `--copyright 1 --no-reprint 1`。dry-run 不回收 link-map（曾把正式记录覆盖成 dry-run 结果）。

### 快手现役通道：`scripts/pub/kuaishou_publish_v2.py`（2026-08-23 定规）

> 主管线 vendored KSVideo 的「加入合集」ant-select 已随快手发布页改版失效（页面无合集/原创/AI 入口），v2 为现役快手通道：

```bash
python scripts/pub/kuaishou_publish_v2.py <slug> "YYYY-MM-DD HH:MM" [collectionId]
```

- 流程：草稿放弃 → 上传 → 描述（话题 ≤4 裁剪）→ 地区 → **封面（上传+预览验证）** → 定时 → 合集内发布（URL 带 collectionId）→ 发布验证 → link-map 条件写入
- 坑位：① 描述话题超 4 个会被快手拒发（「话题标签数量超过上限：4」）；② 话题联想面板选择器已失效，话题以描述 # 文本生效；③ 定时作品公开后才计入合集「有效剧集」（发布后验证）；④ **desc 清空 bug（2026-08-29 已修、08-30 加回读门禁闭环）**：vendored `ks_uploader_main.py` 打完简介后有一步 08-20 加的「Control+A→Delete→12×Backspace 清残留 chips」，实际把刚打的简介全选删光、只剩话题循环补的标签——线上共 5 支中招成纯标签作品（08-22 arch-overview / 08-25 auto-editing / 08-27 desktop-tutorial+token-bill / 08-28 five-levels，08-29 修复时只发现 2 支），v2 通道无此步故未全灭。修复=移除打完后的清空（打字前的清空保留）+话题循环跳过简介文本已含标签防双写；**2026-08-30 升级**：四上传器（快手 v1/v2、抖音、视频号）发布前回读门禁 + B站投稿前字段校验（见「严禁只有话题没有标题/简介的作品上线」），线上 5 支受害作品经 `kuaishou_fix_desc.py`（workId 直达 `article/edit/video?workId=`，无需卡片定位；编辑器回读校验后 dump 坐标点发布；列表接口 photo/list 复核简介已更新——DOM 卡片复核受列表加载时序影响不可靠）全部补回标准简介闭环
- 配套：`kuaishou_fix_cover.py`（已发布作品补封面，2026-08-29 适配改版 UI：定位支持 `搜索词|卡片唯一子串` 双关键词（纯 `-"` 跳过搜索走列表子串，纯标签简介的作品搜索索引搜不到）；封面入口两态——已自定义封面点「编辑封面」/ 从未设过封面直接点当前封面图（该态弹窗有静态 file input 可直接 set_input_files）；「清空上传」→拖放区 `expect_file_chooser` 拦截选图兜底；确认按钮「完成」/「确认」两态兼容；get_by_text/locator 对该站部分元素计数为 0，按钮一律 dump 坐标点击；**卡片 img src 前后变化为唯一真验证**。清空只改弹窗草稿，不点完成/发布则作品封面不受影响）、`kuaishou_delete_scheduled.py`（按关键词删定时，去重用）、`kuaishou_delete_video.py`（删已发布作品，先只读扫描确认唯一命中再 --confirm）、`kuaishou_check_status.py`（定时状态检查）

### B 站通道：biliup-rs

- 601「上传过快」频控为账号级，触发后等 24h+ 再试（2026-08-21 触发、08-23 解除实证）；批量投稿逐篇间隔 ≥300s
- **21566「投稿过于频繁」≠ 601**（2026-08-23 实证）：投稿**次数**限额（当前账号 10 篇/天），当日投满后视频文件仍能上传成功但提交被拒、报 `Unknown Error`。批量 >10 篇必须跨天；命中后等 24h 滚动窗口过后重试
- `--dtime` 定时距提交需 >4h；封面 `--cover` 本地横版路径自动上传
- 投稿后字段核对：`/x/web/archives`（稿件列表）、`/x/vupre/web/archive/view?aid=`（详情，浏览器内 fetch；requests 直调 404）

### 全平台发布与逐平台状态确认（2026-08-27 修订：取消抖音先行顺序门禁）

> 背景：原「抖音先行 + 后台状态门禁」（2026-08-20，源自 ccswitch 抖音被拒导致多平台无效副本）要求先发抖音、确认其状态再发其余平台。2026-08-27 用户定规**取消发布顺序约束**：四平台不分先后，串行执行只为 cookie 会话与 link-map 写入安全；发布成功与否由**现存检查工具逐平台确认**，某平台被拒按「发布后复查闭环」层级处置，**不再前置阻断其他平台**。

- **全平台缺省（2026-08-27 用户定规，优先级最高）**：发布一个视频 = **抖音/快手/B站/视频号四平台全发**，这是缺省动作不是可选项。**禁止「只发抖音、其余平台等数据起量再跟进」**——「待数据起量后跟进」「待跟进」这类挂起理由一律无效（2026-08-27 DSH ep1 事故：只发抖音挂了 12 小时+ 才被用户发现补齐；同类还有 transformer-matrix-internals 只发抖音、codex-desktop-tutorial 漏 B站/快手）。
  - 仅两类例外可少平台，且必须显式声明理由并报告用户：① **内容级拒绝主题**按 AGENTS.md 2026-08-27 定规排掉具体平台（如第三方模型接入官方客户端教学不排抖音——注意这是「排掉某平台」，其余照发，绝不是「只发一个平台」）；② 用户明示指定平台子集。
- **发布执行（无顺序约束）**：四平台同窗口挂齐，串行跑。快手走 v2（`py -3.11 scripts/pub/kuaishou_publish_v2.py <slug> "YYYY-MM-DD HH:MM"`）；B站 `--platforms bilibili`（biliup dtime 平台侧定时）；抖音 `--platforms douyin`；视频号 `--platforms shipinhao`（**2026-08-28 实测定规**：平台侧定时只认 ~24h 内近档——当天档可挂成功（五级卡「将于8-28 20:00发表」实证），跨日档表单态全对但提交被**静默降级为立即发表**（9-1×3、8-30 41h×1 四次实验实锤）；跨日档一律 schtasks 到点直发兜底）。
- **发布成功确认（用现存检查工具，上传器日志不可信）**：每个平台发布/挂定时后，用对应检查工具确认实际状态——抖音 `py -3.11 -m scripts.pub.douyin_check_status "<标题关键词>"`、快手 `py -3.11 -m scripts.pub.kuaishou_check_status <关键词>`、视频号 `py -3.11 -m scripts.pub.shipinhao_delete_video --scan`、B站稿件列表（`.tmp/bili_archives_check.py`，浏览器内 fetch `/x/web/archives`，state=-40 定时中 / 0 通过可见）。判据与节奏见「挂定时后必须复核实际状态」与「发布后复查闭环」。**检查不过 ≠ 连坐**：只处理该平台（按复查闭环的层级处置），其余平台照发照查。
- **严禁只有话题没有标题/简介的作品上线（2026-08-30 用户定规，全平台最高优先）**：任何平台的简介/描述都必须以正文为主体（标题或正文钩子在场），话题标签只能作正文后的附加行——**线上不得存在「打开作品只有一串 #标签、没有一句正文」的作品**。① 发布前门禁已内建：四上传器（快手 v1/v2、抖音、视频号）填完标题/简介后**强制回读校验**，正文不在场即阻断发布并截图（`*_desc_guard_fail.png`），B站 CLI 通道投稿前校验标题/简介字段本体非空——回读失败宁可发布失败，不许静默上线；② 发布后复核以**列表接口回读简介**为准（快手 photo/list、抖音 work_list、视频号 post_list 的 title/desc 字段），发现话题-only 立即编辑页补正文；③ 历史事故：2026-08-20~08-28 快手 v1「清残留 chips」步骤删光简介，线上 5 支纯标签作品（five-levels/desktop-tutorial/token-bill/auto-editing/arch-overview），2026-08-30 经 `kuaishou_fix_desc.py`（workId 直达编辑页，dump 坐标点发布，列表接口复核）全部补回标准简介闭环。
- **抖音简介乱码治理 + 话题策展（2026-08-30 审计定规）**：
  - **根因（未修完的管线 bug，修复前每次上传都会复发）**：`meta.py::build_description` 把「话题」行拼进简介，douyin_uploader_main.py 的 fill_title_and_description 又逐个手打话题——双写叠加被话题下拉打乱，08-22 起的 20 支简介尾部形如 `#deepseek #h a#源 码#AI编程码解析arness`（线上可见乱码，含 9 支 DSH 定时卡）。管线修复二选一（待办）：抖音变体简介不补话题，或上传器检测 desc 已含话题行则跳过手打（快手 v1 已有同款 `if f"#{tag}" in desc_text: continue`）。
  - **存量修复脚本 `scripts/pub/douyin_fix_topics.py`**：mid 直达编辑页（`creator-micro/content/post/video?mid=<id>&enter_from=edit_item`；定时卡按钮=「继续编辑」、已发布=「编辑作品」）→ 读旧简介截掉 # 尾 → 重打干净正文+策展话题行 → 三重守卫（正文在场/≥3 话题/旧文标记出现即拒交+截图）→ 点「提交修改」→ cover/gen/post 响应 status_code=0 判成。逐支结果记 `D:/tmp/pub_field_audit/douyin_fix_log.json`。**2026-08-30 当日 20+ 次尝试全被编辑器回爬拦截（零脏写上线）**：字节 magic-editor 受控模型会把初始文档回爬追加（清空/原子替换 insertText/有头模式/冷却重试均复现），脚本已完备，换时段新会话先跑金丝雀 `python scripts/pub/douyin_fix_topics.py 7678904270594297123`（ep3），通过即放量；**9-1 08:00 首批 DSH 定时卡发出前必须完成**（脚本或人工创作者中心逐支改约 20 分钟）。
  - **抖音编辑页/管理页改版实录（2026-08-30）**：管理页**无「定时发布」tab**（定时卡混在「全部」列表，卡片带「定时发布中 定时: xxx / 修改定时」标记；douyin_check_status.py 的 tab 清单过时，「全部」tab 兜底仍可用）；新增「作品合集(N)」入口；提交保存 = `POST /aweme/v1/cover/gen/post/`（payload 含 title/caption/cover_uri 等，**话题由服务端从 caption 的 #token 解析——纯文本话题行即生效，无需下拉 chip 化**；提交成功页面跳创作中心首页）。编辑器自动化教训：受控模型对 JS 清 DOM 会回滚（必须真实键盘事件）；话题下拉候选点击会误进正文区（本项目已放弃 chip 化，话题行走纯文本）。
  - **话题策展公式（4 槽/支，抖音上限 4）**：①主体大词（#deepseek/#codex/#claudecode）+②账号垂直（#AI编程）+③内容形态（#源码解析/#大模型）+④长尾按集轮换（#agent/#AI工具/#AI安全/#程序员）。零流量词禁上（#harness/#主循环/#skill/#AGENTS配置 类替换为有真实流量池的词）；抖音热榜科技方向命中才蹭榜，否则不硬凑（douyin-topic 定规）。20 支存量作品的完整策展表内置在 douyin_fix_topics.py TARGETS，新视频发布前照此公式定 metadata「话题」行。
- **发布后 checklist 增查：封面在列确认（2026-08-28 用户定规，严禁无封面发布）**：发布确认不只查「作品在列」，还要查**作品卡片带 v3/v4 自定封面**（抖音 manage 卡片缩略图 / 快手 check_status 卡片封面 / B站稿件封面 / 视频号 scan）。发现无封面或黑帧封面：立即用 `douyin_fix_cover_v2.py <关键词> <横版> <竖版> <expect令牌>`（expect 令牌必须取自目标卡片**抖音侧**标题/简介的独特字串，防误中其他卡片——2026-08-28 TS教父关键词误中肝了一天事故）或 `kuaishou_fix_cover.py` 编辑页补挂，平台侧复核到封面在列才算闭环，并在 link-map 该 slug 的 pub_video 记 `cover_fixed_at`。上传器「封面已设置」日志不可信（弹窗静默失败先例：视频号 4:3 横版 dialog hidden 14 次流程仍继续）。
- **抖音改封面用 v2 流程（2026-08-28 实战定规，v1 已废弃）**：`scripts/pub/douyin_fix_cover_v2.py`——编辑页「设置封面」区有**横封面4:3 与竖封面3:4 两个独立卡槽**，App/主页网格展示的是**竖封面**（只换横版 = 用户视角「没换封面」，v1 全军覆没的根因：弹窗默认开在「设置横封面」页，竖版图被传进横封面板）。v2 关键点：① 锚缩略图 img hover → 点可见的 `div[class*="hover-show"]`「编辑封面」浮层；② **弹窗标题必须校验**是目标卡槽（设置竖封面/设置横封面）再传图；③ 上传槽 = modal 内**最后一个** `input.semi-upload-hidden-input`（第 1 个是「AI生成参考图」槽，传错槽「完成」照样关弹窗=假成功）；④ **卡槽 img src 前后变化是唯一真验证**，「弹窗已关」「提交成功」都不算数；⑤ 双卡槽都 src 变化才提交修改（任一失败即中止，省修改额度——每作品限改 5 次）。
- **收尾自检（发布会话结束前强制）**：核对 link-map `<slug>.pub_video.results` 四平台齐全；不齐 = 发布任务未完成，不许收尾归档。注意 `publish.py` 的 `save_to_linkmap` 每次运行会**整体覆盖** results 字段、快手 v2 单独写——串行发完后必须把四平台真实状态合并写回再收尾。
- 配套工具：`scripts/pub/douyin_delete_verified.py`（带弹窗全文安全阀+删除后验证的删除）、`scripts/pub/douyin_scan_works.py`（只读扫描）。

### 挂定时后必须复核实际状态（2026-08-27 定规，全平台强制）

> 背景：codex-desktop-tutorial 发布夜，视频号「定时 20:00」连续两次静默失败——`tencent_uploader_main.py::set_schedule_time_tencent` 的 label 定位选择器失效，定时没设置上但流程直接走到发表按钮，**实际立即发布（23:01 / 02:17 两次实锤），上传器日志仍报「✅ 发布成功」**。另有：中途 kill 发布进程 ≠ 没发布（进程死在上传等待阶段，页面侧可能已提交出片）。

- **定规**：`--schedule` 挂完后（以及 kill 过发布进程后），**必须扫平台后台复核**：抖音 `douyin_check_status.py`（状态标记必须含「定时」且无「不适宜公开」）；视频号 `shipinhao_delete_video.py --scan`（看新条目时间戳——出现在当天上传时刻 = 立即发布实锤，正确定时应不在已发布列表）。上传器的成功日志不可信。
- **兜底**：平台侧定时控件失效时，用 Windows 任务计划程序本地直发落 20:00 窗口（`schtasks /create /sc once /st 19:50` + bat 包装 `py -3.11 -m scripts.pub.publish`，参考 D:\tmp\sph_publish_1950.bat 与任务名 sph-publish-2000）——平台侧优先，此为坏路兜底，机器需开机。
- ~~待修：tencent 定时选择器~~ **2026-08-28 已重写修复**：旧 `label.nth(1)` 只搜主 frame + `query_selector_all` 穿不透 Shadow DOM（面板全在主 frame Shadow DOM 里，v4-v9 探针实证）。新实现（`tencent_uploader_main.py::set_schedule_time_tencent`）：全 frame locator 探测定时 radio → 日历选日（跨月翻页+日期回读验证）→ 时/分转盘点选（虚拟列表 hover+滚轮推进、按列 x 坐标分左右防串列）→ 主输入框全串 `YYYY-MM-DD HH:MM` 终验；`submit_publish` 加终防线：scheduled 策略下未验证挂上即拒绝点发表，宁可失败不可误发。配套：原创分成提示弹窗（Shadow DOM）改 locator 显式点「直接发表」（AI 内容不声明原创）；`error_capture` 修复「不超过」误命中「超过」。**残余限制**：跨日（>~24h）定时平台侧静默降级立即发表（定规见「发布执行」），跨日档必须 schtasks 直发；AI 声明开关与 4:3 横版封面 UI 超时跳过仍在（出片后后台手动补）。

### 发布后复查闭环（2026-08-27 用户定规，强制）

> 发布不是终点。平台审核有两类时点：发布前预审（分钟级）与**发布后追罚**（DSH 案例：过审发布 16 分钟后「减少推荐」）。每个平台、每次发布（含定时出片）都要在一段时间后复查，确认真正通过审核；未通过的按层级处置后重发，直到全部终态才算发布闭环完成。

- **复查节奏**：发布/出片后 **20-30 分钟首查**（覆盖预审与早期追罚），**24 小时二查**（覆盖延迟追罚）。首查仍「审核中」→ 每 30-60 分钟追查直到出终态。
- **各平台复查命令与通过判据**：
  | 平台 | 命令 | 通过判据 |
  |------|------|----------|
  | 抖音 | `py -3.11 -m scripts.pub.douyin_check_status "<标题关键词>"` | 「定时发布/已发布」且无「不适宜公开/仅自己可见/未通过」 |
  | 快手 | `py -3.11 -m scripts.pub.kuaishou_check_status <关键词>` | 已进入定时发布/已发布，无违规标记 |
  | 视频号 | `py -3.11 -m scripts.pub.shipinhao_delete_video --scan` | 新条目在列表且 st=1、时间戳正确（不在列表 = 被拒或审核中，去后台看） |
  | B站 | 浏览器内 fetch `/x/web/archives` 稿件列表（见 B站小节） | 稿件状态「通过/可见」，字段核对 |
- **未通过的处置（先判层级，2026-08-27 定规）**：
  1. **元信息层**（外链/违禁词/动作词）→ 按 platform-compliance 案例库改标题/简介/话题（或平台变体），删旧条目重发同视频，复查。
  2. **内容层**（音频/画面主题被拒，「不适宜公开」）→ **不要改口径重投**（8-27 三度实证无效且消耗账号违规计数）：删被拒条目，报用户拍板——剪特供版（去掉敏感段）或放弃该平台；其余平台照常。
  3. **追罚类**（已过审后「减少推荐」等）→ 按案例库定位根因（多为外链/指路句），改后删旧重发。
- **记录**：复查结果写 `content/link-map.json` 对应 slug 的 `pub_video.review` 字段（时间 + 各平台终态），全平台终态（通过/已放弃）后本次发布才算完成。
- **长程关注**：会话内用后台任务/定时脚本跟进；会话外用 Windows 任务计划（`schtasks`）挂复查命令落日志，下次会话先读日志收口。

### 违规/未通过视频必须清理（2026-08-27 用户定规，强制）

> 发布后发现违规（追罚/仅自己可见/不适宜公开）或审核未通过的视频，**必须从平台删除清理，账号不留违规内容**——挂着违规作品持续消耗账号权重（同主体 3 次中度违规全账号限流）。清理后按上一节分层处置决定是否重发。

- **四平台清理工具**：抖音 `douyin_delete_verified.py "<标题关键词>"`；快手 `kuaishou_delete_video.py <关键词> [--confirm]`（2026-08-27 新增，删已发布；`kuaishou_delete_scheduled.py` 只管待发布）；B站 `bilibili_delete_video.py <bvid>`；视频号 `shipinhao_delete_video.py --keyword <词> --confirm`。bvid/photo_id 从 `content/link-map.json` 的 `bilibili_id`/`kuaishou_id` 取（publish 自动回收）。
- **快手定位坑（2026-08-27 实锤）**：作品管理卡片文本只显示话题标签不显示标题——定位关键词用话题词（如 `#零基础教程` 里的 `零基础教程`），用标题词匹配 0 命中。
- **B站登录坑（2026-08-27 实锤）**：`cookies/bilibili.json` 是 biliup 的 `cookie_info` 格式，**不是 Playwright storage_state**——直接 `new_context(storage_state=…)` 会「未登录」重定向扫码页；要手动转 `add_cookies`（`bilibili_delete_video.py::storage_state()` 已内置正确转换，复用它）。member API 端点对纯 requests 全 404（WAF 指纹），只能浏览器内 fetch。
- **并发会话清目录坑（2026-08-27 实锤）**：`video-generation/build/<slug>/` 可能被并发会话整目录清掉（发布运行中 mp4 消失、metadata.txt 一起丢）——发布前后确认 mp4 在场；**重要 metadata 发布前备份一份到 build 外**（或从本 skill 记录重建）；音频 `audio/<slug>_t/` 与 deck/narrations 在 build 外，丢了 build 重渲即可恢复（约 25 分钟，换声旁路自动接管）。

**主管线**（`scripts/pub/publish.py`，抖音/视频号/B站通道 + 公众号 mp API）自动处理：封面横竖双版生成（复用 `scripts/video/cover.py`）、**metadata lint 门禁**（`--confirm` 前跑，FAIL 拒发；lint 自身异常同样拒发，`--force` 逃生留痕；含**时长纪律**——ffprobe 成片 >150s 且无「豁免_时长」拒发，openspec douyin-featured-selection）、标题裁剪、AI 声明、合集选择（抖音/视频号）、平台间隔风控缓冲（180-480s）、结果回收 link-map。**快手走 v2**（主管线 KSVideo 选择器过期待修）。⚠️ link-map 无文件锁——多平台并行发布时互相覆盖（2026-08-23 实证），串行发布或事后核对。

## 合集数据与转化定规（2026-08-30，openspec collection-data-conversion）

> 合集是搜索/主页之外第三内容入口；合集粒度数据回流走 `make analytics-album`（snapshots/album/*.jsonl），报表看板见 video-analytics「系列健康度」节。

### 三平台合集现状与数据通道（2026-08-30 实查）

- **抖音**：Web 合集管理在创作者中心「内容管理 → 作品合集」tab（旧结论「Web 无入口」作废）。数据接口 `web/api/mix/list`（清单+浅层 statis）+ `web/api/creator/item/mix/mget?fields=metrics`（完整 14 项：播放/点赞/评论/收藏/分享/完播率/2S跳出率/人均时长/封面曝光/封面点击/封面CTR/**追更订阅 subscribe_count**/退订/总时长）——追更订阅与封面 CTR 是合集特有转化位，UI 行不显示，采集器被动拦截两个端点。
- **快手**：合集数据只有 `rest/cp/works/v2/collection/list`（viewCount 等基础字段 + `offlineReason`/`urgeUpdateCount` 催更数）；数据中心无合集维度。`collection/tab` 是纯 tab 计数（collect.py SKIP_PAT 保持）。~~2026-08-30 两个合集均 size=0 离线~~ **2026-08-30 下午已解（collection-packaging-optimize）：双合集归一为「AI 编程实战课」38 集并公开展示（总播放 4.1w+），空壳旧合集已解散**；数据通道随公开生效自然恢复。
- **B站**：合集权益两级门——Lv2 解锁入口，但创建受「合集个数」配额限（API 20082，配额按粉丝量定级）；`/upload-manager/ep` 合集管理页 SPA headless/headful 均不渲染 tab（页面壳正常、seasons API 正常），管理一律走 API。脚本 `scripts/pub/bilibili_collection_create.py` 已闭环封面上传→建合集→挂成员全流程，配额开通后一键执行。
- 视频号无合集功能，永久排除。
- **合集包装定规（2026-08-30，openspec collection-packaging-optimize）**：三平台合集名严格统一《AI 编程实战课》；简介结构=价值承诺（工具怎么用/源码怎么读）→主线三条→「配置判据直接拷走」→更新节奏+收藏钩子（抖音 200 字内无外链版/B站带博客链接+三连版）；封面=`scripts/video/collection_cover.py` 生成（抖音 1080×1080 方图/B站 1920×1080，色板走 palette.py 单源，青色≥0.8%/字形≥2.0% 双门禁）；文案发布前过 platform-compliance 扫描。

### 合集内排序策略（C1 定规 + 实操清单）

- **策略**：首位放系列最强单集（承接主页/搜索进合集的流量）；其余按系列正序（EP.1 → EP.N），追更动线自然。新爆款产生时更新首位。
- **抖音执行记录（2026-08-30，已保存并回读验证）**：首位=「我肝了一天，DeepSeek Harness 的源码解析」(28,268 播放) → ep1(19,961) → 安装(11,866) → 必装插件(7,283) → 桌面CLI(5,934)，尾部 20 条保持主题序。**两处修订**：① 原 strategy 点名 deepseek-harness-plugin-system 经查无抖音作品（link-map 27,324 是误映射到 source-code 的播放），champion 按抖音实况取 source-code；② 编辑面板拖拽持久化行为诡异（点「取消」后顺序仍生效）——实改后必须用 verify 回读为准。ep2~ep11 定时中，发布后需核合集挂载并补插到 ep1 之后。
- **实操**（抖音 Web：内容管理 → 作品合集 →「设置排序」）：① 置顶 deepseek-harness-plugin-system；② dsh-source-deep-dive ep1~ep11 按期号正序；③ deepseek-harness 系列按期号正序；④ 其余散集作品按播放降序垫后。快手合集编辑页无拖拽排序入口（App 内核对，补成员时顺手确认）。
- **门禁**：排序是平台写操作且对外可见——会话内操作前报用户确认，改完回读截图。

### 置顶评论 × 合集钩子（C2，备稿模板）

- 系列视频 `置顶评论:` 备稿在承接文案外加导流句：「本系列全集已收录合集《AI 编程实战课》，收藏追更不迷路」（合集名跨平台严格一致）；与粉丝群链接并存（管线自动挂尾，互不冲突）。
- lint 已识别：系列视频（EP 期号标题）简介/置顶评论缺钩子 → WARN「合集钩子」（metadata_lint `check_series_hook`）。
- 存量承接：48h 回看窗口内的已发布视频补挂新模板，不批量回改历史。

### 简介追更钩子（C3，定规）

- 系列视频 `简介:` 末尾（互动问题后）加「本系列全集已收录合集《AI 编程实战课》」——站内合集指路**不触抖音简介外链红线**（红线只禁站外链接）；规则落点在 metadata-optimizer skill「简介与话题」节。

### 粉丝群追更联动（C4，发布后节拍）

- 前置（已就绪，2026-08-30）：`scripts/pub/config.py::DOUYIN_FAN_GROUP_URL = https://v.douyin.com/group/468641640402`——用户实证 **v.douyin.com 短链在抖音评论区可直接发送**（站内域名不触外链红线，无需口令/特殊格式）；douyin_pin_comment 挂尾自动去重（文案已含不重复）。存量视频在 48h 承接窗口补挂时生效。
- 节拍：新集发布确认后 → 粉丝群内人工推一条更新消息（新集标题 + 一句话价值）——群是当前唯一私域入口，合集更新触达靠粉丝信息流 + 群推送双通道。

### 实验挂账（C6）

- 合集封面/简介/排序实改统一挂 `collection-repackaging` 实验（`make experiment ARGS="add collection-repackaging --slugs=<在更系列 slug>"`），观察期 ≥5 天后用「系列健康度」新数据 verify（追更订阅增量 / 封面 CTR 变化 / 合集播放增量），结论人写。
