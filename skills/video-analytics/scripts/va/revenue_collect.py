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
import re

from . import common
from .common import PUB_COOKIES, SNAP_DIR, now_iso, record_error, setup_utf8, today

# 收益相关的 URL 片段（宽匹配；截获后由关键字深挖判真伪）
REVENUE_TARGETS = {
    "bilibili": {
        "url": "https://member.bilibili.com/platform/home",
        "match_sub": ["income", "bcoin", "revenue", "wallet", "profit", "award"],
        "nav_clicks": ["收益中心", "收益", "创作激励"],
        # 2026-08-30 实采固化：真端点在 api.bilibili.com/x/earnings/up/index/income*（老 member
        # 域 x2/creative/web/income* 已 404）；靠收益主页被动拦截即命中，无需主动 fetch
        "fetch_candidates": [],"depth_note": "income_judge_report.current_month_income/last_month_income",
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


def _bili_storage_state() -> dict:
    """bilibili.json 是 biliup 的 cookie_info 格式，Playwright 不能直接加载（会零 cookie 被
    重定向登录页——2026-08-30 实锤）。转成 storage_state：domain 缺省 .bilibili.com、secure、Lax。"""
    data = json.loads((PUB_COOKIES / "bilibili.json").read_text(encoding="utf-8"))
    raw = data["cookie_info"]["cookies"] if "cookie_info" in data else data.get("cookies") or []
    cookies = []
    for c in raw:
        cookies.append({
            "name": c.get("name"), "value": c.get("value"),
            "domain": c.get("domain") or ".bilibili.com",
            "path": c.get("path") or "/",
            "expires": c.get("expires") if isinstance(c.get("expires"), (int, float)) else -1,
            "httpOnly": bool(c.get("httpOnly", False)),
            "secure": True,
            "sameSite": "Lax",
        })
    return {"cookies": cookies, "origins": []}


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
        if which == "bilibili":
            context = await browser.new_context(storage_state=_bili_storage_state())
        else:
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


async def collect_weixin() -> dict:
    """公众号流量主收益（文章侧）：wechat-profile 持久会话打开流量主页，解析渲染文本。

    收益数字直接渲染在 publisher_index 页面（无 JSON XHR），按文本行解析：
    累计收入 / 创作者分成广告收入 / 昨日增量 / 互选合作 / 带货与内容推广。
    登录态：复用 wechat-profile/（msedge 通道，与 wechat-publishing 同一口径），
    token 从 mp 首页 URL 动态提取；跳登录页即报失效。
    """
    from patchright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            str(common.ROOT / "wechat-profile"), channel="msedge", headless=True,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1440, "height": 900})
        page = browser.pages[0] if browser.pages else await browser.new_page()
        try:
            await page.goto("https://mp.weixin.qq.com/", wait_until="domcontentloaded", timeout=90000)
            await page.wait_for_timeout(6000)
            m = re.search(r"[?&]token=(\d+)", page.url)
            if not m:
                raise RuntimeError("mp 首页无 token（登录态失效，需重新扫码）")
            await page.goto(
                f"https://mp.weixin.qq.com/promotion/publisher/publisher_index?token={m.group(1)}&lang=zh_CN",
                wait_until="domcontentloaded", timeout=90000)
            await page.wait_for_timeout(10000)
            text = await page.evaluate("() => (document.body.innerText || '')")
        finally:
            await browser.close()

    def _after(label: str) -> float | None:
        lines = [x.strip() for x in text.splitlines()]
        for i, ln in enumerate(lines):
            if ln.startswith(label) and i + 1 < len(lines):
                try:
                    return float(lines[i + 1].replace(",", ""))
                except ValueError:
                    return None
        return None

    m = re.search(r"昨日\s*\+?\s*([\d.]+)", text)
    fields = {
        "累计收入": _after("累计收入"),
        "创作者分成广告收入": _after("创作者分成广告收入"),
        "昨日增量": float(m.group(1)) if m else None,
        "互选合作收入": _after("互选合作收入"),
        "带货与内容推广": _after("带货与内容推广"),
    }
    if fields["累计收入"] is None:
        raise RuntimeError(f"流量主页未解析到收入数字（页面头 200 字: {text[:200]}）")
    return {
        "platform": "weixin", "date": today(), "fetched_at": now_iso(),
        "fields": fields, "source_urls": ["publisher_index"], "raw_evidence": "页面文本解析（无 XHR）",
    }


def run(platforms: list[str]) -> int:
    setup_utf8()
    import time
    ok, fail = [], []
    for plat in platforms:
        try:
            if plat == "weixin":
                record = asyncio.run(collect_weixin())
            else:
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
    ap.add_argument("--platform", default="bilibili,shipinhao,douyin,kuaishou,weixin")
    args = ap.parse_args()
    plats = [x.strip() for x in args.platform.split(",") if x.strip()]
    return run(plats)


if __name__ == "__main__":
    raise SystemExit(main())
