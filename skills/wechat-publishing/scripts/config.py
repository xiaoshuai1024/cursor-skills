"""微信公众号发布的常量配置。

所有路径、域名、样式、选择器集中在此,微信改版时改一处即可。
"""
import json
import os
import sys

# ============ 浏览器 ============
# Windows 本机 Chrome 损坏用 msedge；macOS/Linux 用系统 Chrome（真实浏览器，避 mp/抖音反自动化）。
# 可用 BROWSER_CHANNEL 环境变量覆盖（如设为 chromium 用 Playwright 自带浏览器）。
BROWSER_CHANNEL = os.environ.get("BROWSER_CHANNEL", "msedge" if sys.platform == "win32" else "chrome")

# ============ 路径 ============
def _find_project_root():
    # Makefile 已传 WECHAT_PROJECT_ROOT（junction 场景下脚本真实路径找不到 hugo.toml）
    env_root = os.environ.get("WECHAT_PROJECT_ROOT")
    if env_root and os.path.exists(os.path.join(env_root, "hugo.toml")):
        return env_root
    p = os.path.dirname(os.path.abspath(__file__))
    while p != os.path.dirname(p):
        if os.path.exists(os.path.join(p, "hugo.toml")):
            return p
        p = os.path.dirname(p)
    return os.getcwd()  # fallback: 让后续步骤报可读的错误

PROJECT_ROOT = _find_project_root()
PUBLIC_DIR = os.path.join(PROJECT_ROOT, "public")
SVG_DIR = os.path.join(PROJECT_ROOT, "static", "svg")
WECHAT_BUILD_DIR = os.path.join(PROJECT_ROOT, ".wechat-build")
WECHAT_PROFILE_DIR = os.path.join(PROJECT_ROOT, "wechat-profile")
LINK_MAP_PATH = os.path.join(PROJECT_ROOT, "content", "link-map.json")

# 内链替换支持的平台(其余平台内链回退博客站)
SUPPORTED_PLATFORMS = ["weixin", "juejin"]

# ============ 站点（从环境变量读，见 .env.local.example）============
BASE_URL = os.environ.get("SITE_BASE_URL", "")
# 站点名后缀:html <title> 里 Hugo 会拼上,公众号标题必须去掉。
# env 未传时曾经为空 → 标题残留「 - 1024 工程笔记」发到公众号,故内置默认值兜底。
SITE_NAME_SUFFIX = os.environ.get("SITE_NAME_SUFFIX", " - 1024 工程笔记")
DEFAULT_AUTHOR = os.environ.get("WECHAT_AUTHOR", "")
COPYRIGHT_TYPE = "1"  # 0=不声明 1=文字原创 2=漫画原创

# ============ 合集（账号专属，从环境变量读）============
# WECHAT_ALBUMS='{"AI":{"id":"xxx","title":"AI"},...}'；获取合集 id：公众号后台→合集管理
ALBUMS = json.loads(os.environ.get("WECHAT_ALBUMS", "{}"))
DEFAULT_ALBUM = os.environ.get("WECHAT_DEFAULT_ALBUM") or None  # None=不挂合集

# ============ 封面 ============
COVER_SIZE = (1800, 1000)  # 9:5
IMAGE_RENDER_WIDTH = 1600  # 正文图渲染宽度

# ============ 公众号(2026-06 实测结构)============
WECHAT_MP_URL = "https://mp.weixin.qq.com/"
# 编辑器 URL 模板(token 运行时从 home 页抓取,登录态有效时直拼即进编辑器)
WECHAT_EDITOR_URL_TPL = (
    "https://mp.weixin.qq.com/cgi-bin/appmsg"
    "?t=media/appmsg_edit_v2&action=edit&isNew=1&type=10&createType=8"
    "&token={token}&lang=zh_CN"
)
SELECTORS = {
    "title": "#title",                              # TEXTAREA,实测 id 确实是 title
    "author": "#author",                            # INPUT
    "digest": "#js_description",                    # TEXTAREA 摘要
    "cover_input": "input[name='file']",            # 封面/图片上传(共用 file input)
    "save_draft": "button:has-text('保存为草稿')",  # 文字定位,避免 id 变化
    "img_upload_input": "input[name='file']",       # 正文图片上传
    "editor_body": ".ProseMirror",                  # ProseMirror 正文编辑区(contenteditable div)
    "logged_in_marker": ".weui-desktop-menu__item",
}

# ============ inline 样式(经典公众号排版 + #2563eb 主色)============
INLINE_STYLES = {
    "p": "margin:0 0 1em;line-height:1.75;font-size:16px;color:#1e293b;letter-spacing:0.5px;",
    "h2": "margin:1.8em 0 0.8em;font-size:20px;font-weight:bold;color:#1e293b;border-left:4px solid #2563eb;padding-left:12px;",
    "h3": "margin:1.5em 0 0.6em;font-size:17px;font-weight:bold;color:#1e293b;",
    "h4": "margin:1.3em 0 0.5em;font-size:16px;font-weight:bold;color:#1e293b;",
    "blockquote": "margin:1em 0;padding:12px 16px;background-color:#f1f5f9;border-left:4px solid #2563eb;color:#475569;font-size:15px;",
    "pre": "margin:1em 0;padding:16px;background-color:#1e293b;border-radius:8px;overflow-x:auto;font-size:14px;line-height:1.6;color:#e2e8f0;",
    "code": "background-color:#e2e8f0;padding:2px 6px;border-radius:3px;font-size:14px;color:#dc2626;",
    "a": "color:#2563eb;text-decoration:none;border-bottom:1px solid #2563eb;",
    "img": "max-width:100%;height:auto;display:block;margin:1em auto;border-radius:4px;",
    "ul": "margin:0 0 1em;padding-left:1.5em;line-height:1.75;color:#1e293b;",
    "ol": "margin:0 0 1em;padding-left:1.5em;line-height:1.75;color:#1e293b;",
    "li": "margin:0.3em 0;",
    "table": "width:100%;border-collapse:collapse;margin:1em 0;font-size:14px;",
    "th": "background-color:#2563eb;color:#fff;padding:8px;border:1px solid #cbd5e1;",
    "td": "padding:8px;border:1px solid #cbd5e1;color:#1e293b;",
    "strong": "color:#1e293b;font-weight:bold;",
    "hr": "border:none;border-top:1px solid #e2e8f0;margin:1.5em 0;",
}

# 不加 inline 样式的标签(让浏览器/编辑器默认)
SKIP_STYLE_TAGS = {"span", "br", "em"}

# ============ 图片占位符 ============
# 正文 img 的 src 替换成这个,发布时替换成微信图床 URL
IMG_PLACEHOLDER_FMT = "wx-image://{n}"

# ============ 超时与重试(秒)============
LOGIN_WAIT_TIMEOUT = 180
HEADLESS_LOGIN_WAIT = 20  # headless 模式下确认登录态的短等待;超时转弹窗扫码
UPLOAD_TIMEOUT = 20
MAX_RETRY = 5
HUMAN_DELAY = (0.5, 1.5)  # 操作间随机延时范围

# ============ 内容限制 ============
WECHAT_MAX_CHARS = 20000  # 公众号图文正文上限(约2万字),超限警告

# ============ 自动发布(群发通知)============
# 订阅号每日群发 1 次;无通知次数时按天顺延定时,最长 PUBLISH_RETRY_DAYS 天,全无则失败
# masssend 系 API(time_send/check_ad/check_hot_time)要求的 fingerprint。
# 账号级稳定值(2026-08-03 两次 UI 运行 + 0807 日志均一致),仅在打开群发弹窗时由前端生成,无法从页面加载提取。
# 若 API 定时再报 67011/-1,说明微信轮换了 fingerprint —— 跑一次 schedule_ui_v2 --capture-only 从日志抓新值。
MASS_SEND_FINGERPRINT = os.environ.get("WECHAT_FINGERPRINT", "")  # 账号级指纹（微信会轮换，跑 schedule_ui_v2 --capture-only 重抓）；未配则跳过群发定时
PUBLISH_RETRY_DAYS = 7
PUBLISH_STATUS_TIMEOUT = 60  # 发布状态回查轮询上限(秒)
MASS_SEND_URL = "https://mp.weixin.qq.com/cgi-bin/masssend"
MASS_SEND_PAGE_URL = "https://mp.weixin.qq.com/cgi-bin/masssendpage"
CHECK_PUBLISH_STATUS_URL = "https://mp.weixin.qq.com/cgi-bin/check_publish_status"
