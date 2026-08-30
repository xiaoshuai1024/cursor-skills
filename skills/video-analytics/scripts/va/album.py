# -*- coding: utf-8 -*-
"""合集粒度采集（openspec collection-data-conversion D1/D2）。

抖音: 内容管理 → 作品合集 tab，被动拦截 mix/list（合集清单+浅层 statis）
      与 mix/mget?fields=metrics（14 项合集指标，UI 行只露 8 项）
快手: 合集管理页，被动拦截 collection/list（基础字段 + offlineReason）
B站:  合集权益未解锁（2026-08-30 实查：内容管理无合集入口、候选直达 URL 重定向
      首页、粉丝 19 未达门槛），暂无采集通道，达标后按抖音款式补

落: data/analytics/snapshots/album/{douyin,kuaishou}.jsonl（append-only，同日去重）
口径备注（2026-08-30 抓包实证）:
- 抖音 metrics: view_count / like_count / comment_count / favorite_count / share_count /
  completion_rate / bounce_rate_2s / avg_view_second(秒) / cover_show / cover_click /
  cover_click_rate / subscribe_count(追更) / unsubscribe_count / view_second(总时长)
- mix/list statis 只有 play_vv/collect_vv（UI 行口径）；完整指标必须走 mget
- 快手 collection/tab 是纯 tab 计数（噪音，collect.py SKIP_PAT 保持）；
  collection/list 的 viewCount 等在合集离线（size=0 / 有效剧集数不足）时恒 0

用法:
    python -m va.album                       # 抖音+快手
    python -m va.album --platform douyin     # 单平台
"""
from __future__ import annotations

import argparse
import asyncio
import json

from . import common
from .common import PUB_COOKIES, ROOT, append_snapshots, record_error, setup_utf8, now_iso


class AlbumError(Exception):
    pass


async def _browser_session(cookie_name: str, nav_url: str, match: list[str],
                           tab_text: str | None, wait_ms: int = 5000):
    """导航 + 被动拦截 JSON XHR。tab_text 给了就先点（触发页面自己发签名请求）。"""
    import sys
    sys.path.insert(0, str(ROOT / "scripts" / "pub" / "vendor"))
    from patchright.async_api import async_playwright

    cookie_file = PUB_COOKIES / cookie_name
    if not cookie_file.exists():
        raise AlbumError(f"cookie 不存在: {cookie_file}")

    captured: list[dict] = []

    async def on_response(resp):
        try:
            url = resp.url
            if not any(m in url for m in match):
                return
            if "json" not in (resp.headers or {}).get("content-type", ""):
                return
            captured.append({"url": url, "body": await resp.text()})
        except Exception:
            pass

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(
            storage_state=str(cookie_file), viewport={"width": 1560, "height": 900})
        page = await context.new_page()
        page.on("response", lambda r: asyncio.ensure_future(on_response(r)))
        await page.goto(nav_url, wait_until="domcontentloaded", timeout=90000)
        await page.wait_for_timeout(6000)
        if tab_text:
            tab = page.get_by_text(tab_text, exact=False).first
            if await tab.count():
                await tab.click()
                await page.wait_for_timeout(wait_ms)
            else:
                print(f"[album] 未找到「{tab_text}」入口（DOM 变更？）")
        await browser.close()
    return captured


# ---------------------------------------------------------------- 抖音

def collect_douyin() -> list[dict]:
    bodies = asyncio.run(_browser_session(
        "douyin.json",
        "https://creator.douyin.com/creator-micro/content/manage",
        match=["web/api/mix/list", "mix/mget"],
        tab_text="作品合集"))

    lists: dict[str, dict] = {}
    metrics: dict[str, dict] = {}
    for c in bodies:
        try:
            b = json.loads(c["body"])
        except json.JSONDecodeError:
            continue
        if "mix/list" in c["url"]:
            for m in b.get("mix_list") or []:
                mid = str(m.get("mix_id") or "")
                if mid:
                    st = m.get("statis") or {}
                    lists[mid] = {
                        "title": (m.get("mix_name") or "").strip(),
                        "play_vv": st.get("play_vv"),
                        "collect_vv": st.get("collect_vv"),
                        "updated_to_episode": st.get("updated_to_episode"),
                    }
        elif "mix/mget" in c["url"]:
            for m in b.get("mixs") or []:
                mid = str(m.get("id") or "")
                if mid and m.get("metrics"):
                    metrics[mid] = m["metrics"]

    if not lists:
        raise AlbumError("douyin: 未拦截到 mix/list（登录态失效或 DOM 改版）")
    if not metrics:
        raise AlbumError("douyin: mix/mget 指标未触发（合集 tab 未加载完？重跑一次）")

    records = []
    for mid, info in lists.items():
        records.append({
            "platform": "album/douyin",
            "item_id": mid,
            "title": info["title"],
            "fetched_at": now_iso(),
            "raw": {**info, **(metrics.get(mid) or {})},
        })
    return records


# ---------------------------------------------------------------- 快手

def collect_kuaishou() -> list[dict]:
    bodies = asyncio.run(_browser_session(
        "kuaishou.json",
        "https://cp.kuaishou.com/article/manage/collection",
        match=["collection/list"],  # collection/tab 是 tab 计数，保持当噪音
        tab_text=None))

    records = []
    for c in bodies:
        try:
            b = json.loads(c["body"])
        except json.JSONDecodeError:
            continue
        for it in (b.get("data") or {}).get("list") or []:
            cid = str(it.get("collectionId") or "")
            if not cid:
                continue
            records.append({
                "platform": "album/kuaishou",
                "item_id": cid,
                "title": (it.get("title") or "").strip(),
                "fetched_at": now_iso(),
                "raw": {
                    "view_count": it.get("viewCount"),
                    "like_count": it.get("likeCount"),
                    "comment_count": it.get("commentCount"),
                    "collect_count": it.get("collectCount"),
                    "size": it.get("size"),
                    "show_on_profile": it.get("showOnProfile"),
                    "offline_reason": it.get("offlineReason"),
                    "urge_update_count": it.get("urgeUpdateCount"),
                    "publish_status": it.get("publishStatus"),
                },
            })
    if not records:
        raise AlbumError("kuaishou: 未拦截到 collection/list（登录态失效或 DOM 改版）")
    return records


COLLECTORS = {"douyin": collect_douyin, "kuaishou": collect_kuaishou}


def run(platforms: list[str]) -> int:
    setup_utf8()
    import time
    ok, fail = [], []
    for plat in platforms:
        try:
            records = COLLECTORS[plat]()
            added, skipped = append_snapshots(f"album/{plat}", records)
            print(f"[album/{plat}] 采集 {len(records)} 个合集，新增快照 {added}，当日已采跳过 {skipped}")
            for r in records:
                m = r["raw"]
                print(f"  - {r['title']}: 播放 {m.get('view_count') or m.get('play_vv')}，"
                      f"订阅 {m.get('subscribe_count', '—')}，集数 {m.get('updated_to_episode') or m.get('size')}")
            ok.append(plat)
        except Exception as e:  # 单平台失败降级
            record_error(f"album/{plat}", f"{type(e).__name__}: {e}")
            print(f"[album/{plat}] ❌ 采集失败（已降级跳过）: {str(e)[:160]}")
            fail.append(plat)
        time.sleep(3)
    print(f"完成: ok={ok} fail={fail}")
    return 0 if ok or not platforms else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", default="douyin,kuaishou", help="douyin|kuaishou（逗号分隔）")
    args = ap.parse_args()
    return run([x.strip() for x in args.platform.split(",") if x.strip()])


if __name__ == "__main__":
    raise SystemExit(main())
