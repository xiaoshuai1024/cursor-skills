# -*- coding: utf-8 -*-
"""深度采集：单视频过程指标锚点（完播率/平均播放时长/3s退出/封面点击/涨粉）。

抖音: 页面上下文裸 fetch `web/api/creator/data/item/summarize/`（免签名，实测通过）
      + `janus/.../item_analysis/metrics_trend`（metrics=view_count 逐小时，冷启动分析）
B站: HTTP GET `x/web/data/archive_diagnose/compare?size=N`（stat 下含 full_play_ratio/crash_rate/tm_rate）
快手: 数据中心接口未探测 → P2（当前播放量级低，优先级最低）

产出: data/analytics/snapshots/deep/{platform}.jsonl（append + 同日去重，与列表快照分离）
用法: python -m va.deep_collect [--platform douyin,bilibili] [--limit N]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import urllib.request
from pathlib import Path

from . import common
from .common import PUB_COOKIES, ROOT, setup_utf8, now_iso

DY_COMMON = ("aid=2906&app_name=aweme_creator_platform&device_platform=web&referer="
             "&cookie_enabled=true&screen_width=1280&screen_height=720&browser_language=zh-CN"
             "&browser_platform=Win32&browser_name=Mozilla&browser_version=126.0.0.0"
             "&browser_online=true&timezone_name=Asia%2FShanghai")


def deep_snap_path(platform: str) -> Path:
    d = common.SNAP_DIR / "deep"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{platform}.jsonl"


def append_deep(platform: str, records: list[dict]) -> tuple[int, int]:
    p = deep_snap_path(platform)
    existing = set()
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    r = json.loads(line)
                    existing.add((r.get("item_id"), (r.get("fetched_at") or "")[:10]))
                except json.JSONDecodeError:
                    pass
    added = skipped = 0
    with p.open("a", encoding="utf-8") as f:
        for r in records:
            key = (r.get("item_id"), (r.get("fetched_at") or "")[:10])
            if key in existing:
                skipped += 1
                continue
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            existing.add(key)
            added += 1
    return added, skipped


def mapped_ids(platform: str) -> dict[str, str]:
    """item_id -> slug（link-map 已回填的）。"""
    lm = common.load_link_map()
    field = {"douyin": "douyin_id", "bilibili": "bilibili_id"}[platform]
    out = {}
    for slug, v in lm.items():
        pv = v.get("pub_video") if isinstance(v, dict) else None
        if isinstance(pv, dict) and pv.get(field):
            out[str(pv[field])] = slug
    return out


# ---------------------------------------------------------------- 抖音

async def deep_douyin(limit: int) -> list[dict]:
    sys.path.insert(0, str(ROOT / "scripts" / "pub" / "vendor"))
    from patchright.async_api import async_playwright

    ids = mapped_ids("douyin")
    # 优先采播放量大的（近期已发布作品），定时件（play=0）在列表快照里能识别
    latest = common.latest_by_item("douyin")
    ranked = sorted(ids.items(), key=lambda kv: -((latest.get(kv[0]) or {}).get("raw") or {}).get("play_count") or 0)
    if limit:
        ranked = ranked[:limit]

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False, args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(storage_state=str(PUB_COOKIES / "douyin.json"))
        page = await context.new_page()
        await page.goto("https://creator.douyin.com/creator-micro/content/manage",
                        wait_until="domcontentloaded", timeout=90000)
        await page.wait_for_timeout(5000)

        records = []
        for iid, slug in ranked:
            try:
                body = await page.evaluate(
                    """async (iid) => {
                        const u = `/web/api/creator/data/item/summarize/?%s&item_id=${iid}`;
                        const r = await fetch(u, {credentials: 'include'});
                        return await r.json();
                    }""" % DY_COMMON, iid)
                items = body.get("item_list") or []
                sd = (items[0].get("summarize_data") or {}) if items else {}
                if not sd:
                    raise CollectDataError("summarize 空")
                trend = await page.evaluate(
                    """async (iid) => {
                        const u = `/janus/douyin/creator/data/item_analysis/metrics_trend?%s`
                              + `&item_id=${iid}&trend_type=1&time_unit=2&metrics_group=0,1,2,3&metrics=view_count`;
                        const r = await fetch(u, {credentials: 'include'});
                        return await r.json();
                    }""" % DY_COMMON, iid)
                tm = ((trend.get("trend_map") or {}).get("view_count") or {}).get("0") or []
                hourly = [(x.get("date_time"), float(x.get("value") or 0)) for x in tm]
                records.append({
                    "platform": "douyin", "item_id": iid, "slug": slug, "fetched_at": now_iso(),
                    "raw": {
                        "play_finish_ratio": sd.get("play_finish_ratio"),
                        "play_avg_time": sd.get("play_avg_time"),
                        "cover_click_ratio": sd.get("cover_click_ratio"),
                        "home_page_view_count": sd.get("home_page_view_count"),
                        "new_fans_count": sd.get("new_fans_count"),
                        "play_count": ((items[0].get("statistics") or {}).get("play_count")),
                        "hourly_views": hourly[:48],
                    },
                })
                print(f"  [{slug[:36]}] 完播率={sd.get('play_finish_ratio')} 平均时长={round(sd.get('play_avg_time') or 0, 1)}s 涨粉={sd.get('new_fans_count')}")
            except Exception as e:
                print(f"  [{slug[:36]}] ❌ {type(e).__name__}: {str(e)[:100]}")
            await page.wait_for_timeout(1200)
        await browser.close()
    return records


class CollectDataError(Exception):
    pass


# ---------------------------------------------------------------- B站

def deep_bilibili() -> list[dict]:
    data = json.loads((PUB_COOKIES / "bilibili.json").read_text(encoding="utf-8"))
    cookies = {c["name"]: c["value"] for c in data["cookie_info"]["cookies"]}
    hdr = "; ".join(f"{k}={cookies[k]}" for k in ("SESSDATA", "bili_jct", "DedeUserID") if k in cookies)
    ids = mapped_ids("bilibili")
    req = urllib.request.Request(
        "https://member.bilibili.com/x/web/data/archive_diagnose/compare?size=30",
        headers={"Cookie": hdr, "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                 "Referer": "https://member.bilibili.com/platform/home"})
    body = json.loads(urllib.request.urlopen(req, timeout=20).read().decode("utf-8"))
    if body.get("code") != 0:
        raise CollectDataError(f"archive_diagnose code={body.get('code')}")

    # not_ready_field 里的指标不算数 → 显式 None（不用 0 冒充）
    records = []
    for it in (body.get("data") or {}).get("list") or []:
        bvid = it.get("bvid")
        slug = ids.get(str(bvid))
        if not slug:
            continue
        st = it.get("stat") or {}
        not_ready = set(st.get("not_ready_field") or [])

        def pick(key, scale=100.0):
            if key in not_ready or st.get(key) in (None, 0) and key in not_ready:
                return None
            v = st.get(key)
            return round(v / scale, 4) if isinstance(v, (int, float)) else None

        records.append({
            "platform": "bilibili", "item_id": str(bvid), "slug": slug, "fetched_at": now_iso(),
            "raw": {
                "full_play_ratio": pick("full_play_ratio"),        # 完播比（%）
                "crash_rate_3s": pick("crash_rate"),               # 3秒退出率（%）
                "cover_ctr": pick("tm_rate"),                      # 封标点击率（%）
                "interact_rate": pick("interact_rate"),
                "play_trans_fan_rate": pick("play_trans_fan_rate"),
                "new_fans_count": st.get("total_new_attention_cnt") if "total_new_attention_cnt" not in not_ready else None,
                "avg_play_time": st.get("avg_play_time") if "avg_play_time" not in not_ready else None,
                "play": st.get("play"),
                "duration": it.get("duration"),
            },
        })
        print(f"  [{slug[:36]}] 完播比={records[-1]['raw']['full_play_ratio']} 3s退出={records[-1]['raw']['crash_rate_3s']} CTR={records[-1]['raw']['cover_ctr']}")
    return records


def main() -> int:
    setup_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", default="douyin,bilibili")
    ap.add_argument("--limit", type=int, default=0, help="抖音最多采 N 条（0=全部已映射）")
    args = ap.parse_args()
    ok = []
    for plat in args.platform.split(","):
        plat = plat.strip()
        try:
            records = asyncio.run(deep_douyin(args.limit)) if plat == "douyin" else (
                deep_bilibili() if plat == "bilibili" else None)
            if records is None:
                print(f"[{plat}] 未知平台，跳过")
                continue
            added, skipped = append_deep(plat, records)
            print(f"[{plat}] 深度快照 {len(records)} 条（新增 {added}，当日跳过 {skipped}）")
            ok.append(plat)
        except Exception as e:
            common.record_error(f"deep_{plat}", f"{type(e).__name__}: {e}")
            print(f"[{plat}] ❌ 深度采集失败: {str(e)[:150]}")
    print(f"深度采集完成: {ok}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
