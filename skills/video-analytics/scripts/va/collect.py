# -*- coding: utf-8 -*-
"""采集入口：五平台只读采集 → 增量快照 → 身份映射回填。

B站: member HTTP API（SESSDATA，免浏览器）
抖音/快手/视频号: patchright + 发布登录态，XHR 拦截后台接口原始 JSON

用法:
    python -m va.collect                     # 全平台
    python -m va.collect --platform bilibili # 单平台
    python -m va.collect --no-uid            # 只采集不回填
"""
from __future__ import annotations

import argparse
import asyncio
import json
import urllib.request

from . import common
from .common import PUB_COOKIES, ROOT, append_snapshots, record_error, setup_utf8, now_iso


class CollectError(Exception):
    pass


# ---------------------------------------------------------------- bilibili

BILI_ARCHIVES = "https://member.bilibili.com/x2/creative/web/archives/sp?pn=%d&ps=%d"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def _bili_cookie_header() -> str:
    data = json.loads((PUB_COOKIES / "bilibili.json").read_text(encoding="utf-8"))
    raw = data["cookie_info"]["cookies"] if "cookie_info" in data else data.get("cookies") or []
    cookies = {c["name"]: c["value"] for c in raw}
    need = [k for k in ("SESSDATA", "bili_jct", "DedeUserID") if k in cookies]
    if "SESSDATA" not in cookies:
        raise CollectError("bilibili.json 缺 SESSDATA，登录态失效")
    return "; ".join(f"{k}={cookies[k]}" for k in need)


def collect_bilibili() -> list[dict]:
    hdr = _bili_cookie_header()
    records, pn = [], 1
    while True:
        req = urllib.request.Request(
            BILI_ARCHIVES % (pn, 20),
            headers={"Cookie": hdr, "User-Agent": UA,
                     "Referer": "https://member.bilibili.com/platform/upload-manager/frame"},
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            body = json.loads(r.read().decode("utf-8"))
        if body.get("code") != 0:
            raise CollectError(f"archives/sp code={body.get('code')} {body.get('message')}")
        arcs = (body.get("data") or {}).get("arc_audits") or []
        if not arcs:
            break
        for a in arcs:
            arc, st = a.get("Archive") or {}, a.get("stat") or {}
            bvid = arc.get("bvid")
            if not bvid:
                continue
            pub = arc.get("ptime") or 0
            records.append({
                "platform": "bilibili",
                "item_id": str(bvid),
                "title": arc.get("title") or "",
                "published_at": datetime_from_epoch(pub) if pub else None,
                "fetched_at": now_iso(),
                "raw": {
                    "aid": arc.get("aid"),
                    "duration": arc.get("duration") or None,
                    "view": st.get("view"),
                    "like": st.get("like"),
                    "coin": st.get("coin"),
                    "favorite": st.get("favorite"),
                    "danmaku": st.get("danmaku"),
                    "reply": st.get("reply"),
                    "share": st.get("share"),
                },
            })
        page = (body.get("data") or {}).get("page") or {}
        if pn * 20 >= (page.get("count") or 0):
            break
        pn += 1
    # stat=None 的是定时/未公开稿件，保留但标记
    return records


def datetime_from_epoch(sec) -> str | None:
    if not sec:
        return None
    from datetime import datetime
    return datetime.fromtimestamp(int(sec), common.CST).strftime("%Y-%m-%d %H:%M")


# ---------------------------------------------------------------- browser 平台（XHR 拦截）

BROWSER_TARGETS = {
    "douyin": {
        "url": "https://creator.douyin.com/creator-micro/content/manage",
        "match": ["janus/douyin/creator/pc/work_list"],
        "extract": "douyin",
        "paginate": "douyin",  # 页面内 fetch 直接翻页（GET + max_cursor）
    },
    "kuaishou": {
        "url": "https://cp.kuaishou.com/article/manage/video",
        "match": ["rest/cp/works/v2/video/pc/photo/list"],
        "extract": "kuaishou",
        "paginate": None,  # __NS_sig3 签名，只能滚动加载
    },
    "shipinhao": {
        "url": "https://channels.weixin.qq.com/platform",
        "match": ["mmfinderassistant-bin/post/post_list", "mmfinderassistant-bin/post_list",
                  "mmfinderassistant-bin/finder/list"],
        "extract": "shipinhao",
        # 2026-08-29 接口改版：列表迁到 content 子应用 POST post/post_list（页内 fetch 可翻页，
        # pageSize 20 两页拉全量），旧 mmfinderassistant-bin/post_list 从此 404
        "paginate": "shipinhao",
        "nav_click": "内容管理",  # 列表子应用挂在首页菜单下，需点击进入
    },
}

# 拦截时排除的噪音端点（用户信息/计费/监控等）
SKIP_PAT = ["charge", "sts2", "monitor", "passport", "user/info", "account_base", "relation_account",
            "exclusive_operator", "ai_creation", "fans/index", "msg/", "user_message", "im/token",
            "banner", "jwt", "oversea", "ttwid", "mix/list", "playlet", "anchor", "notice", "vmok",
            "prefetch", "upgrade", "notification", "helper/", "auth/", "beacon", "logan", "emotion",
            "kconf", "school", "satisfy", "comment/report", "upload/tips", "collection/tab",
            "home/info", "home/userInfo", "publish/refresh", "radar", "gifshow"]


async def collect_browser(which: str) -> list[dict]:
    import sys
    sys.path.insert(0, str(ROOT / "scripts" / "pub" / "vendor"))
    from patchright.async_api import async_playwright

    conf = BROWSER_TARGETS[which]
    cookie_file = PUB_COOKIES / f"{which}.json"
    if not cookie_file.exists():
        raise CollectError(f"cookie 不存在: {cookie_file}")

    captured: list[dict] = []

    async def on_response(resp):
        try:
            url = resp.url
            if not any(m in url for m in conf["match"]):
                return
            if any(s in url for s in SKIP_PAT):
                return
            body = await resp.json()
            captured.append(body)
        except Exception:
            pass

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(storage_state=str(cookie_file))
        page = await context.new_page()
        page.on("response", lambda r: asyncio.ensure_future(on_response(r)))
        await page.goto(conf["url"], wait_until="domcontentloaded", timeout=90000)
        await page.wait_for_timeout(6000)
        if conf.get("nav_click"):
            # 子应用入口菜单（失败不致命：已在目标页时靠被动拦截/直接 fetch）
            try:
                await page.click(f"text={conf['nav_click']}", timeout=8000)
                await page.wait_for_timeout(6000)
            except Exception:
                pass
        if conf.get("paginate") == "douyin":
            # work_list 直连翻页：GET + max_cursor，比滚动加载稳（老作品在深页）
            cursor, seen_n = 0, -1
            for _ in range(15):
                body = await page.evaluate(
                    """async (c) => {
                        const u = `/janus/douyin/creator/pc/work_list?status=0&count=20&max_cursor=${c}`
                              + `&scene=star_atlas&device_platform=android&cookie_enabled=true`
                              + `&screen_width=1280&screen_height=720&browser_language=zh-CN`
                              + `&browser_platform=Win32&browser_name=Mozilla&browser_version=126.0.0.0`;
                        const r = await fetch(u, {credentials: 'include'});
                        return await r.json();
                    }""", cursor)
                captured.append(body)
                n = len(body.get("aweme_list") or [])
                if not body.get("has_more") or n == 0 or n == seen_n:
                    break
                seen_n = n
                nxt = body.get("max_cursor")
                if nxt is None or nxt == cursor:
                    break
                cursor = nxt
                await page.wait_for_timeout(1500)
        elif conf.get("paginate") == "shipinhao":
            # post/post_list 页内 fetch 翻页：POST currentPage 递增（列表 UI 是按钮翻页，滚动不加载）
            for pg in range(1, 10):
                body = await page.evaluate(
                    """async (pg) => {
                        const r = await fetch(
                            '/micro/content/cgi-bin/mmfinderassistant-bin/post/post_list',
                            {method: 'POST', credentials: 'include',
                             headers: {'Content-Type': 'application/json'},
                             body: JSON.stringify({pageSize: 20, currentPage: pg, userpageType: 11,
                                  stickyOrder: false, timestamp: String(Date.now()),
                                  _log_finder_uin: '', _log_finder_id: ''})});
                        return await r.json();
                    }""", pg)
                captured.append(body)
                d = body.get("data") or {}
                n = len(d.get("list") or [])
                if n == 0 or not d.get("continueFlag"):
                    break
                await page.wait_for_timeout(1200)
        else:
            for _ in range(12):  # 滚动翻页加载全量列表
                await page.mouse.wheel(0, 4000)
                await page.wait_for_timeout(1800)
        await browser.close()

    if not captured:
        raise CollectError(f"{which}: 未拦截到列表接口（可能登录态失效或 DOM 改版）")
    fn = EXTRACTORS[conf["extract"]]
    records = fn(captured)
    if not records:
        raise CollectError(f"{which}: 接口有响应但解析出 0 条")
    return records


# ---------------------------------------------------------------- 各平台解析

def _norm_text(s) -> str:
    return str(s or "").split("\n")[0].strip()


def extract_douyin(bodies: list[dict]) -> list[dict]:
    items, seen = [], set()
    for body in bodies:
        for it in body.get("aweme_list") or []:
            st = it.get("statistics") or {}
            iid = str(st.get("aweme_id") or it.get("item_id") or "")
            if not iid or iid in seen:
                continue
            seen.add(iid)
            items.append({
                "platform": "douyin",
                "item_id": iid,
                "title": _norm_text(it.get("item_title") or it.get("desc")),
                "published_at": datetime_from_epoch(it.get("create_time")),
                "fetched_at": now_iso(),
                "raw": {
                    "play_count": st.get("play_count"),
                    "digg_count": st.get("digg_count"),
                    "comment_count": st.get("comment_count"),
                    "collect_count": st.get("collect_count"),
                    "forward_count": st.get("forward_count"),
                    "share_count": st.get("share_count"),
                    "duration_ms": it.get("duration"),
                    "timer_status": (it.get("timer") or {}).get("status"),
                    "in_reviewing": (it.get("status") or {}).get("in_reviewing"),
                    "self_see": (it.get("status") or {}).get("self_see"),
                },
            })
    return items


def extract_kuaishou(bodies: list[dict]) -> list[dict]:
    items, seen = [], set()
    for body in bodies:
        data = body.get("data") or {}
        for it in data.get("list") or []:
            iid = str(it.get("workId") or "")
            if not iid or iid in seen:
                continue
            seen.add(iid)
            up = it.get("uploadTime") or 0
            items.append({
                "platform": "kuaishou",
                "item_id": iid,
                "title": _norm_text(it.get("title")),
                "published_at": datetime_from_epoch(int(up) / 1000) if up else None,
                "fetched_at": now_iso(),
                "raw": {
                    "play_count": it.get("playCount"),
                    "like_count": it.get("likeCount"),
                    "comment_count": it.get("commentCount"),
                    "duration_second": it.get("durationSecond"),
                    "publish_status": it.get("publishStatus"),
                },
            })
    return items


def extract_shipinhao(bodies: list[dict]) -> list[dict]:
    items, seen = [], set()
    for body in bodies:
        if isinstance(body, dict) and body.get("errCode") not in (0, None):
            raise CollectError(f"shipinhao 接口 errCode={body.get('errCode')}（登录态失效需重新扫码）")
        data = body.get("data") or {}
        for it in (data.get("list") or data.get("finderList") or data.get("post_list") or []):
            obj = it.get("objectDesc") or it.get("object") or it
            iid = str(obj.get("objectId") or it.get("objectId") or "")
            if not iid or iid in seen:
                continue
            seen.add(iid)
            # 2026-08-29 改版后 desc 是对象（desc.description=文案、desc.media[0]=视频元信息）
            d = it.get("desc") if isinstance(it.get("desc"), dict) else {}
            media_list = d.get("media") if isinstance(d.get("media"), list) else []
            media = (media_list or [{}])[0]
            text = d.get("description") or obj.get("description")
            up = it.get("createTime") or 0
            items.append({
                "platform": "shipinhao",
                "item_id": iid,
                "title": _norm_text(text),
                "published_at": datetime_from_epoch(up) if up else None,
                "fetched_at": now_iso(),
                "raw": {
                    # 改版后列表级自带播放/互动/完播/涨粉（旧接口 play 恒 None 的缺口补齐）
                    "play_count": it.get("readCount"),
                    "like_count": it.get("likeCount"),
                    "comment_count": it.get("commentCount"),
                    "forward_count": it.get("forwardCount"),
                    "fav_count": it.get("favCount"),
                    "follow_count": it.get("followCount"),
                    "completion_rate": it.get("fullPlayRate"),
                    "avg_play_sec": it.get("avgPlayTimeSec"),
                    "yesterday_play": it.get("yesterdayReadCount"),
                    "duration_second": media.get("videoPlayLen"),
                    "publish_status": it.get("status"),
                },
            })
    return items


EXTRACTORS = {
    "douyin": extract_douyin,
    "kuaishou": extract_kuaishou,
    "shipinhao": extract_shipinhao,
}

COLLECTORS = {"bilibili": collect_bilibili}


# ---------------------------------------------------------------- main

def run(platforms: list[str], do_uid: bool = True) -> int:
    setup_utf8()
    import time
    ok, fail = [], []
    for plat in platforms:
        try:
            if plat == "bilibili":
                records = collect_bilibili()
            else:
                records = asyncio.run(collect_browser(plat))
            added, skipped = append_snapshots(plat, records)
            print(f"[{plat}] 采集 {len(records)} 条，新增快照 {added}，当日已采跳过 {skipped}")
            ok.append(plat)
        except Exception as e:  # 单平台失败降级
            record_error(plat, f"{type(e).__name__}: {e}")
            print(f"[{plat}] ❌ 采集失败（已降级跳过）: {str(e)[:160]}")
            fail.append(plat)
        time.sleep(3)
    if do_uid and ok:
        from . import fetch_uid
        fetch_uid.run(platforms=ok)
    print(f"完成: ok={ok} fail={fail}")
    return 0 if ok or not platforms else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", default="all",
                    help="bilibili|douyin|kuaishou|shipinhao|all（逗号分隔）")
    ap.add_argument("--no-uid", action="store_true", help="只采集不做身份映射回填")
    args = ap.parse_args()
    plats = (["bilibili", "douyin", "kuaishou", "shipinhao"]
             if args.platform == "all" else [x.strip() for x in args.platform.split(",")])
    return run(plats, do_uid=not args.no_uid)


if __name__ == "__main__":
    raise SystemExit(main())
