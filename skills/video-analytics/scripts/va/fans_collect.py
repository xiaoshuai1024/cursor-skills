# -*- coding: utf-8 -*-
"""账号级粉丝数据采集：日粒度涨粉/掉粉序列（涨粉 = 用户核心目标）。

抖音: 页面上下文裸 fetch `aweme/janus/creator/data/overview/all/`（含 fans/new_fans/cancel_fans 日序列）
B站: 公开 `api.bilibili.com/x/relation/stat?vmid=<mid>`（免登录，日快照差分得净增，掉粉不造数）
快手: 数据中心粉丝页 P2（播放量级低暂缓）

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
        if tot is None:
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


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", default="douyin,bilibili")
    args = ap.parse_args()
    for plat in args.platform.split(","):
        plat = plat.strip()
        try:
            record = asyncio.run(fans_douyin()) if plat == "douyin" else (
                fans_bilibili() if plat == "bilibili" else None)
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
