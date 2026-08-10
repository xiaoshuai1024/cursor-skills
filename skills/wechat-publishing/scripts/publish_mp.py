"""微信公众号草稿箱 API 发布器(复刻 wechatsync 的 Web 端实现,跳过前端风控)。

原理:用 Playwright persistent context 持有真实登录态 cookie,通过 context.request
直接调用 mp.weixin.qq.com 的 Web 后台内部 API(与编辑器点「保存为草稿」同一接口)。
全程无模拟点击 / 键盘,不触发前端反自动化埋点 —— 这正是 wechatsync 相比「Playwright
模拟操作 ProseMirror」方案不被风控的原因。

流程:
1. 打开 mp.weixin.qq.com,确认登录态(首次需扫码,之后复用 wechat-profile/),提取
   token / ticket / user_name / svr_time
2. 读 .wechat-build/<slug>/wechat-ready-weixin.html,把本地图片上传到微信图床(cdn_url)
3. POST cgi-bin/operate_appmsg(sub=create&type=77) 创建草稿,返回 appMsgId
4. 回填 content/link-map.json 的 draft_appmsgid

参考实现:wechatsync/packages/core/src/adapters/platforms/weixin.ts

用法(需全局 Python311,含 playwright):
    PYTHONIOENCODING=utf-8 python3 -m publish_mp --slug <slug>
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from typing import Optional

# Windows GBK 终端下 emoji/中文 print 会崩,强制 stdout utf-8
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("❌ 需要全局 Python311 的 playwright。当前解释器未安装:python3 -m pip install playwright")

import config


def _svg_to_png(svg_path: str, out_path: str, width: int) -> None:
    """把 SVG 转 PNG。按优先级尝试:rsvg-convert → cairosvg → sharp(Node.js)。"""
    import shutil
    import subprocess

    if shutil.which("rsvg-convert"):
        subprocess.run(
            ["rsvg-convert", "-w", str(width), svg_path, "-o", out_path],
            check=True, capture_output=True,
        )
        return

    try:
        import cairosvg
        cairosvg.svg2png(url=svg_path, write_to=out_path, output_width=width)
        return
    except (ImportError, OSError):
        pass

    if shutil.which("node"):
        script = (
            "require('sharp')("
            f"{repr(svg_path)}"
            f").resize({width}).png().toFile("
            f"{repr(out_path)}"
            ").then(()=>process.exit(0)).catch(e=>{console.error(e);process.exit(1)})"
        )
        # sharp 在仓库根 node_modules
        repo_root = config.PROJECT_ROOT
        env = os.environ.copy()
        env["NODE_PATH"] = os.path.join(repo_root, "node_modules") + os.pathsep + env.get("NODE_PATH", "")
        subprocess.run(
            ["node", "-e", script],
            check=True, capture_output=True, env=env,
        )
        return

    raise RuntimeError("SVG→PNG 转换失败:需要 rsvg-convert / cairosvg / sharp 至少一个可用")

# 公众号 API 错误码(取自 wechatsync weixin.ts formatError)
ERROR_MAP = {
    -6: "请输入验证码",
    -8: "请输入验证码",
    -1: "系统错误,请注意备份内容后重试",
    -2: "参数错误,请注意备份内容后重试",
    -5: "服务错误,请注意备份内容后重试",
    -99: "内容超出字数,请调整",
    -206: "服务负荷过大,请稍后重试",
    200002: "参数错误,请注意备份内容后重试",
    200003: "登录态超时,请重新登录",
    412: "图文中含非法外链",
    62752: "可能含有具备安全风险的链接,请检查",
    64502: "你输入的微信号不存在",
    64505: "发送预览失败,请稍后再试",
    64506: "保存失败,链接不合法",
    64507: "内容不能包含外部链接",
    64562: "请勿插入非微信域名的链接",
    64509: "正文中不能包含超过3个视频",
    64515: "当前素材非最新内容,请重新打开并编辑",
    64702: "标题超出64字长度限制",
    64703: "摘要超出120字长度限制",
    64705: "内容超出字数,请调整",
    10806: "正文不能有违规内容,请重新编辑",
    10807: "内容不能违反公众平台协议",
    220001: "素材管理中的存储数量已达上限",
    220002: "图片库已达到存储上限",
    # masssend 群发特有错误码
    64004: "定时发表校验失败(可能今日已无可选时间/无通知次数)",
    64005: "群发失败(需扫码确认或今日次数已用完)",
    64006: "该素材不可群发",
}

# 需要扫码确认的信号(风险操作保护开启时,群发/定时设置需管理员扫码)
NEED_QR_MARKERS = ("扫码", "scan", "need_qrcode", "qrcode", "checkcode", "verify", "验证码")

# 内容/素材类错误:重试也没用,直接终止而非顺延(避免白调 7 次 API)
NON_RETRYABLE_RET = {-1, -2, -5, 412, 10806, 10807, 64006, 64506, 64507, 64509, 64562, 64705}

MIME_BY_EXT = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def get_token(request) -> Optional[dict]:
    """GET mp.weixin.qq.com 提取登录态字段(复刻 weixin.ts checkAuth)。

    注意:token 限定 [A-Za-z0-9_-] 字符类 —— 未登录页的 data:{...t:"https://..."} 含
    `//`,不会被误匹配为 token。ticket 缺失也视为未登录(filetransfer 强依赖 ticket)。
    """
    resp = request.get(config.WECHAT_MP_URL)
    html = resp.text()

    m = re.search(r'data:\s*\{[\s\S]*?t:\s*["\']([A-Za-z0-9_-]+)["\']', html)
    if not m:
        return None
    token = m.group(1)

    def grab(pattern: str) -> str:
        mm = re.search(pattern, html)
        return mm.group(1) if mm else ""

    ticket = grab(r'ticket:\s*["\']([^"\']+)["\']')
    if not ticket:
        return None

    return {
        "token": token,
        "ticket": ticket,
        "userName": grab(r'user_name:\s*["\']([^"\']+)["\']'),
        "svrTime": grab(r'time:\s*["\'](\d+)["\']') or str(int(time.time())),
    }


def upload_image(request, mp: dict, local_path: str) -> dict:
    """上传本地图片到微信图床,返回响应 dict(含 cdn_url / fileid)。

    正文图取 cdn_url,封面图还需 fileid。
    """
    with open(local_path, "rb") as f:
        data = f.read()
    ext = os.path.splitext(local_path)[1].lower()
    mime = MIME_BY_EXT.get(ext, "image/jpeg")
    ts = str(int(time.time() * 1000))
    name = os.path.basename(local_path)

    url = (
        "https://mp.weixin.qq.com/cgi-bin/filetransfer"
        f"?action=upload_material&f=json&scene=8&writetype=doublewrite&groupid=1"
        f"&ticket_id={mp['userName']}&ticket={mp['ticket']}&svr_time={mp['svrTime']}"
        f"&token={mp['token']}&lang=zh_CN&seq={ts}&t={random.random()}"
    )
    resp = request.post(
        url,
        headers={
            "Origin": "https://mp.weixin.qq.com",
            "Referer": "https://mp.weixin.qq.com/",
        },
        multipart={
            "type": mime,
            "id": ts,
            "name": name,
            "lastModifiedDate": time.strftime("%a %b %d %Y %H:%M:%S GMT+0800"),
            "size": str(len(data)),
            "file": {"name": name, "mimeType": mime, "buffer": data},
        },
    )
    res = resp.json()
    if res.get("base_resp", {}).get("err_msg") != "ok" or not res.get("cdn_url"):
        raise RuntimeError(f"图片上传失败: {local_path} -> {res}")
    # 返回完整响应:正文图取 cdn_url,封面图另取 fileid
    return res


def replace_images(request, mp: dict, html: str, out_dir: str) -> str:
    """把正文里的本地图片 / 漏网 SVG 换成微信 cdn_url。

    返回替换后的 HTML;外链 / 微信图床原样保留。
    """
    def repl(match: re.Match) -> str:
        src = match.group(1)
        # 已是微信图床或外链 → 保持原样
        if "mmbiz.qpic.cn" in src:
            return match.group(0)
        # 本地图片(prepare.py filepath 模式产出的绝对路径)
        if os.path.exists(src):
            cdn = upload_image(request, mp, src)["cdn_url"]
            return f'src="{cdn}"'
        # 漏网 SVG(convert_images 的 ?v= 查询参数正则匹配不到,兜底转换;失败则保留原样)
        mm = re.match(r"/svg/(.+\.svg)(\?.*)?$", src)
        if mm:
            svg_path = os.path.join(config.SVG_DIR, mm.group(1))
            if os.path.exists(svg_path):
                try:
                    png_path = os.path.join(out_dir, f"img-svg-{int(time.time() * 1000)}.png")
                    _svg_to_png(svg_path, png_path, config.IMAGE_RENDER_WIDTH)
                    cdn = upload_image(request, mp, png_path)["cdn_url"]
                    return f'src="{cdn}"'
                except Exception as exc:  # noqa: BLE001 转换失败不阻断发布
                    print(f"⚠️ SVG 转换失败,保留原引用: {svg_path} ({exc})")
        return match.group(0)

    return re.sub(r'src="([^"]*)"', repl, html)


def build_album_field(album_id: str, album_title: str) -> str:
    """构造 create 表单的 appmsg_album_info0 值(富结构,2026-08-03 实证)。

    注意:简单格式 `{"appmsg_album_infos":[{"id":..,"title":..}]}` 会被服务端忽略,
    必须用带 album_id / 嵌套 appmsg_album_infos / tagSource 的富结构才能写入合集。
    """
    inner = {"id": album_id, "title": album_title, "album_id": int(album_id),
             "appmsg_album_infos": [], "tagSource": 0}
    return json.dumps(
        {"id": album_id, "title": album_title, "album_id": int(album_id),
         "appmsg_album_infos": [inner]},
        ensure_ascii=False,
    )


def create_draft(request, mp: dict, title: str, digest: str, content: str,
                 cover: Optional[dict] = None, *,
                 author: str = "", copyright_type: str = "0",
                 album: Optional[dict] = None) -> str:
    """创建草稿,返回 appMsgId(复刻 weixin.ts publish 的 formData)。

    cover: 封面 {"cdn_url","fileid"}(由 cover.png 上传得到);None 则不设封面。
    author: 作者名(公众号对个人订阅号可能忽略,编辑器默认带出账号作者)。
    copyright_type: 原创声明 "0"=不声明 "1"=文字原创 "2"=漫画原创。
    album: 合集 {"id","title"};None 则不挂合集(默认。发布走 --album 传 AI 合集)。
    """
    cv = cover or {}
    form = {
        "token": mp["token"],
        "lang": "zh_CN",
        "f": "json",
        "ajax": "1",
        "random": str(random.random()),
        "AppMsgId": "",
        "count": "1",
        "data_seq": "0",
        "operate_from": "Chrome",
        "isnew": "0",
        # 标题 / 作者 / 摘要 / 正文
        "title0": title,
        "author0": author,
        "writerid0": "0",
        "fileid0": cv.get("fileid", ""),
        "digest0": digest or "",
        "auto_gen_digest0": "0" if digest else "1",
        "content0": content,
        "sourceurl0": "",
        # 封面:cover.png 上传所得 cdn_url + fileid;crop_list 留空由后台裁剪
        "cdn_url0": cv.get("cdn_url", ""),
        "cdn_235_1_url0": cv.get("cdn_url", ""),
        "cdn_1_1_url0": cv.get("cdn_url", ""),
        "cdn_url_back0": cv.get("cdn_url", ""),
        "crop_list0": "",
        # 评论 / 打赏 / 视频推荐
        "need_open_comment0": "1",
        "only_fans_can_comment0": "0",
        "can_reward0": "0",
        "related_video0": "",
        "is_video_recommend0": "-1",
        "ad_video_transition0": "",
        # 其余固定字段(wechatsync 原样)
        "music_id0": "",
        "video_id0": "",
        "voteid0": "",
        "voteismlt0": "",
        "supervoteid0": "",
        "cardid0": "",
        "cardquantity0": "",
        "cardlimit0": "",
        "vid_type0": "",
        "show_cover_pic0": "0",
        "shortvideofileid0": "",
        "copyright_type0": copyright_type,
        "releasefirst0": "",
        "platform0": "",
        "reprint_permit_type0": "",
        "allow_reprint0": "",
        "allow_reprint_modify0": "",
        "original_article_type0": "",
        "ori_white_list0": "",
        "free_content0": "",
        "fee0": "0",
        "ad_id0": "",
        "guide_words0": "",
        "is_share_copyright0": "0",
        "share_copyright_url0": "",
        "source_article_type0": "",
        "reprint_recommend_title0": "",
        "reprint_recommend_content0": "",
        "share_page_type0": "0",
        "share_imageinfo0": '{"list":[]}',
        "share_video_id0": "",
        "dot0": "{}",
        "share_voice_id0": "",
        "insert_ad_mode0": "",
        "categories_list0": "[]",
    }
    # 合集:create 时挂进指定合集(富结构,见 build_album_field)
    if album:
        form["appmsg_album_info0"] = build_album_field(album["id"], album["title"])

    url = (
        "https://mp.weixin.qq.com/cgi-bin/operate_appmsg"
        f"?t=ajax-response&sub=create&type=77&token={mp['token']}&lang=zh_CN"
    )
    resp = request.post(
        url,
        headers={
            "Origin": "https://mp.weixin.qq.com",
            "Referer": "https://mp.weixin.qq.com/",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        form=form,
    )
    res = resp.json()
    if not res.get("appMsgId"):
        ret = res.get("ret", res.get("base_resp", {}).get("ret"))
        detail = ERROR_MAP.get(ret, f"未知错误码: {ret}")
        raise RuntimeError(f"{detail} | 响应: {res}")
    return str(res["appMsgId"])


class MassSendError(RuntimeError):
    """群发失败。ret 为微信错误码;ret 在 NON_RETRYABLE_RET 内时顺延无意义。"""

    def __init__(self, message: str, ret: Optional[int] = None):
        super().__init__(message)
        self.ret = ret

    @property
    def retryable(self) -> bool:
        return self.ret not in NON_RETRYABLE_RET


def mass_send(request, mp: dict, appmsgid: str, *, send_time: Optional[str] = None) -> dict:
    """群发/定时群发。send_time 为 None → 立即群发;否则 action=time_send 定时。

    返回响应 dict;业务失败(无次数/需扫码/素材不可发)抛 MassSendError。
    """
    base = f"{config.MASS_SEND_URL}?t=ajax-response&token={mp['token']}&lang=zh_CN"
    if send_time is not None:
        base += "&action=time_send"
    form = {
        "token": mp["token"],
        "lang": "zh_CN",
        "f": "json",
        "ajax": "1",
        "msgid": appmsgid,
        "sync_version": "1",
    }
    if send_time is not None:
        form["send_time"] = send_time
    resp = request.post(
        base,
        headers={
            "Origin": "https://mp.weixin.qq.com",
            "Referer": "https://mp.weixin.qq.com/",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        form=form,
    )
    res = resp.json()
    ret = res.get("ret", res.get("base_resp", {}).get("ret"))
    if ret and int(ret) != 0:
        detail = ERROR_MAP.get(int(ret), f"未知错误码: {ret}")
        raise MassSendError(f"{detail} | 响应: {res}", ret=int(ret))
    return res


def check_publish_status(request, mp: dict, appmsgid: str, timeout: int = config.PUBLISH_STATUS_TIMEOUT) -> str:
    """轮询发布状态(最长 timeout 秒),返回 'published' / 'pending' / 'failed'。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = request.get(
                config.CHECK_PUBLISH_STATUS_URL,
                params={"msgid": appmsgid, "publish_type": "1", "token": mp["token"], "lang": "zh_CN", "f": "json", "ajax": "1"},
            )
            res = resp.json()
        except Exception as exc:  # noqa: BLE001 网络抖动不阻断,重试
            time.sleep(3)
            continue
        ret = res.get("base_resp", {}).get("ret")
        if ret == 0:
            # 依实际返回判断:有 publish 信息且状态为终态
            pub = res.get("publish_info") or res.get("appmsgex") or res.get("sent_result") or {}
            if pub:
                return "published"
            return "pending"
        time.sleep(3)
    return "pending"


def _tomorrow_unix(day_offset: int) -> str:
    """返回未来 day_offset 天的发布时间(unix 秒)。day_offset 从 1 开始(明天)。"""
    from datetime import datetime, timedelta

    # 取未来某天 09:00 本地时间(避开凌晨群发时段)
    target = datetime.now() + timedelta(days=day_offset)
    target = target.replace(hour=9, minute=0, second=0, microsecond=0)
    return str(int(target.timestamp()))


def publish_auto(request, mp: dict, appmsgid: str, *, draft_only: bool = False) -> str:
    """自动发布入口:检测配额 → 立即群发 → 无配额顺延定时(最长 PUBLISH_RETRY_DAYS 天)。

    draft_only=True → 只返回 'draft',不发布。
    返回 'published'(立即发布成功) / 'scheduled'(已预约定时) / 'draft'(只存草稿)。
    7 天全无通知次数 → 抛 RuntimeError('7 天内均无通知次数')。
    """
    if draft_only:
        return "draft"

    # 先乐观尝试立即群发(服务端自校验配额);失败则顺延
    try:
        res = mass_send(request, mp, appmsgid)
        print(f"📨 立即群发成功: {res.get('msgid', appmsgid)}")
        return "published"
    except MassSendError as exc:
        msg = str(exc)
        if any(m in msg for m in NEED_QR_MARKERS):
            raise RuntimeError(
                "需要扫码确认(风险操作保护)。到后台「设置与开发→安全中心→风险操作保护→群发消息」关闭后可免扫码,或手动扫码。"
            ) from exc
        # 内容/素材类错误:顺延无意义,直接失败
        if not exc.retryable:
            raise RuntimeError(msg) from exc
        print(f"  立即群发失败(可顺延): {msg}")

    # 立即群发失败(可顺延) → 逐日顺延定时
    for day in range(1, config.PUBLISH_RETRY_DAYS + 1):
        ts = _tomorrow_unix(day)
        try:
            res = mass_send(request, mp, appmsgid, send_time=ts)
            print(f"📅 已预约定时群发: {day} 天后 (send_time={ts})")
            return "scheduled"
        except MassSendError as exc2:
            msg2 = str(exc2)
            if any(m in msg2 for m in NEED_QR_MARKERS):
                raise RuntimeError(
                    "需要扫码确认(风险操作保护)。到后台关闭「群发消息」风险操作保护后可免扫码。"
                ) from exc2
            if not exc2.retryable:
                raise RuntimeError(msg2) from exc2
            print(f"  第 {day} 天无通知次数: {msg2}")

    raise RuntimeError("7 天内均无通知次数,发布失败。草稿已保留,请手动处理。")


def update_link_map_publish(slug: str, status: str, published_at: str = "") -> None:
    """在 link-map.json 的 weixin 节点追加发布状态字段。"""
    path = config.LINK_MAP_PATH
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}
    wx = data.setdefault(slug, {}).setdefault("weixin", {})
    wx["publish_status"] = status
    if published_at:
        wx["published_at"] = published_at
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def update_link_map(slug: str, draft_appmsgid: str) -> None:
    """回填 link-map.json 的 weixin.draft_appmsgid。"""
    path = config.LINK_MAP_PATH
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    data.setdefault(slug, {}).setdefault("weixin", {})["draft_appmsgid"] = draft_appmsgid
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="公众号草稿箱 API 直推(Playwright 登录态,无 wechatsync)")
    parser.add_argument("--slug", required=True, help="文章 slug")
    parser.add_argument("--platform", default="weixin", help="平台(当前仅 weixin)")
    parser.add_argument("--build-dir", default=None, help="构建产物目录(默认 .wechat-build/<slug>)")
    parser.add_argument("--profile", default=config.WECHAT_PROFILE_DIR, help="Playwright 持久化登录 profile")
    parser.add_argument(
        "--channel", default=config.BROWSER_CHANNEL,
        help="浏览器 channel。默认按平台(见 config.BROWSER_CHANNEL):Windows=msedge / macOS=chrome,可用环境变量 BROWSER_CHANNEL 覆盖",
    )
    parser.add_argument(
        "--no-headless", action="store_true",
        help="强制弹可见窗口(调试/首次扫码用)。默认已登录时 headless 无窗口,登录态失效才弹窗",
    )
    parser.add_argument(
        "--draft-only", action="store_true",
        help="只存草稿,不自动发布(逃生舱,保留旧行为)",
    )
    parser.add_argument(
        "--album", default=config.DEFAULT_ALBUM,
        help=f"挂载的合集名(默认 {config.DEFAULT_ALBUM},来自 config.ALBUMS);传 'none' 不挂",
    )
    args = parser.parse_args()

    album = None
    if args.album != "none":
        if args.album not in config.ALBUMS:
            sys.exit(f"❌ 未知合集: {args.album}(可选 {list(config.ALBUMS)})")
        album = config.ALBUMS[args.album]

    build_dir = args.build_dir or os.path.join(config.WECHAT_BUILD_DIR, args.slug)
    html_path = os.path.join(build_dir, f"wechat-ready-{args.platform}.html")
    meta_path = os.path.join(build_dir, "meta.json")
    for p in (html_path, meta_path):
        if not os.path.exists(p):
            sys.exit(f"❌ 缺少 {p},先运行 make wechat-prepare slug={args.slug}")

    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)

    def launch(headless: bool):
        return p.chromium.launch_persistent_context(
            args.profile,
            channel=args.channel,
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1440, "height": 900},
        )

    with sync_playwright() as p:
        ctx = launch(headless=not args.no_headless)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(config.WECHAT_MP_URL, wait_until="domcontentloaded")

        # 默认 headless:已登录的会话(wechat-profile/ 里 cookie 有效)不用弹窗。
        # token/ticket 只存在于首页 HTML,故仍需打开一次首页;login 态失效再弹窗扫码。
        mp = None
        if not args.no_headless:
            print("🔌 无窗口模式获取登录态(复用 wechat-profile/ 会话)...")
            deadline = time.time() + config.HEADLESS_LOGIN_WAIT
            while time.time() < deadline:
                mp = get_token(ctx.request)
                if mp:
                    break
                time.sleep(2)

        if not mp:
            # 登录态失效或首次使用(无 cookie)→ 弹可见窗口扫码,登录后写回 wechat-profile/
            print("🔌 未检测到有效登录态,弹出浏览器窗口(首次使用请在窗口扫码登录)...")
            ctx.close()
            ctx = launch(headless=False)
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(config.WECHAT_MP_URL, wait_until="domcontentloaded")
            deadline = time.time() + config.LOGIN_WAIT_TIMEOUT
            while time.time() < deadline:
                mp = get_token(ctx.request)
                if mp:
                    break
                time.sleep(3)
            if not mp:
                ctx.close()
                sys.exit(f"❌ {config.LOGIN_WAIT_TIMEOUT}s 内未获取登录态(未扫码或超时)")

        print(f"✅ 登录态 OK: {mp['token'][:6]}... (ticket={bool(mp['ticket'])})")

        with open(html_path, encoding="utf-8") as f:
            html = f.read()
        html = replace_images(ctx.request, mp, html, build_dir)

        # 封面:prepare.py 已从首图生成 cover.png(9:5),上传后填入草稿封面字段
        cover_path = os.path.join(build_dir, "cover.png")
        cover = None
        if os.path.exists(cover_path):
            try:
                cres = upload_image(ctx.request, mp, cover_path)
                cover = {
                    "cdn_url": cres.get("cdn_url", ""),
                    # upload_material 响应的素材 ID 字段名是 "content"(实测),非 fileid/id
                    "fileid": str(cres.get("content") or cres.get("fileid") or cres.get("id") or ""),
                }
                print(f"🖼️  封面上传 OK: fileid={cover['fileid']} cdn={cover['cdn_url'][:40]}...")
            except RuntimeError as exc:
                print(f"⚠️ 封面上传失败(草稿仍会创建,封面后台手动补): {exc}")
        else:
            print(f"⚠️ 无 {cover_path},跳过封面(后台需手动补)")

        draft_id = create_draft(
            ctx.request,
            mp,
            title=meta["title"],
            digest=meta.get("digest", ""),
            content=html,
            cover=cover,
            author=config.DEFAULT_AUTHOR,
            copyright_type=config.COPYRIGHT_TYPE,
            album=album,
        )
        if album:
            print(f"📁 已挂合集: {album['title']} ({album['id']})")

        # 自动发布(群发通知):无通知次数自动顺延定时,最长 7 天。
        # 发布与状态回查都需 ctx.request,故放在 ctx 生命周期内。
        pub_result = "draft"
        pub_status = ""
        pub_err = ""
        if args.draft_only:
            print("🔒 --draft-only:只存草稿,不发布")
        else:
            print("📨 开始自动发布(群发通知)...")
            try:
                pub_result = publish_auto(ctx.request, mp, draft_id, draft_only=False)
                if pub_result == "published":
                    # 提交成功 ≠ 粉丝已收到,回查终态
                    pub_status = check_publish_status(ctx.request, mp, draft_id)
            except RuntimeError as exc:
                pub_result = "failed"
                pub_err = str(exc)
                print(f"❌ 自动发布失败: {pub_err}")
        ctx.close()

    update_link_map(args.slug, draft_id)
    print(f"✅ 草稿创建成功 appMsgId={draft_id}")
    print(f"   link-map.json 已回填: {args.slug}/weixin/draft_appmsgid={draft_id}")

    # 发布结果落库 + 状态回查
    if pub_result == "published":
        if pub_status == "published":
            print("✅ 群发推送成功,粉丝已收到通知")
            update_link_map_publish(args.slug, "published")
        else:
            print(f"⏳ 群发已提交,状态回查为 {pub_status or 'pending'}(异步处理中)")
            update_link_map_publish(args.slug, "pending")
    elif pub_result == "scheduled":
        print("📅 已预约定时群发(今日无通知次数,已顺延)。link-map.json 记 publish_status=pending")
        update_link_map_publish(args.slug, "pending")
    elif pub_result == "draft":
        print("   → 草稿已保存,未发布(--draft-only 或默认逃生)")
    elif pub_result == "failed":
        print(f"   → 发布失败: {pub_err}。草稿已保留在草稿箱,请手动处理")
        update_link_map_publish(args.slug, "failed")
    else:
        print(f"   → 发布结果: {pub_result}")


if __name__ == "__main__":
    main()
