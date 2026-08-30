# -*- coding: utf-8 -*-
"""抖音指数（原热点宝）+ 创作者中心垂类推荐拉取（登录态 DOM 采集）。

B1 源: 抖音指数「实时热点」板（30 条/页 × ≤3 页）
B2 源: 抖音指数「飙升热点」板（30 条）—— 话题上升信号，涨粉/低粉代理的证据
C  源: 创作者中心首页「猜你喜欢·热门话题」个性化垂类 Top5（带热度）

设计决策（2026-08-30 spike 实证）:
- 指数页 XHR 均带 msToken/X-Bogus/_signature 签名 → 只走 Playwright+DOM，不逆 API
- 巨量算数已升级为「抖音指数」并接入创作者中心（trendinsight.oceanengine.com/hotspot/main
  重定向 creator.douyin.com/creator-micro/creator-count/arithmetic-index）
- 登录态双回退: .douyin-topic/profile-douyin/ 持久 profile（与 search_works 共享）
  → scripts/pub/cookies/douyin.json 注入 → 都没有则跳过（notes 记原因，不中断）
- 官方「低粉爆款」独立榜已随升级下线；低粉信号由评分侧用 rising 证据合成代理分
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Optional

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

try:
    from fetch_sources import OUTPUT_ROOT, UA_POOL, cache_get, cache_set
except ImportError:  # 允许作为普通脚本从其他目录调用
    UA_POOL = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    ]
    OUTPUT_ROOT = Path(".douyin-topic")


CHANNEL = "msedge" if sys.platform == "win32" else "chrome"
PROFILE_DIR = OUTPUT_ROOT / "profile-douyin"
INDEX_URL = "https://trendinsight.oceanengine.com/hotspot/main"
CREATOR_HOME_URL = "https://creator.douyin.com/creator-micro/home"


def _resolve_pub_cookies() -> Optional[Path]:
    """发布管线 cookie 路径解析：env > 从 cwd 向上找 > 从脚本位置向上找。

    不能用 project_root()：skill 住在 .skills submodule 里，它找到的根是 submodule
    而非博客仓，douyin.json 在博客仓的 scripts/pub/cookies/ 下。
    """
    env_path = os.environ.get("DOUYIN_COOKIE_FILE")
    if env_path and Path(env_path).exists():
        return Path(env_path)
    rel = Path("scripts") / "pub" / "cookies" / "douyin.json"
    for start in (Path.cwd(), Path(__file__).resolve()):
        for parent in [start, *start.parents]:
            candidate = parent / rel
            if candidate.exists():
                return candidate
    return None

CACHE_KEY = "source_trend"
VALUE_RE = re.compile(r"^[\d.]+[万亿]?$")
RANK_RE = re.compile(r"^\d{1,2}$")
BOARD_SKIP_WORDS = {"排名", "热点名称", "热点指数", "热点指数变化", "热度", "查看全部"}


def _utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass


def parse_cn_number(text: str) -> Optional[float]:
    """「1164.6万」→ 11646000.0；「2.3亿」→ 2.3e8；纯数字直通；解析失败 None。"""
    text = (text or "").strip().replace(",", "")
    if not text:
        return None
    mult = 1.0
    if text.endswith("万"):
        mult, text = 1e4, text[:-1]
    elif text.endswith("亿"):
        mult, text = 1e8, text[:-1]
    try:
        return float(text) * mult
    except ValueError:
        return None


def _random_viewport() -> dict:
    return {"width": random.randint(1410, 1536), "height": random.randint(860, 940)}


def _humanize_scroll(page, rounds: int = 3) -> None:
    """随机滚动 + 抖动（懒加载触发 + 反固定节奏）。"""
    for _ in range(rounds):
        page.mouse.wheel(0, random.randint(300, 800))
        time.sleep(random.uniform(0.8, 2.0))
    if random.random() < 0.3:
        page.mouse.wheel(0, -random.randint(200, 500))
        time.sleep(random.uniform(0.5, 1.2))


def _dismiss_dialog(page) -> None:
    """关掉升级公告等弹窗（有则点，无则过）。"""
    for sel in ("button:has-text('确认')", "[aria-label='close']", ".semi-modal-close"):
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=1200):
                btn.click()
                time.sleep(random.uniform(0.8, 1.5))
                return
        except Exception:
            continue


def _wait_settled(page, tries: int = 6) -> None:
    """等页面稳定（该站会多次重建执行上下文，不能用 networkidle）。"""
    for _ in range(tries):
        time.sleep(random.uniform(2.5, 4.5))
        try:
            page.wait_for_load_state("domcontentloaded", timeout=4000)
        except Exception:
            pass


def _body_text(page) -> str:
    try:
        return page.evaluate("document.body ? document.body.innerText : ''") or ""
    except Exception:
        return ""


def _try_login_profile(timeout_s: int = 150) -> bool:
    """headful 打开抖音首页等扫码（一次性，登录态落 profile-douyin/）。"""
    from playwright.sync_api import sync_playwright

    print("🔑 未登录。打开抖音首页，请在弹出的浏览器窗口扫码（一次性）…")
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE_DIR), channel=CHANNEL, headless=False,
            args=["--disable-blink-features=AutomationControlled", "--lang=zh-CN"],
            viewport=_random_viewport(), user_agent=random.choice(UA_POOL),
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            page.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=40000)
        except Exception:
            pass
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            if _has_session(ctx):
                print("✅ 登录成功，登录态已持久化到 profile-douyin/")
                ctx.close()
                return True
            time.sleep(2)
        ctx.close()
    return False


def _has_session(ctx) -> bool:
    try:
        for cookie in ctx.cookies():
            if cookie.get("name") == "sessionid" and cookie.get("value"):
                return True
    except Exception:
        pass
    return False


def _open_context():
    """登录态双回退打开浏览器上下文。返回 (pw, browser, ctx, note)；失败前者为 None。"""
    from playwright.sync_api import sync_playwright

    pw = sync_playwright().start()
    browser = pw.chromium.launch(
        channel=CHANNEL, headless=True,
        args=["--disable-blink-features=AutomationControlled"],
    )
    # 回退①: skill 自有持久 profile（与 search_works 共享，Chrome profile 目录形态）
    if PROFILE_DIR.exists() and any(PROFILE_DIR.iterdir()):
        ctx = pw.chromium.launch_persistent_context(
            str(PROFILE_DIR), channel=CHANNEL, headless=True,
            args=["--disable-blink-features=AutomationControlled", "--lang=zh-CN"],
            viewport=_random_viewport(), user_agent=random.choice(UA_POOL),
        )
        if _has_session(ctx):
            return pw, browser, ctx, ""
        ctx.close()
    # 回退②: 发布管线的 douyin.json 注入（spike 实证覆盖 creator.douyin.com，
    # 无 sessionid 也有 ttwid 等有效态，直接信任交给页面渲染结果检验）
    pub_cookies = _resolve_pub_cookies()
    if pub_cookies:
        ctx = browser.new_context(
            storage_state=str(pub_cookies), user_agent=random.choice(UA_POOL),
            viewport=_random_viewport(), locale="zh-CN",
        )
        return pw, browser, ctx, ""
    browser.close()
    pw.stop()
    return None, None, None, (
        "B/C 源跳过：无可用登录态（profile-douyin 未登录且 scripts/pub/cookies/douyin.json 缺失）。"
        "补登录态: py -3.11 -m fetch_trend --login 或 make topic-works --login（扫码一次）"
    )


# ---------- 板块解析（innerText 按行容错抽取） ----------

def _parse_pairs(lines: list[str], stop_words: set[str], limit: int) -> list[dict]:
    """从行序列抽 (名称, 数值) 对：值行向前配对最近的非值行。"""
    rows: list[dict] = []
    pending_name: Optional[str] = None
    for line in lines:
        if line in BOARD_SKIP_WORDS or any(stop in line for stop in stop_words):
            if rows or pending_name:
                break
            continue
        if VALUE_RE.match(line):
            if pending_name:
                rows.append({"word": pending_name, "value_display": line})
                pending_name = None
                if len(rows) >= limit:
                    break
            continue
        if RANK_RE.match(line):
            continue  # 排名行（4-10 名），名称单独成行
        pending_name = line
    return rows


def _parse_board(text: str, marker: str, limit: int) -> list[dict]:
    """按板块标记切出片段再抽 (名称, 数值) 对。"""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    try:
        start = lines.index(marker)
    except ValueError:
        return []
    segment = lines[start + 1:]
    for end_marker in ("抖音实时热点", "抖音飙升热点", "猜你喜欢", "通知", "活动中心"):
        if end_marker != marker:
            try:
                segment = segment[:segment.index(end_marker)]
            except ValueError:
                continue
    rows = _parse_pairs(segment, stop_words={"共30条记录"}, limit=limit)
    return rows


def _parse_foryou(text: str, limit: int = 5) -> list[dict]:
    """创作者中心「热门话题」Top N：排名/名称/热度/数值 交替出现。"""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    try:
        start = lines.index("热门话题")
    except ValueError:
        return []
    segment = lines[start + 1:]
    for end_marker in ("查看全部", "热门视频", "热门课程"):
        try:
            segment = segment[:segment.index(end_marker)]
        except ValueError:
            continue
    rows: list[dict] = []
    pending_name: Optional[str] = None
    for line in segment:
        if line in BOARD_SKIP_WORDS or RANK_RE.match(line):
            continue
        if VALUE_RE.match(line):
            if pending_name:
                rows.append({"word": pending_name, "value_display": line})
                pending_name = None
                if len(rows) >= limit:
                    break
            continue
        pending_name = line
    return rows


def _rows_to_items(rows: list[dict], sub_board: str, source: str,
                   personalized: bool = False) -> list[dict]:
    items = []
    for row in rows:
        items.append({
            "word": row["word"],
            "group_id": None,
            "hot_value": parse_cn_number(row.get("value_display", "")),
            "hot_value_display": row.get("value_display"),
            "view_count": None,
            "video_count": None,
            "discuss_video_count": None,
            "sub_board": sub_board,
            "boards": [sub_board],
            "source": source,
            "personalized": personalized,
        })
    return items


def _goto(page, target: str) -> None:
    try:
        page.goto(target, wait_until="commit", timeout=45000)
    except Exception as exc:
        print(f"[goto-warn] {str(exc)[:100]}")
    _wait_settled(page)
    _dismiss_dialog(page)
    _humanize_scroll(page)


def _paginate(page, board_marker: str, pager_index: int, pages: int = 3) -> list[dict]:
    """实时/飙升板翻页采集（byted-pager 组件，10 条/页 × ≤3 页；取不到下一页就只收当页）。"""
    label = "main" if "实时" in board_marker else "rising"
    all_rows = _parse_board(_body_text(page), board_marker, limit=10)
    seen_words = {r["word"] for r in all_rows}
    for page_no in range(2, pages + 1):
        try:
            pager = page.locator("div.byted-pager").nth(pager_index)
            btn = pager.locator("li.byted-pager-item").filter(has_text=str(page_no))
            if btn.count() == 0:
                break
            btn.first.click()
        except Exception:
            break
        time.sleep(random.uniform(3.0, 5.5))
        rows = _parse_board(_body_text(page), board_marker, limit=10)
        fresh = [r for r in rows if r["word"] not in seen_words]
        if not fresh:
            break
        seen_words.update(r["word"] for r in fresh)
        all_rows.extend(fresh)
        print(f"[trend] {label} 板第 {page_no} 页 +{len(fresh)} 条")
    return all_rows


def collect(pw, ctx, notes: list[str]) -> dict:
    """打开指数页 + 创作者中心首页，采 B1/B2/C 三组条目。"""
    result: dict[str, list[dict]] = {"main": [], "rising": [], "foryou": []}
    page = ctx.new_page()
    try:
        _goto(page, INDEX_URL)
        text = _body_text(page)
        main_rows = _paginate(page, "抖音实时热点", pager_index=0)
        rising_rows = _paginate(page, "抖音飙升热点", pager_index=1)
        if not main_rows and not rising_rows:
            # 单次重试（headless 偶发被拦重载）
            time.sleep(random.uniform(4.0, 7.0))
            _goto(page, INDEX_URL)
            main_rows = _paginate(page, "抖音实时热点", pager_index=0)
            rising_rows = _paginate(page, "抖音飙升热点", pager_index=1)
        if not main_rows and not rising_rows:
            notes.append("B 源解析为空：指数页结构变化或登录态失效，本批仅用 A 源")
        result["main"] = _rows_to_items(main_rows, "main", "trend")
        result["rising"] = _rows_to_items(rising_rows, "rising", "trend")
    except Exception as exc:
        notes.append(f"B 源失败: {str(exc)[:160]}")
    try:
        _goto(page, CREATOR_HOME_URL)
        foryou_rows = _parse_foryou(_body_text(page))
        if not foryou_rows:
            notes.append("C 源解析为空：创作者中心首页无「热门话题」板块（可能改版）")
        result["foryou"] = _rows_to_items(foryou_rows, "foryou", "foryou", personalized=True)
    except Exception as exc:
        notes.append(f"C 源失败: {str(exc)[:160]}")
    page.close()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="抖音指数+创作者中心垂类推荐拉取(登录态 DOM)")
    parser.add_argument("--out", default=str(OUTPUT_ROOT / "trend.json"))
    parser.add_argument("--no-cache", action="store_true", help="忽略缓存强制刷新")
    parser.add_argument("--login", action="store_true", help="仅扫码登录（一次性）")
    parser.add_argument("--no-cache-write", action="store_true", help="结果不写缓存")
    args = parser.parse_args()
    _utf8_stdio()

    if args.login:
        ok = _try_login_profile()
        return 0 if ok else 1

    if not args.no_cache:
        cached = cache_get(CACHE_KEY)
        if cached is not None:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(
                json.dumps(cached, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"✅ [cache] trend 数据已写入 {args.out}")
            return 0

    notes: list[str] = []
    pw, browser, ctx, open_note = _open_context()
    if open_note:
        notes.append(open_note)
        result = {"fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                  "main": [], "rising": [], "foryou": [], "notes": notes}
    else:
        collected = collect(pw, ctx, notes)
        try:
            ctx.close()
            browser.close()
            pw.stop()
        except Exception:
            pass
        result = {"fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"), **collected, "notes": notes}

    if not args.no_cache_write and (result["main"] or result["rising"] or result["foryou"]):
        cache_set(CACHE_KEY, result)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ trend 数据已写入 {out_path}"
          f"（main:{len(result['main'])} rising:{len(result['rising'])}"
          f" foryou:{len(result['foryou'])}）")
    for note in notes:
        print(f"⚠️ {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
