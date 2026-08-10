# -*- coding: utf-8 -*-
"""掘金登录态获取与复用（B 源用）+ 登录态搜索。

  - msedge 持久化会话（userDataDir=.tech-topic/msedge-profile），首次弹窗登录，之后复用 cookie。
    本机 Chrome 损坏（见 CLAUDE.md），统一用 msedge，与 wechat-publishing 一致。
  - 登录闸: 轮询检测掘金 cookie（不依赖 stdin），未登录时弹窗，用户登录后自动继续。
  - 搜索: in-browser fetch 调 search_api（cookies/Referer 浏览器自动带），比 cookie 提取+requests 稳。

用法:
  py -m browser_login test --keyword "Claude Code"   # 0.7 spike: 登录 + 试搜 + dump 结构
  （login_gate / search_via_page 供 fetch_juejin.py 的 B 源调用）
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# macOS 用系统 Chrome（实测可用；本机未装 Edge）；Windows 用 msedge（本机 Chrome 损坏，见 CLAUDE.md）。与 douyin fetch_video 一致。
CHANNEL = os.environ.get("TECH_TOPIC_BROWSER", "msedge" if sys.platform == "win32" else "chrome")
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
LOGIN_COOKIE_HINTS = {"sessionid", "sessionid_ss", "session_sta", "passport_auth_status", "sid_guard"}


def _utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass


def project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "hugo.toml").exists() or (parent / ".git").exists():
            return parent
    return current.parents[-1]


OUTPUT_ROOT = project_root() / ".tech-topic"
PROFILE_DIR = OUTPUT_ROOT / "msedge-profile"


def _is_logged_in(ctx) -> bool:
    """掘金登录态：命中已知登录 cookie，或首页 DOM 无「立即登录」按钮。"""
    try:
        cookies = ctx.cookies("https://juejin.cn")
        names = {c["name"] for c in cookies}
        if names & LOGIN_COOKIE_HINTS:
            return True
    except Exception:
        pass
    return False


def login_gate(headless: bool = False, timeout: int = 600):
    """启动持久化 msedge，确保登录态。返回 (pw, ctx, page, ok)。调用方负责 pw.stop()/ctx.close()。"""
    from playwright.sync_api import sync_playwright

    pw = sync_playwright().start()
    ctx = pw.chromium.launch_persistent_context(
        str(PROFILE_DIR),
        channel=CHANNEL,
        headless=headless,
        args=["--disable-blink-features=AutomationControlled", "--lang=zh-CN"],
        viewport={"width": 1440, "height": 900},
        user_agent=UA,
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://juejin.cn", wait_until="domcontentloaded", timeout=40000)
    page.wait_for_timeout(2000)

    if _is_logged_in(ctx):
        print("✅ 掘金登录态就绪（复用持久化 profile）")
        return pw, ctx, page, True

    print("⚠️ 未检测到登录态。请在弹出的浏览器窗口登录掘金（扫码/手机号）。")
    print(f"   脚本自动检测，最长等 {timeout}s …")
    try:
        page.goto("https://juejin.cn/login", wait_until="domcontentloaded", timeout=40000)
    except Exception:
        pass
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(3)
        if _is_logged_in(ctx):
            print("✅ 检测到登录，cookie 已持久化")
            return pw, ctx, page, True
    print("❌ 等待登录超时")
    return pw, ctx, page, False


def search_via_page(page, query: str, search_type: int = 0, limit: int = 20) -> dict[str, Any]:
    """登录态下 in-browser GET 调 search_api（cookies 浏览器自动带）。

    真实参数来自抓包（2026-08-08）：GET、query 参数（非 keyword）、aid/uuid/spider/id_type/
    cursor/limit/search_type/sort_type/version。POST+keyword 实测返回空。
    """
    import random
    from urllib.parse import quote
    uuid = str(random.randint(10**18, 10**19 - 1))
    url = (
        "https://api.juejin.cn/search_api/v1/search"
        f"?aid=2608&uuid={uuid}&spider=0&query={quote(query)}"
        f"&id_type=0&cursor=0&limit={limit}&search_type={search_type}&sort_type=0&version=1"
    )
    return page.evaluate("async (u) => (await (await fetch(u)).json())", url)


def _parse_search_hits(data: dict[str, Any]) -> list[dict[str, Any]]:
    """从 search 响应抽文章记录：data[].result_model.article_info（result_type==2 即文章）。"""
    out: list[dict[str, Any]] = []
    for it in data.get("data") or []:
        if it.get("result_type") != 2:  # 2 = 文章
            continue
        ai = (it.get("result_model") or {}).get("article_info") or {}
        aid = ai.get("article_id")
        if not aid:
            continue
        out.append({
            "article_id": str(aid),
            "title": (ai.get("title") or "").strip(),
            "brief": (ai.get("brief_content") or "").strip(),
            "category_id": ai.get("category_id"),
            "digg_count": ai.get("digg_count") or 0,
            "view_count": ai.get("view_count") or 0,
            "collect_count": ai.get("collect_count") or 0,
            "comment_count": ai.get("comment_count") or 0,
            "ctime": ai.get("ctime") or 0,
            "rtime": ai.get("rtime") or 0,
            "is_original": ai.get("is_original") or 0,
            "author": "",
            "url": f"https://juejin.cn/post/{aid}",
            "source": "B",
            "matched_keywords": [],
        })
    return out


def search(keywords: list[str], per_keyword_limit: int = 20, login_timeout: int = 5) -> list[dict[str, Any]]:
    """供 pipeline 调用：headless 复用已登录 profile 搜索；未登录则快速降级返回空。

    login_timeout=5：只检测是否已登录，不阻塞等用户登录（首次登录用 `login` 子命令）。
    """
    if not keywords:
        return []
    pw, ctx, page, ok = login_gate(headless=True, timeout=login_timeout)
    if not ok:
        print("ℹ️ B 源：未登录，降级跳过搜索（先 `make tech-topic-login` 登录）")
        return []
    try:
        seen: dict[str, dict[str, Any]] = {}
        for kw in keywords:
            try:
                hits = _parse_search_hits(search_via_page(page, kw, limit=per_keyword_limit))
                for h in hits:
                    h["matched_keywords"] = [kw]
                    seen.setdefault(h["article_id"], h)
                print(f"  B 源搜索 '{kw}': {len(hits)} 篇")
            except Exception as exc:
                print(f"  ⚠️ B 源搜索 '{kw}' 失败: {exc}")
            time.sleep(1.5)
        return list(seen.values())
    finally:
        try:
            ctx.close()
            pw.stop()
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="掘金登录态搜索（B 源）")
    sub = parser.add_subparsers(dest="cmd", required=True)

    login_p = sub.add_parser("login", help="首次交互登录掘金（cookie 持久化，之后免登录）")
    login_p.add_argument("--headless", action="store_true")
    login_p.add_argument("--timeout", type=int, default=600)

    t = sub.add_parser("test", help="登录 + 试搜（调试用）")
    t.add_argument("--keyword", default="Claude Code")
    t.add_argument("--search-type", type=int, default=0)
    t.add_argument("--headless", action="store_true")
    t.add_argument("--timeout", type=int, default=600)

    args = parser.parse_args()
    _utf8_stdio()

    if args.cmd == "login":
        pw, ctx, page, ok = login_gate(headless=args.headless, timeout=args.timeout)
        try:
            ctx.close()
        except Exception:
            pass
        pw.stop()
        return 0 if ok else 1

    # test
    pw, ctx, page, ok = login_gate(headless=args.headless, timeout=args.timeout)
    try:
        if not ok:
            return 1
        data = search_via_page(page, args.keyword, search_type=args.search_type, limit=10)
        hits = _parse_search_hits(data)
        print(f"err_no={data.get('err_no')} 解析到 {len(hits)} 篇:")
        for h in hits[:5]:
            print(f"  · {h['title'][:40]} | 👍{h['digg_count']} | {h['url']}")
    finally:
        try:
            ctx.close()
        except Exception:
            pass
        pw.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
