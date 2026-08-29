---
name: wechat-publishing
description: 博客文章同步到微信公众号草稿箱。mp 后台 API 直推（Playwright+msedge 登录态，跳过风控），含封面自动化、代码高亮、原文链接注入、内链替换，及 background 简写被过滤等已踩坑位。
---

# 公众号发布

## 何时用

写完文章并通过 Hugo 构建（`hugo --gc --minify`）后，同步到公众号草稿箱时调用。

## 方案：mp 后台 API 直推（`publish_mp.py`）

用 Playwright persistent context 持有真实登录态 cookie，通过 `context.request` 直接调 `mp.weixin.qq.com` 的 Web 后台内部 API（与编辑器「保存为草稿」同一接口）。**全程无模拟点击/键盘，不触发前端反自动化埋点**——这是相比 wechatsync 扩展桥接（掉线频繁）、Playwright 模拟点击 ProseMirror（被风控）的第三条路。

入口：`make wechat-publish-mp slug=<slug>`（旧 `make wechat-publish` 走 wechatsync，**已弃用**）。

## 前置条件

- **msedge 浏览器**：本机 Chrome 安装损坏（SxS 并行配置错误），Playwright 内置 chromium 访问 mp 站必崩（Page crashed）。**所有 Playwright 任务必须 `channel="msedge"`**。
- `wechat-profile/`（gitignore）持久化登录态，首次需扫码；检测登录看 cookie 是否含 `slave_sid`。
- 两套 Python：`.venv`（`prepare` 用，含 `bs4`）；全局 Python311（`publish_mp` 用，含 `playwright`）。Makefile 已分别调用，勿混。
- 文章已 `hugo --gc --minify` 构建到 `public/`。

## 发布流程

### Step 1: 构建 + 部署博客站
```bash
hugo --gc --minify          # 构建到 public/
./deploy.sh "备注"          # 推源码 + 部署 Pages
```

### Step 1.5: 内容留存终检（2026-08-26 定规，openspec wechat-article-retention）

推草稿前过 blog-writing `references/wechat-retention.md` 的留存清单（发布前留存检查清单一节）：

- **打开层**：`wechat_title` 已定稿（≤25 字、钩子前 13 字，不拿博客 SEO 长标题直发）；`wechat_digest` 已定稿（前 40 字含痛点或硬数字）。两个字段都是 front matter 可选项，**prepare.py 自动读取**，缺省回退 `title`/`description`
- **首屏/节奏/扫读/钩子兑现**：正文前 150 字可见问题定义+钩子且首屏内有一张图；二级标题间隔 ≤1200 字；代码块 ≤15 行；段首承重（扫读测试：只读小标题+段首句+加粗逻辑仍成立）；开头钩子承诺逐节有回收
- **收藏触发与往期关联**：文中至少一处可收藏资产（速查/对比表/决策树），转化段点到它；文末放 2-3 篇相关旧文（relref，自动转平台链接）
- **转化段不进源稿**：「点在看/关注」转化文案**不写在 content/posts 源文件**（博客版错位）——推荐流程 = `make wechat-draft-only` 存草稿 → 后台编辑器在结论段后补价值锚定式转化段（单动作；禁诱导分享/强制关注）→ 群发
- **发布配置四查**（2026-08-26 定规）：①**作者**录入（`WECHAT_AUTHOR` 非空，表单 `author0` 自动带；空 = 草稿作者栏空白，补 env 再发）②**合集**挂对（`--album` 默认 AI，`前端技术`/`碎碎念`/`none` 按文章类目选，挂错后台改不了只能删草稿重来）③**原创声明**（`copyright_type0=1` 文字原创已默认；转载/重编文传 0）④**广告开关**（建草稿 API 不含流量主广告设置，群发前 mp 后台人工核对文中/文末广告与预期一致）
- **48h 数据回看**：发布满 48h 看后台（送达/打开/读完/分享/在看/关注净增），结论一句话写 `link-map.json` 该 slug 备注，**对照完读率基准线归档**（2026-08-26 调研：<30% 推荐终止 / ≥50% 进中级池 / >65% 持续加推；转发率正常 1%-3%）——打开低修 `wechat_title`/`wechat_digest`，完读低修首屏/节奏，分开归因；连续两篇读完率低于历史中位 → 对最近一篇做首屏+节奏专项复盘（不建自动采集，人工回看）

### Step 2: 准备公众号内容
```bash
make wechat-prepare slug=<slug>
```

`scripts/wechat/prepare.py`（走 `--for-wechatsync` 路径）做的事：
1. 从 `public/posts/<slug>/index.html` 的 `.content` 区提取正文，剔除导航/TOC/分享按钮
2. `clean_and_style()`：注入 inline 样式（公众号不支持 CSS class），清除非 span 标签的 class
3. `convert_images()`：SVG → PNG（公众号不支持 SVG），**首图额外按 9:5 裁出 `cover.png`**
4. `replace_internal_links()`：内链按平台替换（`link-map.json` 已记录的用平台链接，否则回退博客站）
5. **`_process_code_blocks()`**：代码块 `<pre>` → `<section>` + 逐行 `<p>`，Hugo chroma class → Monokai inline 颜色（映射表见下）。**背景色写法见「代码块背景」坑**。
6. **`strip_leading_cover()`（2026-08-29 定规，仅 weixin 版）**：正文开头的封面重复图剥掉——博客端源稿普遍以 `<img cover.png>` 题图开头，公众号封面正是从这同一张图裁出；平台侧推送卡片与文章详情页首屏已展示过封面，正文再以同一张图开头就是同图重复，还把首屏 150 字钩子往下挤（wechat-retention：标题+封面吃掉首屏一半）。判据=文档第一张图且沿祖先链无任何前置兄弟；首图嵌在正文间的总览图不剥。juejin 版不剥。**必须在 convert_images 之后执行——封面裁切取的是剥前的首图**
7. 文末注入原文链接段落
8. 按平台生成 `wechat-ready-{weixin,juejin}.html` + `wechat-ready.html`

产物在 `.wechat-build/<slug>/`（gitignore）。

### ⚠️ 发布前检查（防重复发布，2026-08-06 定规）

**任何发布动作（建草稿/定时/群发）前必须先过防重复检查**——同一篇文章不能已上线还重发，也不能同渠道发两次：

1. **link-map.json**：slug 是否已有 `published_url`，或 `publish_status` 为 `published` / `scheduled` / `published_free_no_push`？有 → 已发布过，**拒绝重发**。
2. **公众号发表记录**：home「近期发表」/「全部发表记录」搜标题——文章已在主页（免费发布或群发都算已上线）？在 → **拒绝重发**。
3. **草稿箱**：避免对同一 slug 反复 `sub=create` 堆草稿（清理见「草稿箱清理」节）。

> 2026-08-05 事故：ai-dev-openspec-superpowers-workflow 被 schedule_ui_v2「今天」静默免费发布上主页（无推送），后又误排 08-10 定时，用户手动取消。**教训：发前必查，已上线不重发。**

### Step 3: 推送到草稿箱 + 自动发布
```bash
make wechat-publish-mp slug=<slug>       # 存草稿 + 自动群发通知
make wechat-draft-only slug=<slug>       # 只存草稿(留存规范推荐路径:草稿阶段补转化段再群发,亦作逃生舱)
```

Makefile 自动：`wechat-prepare`（刷新内容）→ `publish_mp.py`（全局 Python311）。**默认 headless 无窗口**（复用 `wechat-profile/` 会话，token/ticket 从首页 HTML 抠）；登录态失效或首次使用时才弹可见窗口扫码。`--no-headless` 可强制弹窗。`publish_mp.py` 流程：
1. 开 msedge，复用 `wechat-profile/` 登录态，GET mp 首页提取 `token`/`ticket`/`user_name`/`svr_time`（token 正则限定 `[A-Za-z0-9_-]`，避免误匹配未登录页的 `https://`）
2. 读 `wechat-ready-weixin.html`，把正文本地图片上传到微信图床（`cdn_url` 替换 img src）
3. **上传 `cover.png` 做封面**（见下节）
4. POST `cgi-bin/operate_appmsg?sub=create&type=77` 创建草稿（表单带 `author0=${WECHAT_AUTHOR}` + `copyright_type0=1` 文字原创）→ 返回 `appMsgId`
5. **自动群发通知**：`POST /cgi-bin/masssend`（立即群发）；今日无通知次数 → `action=time_send` 逐日顺延定时，最长 7 天，全无则失败（草稿保留）
6. 回填 `link-map.json` 的 `draft_appmsgid` + 发布状态（`published` / `pending` / `failed`）

### Step 4: 发布后核对

**自动发布 = 粉丝收到推送，不可撤销。** 建议发布前在手机端预览核对（公众号后台编辑器预览不过滤样式，会骗人；手机端才是真实渲染）。核对封面 + 代码块背景 + 排版无误后再跑 `make wechat-publish-mp`。发布后把永久链接填入 `link-map.json` 的 `published_url`。

> 想保留「先看草稿再人工发布」旧流程：用 `make wechat-draft-only slug=<slug>`，只存草稿不发布。

## 封面自动化（2026-08-01 起，已验证）

`prepare.py` 已从首图生成 `cover.png`（`COVER_SIZE=(1800,1000)`，9:5）。`publish_mp.py` 上传它并填封面字段，无需后台手动补。首图本身源自博客正文的题图，**weixin 版正文会把这张开头重复图剥掉**（见发布流程 Step 2 第 6 步），封面只在推送卡片/详情页首屏出现一次，不随正文重复展示。

**关键坑：upload_material 响应里素材 ID 的字段名是 `content`，不是 `fileid`/`id`。** 响应结构：
```json
{"base_resp":{"ret":0,"err_msg":"ok"}, "location":"bizfile", "type":"image",
 "content":"100001138", "cdn_url":"https://mmbiz.qpic.cn/...", "ai_status":1}
```
`publish_mp.py` 按 `content` → `fileid` → `id` 顺序提取，填入草稿表单 `fileid0` / `cdn_url0` / `cdn_235_1_url0` / `cdn_1_1_url0`。

**`crop_list0` 留空**：mp 服务端会自动按 2.35:1 生成裁剪（appmsg_edit 详情验证返回 `crop_list:{ratio:2.35_1,...}`），不用手算坐标。

**验证封面是否真写进草稿**：GET 草稿详情接口，看 `file_id`/`cover`/`cdn_url` 是否有值——
```
cgi-bin/appmsg?t=media/appmsg_edit&action=edit&type=77&appMsgId=<id>&token=<token>&f=json
```
返回 `app_msg_info`（JSON 字符串），里面有 `file_id`/`cover`/`cdn_url`/`crop_list`。

> 注意：列表接口 `operate_appmsg?sub=get` 返回 `ret:2` 空列表，**不可用**；`appmsg?t=media/appmsg_list` 也返回空。查单篇只能用上面的 `appmsg_edit`。

## 代码块背景（关键坑，已修）

**公众号渲染端过滤 `background:` 简写属性（`<div>` 上尤甚）**——旧实现用 `<div style="background:#334155">`，整块代码块在手机端变白底。

`prepare.py` `_process_code_blocks` 现在三重保险：
1. `background` → **`background-color`**（明确属性，保留率高）
2. 容器 `<div>` → **`section`**（公众号对 section 支持更好）
3. **每行 `<p>` 也带 `background-color:#334155`**（兜底：容器背景万一被剥，每行仍深色，整块不白）

`config.py` 的 `INLINE_STYLES`（blockquote / `th` 表头 / `pre` / `code`）**一律 `background-color`**，禁止 `background:` 简写。

**改代码块/背景相关样式后，必须重新同步并在手机端验证**——后台预览看不出问题。

## 代码高亮：Chroma class → Monokai 颜色

Hugo 用 chroma 以 class-based 方式生成高亮（`noClasses = false`）。公众号不支持 CSS class，`prepare.py` 把 class 转 inline 颜色：

| Hugo chroma class | Monokai 色值 | 语义 |
|---|---|---|
| `k` `kc` `kn` `ow` | `#f92672` | 关键字 (async, def, import, True, is...) |
| `o` | `#f92672` | 运算符 (=, ->, ., >=, ==) |
| `bp` `nb` `nc` `ne` `nf` `fm` | `#a6e22e` | 名称 (self, 类名, 函数名, __init__) |
| `n` `nn` `p` | `#f8f8f2` | 变量 / 标点 |
| `s2` `sa` `si` | `#e6db74` | 字符串 |
| `se` `mi` `mf` | `#ae81ff` | 转义字符 / 数字 |
| `c1` | `#75715e` | 注释 |
| `err` | `#960050` | 错误 |

> Hugo 产物的属性无引号（`<span class=k>`），正则兼容无引号和双引号。

## 作者与原创声明（API 直推已支持，2026-08-01 实测）

曾误判「mp API 对个人订阅号无效、需后台手填」，实测两者都可直推：

- **作者**：`create_draft` 表单 `author0` 直接生效（`config.DEFAULT_AUTHOR="${WECHAT_AUTHOR}"`），编辑页 `#author` 即显示该值。
- **原创声明**：`copyright_type0="1"`（`config.COPYRIGHT_TYPE`）直接生效，草稿落库即为「文字原创」——编辑页已声明区 `#js_original_open` 显示 `display:flex`、未声明区 `display:none`。账号需 `can_use_copyright=1`（本账号已实测为 1）。

验证手段：打开草稿编辑页，看 `#author` 值 + `#js_original_open` 的 display（`flex`=已声明 / `none`=未声明）。

原文链接：`prepare.py` 文末自动注入完整段落（mp API 的 `sourceurl0` 不稳定）。

## 合集挂载（2026-08-03 实证：create 时直接注入）

**合集是文章普通字段 `appmsg_album_info`**（编辑器/详情返回里叫 `appmsg_album_info`，create 表单字段名是 `appmsg_album_info0`）。发布管线 `publish_mp.py` 已内置：`make wechat-publish-mp slug=<slug>` **默认挂 AI 合集**，用 `album=前端技术` / `album=碎碎念` / `album=none` 覆盖（`config.ALBUMS`）。

**关键坑：字段格式必须是富结构，简单格式会被静默忽略。**

```python
# ✅ 富结构(实测生效,create 后回读 app_msg_info 确认合集已写入)
{"id": "[ALBUM_ID]", "title": "AI", "album_id": [ALBUM_ID],
 "appmsg_album_infos": [{"id": "[ALBUM_ID]", "title": "AI",
                          "album_id": [ALBUM_ID],
                          "appmsg_album_infos": [], "tagSource": 0}]}

# ❌ 简单格式(字段名对了也白搭,服务端忽略)
{"appmsg_album_infos": [{"id": "[ALBUM_ID]", "title": "AI"}]}
```

`publish_mp.py` 的 `build_album_field()` 生成富结构。调试时踩过的字段名全无效：`appmsg_album_info`（无下标）、`audio_info` / `audio_info0`（前端用它承载过合集，但 create 直传不生效）。

**合集 ID**（`appmsgalbummgr?action=list` 实测）：AI=`[ALBUM_ID]`、前端技术=`[ALBUM_ID]`、碎碎念=`[ALBUM_ID]`。

**验证方式**：读草稿详情 `appmsg?t=media/appmsg_edit&action=edit&type=77&appMsgId=<id>&f=json` → `app_msg_info`（JSON 字符串）→ `item[0].multi_item[0].appmsg_album_info.appmsg_album_infos` 看是否含目标 id。

> 已存在的草稿补合集，仍只有两条路：① 人工在 mp 后台编辑器选（headless 保存无法持久化，6 种方式全失败）；② 重新走 `sub=create` 复制（需先取消原排期再重排）。见 memory `wechat-album-set-mechanism`。

## 自动发布与顺延（2026-08-01 实测）

`publish_mp.py` 存草稿后自动群发通知。接口（从 JS bundle 实证）：

| 动作 | 接口 | payload 要点 |
|---|---|---|
| 立即群发 | `POST /cgi-bin/masssend?t=ajax-response` | `{msgid: <appMsgId>, sync_version: 1}` |
| 定时群发 | `POST /cgi-bin/masssend?action=time_send` | 全字符串表单编码，含 `fingerprint`/`random`/`token`/`operation_seq`/`req_id`/`req_time`/`direct_send=1`/`isFreePublish=false`。见下方「time_send 直连」 |
| 取消定时 | `POST /cgi-bin/masssendpage?action=cancel_time_send` | 表单：`id=<数字>` + `fingerprint` + `token` + `lang=zh_CN` + `f=json` + `ajax=1`。**注意：`{id:"..."}` JSON 包会被拒(ret:1)** |
| 状态回查 | `GET /cgi-bin/check_publish_status` | `{msgid, publish_type:1}` |

### time_send 直连（schedule_api.py，2026-08-03 修复 67011/-1 根因）

`publish_mp.py` 的 mass_send() 只带 `{msgid, sync_version}`，**不适用于 time_send**——定时发表必须完整复刻前端 masssend 弹窗的请求，缺字段直接 67011/-1：

- **必带 `fingerprint`**：masssend 系 API（time_send / check_ad / check_hot_time）账号级稳定值，**仅在打开群发弹窗时由前端生成，无法从页面加载/全局对象/cookie/HTML 提取**（曾误抓资源 hash `06fcd5b9...` 当 fingerprint → ret -1）。值在 `config.MASS_SEND_FINGERPRINT`（2026-08-03 两次 UI 运行 + 0807 日志均一致）。若 API 再报 67011/-1 → 微信轮换了 fingerprint → 跑 `schedule_ui_v2 --capture-only` 从日志抓新值。
- **必须全字符串表单编码**（Playwright `form=`，`Content-Type: application/x-www-form-urlencoded`）；布尔/数字混用会被拒（`data=` 发 JSON 是 67011 的另一个根因）。
- `direct_send=1` 缺失直接 67011；`isFreePublish` 必须小写字符串 `"false"`（布尔 False 序列化成 `"False"` 服务端不认）。
- `operation_seq` 从 `masssendpage?f=json&preview_appmsgid=<id>` 拿（每次会话变）；`req_id` 32 位随机字母数字；`req_time` 毫秒+`client_time_diff`。
- 直连前**必须先查配额**（`quota_detail_list`，`quota:0` = 已被排期占用，`original_quota`=上限），无配额日期 time_send 会被拒。`schedule_api.py` 内置此检查，`--dry-run` 只打印 payload 不提交。

### UI 定时发表会创建发布副本（schedule_ui_v2.py，2026-08-03 实证）

`schedule_ui_v2.py`（`python -m scripts.wechat.schedule_ui_v2 <appid> <日期文案> <HH:MM>`）走 UI：编辑器→发表→定时发表开关→日期/时间→发表→继续发表确认循环。成功率高，但机制有坑：

- **每次定时都 `sub=create` 一个新「发布副本」，原稿留草稿箱、副本离箱排期**（100001177→100001246、100001271→100001273 实证）。副本不可在后台手动编辑合集。
- **取消定时 = 副本回草稿箱**：`cancel_time_send` 后副本回到草稿箱（100001159、100001248 实证），可再删或重新排。校验副本身份勿信面板文案，用草稿箱盘点核对。
- **headless 定时面板部分 li 隐藏**：`page.hover()`/`link.click()` 报 "element is not visible"，用 `page.evaluate` JS click（`link.click()` / `btn.click()`）触发 Vue handler。点击取消后页面会跳转，销毁 execution context——校验状态需重新加载页面再查。
- **合集继承**：`sub=create` 副本从原稿继承 `appmsg_album_info`——原稿带合集则副本带（DeepSeek），原稿不带则副本不带（CcSwitch 100001199→100001248 无合集）。给已排副本补合集的唯一可靠方式：「原稿先挂合集（人工或 create 注入）→ 取消旧排期 → 重新定时」。
- **删除原稿/副本不影响已排期副本**：cleanup 删 100001271 后，其副本 100001273 的排期仍有效（实证）。
- **⚠️ 禁止定时「今天」（2026-08-05 事故）**：前端 dayChange 对「今天」降级为 `isFreePublish=true` 免费发布——文章**静默上主页、无粉丝推送**，走即时 masssend 不走 time_send，脚本 time_send 检测永远不触发 → 空响应「假失败真发布」（草稿 100001282 被免费发布上主页，挂太久无法撤回）。`schedule_ui_v2.py` 已加硬守卫 `is_today_label` 拒绝「今天/今日/当天日期」，**只允许定时未来配额日**（isFreePublish=false 群发通知）。真今天发需即时群发（暂不可靠）。教训：**空响应 ≠ 失败**，发布后查 home「近期发表」核对真实结果。
- **⚠️ 「继续发表」即使选了未来日期也可能走免费发布（2026-08-16 事故）**：double_check 弹窗确认时，mp 在部分状态下（弹窗链路切到发布页变体）会把请求发成 `masssend?t=ajax-response&is_release_publish_page=1` + `isFreePublish=true`——即使表单里带着未来 `send_time`。后果是**同一篇文章一次群发通知、一次免费发布，重复上线**，且界面像失败（响应为空）。**已修**：`schedule_ui_v2.py` 现用 `page.route` 熔断，凡 `masssend` 且 body 含 `isFreePublish=true` 一律 abort，脚本走到「未检测到 time_send」报错退出、草稿保留可安全重跑。**铁律：定时成功的唯一判据是抓到 `action=time_send` 且 `isFreePublish=false`、ret:0**；跑完必查「发表记录」页有无意外新条目。
- **编辑器每次点「发表」都会自动另存一个新 appMsgId（2026-08-16 实证）**：进编辑器点「发表」即 `sub=create` 副本（428→448/470、404→459、411→464…），**失败重跑 N 次就堆 N 个副本**。本轮 5 篇排期在草稿箱堆了 18+ 条废稿。流程纪律：批量定时后**必须** `list_drafts` → 更新 link-map keep-set（成功排期的新 id 记入 `scheduled_appmsgid`）→ `cleanup_drafts --delete`；失败重试前先盘点，别盲目重跑。
- **登录态短效（<1 天）**：mp 会话隔夜即踢（页面 `t:""`/`ticket:""` 即失效）。批量长流程跑前先 `get_token` 校验；失效需弹窗重扫码，一次扫码窗口给足 15 分钟并在终端明确提示。

**顺延语义**：个人订阅号每日群发 1 次（通知次数）。立即群发失败（无通知次数/可顺延错误）→ 逐日尝试 `send_time=明天/后天/…`，最长 `PUBLISH_RETRY_DAYS=7` 天，全无则抛「7 天内均无通知次数」，草稿保留。

**不可顺延错误**（内容违规 10806 / 非法外链 412 / 素材不可群发 64006 等）：直接失败，不白试 7 次。见 `NON_RETRYABLE_RET`。

**扫码**：群发/定时设置若触发风险操作保护，会报「需要扫码」。到后台「设置与开发→安全中心→风险操作保护→群发消息」关闭可免扫码。

**测试草稿可回滚**：`operate_appmsg sub=create` 建草稿 → `sub=del` 删（`{AppMsgId}`），实测全链路可逆，不影响生产。

## 草稿箱清理（测试草稿一律删除）

**规则（用户 2026-08-03 明确）：调试/测试创建的草稿用后必须删除，不留堆积。** 草稿箱曾堆到 53 条（38 条 DeepSeek 副本 + OpenSpec/CcSwitch 副本），全部是反复调试 `sub=create` 的产物。

清理工作流（安全优先，删前必盘点）：

```bash
python -m scripts.wechat.list_drafts              # 1. 盘点全部草稿 → .wechat-build/draft-inventory.json
python -m scripts.wechat.cleanup_drafts           # 2. dry-run,打印将删除清单
python -m scripts.wechat.cleanup_drafts --delete  # 3. 真正删除
```

- **`list_drafts.py`**：草稿箱列表页 DOM 枚举（滚动触发加载全部）。**反例：`appmsg?action=list_card` 等接口 ctx.request 直调会被风控静默返回空**，必须走页面。草稿箱 URL = 首页「草稿箱」菜单项（`cgi-bin/appmsg?action=list_card&type=77&begin=0&count=10`），卡片 `.weui-desktop-card[data-appid]`。
- **`cleanup_drafts.py`**：保留集 = `link-map.json` 全部 `weixin.draft_appmsgid`/`scheduled_appmsgid`（正式文章/排期稿）+ 显式补的 4 个排期原稿（100001177/100001182/100001191/100001199）。其余一律删。删除用 `operate_appmsg?sub=del`（最小 payload：`{AppMsgId, count}` 即可，实测 ret=0）。
- **删除前必须确认排期**：定时发表的稿件有的会离开草稿箱（100001246/100001248 不在箱内）、有的仍在箱内（100001182/100001191 在箱内且排期有效）。删前先看首页「定时发表」面板，确认没有排期指向待删 ID。
- **排期副本与箱内原稿是两回事**：副本离箱排期，删除箱内原稿（或另一副本）不影响已排期副本（cleanup 删 100001271 后 100001273 排期仍有效，实证）。取消定时后副本回箱，此时删掉才安全。

## 已知坑位

- **Windows 编码**：Makefile `wechat-publish-mp` / `wechat-prepare` 均设 `PYTHONIOENCODING=utf-8`，勿删。Python 子进程、JSON 请求、终端 print 中文都要显式 utf-8。
- **msedge channel**：见前置条件，Chrome 损坏，禁用 chrome/内置 chromium。
- **背景白**：见「代码块背景」，任何 `background:` 简写都会被过滤。
- **公众号 2 万字上限**：`config.py` `WECHAT_MAX_CHARS = 20000`，prepare 超限 warn。
- **标题残留站名后缀（2026-08-16 事故）**：`prepare.py` 靠 `SITE_NAME_SUFFIX` 去掉 `<title>` 里的「 - 1024 工程笔记」，但该值靠 env 传入、Makefile 没传 → 正则为空，**标题带着站名发到公众号**。已修：`config.py` 内置默认 `" - 1024 工程笔记"`，`prepare.py` 再加写法变体兜底正则（`1024\s*工程笔记`）。换站名时记得同步改这两处。
- **草稿堆积（应主动清理，勿留）**：`publish_mp.py` 每次 `sub=create` 新建草稿（不覆盖旧草稿）。反复调试会产生多个废弃草稿——**按「草稿箱清理」节处理，测试草稿当场删**；`link-map.json` 只保留最后一次的 `draft_appmsgid`。

## 文件结构速查

| 文件 | 作用 |
|---|---|
| `scripts/wechat/config.py` | 路径、inline 样式常量（一律 `background-color`）、封面尺寸、超时、`ALBUMS` 合集映射 |
| `scripts/wechat/prepare.py` | 内容准备（清洗/样式/SVG→PNG/cover.png/代码高亮/原文链接） |
| `scripts/wechat/publish_mp.py` | **mp API 直推**（登录态/上传图+封面/创建草稿+合集/回填 link-map） |
| `scripts/wechat/schedule_api.py` | 直连 `time_send` 定时发表（全字符串表单 + fingerprint，`--dry-run` 预览；先查配额） |
| `scripts/wechat/schedule_ui_v2.py` | UI 定时发表（创建发布副本；headless 面板用 JS-click；`--capture-only` 停确认弹窗抓 fingerprint） |
| `scripts/wechat/list_drafts.py` | 草稿箱 DOM 盘点（`.wechat-build/draft-inventory.json`） |
| `scripts/wechat/cleanup_drafts.py` | 批量删除测试草稿（dry-run 默认，`--delete` 执行） |
| `Makefile` | `wechat-prepare` / `wechat-publish-mp`（传 `album=`） |
| `content/link-map.json` | slug → 平台草稿 ID / 永久链接 映射表 |
| `wechat-profile/` | Playwright 持久登录态（gitignore） |
| `.wechat-build/` | 构建产物（gitignore） |
