# 公众号同步(mp 后台 API 直推)

把 Hugo 博客文章同步到微信公众号并**自动群发通知**。`prepare` 处理格式,`publish_mp` 直调 mp 后台 API 存草稿 + 群发,**全程无 wechatsync、无 Chrome 扩展、无手工粘贴**。

## 架构

```
Hugo 源码(Markdown + drawio SVG)
        │
        ├─ make build + deploy.sh        → 博客站
        │
        └─ make wechat-publish-mp        → 公众号群发推送(自动)
             │
             ├─ prepare(.venv)
             │   SVG→PNG、首图→cover.png、relref 展开、
             │   inline 样式、代码块 <pre>→<section>+<p>(background-color)
             │
             └─ publish_mp(Python311 + Playwright msedge)
                 复用 wechat-profile 登录态 → 上传正文图 + 封面
                 → POST operate_appmsg 创建草稿
                 → POST masssend 群发通知(无次数自动顺延定时,最长7天)
                 → 回填 link-map(草稿ID + 发布状态)
```

**原理**:Playwright persistent context 持有真实登录态 cookie,通过 `context.request` 直接调 `mp.weixin.qq.com` 的 Web 后台内部 API(与编辑器「保存为草稿」同一接口)。无模拟点击/键盘,不触发前端反自动化埋点——这是弃用 wechatsync(扩展桥接掉线频繁)后的现行方案。

## 代码块背景(关键坑)

公众号渲染端**过滤 `background:` 简写**(div 尤甚) → 整块白。`prepare.py` `_process_code_blocks`:
- `<pre><code>` → `<section>` + 逐行 `<p>`,**容器和每行 `<p>` 都用 `background-color:#334155`**(非 `background` 简写,每行兜底)
- Hugo chroma class → Monokai inline 颜色
- 行内 `<code>` → `<span style="background-color:...">`

`config.py` 的 `INLINE_STYLES`(blockquote / th / pre / code)一律 `background-color`。改样式后**必须手机端验证**(后台预览不过滤,会骗人)。

## 封面自动化

prepare 从首图按 9:5 裁出 `cover.png`;publish_mp 上传它填 `fileid0`/`cdn_url0`/`cdn_235_1_url0`/`cdn_1_1_url0`。

**坑:upload_material 响应里素材 ID 字段名是 `content`**(不是 fileid/id):
```json
{"base_resp":{"ret":0}, "content":"100001138", "cdn_url":"https://mmbiz.qpic.cn/..."}
```
`crop_list0` 留空,服务端自动按 2.35:1 生成裁剪。

## 前置依赖

- **浏览器 channel**(平台默认,见 `config.BROWSER_CHANNEL`):Windows=msedge(本机 Chrome 损坏)/ macOS=chrome(系统自带)。内置 chromium 访问 mp 必崩,故用真实浏览器;可用环境变量 `BROWSER_CHANNEL` 覆盖。
- `.venv`(prepare + publish_mp 共用,含 playwright/bs4)
- SVG→PNG:rsvg-convert / cairosvg / sharp 任一

```bash
python3 -m venv .venv
# macOS/Linux: . .venv/bin/activate     Windows: . .venv/Scripts/activate
. .venv/bin/activate && pip install -r requirements-wechat.txt
python3 -m playwright install   # 装驱动;浏览器用系统 Chrome(macOS)/ msedge(Windows),channel 见 config
```

### 登录(一次性)

首次 `make wechat-publish-mp` 弹 msedge 窗口,扫码登录公众号。登录态存 `wechat-profile/`(gitignore),之后复用。

> 已登录后默认 **headless 无窗口**跑(登录态存在 cookie + 首页 HTML 里;token/ticket 只能从首页 HTML 正则抠,故仍需打开首页但不开窗)。会话失效才弹窗重新扫码;`publish_mp.py --no-headless` 可强制弹窗调试。

## 使用流程

```bash
make build                            # Hugo 构建
./deploy.sh                           # 发博客站
make wechat-publish-mp slug=<slug>    # 存草稿 + 自动群发通知
make wechat-draft-only slug=<slug>    # 只存草稿不发布(逃生舱,旧行为)
```

自动:prepare 生成 HTML → 上传正文图 + 封面 → 创建草稿 → **自动群发通知**(无通知次数自动顺延定时,最长 7 天)→ 回填 `link-map.json` 的 `draft_appmsgid` + `publish_status`。

### 发布语义

- **自动发布 = 粉丝收到推送,不可撤销。** 建议发布前在手机端预览核对(必须手机,后台预览不过滤样式)。
- 今日无通知次数(个人订阅号每天 1 次)→ 自动顺延到明天/后天…,最长 `PUBLISH_RETRY_DAYS=7` 天;7 天全无 → 失败(草稿保留),提示手动处理。
- 发布后把永久链接填入 `link-map.json` 的 `published_url`。
- 若触发风险操作保护(需扫码):到后台「设置与开发→安全中心→风险操作保护→群发消息」关闭可免扫码。

> 作者与原创声明已由 API 直推(`author0`=[YOUR_BLOG_NAME],`copyright_type0`=1 文字原创),无需后台手填/手勾(2026-08-01 实测)。

## 内链处理

博客内链(`{{< relref >}}` → `href=/posts/<slug>/`)在公众号失效。prepare 按平台生成专属 HTML 替换:

- `content/link-map.json`:每篇各平台的「已发布」链接
- publish_mp 创建草稿后自动回填 `draft_appmsgid`
- 替换规则:有 `published_url` → 用平台链接;否则回退博客站绝对 URL

### 维护已发布链接

`wechat-publish-mp` 只自动回填草稿 ID。发布后手动补 `published_url`:

```json
{
  "ai-dev-contract-gates": {
    "weixin": {
      "draft_appmsgid": "100000019",      // 自动回填
      "published_url": "https://mp.weixin.qq.com/s?__biz=xxx&mid=xxx&idx=1&sn=xxx"  // 手动填
    }
  }
}
```

微信 `published_url` 从公众号「发表记录」复制 `mp.weixin.qq.com/s?...` 永久链接(草稿 appmsgid 不能做正文内链)。

### 局限

1. **鸡生蛋**:发文章 A 引用 B,B 未发布/未填映射 → A 该内链回退博客
2. **按顺序发**:先发老文章并填映射,后发的才能用到平台内链

## 排查

| 现象 | 处理 |
|------|------|
| `rsvg-convert: command not found` | 装 librsvg,或用 cairosvg / sharp |
| 渲染产物不存在 | 先 `make build` |
| Page crashed / 浏览器崩 | 确认 `channel="msedge"`(Chrome 损坏) |
| 未获取登录态 | `wechat-profile/` 失效,删后重新扫码 |
| 代码块手机端白底 | 检查是否用了 `background:` 简写,改 `background-color` |
| 封面没绑上 | 确认 `fileid0` 非空(素材 ID 取响应 `content` 字段) |
| 发布提示需扫码 | 到后台关闭「群发消息」风险操作保护,或手动扫码 |
| 7 天内均无通知次数 | 连续每日都有发布/预约占用;草稿保留,手动处理 |
| 立即群发失败但可顺延 | 属正常:无通知次数,自动转定时顺延 |

## 目录约定

| 目录/文件 | 作用 | git |
|----------|------|-----|
| `.wechat-build/` | 中间产物(wechat-ready.html / PNG / meta.json / cover.png) | gitignore |
| `wechat-profile/` | Playwright 持久登录态 | gitignore |
| `scripts/wechat/prepare.py` | 内容准备(核心) | 入库 |
| `scripts/wechat/publish_mp.py` | mp API 直推 + 自动群发 | 入库 |
| `scripts/wechat/config.py` | 常量(样式/路径,一律 background-color) | 入库 |
| `content/link-map.json` | slug → 平台草稿 ID / 永久链接 | 入库 |
