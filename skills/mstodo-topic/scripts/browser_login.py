# -*- coding: utf-8 -*-
"""To Do 网页版登录态获取/复用 + Bearer 偷取 + 接口抓包（mstodo-topic skill）。

实测结论（2026-08-26）：
- msedge 持久化 profile（.mstodo-topic/msedge-profile）+ patchright（原生 playwright 启动 msedge 崩）。
- 未登录落地页有「请登录你的帐户」文案且不跳 login.* → 登录判定必须看 DOM 应用标记（侧栏「我的一天」等）。
- 会话可静默恢复：落地页点「开始使用」→ MSAL 帐户瓦片（<small> 含邮箱）点一下 → 免密回应用。
- 应用对 substrate.office.com 的请求带 Authorization Bearer（裸 fetch 401，cookie 不够）；
  MSAL token 在 localStorage 被加密 → 导航前挂 request 监听偷应用自身请求头，同会话复用。
- 空闲启动可能不发同步请求 → 落地后 reload 原地/点侧栏列表逼应用发请求。

用法:
  py -m browser_login login [--capture] [--watch 120] [--timeout 600]
  py -m browser_login status
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
from collections import Counter
from typing import Any

import mstodo_common as mc

mc._utf8_stdio()

# Windows 用 msedge（本机 Chrome 损坏，见 CLAUDE.md）；macOS 用 chrome。与 tech-topic / douyin 一致。
CHANNEL = "msedge" if sys.platform == "win32" else "chrome"
# 应用侧栏标记（登录成功的硬证据）；中英双语
APP_MARKERS = ("我的一天", "已计划", "已分配", "My Day", "Planned", "Assigned", "Flagged")
SIGNIN_MARKERS = ("请登录你的帐户", "请登录你的账户", "please sign in")
# 默认无头运行（live.com 直达修复后实测稳定，2026-08-26 连跑 lists+tasks 全通）；
# 需要观察登录/调试时设 MSTODO_HEADED=1 弹可见窗口
HEADLESS = not bool(int(__import__("os").environ.get("MSTODO_HEADED", "0")))

_SHARED: tuple[Any, Any, Any] | None = None  # (pw, ctx, page) 进程内复用，避免每次 fetch 冷启动
_AUTH_HEADERS: dict[str, str] = {}  # 偷来的 Bearer（substrate 鉴权必需）


def _browser_api():
    """patchright 优先（仓库 scripts/pub 惯例，反检测补丁版），缺了再退 playwright。"""
    try:
        from patchright.sync_api import sync_playwright

        return sync_playwright
    except ImportError:
        from playwright.sync_api import sync_playwright

        return sync_playwright


def _host(url: str) -> str:
    return urllib.parse.urlsplit(url).hostname or ""


def _body_text(page, limit: int = 4000) -> str:
    try:
        return page.eval_on_selector("body", f"e => (e.innerText || '').slice(0, {limit})") or ""
    except Exception:
        return ""


def _looks_logged_in(page) -> bool:
    """登录判定（硬证据版）：正文含应用侧栏标记且无登录落地文案，且在 to-do.* 域。
    空白渲染期（无标记）判 False，杜绝误报。"""
    text = _body_text(page).lower()
    if any(marker in text for marker in SIGNIN_MARKERS):
        return False
    if not any(marker in text for marker in APP_MARKERS):
        return False
    return _host(page.url or "").startswith("to-do.")


def open_context(headless: bool = False):
    pw = _browser_api()().start()
    ctx = pw.chromium.launch_persistent_context(
        str(mc.PROFILE_DIR),
        channel=CHANNEL,
        headless=headless,
        args=["--disable-blink-features=AutomationControlled", "--lang=zh-CN", "--js-flags=--max-old-space-size=512"],
        viewport={"width": 1440, "height": 900},
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    return pw, ctx, page


def _make_auth_sniffer(holder: dict[str, Any]):
    """request 监听器：偷应用自身 substrate 请求的 Authorization（+Accept），存进 holder。"""

    def on_request(req) -> None:
        try:
            if holder.get("authorization"):
                return
            if "substrate.office.com" not in (req.url or ""):
                return
            hs = dict(req.headers or {})
            auth = hs.get("authorization") or hs.get("Authorization")
            if auth:
                holder.update({k: v for k, v in hs.items() if k.lower() in ("authorization", "accept")})
        except Exception:
            pass

    return on_request


def _click_landing_cta(page) -> bool:
    """落地页 → 触发 MSAL 跳转（点「开始使用」，兜底「登录」，中英双语文案）。"""
    for text in ("开始使用", "get started", "登录", "sign in"):
        try:
            page.get_by_text(text, exact=False).first.click(timeout=1500)
            return True
        except Exception:
            continue
    return False


def _click_account_tile(page) -> bool:
    """MSAL 帐户选择页 → 点已有帐户瓦片（邮箱在 <small>，ko click 绑容器，点文本冒泡即触发静默 SSO）。"""
    import re

    email_re = re.compile(r"@[\w.-]+\.\w+")
    for candidate in (page.locator("small", has_text="@").first, page.get_by_text(email_re).first):
        try:
            candidate.click(timeout=2000)
            return True
        except Exception:
            continue
    return False


def _nudge_app(page) -> None:
    """逼空闲的应用发同步请求：先点侧栏列表，点不动就原地 reload。"""
    for label in ("任务", "Tasks", "我的一天", "My Day"):
        try:
            page.get_by_text(label, exact=True).first.click(timeout=1200)
            return
        except Exception:
            continue
    try:
        page.goto(page.url, wait_until="domcontentloaded", timeout=60000)
    except Exception:
        pass


def ensure_app_session(page, timeout: int = 120) -> bool:
    """确保页面真正进入应用（含静默 SSO：落地页 CTA → 帐户瓦片 → 应用标记出现）。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _looks_logged_in(page):
            return True
        url = page.url or ""
        if "login.microsoftonline" in url or "login.live.com" in url:
            _click_account_tile(page)
        else:
            _click_landing_cta(page)
        time.sleep(3)
    return _looks_logged_in(page)


def _shared_page():
    """进程内共享的应用页：可见窗口启动（静默 SSO 免交互）→ 偷 Bearer。"""
    global _SHARED, _AUTH_HEADERS
    if _SHARED is None:
        pw, ctx, page = open_context(headless=HEADLESS)
        auth_headers: dict[str, str] = {}
        try:
            page.on("request", _make_auth_sniffer(auth_headers))
            page.goto(mc.TODO_HOME, wait_until="domcontentloaded", timeout=40000)
            if not ensure_app_session(page):
                raise mc.SessionExpired()
            # 等应用自启 substrate 请求带出 Bearer；15s 没动静就 nudge 一轮
            deadline = time.time() + 45
            nudged = 0
            while not auth_headers.get("authorization") and time.time() < deadline:
                time.sleep(1)
                if nudged == 0 and time.time() > deadline - 30:
                    _nudge_app(page)
                    nudged += 1
                elif nudged == 1 and time.time() > deadline - 15:
                    _nudge_app(page)
                    nudged += 1
            if not auth_headers.get("authorization"):
                raise RuntimeError("应用未发出 substrate 请求，没偷到 Bearer —— 重试；仍失败则 make todo-login")
        except Exception:
            try:
                ctx.close()
                pw.stop()
            except Exception:
                pass
            raise
        _AUTH_HEADERS = auth_headers
        _SHARED = (pw, ctx, page)
    return _SHARED[2]


def close_shared() -> None:
    global _SHARED
    if _SHARED is not None:
        try:
            _SHARED[1].close()
            _SHARED[0].stop()
        except Exception:
            pass
        _SHARED = None


def fetch_json(url: str, method: str = "GET", payload: dict[str, Any] | None = None) -> Any:
    """登录态 in-browser fetch。401/403 → SessionExpired；非 JSON → 提示重抓。
    带 payload 时自动补 Content-Type: application/json（OData 写接口要求）。"""
    page = _shared_page()  # 先建会话（顺带偷 Bearer 到 _AUTH_HEADERS），再组装 headers
    headers = dict(_AUTH_HEADERS)  # 偷来的 Bearer（substrate 鉴权必需，cookie 不够，实测 401）
    headers.update(mc.load_endpoints()["headers"])
    if payload is not None:
        headers.setdefault("Content-Type", "application/json")
    headers.setdefault("Accept", "application/json")
    # 同源兜底：应用域重定向后，相对路径按页面实际 origin 拼
    if not url.startswith("http"):
        current = urllib.parse.urlsplit(page.url)
        url = f"{current.scheme}://{current.netloc}{url}"
    js = """async ([u, m, b, h]) => {
        const r = await fetch(u, {method: m, headers: h, body: b, credentials: 'include'});
        const text = await r.text();
        return {status: r.status, ct: r.headers.get('content-type') || '', body: text.slice(0, 500000)};
    }"""
    body = json.dumps(payload, ensure_ascii=False) if payload is not None else None
    res = page.evaluate(js, [url, method.upper(), body, headers])
    if res["status"] in (401, 403):
        raise mc.SessionExpired()
    text = str(res.get("body") or "")
    if "json" not in str(res.get("ct", "")):
        head = text[:300].lower()
        if "<html" in head or "signin" in head:
            raise mc.SessionExpired("接口返回登录页 —— 会话过期，重新 make todo-login")
        raise RuntimeError(
            f"接口返回非 JSON（status={res['status']}）—— 疑似接口变更，make todo-login capture=1 重抓后更新 endpoints.json"
        )
    parsed = json.loads(text)
    if isinstance(parsed, dict) and "error" in parsed and "Value" not in parsed:
        # todob2 会以 JSON error 体响应（如不支持的端点），不只靠 HTTP 状态码
        detail = parsed.get("error")
        raise RuntimeError(f"接口返回 error: {json.dumps(detail, ensure_ascii=False)[:200]}")
    return parsed


class _Recorder:
    """xhr/fetch 响应记录器：逐条落 capture.jsonl，dump 时按 方法+路径模板 聚合摘要。"""

    def __init__(self) -> None:
        self.counter: Counter[str] = Counter()

    def attach(self, page) -> None:
        def on_response(resp) -> None:
            try:
                req = resp.request
                if req.resource_type not in ("xhr", "fetch"):
                    return
                url = req.url or ""
                host = _host(url)
                if any(h in host for h in mc.LOGIN_HOST_HINTS):
                    return  # 登录流程自身的请求，跳过
                content_type = (resp.headers or {}).get("content-type", "")
                body_sample = ""
                if "json" in content_type.lower():
                    try:
                        body_sample = resp.text()[:4000]
                    except Exception:
                        pass
                post_data = ""
                if req.method.upper() not in ("GET", "HEAD"):
                    try:
                        post_data = (req.post_data or "")[:2000]
                    except Exception:
                        pass
                tpl = mc.templated(url)
                self.counter[f"{req.method.upper():<6} {tpl}"] += 1
                mc.save_capture_line(
                    {
                        "ts": mc.utc_now_iso(),
                        "method": req.method.upper(),
                        "url": url,
                        "templated": tpl,
                        "status": resp.status,
                        "content_type": content_type,
                        "request_headers": {k: v for k, v in dict(req.headers or {}).items()
                                            if k.lower() in ("authorization", "accept", "content-type", "prefer")},
                        "post_data": post_data,
                        "body_sample": body_sample,
                    }
                )
            except Exception:
                pass  # 抓包辅助，不因单条失败中断

        page.on("response", on_response)

    def dump(self) -> None:
        if not self.counter:
            print(f"⚠️ 未捕获任何 XHR（检查页面是否加载）——原始记录: {mc.CAPTURE_PATH}")
            return
        print(f"\n===== 抓包摘要（{len(self.counter)} 类请求，按出现次数排序）=====")
        for key, count in self.counter.most_common():
            print(f"  ×{count:<3} {key}")
        print(f"原始记录 → {mc.CAPTURE_PATH}")
        print("下一步: 从上面挑出 清单列表/任务读取/任务写入 三类地址，写进 endpoints.json（见 SKILL.md「接口固化」）")


def login_gate(headless: bool = False, timeout: int = 600, capture: bool = False, watch: int = 120):
    """确保登录态（静默 SSO 可免交互；不行则等用户手动登录）。返回 (pw, ctx, page, ok)。"""
    pw, ctx, page = open_context(headless=headless)
    recorder = _Recorder() if capture else None
    if recorder:
        recorder.attach(page)
        if mc.CAPTURE_PATH.exists():
            mc.CAPTURE_PATH.unlink()  # 每次抓包重开一份，避免旧记录干扰
    try:
        page.goto(mc.TODO_HOME, wait_until="domcontentloaded", timeout=40000)
        page.wait_for_timeout(4000)
    except Exception:
        pass  # 登录跳转期 URL 多变，goto 超时不致命，靠轮询判定

    deadline = time.time() + timeout
    announced = False
    while time.time() < deadline:
        if _looks_logged_in(page):
            print("✅ 登录态就绪（应用已进入，状态持久化在本地 profile）")
            if recorder:
                print(
                    f"\n👀 抓包观察窗 {watch}s：请在浏览器窗口里 ①点开你的目标清单 "
                    "②完成或编辑一条测试待办（让写接口被抓到）…"
                )
                page.wait_for_timeout(watch * 1000)
                recorder.dump()
            return pw, ctx, page, True
        if not announced:
            print("⚠️ 未检测到登录态。正在尝试静默 SSO；若浏览器停在登录页，请手动登录（应用进入后自动继续）。")
            print(f"   最长等 {timeout}s …")
            announced = True
        url = page.url or ""
        if "login.microsoftonline" in url or "login.live.com" in url:
            _click_account_tile(page)  # 有帐户瓦片则代点（静默 SSO），无则等用户输入密码
        else:
            _click_landing_cta(page)
        time.sleep(3)
    print(f"❌ 等待登录超时（{timeout}s）—— 重新执行 make todo-login")
    return pw, ctx, page, False


def cmd_status(_args: argparse.Namespace) -> int:
    pw, ctx, page = open_context(headless=HEADLESS)
    try:
        try:
            page.goto(mc.TODO_HOME, wait_until="domcontentloaded", timeout=40000)
            if not ensure_app_session(page, timeout=90):
                print("❌ 未登录 / 会话过期 —— make todo-login 重新登录")
                return 2
        except Exception as exc:
            print(f"❌ 打开失败: {exc}")
            return 1
        print(f"✅ 登录态有效（应用已进入: {page.url[:60]}）")
        return 0
    finally:
        try:
            ctx.close()
            pw.stop()
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="To Do 网页版登录 + 抓包（mstodo-topic）")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_login = sub.add_parser("login", help="登录（静默 SSO 优先，必要时手动；cookie 持久化）")
    p_login.add_argument("--capture", action="store_true", help="登录后抓包观察，固化接口用")
    p_login.add_argument("--watch", type=int, default=120, help="抓包观察窗秒数（默认 120）")
    p_login.add_argument("--timeout", type=int, default=600, help="等待登录超时秒数（默认 600）")
    sub.add_parser("status", help="检查登录态")
    args = parser.parse_args()

    if args.cmd == "status":
        return cmd_status(args)
    pw, ctx, _page, ok = login_gate(capture=args.capture, watch=args.watch, timeout=args.timeout)
    try:
        ctx.close()
    except Exception:
        pass
    pw.stop()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
