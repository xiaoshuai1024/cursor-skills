# -*- coding: utf-8 -*-
"""账号级粉丝数据采集：日粒度涨粉/掉粉序列（涨粉 = 用户核心目标）。

抖音: 页面上下文裸 fetch `aweme/janus/creator/data/overview/all/`（含 fans/new_fans/cancel_fans 日序列）
B站: 公开 `api.bilibili.com/x/relation/stat?vmid=<mid>`（免登录，日快照差分得净增，掉粉不造数）
视频号: 首页上下文裸 fetch `statistic/fans_trend`（7 日窗口日粒度 + 涨粉来源 tabType 拆解，2026-08-29 接入）
快手: cp.kuaishou.com 页内多候选裸 fetch + fan/follower 关键字深挖（端点无文档，2026-08-30 接入，
      落空时抛错留 raw 线索待迭代；后续按抓包固化端点后可改为直连）

产出: data/analytics/snapshots/fans/{platform}.jsonl（每日一条，append）
用法: python -m va.fans_collect [--platform douyin,bilibili]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import urllib.request
from pathlib import Path

from . import common
from .common import PUB_COOKIES, ROOT, setup_utf8, now_iso, today


def fans_path(platform: str) -> Path:
    d = common.SNAP_DIR / "fans"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{platform}.jsonl"


def append_fans(platform: str, record: dict) -> bool:
    """当日已有快照则跳过（账号级数据天粒度足够）。"""
    p = fans_path(platform)
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    if json.loads(line).get("date") == record.get("date"):
                        return False
                except json.JSONDecodeError:
                    pass
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return True


async def fans_douyin() -> dict:
    sys.path.insert(0, str(ROOT / "scripts" / "pub" / "vendor"))
    from patchright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False, args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(storage_state=str(PUB_COOKIES / "douyin.json"))
        page = await context.new_page()
        await page.goto("https://creator.douyin.com/creator-micro/home",
                        wait_until="domcontentloaded", timeout=90000)
        await page.wait_for_timeout(5000)
        body = await page.evaluate(
            """async () => {
                const r = await fetch('/aweme/janus/creator/data/overview/all/?last_days_type=1', {credentials:'include'});
                const o = await r.json();
                const u = await fetch('/aweme/v1/creator/user/info/', {credentials:'include'});
                const ui = await u.json();
                return {overview: o, user_info: ui};
            }""")
        await browser.close()
    data = body.get("overview", {}).get("data") or {}
    if not data.get("fans"):
        raise RuntimeError(f"overview/all 无 fans 数据: {str(body)[:120]}")

    def series(key):
        return [(x.get("date"), x.get("count")) for x in (data.get(key) or {}).get("option_list") or []]

    # ⚠️ 口径教训（2026-08-24 实测纠偏）：
    # - fans.daily[].count 才是每日粉丝总数（与 user/info.follower_count 吻合）
    # - fans.current_count 是另一个聚合口径（曾误读为总数，3162≠真实 486）
    # - 净增按总数差分计算；new/cancel 序列仅作明细参考（与差分不完全对账）
    total_series = sorted((d, _i(v)) for d, v in series("fans"))
    new_s = dict(series("new_fans"))
    cancel_s = dict(series("cancel_fans"))
    verify = body.get("user_info", {}).get("douyin_user_verify_info") or {}
    follower_now = _i(verify.get("follower_count"))  # 最新总数（权威）
    daily = []
    prev_total = None
    for d, tot in total_series:
        if not tot:
            # 0/None = 当日未结算占位（2026-08-30 实测 08-29 回 0 污染净增 -613），跳过不差分
            continue
        daily.append({"date": d, "total": tot,
                      "new_fans": _i(new_s.get(d)), "cancel_fans": _i(cancel_s.get(d)),
                      "net": (tot - prev_total) if prev_total is not None else None})
        prev_total = tot
    last_total = daily[-1]["total"] if daily else None
    return {
        "platform": "douyin", "date": today(), "fetched_at": now_iso(),
        "follower_total": follower_now if follower_now is not None else last_total,
        "follower_total_eod": last_total,  # 序列末日总数（与 follower_now 差 = 当日未结算增量）
        "series_net": (daily[-1]["total"] - daily[0]["total"]) if len(daily) >= 2 else None,
        "daily": daily,
        "raw_play_daily": series("play"),
    }


def _i(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def fans_bilibili() -> dict:
    data = json.loads((PUB_COOKIES / "bilibili.json").read_text(encoding="utf-8"))
    cookies = {c["name"]: c["value"] for c in data["cookie_info"]["cookies"]}
    mid = cookies.get("DedeUserID")
    if not mid:
        raise RuntimeError("bilibili cookie 缺 DedeUserID")
    req = urllib.request.Request(
        f"https://api.bilibili.com/x/relation/stat?vmid={mid}",
        headers={"User-Agent": "Mozilla/5.0"})
    body = json.loads(urllib.request.urlopen(req, timeout=15).read().decode("utf-8"))
    if body.get("code") != 0:
        raise RuntimeError(f"relation/stat code={body.get('code')}")
    return {
        "platform": "bilibili", "date": today(), "fetched_at": now_iso(),
        "follower_total": (body.get("data") or {}).get("follower"),
        "daily": [],  # 公开接口无日序列，净增靠相邻快照差分
    }


async def fans_shipinhao() -> dict:
    """视频号: 首页上下文裸 fetch statistic/fans_trend（POST startTs/endTs/interval=3 日粒度）。

    响应 add/reduce/netAdd/total 为按日起始的数组（末元素=最近一天）；带 tabType 来源拆解
    （推荐/主页/分享…，涨粉来源归因用）。2026-08-29 随列表接口改版一接入。
    """
    sys.path.insert(0, str(ROOT / "scripts" / "pub" / "vendor"))
    from patchright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(storage_state=str(PUB_COOKIES / "shipinhao.json"))
        page = await context.new_page()
        await page.goto("https://channels.weixin.qq.com/platform",
                        wait_until="domcontentloaded", timeout=90000)
        await page.wait_for_timeout(6000)
        body = await page.evaluate(
            """async () => {
                const end = Math.floor(Date.now() / 1000);
                const start = end - 7 * 86400;
                const r = await fetch(
                    '/cgi-bin/mmfinderassistant-bin/statistic/fans_trend',
                    {method: 'POST', credentials: 'include',
                     headers: {'Content-Type': 'application/json'},
                     body: JSON.stringify({startTs: String(start), endTs: String(end),
                          interval: 3, timestamp: String(Date.now()),
                          _log_finder_uin: '', _log_finder_id: '',
                          rawKeyBuff: '', pluginSessionId: null, scene: 7, reqScene: 7})});
                return await r.json();
            }""")
        await browser.close()
    data = body.get("data") or {}
    total_arr = [_i(x) for x in (data.get("total") or [])]
    if not total_arr or total_arr[-1] is None:
        raise RuntimeError(f"fans_trend 无 total 序列: {str(body)[:120]}")
    add_arr = [_i(x) for x in (data.get("add") or [])]
    reduce_arr = [_i(x) for x in (data.get("reduce") or [])]

    from datetime import datetime, timedelta
    n = len(total_arr)
    base = datetime.now(common.CST)
    dates = [(base - timedelta(days=n - 1 - i)).strftime("%Y-%m-%d") for i in range(n)]
    daily, prev = [], None
    for i, d in enumerate(dates):
        daily.append({"date": d, "total": total_arr[i],
                      "new_fans": add_arr[i] if i < len(add_arr) else None,
                      "cancel_fans": reduce_arr[i] if i < len(reduce_arr) else None,
                      "net": (total_arr[i] - prev) if prev is not None else None})
        prev = total_arr[i]
    # 最近一天涨粉来源拆解（推荐占比是视频号增长的关键归因）
    breakdown = {}
    for t in data.get("fansDataByTabtype") or []:
        nets = [_i(x) for x in (t.get("netAdd") or [])]
        if nets:
            breakdown[t.get("tabTypeName") or str(t.get("tabType"))] = nets[-1]
    return {
        "platform": "shipinhao", "date": today(), "fetched_at": now_iso(),
        "follower_total": total_arr[-1], "follower_total_eod": total_arr[-1],
        "series_net": (total_arr[-1] - total_arr[0]) if n >= 2 else None,
        "daily": daily,
        "fans_source_breakdown": breakdown,
    }


async def fans_kuaishou() -> dict:
    """快手: cp.kuaishou.com 创作者中心，被动 XHR 拦截 + fan/follower 关键字深挖。

    快手创作中心粉丝端点带签名无公开文档——盲拉候选端点实测不命中（2026-08-30），
    改为打开控制台后被动拦截用户/粉丝相关接口，挖到 fan/follower 数值即取用；
    全部落空抛错（errors 留痕，fans_insight_raw 同款抓包证据路径迭代）。
    """
    from .revenue_collect import _deep_find, NOISE

    sys.path.insert(0, str(ROOT / "scripts" / "pub" / "vendor"))
    from patchright.async_api import async_playwright

    MATCH = ["user", "fans", "follower", "profile", "overview", "center"]
    SKIP = NOISE + ["photo/list", "video/list", "work", "upload", "log"]

    captured: list[dict] = []

    async def on_response(resp):
        try:
            u = resp.url
            if not any(m in u for m in MATCH) or any(s in u for s in SKIP):
                return
            captured.append(await resp.json())
        except Exception:
            pass

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(storage_state=str(PUB_COOKIES / "kuaishou.json"))
        page = await context.new_page()
        page.on("response", lambda r: asyncio.ensure_future(on_response(r)))
        await page.goto("https://cp.kuaishou.com/", wait_until="domcontentloaded", timeout=90000)
        await page.wait_for_timeout(6000)
        for nav in ["粉丝管理", "数据中心", "我的主页"]:
            try:
                await page.click(f"text={nav}", timeout=5000)
                await page.wait_for_timeout(5000)
                break
            except Exception:
                continue
        await browser.close()

    hits: dict[str, object] = {}
    for body in captured:
        for p, v in _deep_find(body, keywords=("fan", "follower")):
            hits[p] = v
    total = None
    for p, v in hits.items():
        key = p.split(".")[-1].lower()
        if key in ("fancount", "fanscount", "followercount", "fans_count", "fan_count") and v not in (None, "", 0):
            total = int(v)
            break
    if total is None:
        for p, v in hits.items():
            if isinstance(v, int) and 0 < v < 10_000_000:
                total = v
                break
    if total is None:
        raise RuntimeError(f"未挖到快手粉丝数（拦截 {len(captured)} 响应无 fan 字段），按抓包迭代")
    return {
        "platform": "kuaishou", "date": today(), "fetched_at": now_iso(),
        "follower_total": total, "follower_total_eod": total,
        "daily": [],  # 快照差分得净增
        "raw_fields": {k: v for k, v in list(hits.items())[:20]},
    }


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", default="douyin,bilibili,shipinhao,kuaishou")
    args = ap.parse_args()
    collectors = {
        "douyin": lambda: asyncio.run(fans_douyin()),
        "bilibili": lambda: fans_bilibili(),
        "shipinhao": lambda: asyncio.run(fans_shipinhao()),
        "kuaishou": lambda: asyncio.run(fans_kuaishou()),
    }
    for plat in args.platform.split(","):
        plat = plat.strip()
        try:
            fn = collectors.get(plat)
            record = fn() if fn else None
            if record is None:
                print(f"[{plat}] 未知平台")
                continue
            added = append_fans(plat, record)
            tot = record.get("follower_total")
            net = record.get("series_net")
            print(f"[{plat}] 粉丝总数 {tot} · 序列 {len(record.get('daily') or [])} 天"
                  + (f" · 区间净增 {net:+d}" if net is not None else "")
                  + ("" if added else "（当日已采，跳过）"))
        except Exception as e:
            common.record_error(f"fans_{plat}", f"{type(e).__name__}: {e}")
            print(f"[{plat}] ❌ 粉丝采集失败: {str(e)[:150]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
