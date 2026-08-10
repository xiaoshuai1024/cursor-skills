# -*- coding: utf-8 -*-
"""抖音按关键词搜索具体作品（douyin-topic skill）。

登录态前提: 抖音网页搜索必须登录。首次运行会打开浏览器等你扫码（一次性，
登录态持久化在 .douyin-topic/profile-douyin/，之后免登录）。

用法:
  py -3.11 -m search_works --login           # 仅扫码登录（一次性）
  py -3.11 -m search_works --keywords "AI编程,Claude Code,大模型" --top 20
  py -3.11 -m search_works                    # 默认方向关键词，取 top 20 作品

输出: .douyin-topic/works.json（title/author/aweme_id/播放量/封面）
作品即具体视频，比话题更精确——本 skill 的 Phase 1 也以作品为决策单位。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Optional

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# 浏览器 channel: Windows 本机 Chrome 损坏用 msedge; macOS/Linux 用系统 Chrome(真实浏览器,避抖音反爬)
CHANNEL = "msedge" if sys.platform == "win32" else "chrome"


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


OUTPUT_ROOT = project_root() / ".douyin-topic"
PROFILE_DIR = OUTPUT_ROOT / "profile-douyin"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

DEFAULT_KEYWORDS = ["AI编程", "Claude Code", "AI Agent", "大模型", "提示词", "Cursor", "程序员"]


def is_logged_in(ctx) -> bool:
    for cookie in ctx.cookies():
        if cookie["name"] == "sessionid" and cookie.get("value"):
            return True
    return False


def login_flow(ctx, page, timeout_s: int = 120) -> bool:
    """打开首页等用户扫码；返回是否登录成功。"""
    if is_logged_in(ctx):
        return True
    print("🔑 未登录。正在打开抖音首页，请在弹出的浏览器窗口扫码/登录（一次性）…")
    page.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=40000)
    page.wait_for_timeout(4000)
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if is_logged_in(ctx):
            print("✅ 登录成功，登录态已持久化")
            return True
        page.wait_for_timeout(2000)
    print("⏰ 等待超时，未登录。重新运行 --login 再试")
    return False


_DURATION_RE = re.compile(r"^\d{1,2}:\d{2}(:\d{2})?$")
_LIKES_RE = re.compile(r"^[\d.]+万?$")
_DATE_RE = re.compile(r"^(\d+[天小时分]前|\d{4}-\d{2}-\d{2})$")
_EXCLUDE_BADGES = {"合集", "广告", "直播", "图文"}


def _parse_likes(text: str) -> tuple[Optional[str], int]:
    """'57.4万' → ('57.4万', 574000)；'320' → ('320', 320)。"""
    m = _LIKES_RE.match(text)
    if not m:
        return None, 0
    num = float(text[:-1]) if text.endswith("万") else float(text)
    value = int(num * 10000) if text.endswith("万") else int(num)
    return text, value


def _classify_leaves(leaves: list[dict]) -> dict:
    """按叶元素文本形态分类: 时长/点赞/标题/作者/时间/角标。"""
    out: dict = {"title": "", "author": "", "likes_raw": "", "likes": 0,
                 "duration": "", "badge": "", "time": ""}
    title_cands: list[str] = []
    for leaf in leaves:
        text = leaf["text"].strip()
        if not text:
            continue
        if text in _EXCLUDE_BADGES and not out["badge"]:
            out["badge"] = text
        elif _DURATION_RE.match(text):
            out["duration"] = text
        elif text.startswith("@"):
            pass  # @ 单独一个叶元素，作者在下一叶
        elif _LIKES_RE.match(text):
            out["likes_raw"], out["likes"] = _parse_likes(text)
        elif _DATE_RE.match(text):
            out["time"] = text
        elif len(text) >= 2:
            title_cands.append(text)
    # 标题: 最长文本（含话题标签）
    if title_cands:
        out["title"] = max(title_cands, key=len)[:120]
    # 作者: '@' 叶元素后那个文本
    for i, leaf in enumerate(leaves):
        if leaf["text"].strip() == "@" and i + 1 < len(leaves):
            out["author"] = leaves[i + 1]["text"].strip()[:40]
            break
    return out


def extract_works(page, keyword: str, limit: int = 30) -> list[dict]:
    """从当前搜索页抽取视频卡片（按卡片叶元素分类，点赞可直接筛）。"""
    data = page.evaluate("""() => {
        const cards = [];
        const anchors = document.querySelectorAll('a[href*="/video/"]');
        for (const a of anchors) {
            const m = a.href.match(/\\/video\\/(\\d+)/);
            if (!m) continue;
            const card = a.closest('.search-result-card') || a.parentElement;
            const leaves = [];
            for (const el of card.querySelectorAll('div, span, p, h1, h2, h3')) {
                const t = (el.innerText || '').trim();
                if (t && t.length <= 120 && !el.querySelector('div, span, p, h1, h2, h3')) {
                    leaves.push({ cls: (el.className||'').toString().slice(0, 60), text: t });
                }
            }
            const img = card.querySelector('img');
            cards.push({ aweme_id: m[1], href: a.href, cover: img ? img.src : '', leaves });
        }
        return cards;
    }""")
    works: list[dict] = []
    seen: set[str] = set()
    for c in data:
        aweme = c["aweme_id"]
        if aweme in seen:
            continue
        seen.add(aweme)
        parsed = _classify_leaves(c["leaves"])
        works.append({
            "keyword": keyword,
            "title": parsed["title"],
            "author": parsed["author"],
            "aweme_id": aweme,
            "likes_raw": parsed["likes_raw"],
            "likes": parsed["likes"],
            "duration": parsed["duration"],
            "badge": parsed["badge"],
            "time": parsed["time"],
            "cover": c["cover"],
            "video_url": f"https://www.douyin.com/video/{aweme}",
        })
        if len(works) >= limit:
            break
    return works


def _captcha_visible(page) -> bool:
    """验证码是否**可见**（排除 DOM 里常驻的隐藏验证码容器）。"""
    for handle in page.query_selector_all('iframe[src*="captcha"]'):
        try:
            if handle.is_visible():
                return True
        except Exception:
            continue
    return False


def _await_captcha(page, wait_s: int = 60) -> bool:
    """检测**可见**滑块验证码 → 提示用户手动通过 → 轮询等待放行。

    抖音搜索结果页 DOM 常驻一个隐藏的验证码 iframe，不能用存在性判断，
    必须检查 is_visible()。验证码需真人拖滑块，过掉后会话被放行。
    返回 True 表示无需人工处理（已通过/本就无可见验证码）。
    """
    if not _captcha_visible(page):
        return True  # 无可见验证码，直接放行
    print("⚠️ 检测到可见验证码。请在弹出的浏览器窗口里手动拖滑块/点选验证（60 秒内）…")
    deadline = time.time() + wait_s
    while time.time() < deadline:
        page.wait_for_timeout(2000)
        if not _captcha_visible(page):
            print("✅ 验证码已通过，继续抓取")
            return True
    print("⏰ 等待验证码超时，本次跳过该关键词")
    return False


def search_all(keywords: list[str], top: int = 20, min_likes: int = 0,
               exclude_badges: Optional[set[str]] = None) -> list[dict]:
    """搜索多关键词 → 过滤(角标/最低点赞) → 按点赞降序取 top。"""
    from playwright.sync_api import sync_playwright

    exclude = exclude_badges if exclude_badges is not None else _EXCLUDE_BADGES
    collected: list[dict] = []
    seen: set[str] = set()
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            channel=CHANNEL,
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--lang=zh-CN"],
            viewport={"width": 1440, "height": 900},
            user_agent=UA,
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        if not login_flow(ctx, page):
            ctx.close()
            sys.exit("❌ 未登录，无法搜索作品")
        # 首页加载后先过一轮验证码（如果被拦）
        try:
            page.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=40000)
            page.wait_for_timeout(3000)
            _await_captcha(page)
        except Exception:
            pass
        for kw in keywords:
            url = f"https://www.douyin.com/search/{kw}?type=video"
            print(f"▶ 搜索「{kw}」…")
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=40000)
            except Exception as e:
                print(f"   ⚠️ {e}")
            page.wait_for_timeout(5000)
            if not _await_captcha(page):
                continue  # 验证码没通过，跳过该关键词
            for _ in range(6):
                page.mouse.wheel(0, 1500)
                page.wait_for_timeout(1000)
            works = extract_works(page, kw)
            fresh = [w for w in works if w["aweme_id"] not in seen]
            for w in fresh:
                seen.add(w["aweme_id"])
                collected.append(w)
            print(f"   → 新增 {len(fresh)}/{len(works)} 条，累计 {len(collected)}")
            if len(collected) >= top * 3:
                break  # 留余量给过滤
        ctx.close()

    # 过滤 + 按点赞降序
    filtered = [
        w for w in collected
        if w["badge"] not in exclude
        and w["likes"] >= min_likes
        and w["title"]
    ]
    filtered.sort(key=lambda x: x["likes"], reverse=True)
    return filtered[:top]


def main() -> int:
    parser = argparse.ArgumentParser(description="抖音按关键词搜具体作品")
    parser.add_argument("--keywords", default=None, help="逗号分隔关键词（默认方向词表）")
    parser.add_argument("--top", type=int, default=20, help="最多取多少条作品")
    parser.add_argument("--min-likes", type=int, default=0, help="过滤：点赞数下限（原始数，如 10000=1万）")
    parser.add_argument("--min-wan", type=float, default=0.0, help="过滤：点赞数下限（万为单位，如 1=1万赞）")
    parser.add_argument("--login", action="store_true", help="仅扫码登录，不搜索")
    parser.add_argument("--out", default=None, help="works.json 输出路径")
    args = parser.parse_args()
    _utf8_stdio()

    if args.login:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                str(PROFILE_DIR), channel=CHANNEL, headless=False,
                args=["--disable-blink-features=AutomationControlled", "--lang=zh-CN"],
                viewport={"width": 1440, "height": 900}, user_agent=UA,
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            ok = login_flow(ctx, page)
            ctx.close()
            return 0 if ok else 1

    min_likes = int(args.min_wan * 10000) if args.min_wan else args.min_likes
    keywords = [k.strip() for k in (args.keywords or "").split(",") if k.strip()] or DEFAULT_KEYWORDS
    works = search_all(keywords, args.top, min_likes=min_likes)
    out = Path(args.out) if args.out else OUTPUT_ROOT / "works.json"
    out.write_text(json.dumps({
        "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(works),
        "keywords": keywords,
        "min_likes": min_likes,
        "works": works,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ 共抓取 {len(works)} 条作品（点赞≥{min_likes}，按点赞降序）→ {out}")
    # 标记已仿写作品（避免重复深挖同一部）
    ledger = Path(__file__).resolve().parent.parent / "imitated_ledger.json"
    imitated_ids: set[str] = set()
    if ledger.exists():
        try:
            imitated_ids = {i["aweme_id"] for i in json.loads(ledger.read_text(encoding="utf-8")).get("imitated", [])}
        except (json.JSONDecodeError, OSError):
            pass
    for i, w in enumerate(works, 1):
        mark = " [✅已仿写]" if w["aweme_id"] in imitated_ids else ""
        print(f"  {i:>2}. [{w.get('likes_raw') or '-'}] {w['title'][:42]} | @{w['author']} | {w['video_url']}{mark}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
