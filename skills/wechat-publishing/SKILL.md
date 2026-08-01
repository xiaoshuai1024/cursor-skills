---
name: wechat-publishing
description: 博客文章同步到微信公众号草稿箱。mp 后台 API 直推（Playwright+msedge 登录态，跳过风控），含封面自动化、代码高亮、原文链接注入、内链替换，及 background 简写被过滤等已踩坑位。
---

# 公众号发布

> **打包范围**：本 skill 只打包 SKILL.md（mp 后台 API 直推的流程文档 + 踩坑沉淀）。实际发布脚本（`scripts/wechat/prepare.py` / `publish_mp.py` / `config.py`）、Makefile 目标、`wechat-profile/` 登录态、`link-map.json` 属于使用方博客项目（如 blog-src），不在本 skill 内——按各自项目结构准备。核心可复用的是 mp 直推方案与踩坑位。

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
6. 文末注入原文链接段落
7. 按平台生成 `wechat-ready-{weixin,juejin}.html` + `wechat-ready.html`

产物在 `.wechat-build/<slug>/`（gitignore）。

### Step 3: 推送到草稿箱
```bash
make wechat-publish-mp slug=<slug>
```

Makefile 自动：`wechat-prepare`（刷新内容）→ `publish_mp.py`（全局 Python311）。`publish_mp.py` 流程：
1. 开 msedge，复用 `wechat-profile/` 登录态，GET mp 首页提取 `token`/`ticket`/`user_name`/`svr_time`（token 正则限定 `[A-Za-z0-9_-]`，避免误匹配未登录页的 `https://`）
2. 读 `wechat-ready-weixin.html`，把正文本地图片上传到微信图床（`cdn_url` 替换 img src）
3. **上传 `cover.png` 做封面**（见下节）
4. POST `cgi-bin/operate_appmsg?sub=create&type=77` 创建草稿 → 返回 `appMsgId`
5. 回填 `link-map.json` 的 `draft_appmsgid`

### Step 4: 手机端预览 + 发布

**必须手机端预览**（公众号后台编辑器预览不过滤样式，会骗人；手机端才是真实渲染）。核对封面 + 代码块背景 + 排版无误后点「发布」。发布后把永久链接手动填入 `link-map.json` 的 `published_url`。

## 封面自动化（2026-08-01 起，已验证）

`prepare.py` 已从首图生成 `cover.png`（`COVER_SIZE=(1800,1000)`，9:5）。`publish_mp.py` 上传它并填封面字段，无需后台手动补。

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

## 后台手动设置的两项（API 推送也绕不开）

| 项 | 原因 | 操作 |
|---|---|---|
| 作者「1024工程笔记」 | mp API `author0` 字段对个人订阅号无效 | 草稿编辑页手填 |
| 原创声明 | `copyright_type0` 需手动勾选 | 发布时勾选 |

原文链接：`prepare.py` 文末自动注入完整段落（mp API 的 `sourceurl0` 不稳定）。

## 已知坑位

- **Windows 编码**：Makefile `wechat-publish-mp` / `wechat-prepare` 均设 `PYTHONIOENCODING=utf-8`，勿删。Python 子进程、JSON 请求、终端 print 中文都要显式 utf-8。
- **msedge channel**：见前置条件，Chrome 损坏，禁用 chrome/内置 chromium。
- **背景白**：见「代码块背景」，任何 `background:` 简写都会被过滤。
- **公众号 2 万字上限**：`config.py` `WECHAT_MAX_CHARS = 20000`，prepare 超限 warn。
- **草稿堆积**：`publish_mp.py` 每次 `sub=create` 新建草稿（不覆盖旧草稿）。反复调试会产生多个废弃草稿，需到后台手动删；`link-map.json` 只保留最后一次的 `draft_appmsgid`。

## 文件结构速查

| 文件 | 作用 |
|---|---|
| `scripts/wechat/config.py` | 路径、inline 样式常量（一律 `background-color`）、封面尺寸、超时 |
| `scripts/wechat/prepare.py` | 内容准备（清洗/样式/SVG→PNG/cover.png/代码高亮/原文链接） |
| `scripts/wechat/publish_mp.py` | **mp API 直推**（登录态/上传图+封面/创建草稿/回填 link-map） |
| `Makefile` | `wechat-prepare` / `wechat-publish-mp` |
| `content/link-map.json` | slug → 平台草稿 ID / 永久链接 映射表 |
| `wechat-profile/` | Playwright 持久登录态（gitignore） |
| `.wechat-build/` | 构建产物（gitignore） |
