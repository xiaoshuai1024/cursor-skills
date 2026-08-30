# -*- coding: utf-8 -*-
"""平台收益只读采集（openspec monetize-tracking）。

收益页接口无官方文档且常改版——策略与 va.collect 同骨架但更保守：
XHR 宽匹配拦截 + 原始 JSON 全量落 revenue_raw/ 留证，提取器按关键字
深搜 best-effort；解析不出时只留证据不写快照（report 显示暂无数据），
下一轮按 raw 迭代提取器。只读自己创作者后台，失败降级不阻塞。

用法:
    python -m va.revenue_collect                      # 全部平台
    python -m va.revenue_collect --platform bilibili  # 单平台
产出:
    data/analytics/snapshots/revenue/<platform>.jsonl   （append，同日去重）
    data/analytics/snapshots/revenue_raw/<platform>-<ts>.json（原始证据）
"""
from __future__ import annotations

import argparse
import asyncio
import json

from . import common
from .common import PUB_COOKIES, SNAP_DIR, now_iso, record_error, setup_utf8, today

# 收益相关的 URL 片段（宽匹配；截获后由关键字深挖判真伪）
REVENUE_TARGETS = {
    "bilibili": {
        "url": "https://member.bilibili.com/platform/home",
        "match_sub": ["income", "bcoin", "revenue", "wallet", "profit", "award"],
        "nav_clicks": ["收益中心", "收益", "创作激励"],
        # 无文档端点主动试拉（404/权限错误静默跳过，靠 nav 后被动拦截兜底）
        "fetch_candidates": [
            "/x2/creative/web/income?pn=1&ps=12",
            "/x2/creative/web/income/summary",
        ],
    },
    "shipinhao": {
        # 2026-08-30 开通创作分成后实测：收益页直连 /platform/income（菜单「收入与服务→收入权益」
        # 子项隐藏态，常规 text 点击超时，SPA 需 JS 强制点击；直接 URL 进页最稳）
        "url": "https://channels.weixin.qq.com/platform/income",
        "match_sub": ["profit", "income", "revenue", "award", "balance", "monetize"],
        "nav_clicks": [],
        "fetch_candidates": [
            "/cgi-bin/mmfinderassistant-bin/profit/overview",
            "/cgi-bin/mmfinderassistant-bin/income/overview",
        ],
    },
    "douyin": {
        "url": "https://creator.douyin.com/creator-micro/home",
        "match_sub": ["income", "revenue", "profit", "earning", "settle", "withdraw"],
        "nav_clicks": ["收益", "钱包"],
    },
    "kuaishou": {
        "url": "https://cp.kuaishou.com/",
        "match_sub": ["income", "revenue", "profit", "reward", "settle", "gain", "bonus"],
        "nav_clicks": ["收益", "创作激励", "创作服务"],
    },
}

# 拦截噪音（与 va.collect SKIP_PAT 同源，另排除纯登录/监控域）
NOISE = ["sts2", "monitor", "passport", "logan", "beacon", "jwt", "ttwid",
         "msg/", "user_message", "im/token", "prefetch", "gifshow", "kconf"]

# 字段关键字（小写子串）：深挖命中即视为收益数据
KEYWORDS = ["income", "bcoin", "revenue", "profit", "award", "balance",
            "earning", "settle", "commission"]

MAX_FINDINGS = 120


def _deep_find(obj, keywords=KEYWORDS, path: str = "", depth: int = 0) -> list[tuple[str, object]]:
    """递归收集 key 命中 keywords 的标量 (path, value)。dict/list 键继续下钻。"""
    if depth > 14:
        return []
    out: list[tuple[str, object]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}" if path else str(k)
            if any(w in str(k).lower() for w in keywords) and isinstance(v, (int, float, str)):
                out.append((p, v))
            out += _deep_find(v, keywords, p, depth + 1)
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:30]):
            out += _deep_find(v, keywords, f"{path}[{i}]", depth + 1)
    return out[:MAX_FINDINGS]


def revenue_snap_path(platform: str):
    d = SNAP_DIR / "revenue"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{platform}.jsonl"


def append_revenue(platform: str, record: dict) -> bool:
    """append；同平台同日已存在则跳过。返回是否新写。"""
    p = revenue_snap_path(platform)
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                if (json.loads(line).get("date")) == record.get("date"):
                    return False
            except json.JSONDecodeError:
                continue
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return True


def _unwrap(bodies: list) -> list:
    """解包 respJson 转义 JSON（视频号部分接口把 payload 藏在字符串里）。"""
    out = list(bodies)

    def walk(o):
        if isinstance(o, dict):
            for v in o.values():
                if isinstance(v, str) and v.lstrip().startswith("{"):
                    try:
                        out.append(json.loads(v))
                    except Exception:
                        pass
                else:
                    walk(v)
        elif isinstance(o, list):
            for v in o[:20]:
                walk(v)

    for b in bodies:
        walk(b)
    return out


async def collect_browser(which: str) -> dict:
    import sys
    sys.path.insert(0, str(common.ROOT / "scripts" / "pub" / "vendor"))
    from patchright.async_api import async_playwright

    conf = REVENUE_TARGETS[which]
    cookie_file = PUB_COOKIES / f"{which}.json"
    if not cookie_file.exists():
        raise RuntimeError(f"cookie 不存在: {cookie_file.name}（先 make pub-login platform={which}）")

    captured: list[dict] = []
    urls: list[str] = []

    async def on_response(resp):
        try:
            u = resp.url
            if not any(m in u for m in conf["match_sub"]):
                return
            if any(s in u for s in NOISE):
                return
            body = await resp.json()
            captured.append(body)
            urls.append(u)
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
        for nav in conf.get("nav_clicks", []):
            try:
                await page.click(f"text={nav}", timeout=6000)
                await page.wait_for_timeout(6000)
                break  # 点进第一个命中的菜单即可
            except Exception:
                continue
        for ep in conf.get("fetch_candidates", []):
            try:
                body = await page.evaluate(
                    """async (u) => {
                        const r = await fetch(u, {credentials: 'include'});
                        return await r.json();
                    }""", ep)
                captured.append(body)
                urls.append(ep)
            except Exception:
                continue
        await browser.close()

    # 原始证据全量落盘（无论解析成败）
    raw_dir = SNAP_DIR / "revenue_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"{which}-{today()}-{now_iso().replace(':', '').replace('-', '')[-10:]}.json"
    raw_path.write_text(json.dumps(
        {"urls": urls, "bodies": captured}, ensure_ascii=False), encoding="utf-8")

    fields: dict[str, object] = {}
    for body in _unwrap(captured):
        for p, v in _deep_find(body):
            fields[p] = v
    if not fields:
        raise RuntimeError(
            f"未从拦截响应中挖到收益字段（原始证据已留 {raw_path.name}，按其迭代 KEYWORDS）")
    return {
        "platform": which, "date": today(), "fetched_at": now_iso(),
        "fields": fields, "source_urls": urls[:8], "raw_evidence": raw_path.name,
    }


def run(platforms: list[str]) -> int:
    setup_utf8()
    import time
    ok, fail = [], []
    for plat in platforms:
        try:
            record = asyncio.run(collect_browser(plat))
            added = append_revenue(plat, record)
            n = len(record["fields"])
            print(f"[{plat}] 收益字段 {n} 个" + ("（同日已采，跳过）" if not added else "，快照已写"))
            show = list(record["fields"].items())[:6]
            for k, v in show:
                print(f"    {k} = {v}")
            ok.append(plat)
        except Exception as e:
            record_error(f"revenue-{plat}", f"{type(e).__name__}: {e}")
            print(f"[{plat}] ❌ 采集失败（已降级跳过）: {str(e)[:160]}")
            fail.append(plat)
        time.sleep(3)
    print(f"完成: ok={ok} fail={fail}")
    return 0 if ok or not platforms else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", default="bilibili,shipinhao,douyin,kuaishou")
    args = ap.parse_args()
    plats = [x.strip() for x in args.platform.split(",") if x.strip()]
    return run(plats)


if __name__ == "__main__":
    raise SystemExit(main())
