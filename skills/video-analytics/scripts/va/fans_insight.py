# -*- coding: utf-8 -*-
"""粉丝画像/活跃时段采集 + 发布档校准（openspec fans-insight）。

各平台创作者中心的粉丝画像端点无官方文档——与 revenue_collect 同策略：
XHR 宽匹配拦截 + 原始落盘留证 + 关键字深挖 best-effort；解析不出只留证据。
报告回答一个问题：**粉丝活跃峰值 vs 现行发布档（早8/午12/晚20），晚档该不该挪**。
校准是建议不是自动改档——双窗口定规不动。

用法:
    python -m va.fans_insight                 # 采集 + 报告
    python -m va.fans_insight --report-only   # 只出报告（用既有快照）
产出:
    data/analytics/snapshots/fans_insight/<platform>.jsonl（append，同日去重）
    data/analytics/fans_insight.json（机器可读，含 F1 校准 directive）
    .video-analytics/reports/fans-insight.md（人读）
"""
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime

from . import common
from .common import DATA_DIR, PUB_COOKIES, REPORT_DIR, SNAP_DIR, now_iso, record_error, setup_utf8, today

from .revenue_collect import NOISE, _deep_find

# 现行发布档位（双窗口定规 + DSH 早中晚轮换实验）
CURRENT_SLOTS = [8, 12, 20]
PLATFORM_NAME = {"douyin": "抖音", "kuaishou": "快手", "bilibili": "B站", "shipinhao": "视频号"}

TARGETS = {
    "douyin": {
        # 粉丝数据页直进（2026-08-30 抓包证实 dashboard/fans 端点随页加载）
        "url": "https://creator.douyin.com/creator-micro/data/fans",
        "match_sub": ["fans", "follower", "portrait", "user_state", "dashboard"],
        "nav_clicks": [],
        "fetch_candidates": [
            "/janus/douyin/creator/data/fans/portrait?recent_days=7",
            "/janus/douyin/creator/data/overview/dashboard/fans?recent_days=7",
        ],
    },
    "bilibili": {
        "url": "https://member.bilibili.com/platform/home",
        "match_sub": ["fans", "follower", "portrait", "fan"],
        "nav_clicks": ["粉丝分析", "粉丝数据", "数据中心"],
    },
    "kuaishou": {
        "url": "https://cp.kuaishou.com/",
        "match_sub": ["fans", "follower", "portrait", "fan", "user"],
        "nav_clicks": ["粉丝管理", "数据中心"],
    },
    "shipinhao": {
        "url": "https://channels.weixin.qq.com/platform",
        "match_sub": ["fans", "portrait", "statistic"],
        "nav_clicks": ["数据中心", "粉丝"],
        "fetch_candidates": [
            {"ep": "/cgi-bin/mmfinderassistant-bin/statistic/fans_portrait", "post": True},
        ],
    },
}

# 画像关键字：标量字段 + 序列（活跃时段直方图等）
SCALAR_KW = ("gender", "age", "province", "city", "device", "active", "total_fans", "fan_count")
SERIES_KW = ("hour", "active", "portrait", "age", "gender")


def _snap_path(platform: str):
    d = SNAP_DIR / "fans_insight"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{platform}.jsonl"


def _append(platform: str, record: dict) -> bool:
    p = _snap_path(platform)
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                if json.loads(line).get("date") == record.get("date"):
                    return False
            except json.JSONDecodeError:
                continue
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return True


def _find_series(obj, path: str = "", depth: int = 0) -> dict[str, list]:
    """收集 key 命中 SERIES_KW 的数值 list（活跃时段/年龄/性别分布直方图）。"""
    if depth > 14:
        return {}
    out: dict[str, list] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}" if path else str(k)
            if any(w in str(k).lower() for w in SERIES_KW) and \
               isinstance(v, list) and 0 < len(v) <= 48 and \
               all(isinstance(x, (int, float)) or x is None for x in v):
                out[p] = v
            else:
                out.update(_find_series(v, p, depth + 1))
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:30]):
            out.update(_find_series(v, f"{path}[{i}]", depth + 1))
    return out


def _unwrap_respjson(bodies: list) -> list:
    """解包 respJson 转义 JSON（视频号 portrait 等接口把 payload 藏在字符串里）。"""
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


def _find_named(obj, out: dict, depth: int = 0):
    """提取 {name: ..., value: ...} 结构（视频号 portrait metric_info_list 风格）。

    画像端点把「年龄/性别/地域/活跃时段」放在 name/value 对里——键名本身不含
    关键词，必须按 name 字段识别。value 为 [{dim, value}] 时按 dim 排序展平。
    """
    if depth > 14:
        return
    if isinstance(obj, dict):
        name = obj.get("name")
        if isinstance(name, str) and "value" in obj:
            v = obj["value"]
            if isinstance(v, list) and v and all(isinstance(x, dict) and "value" in x for x in v):
                dims = [str(x.get("dim") or i) for i, x in enumerate(v)]
                out.setdefault(name + "_dims", dims)
                v = [x["value"] for x in v]
            out.setdefault(name, v)
        for v in obj.values():
            _find_named(v, out, depth + 1)
    elif isinstance(obj, list):
        for v in obj[:40]:
            _find_named(v, out, depth + 1)


def _hour_series_from(metrics: dict) -> dict[str, list]:
    """从命名指标里挑活跃时段直方图（name 含 hour/active/time 且 24 点）。"""
    out = {}
    for name, vals in metrics.items():
        n = name.lower()
        if any(w in n for w in ("hour", "active", "time")) and isinstance(vals, list) and len(vals) == 24 \
           and all(isinstance(x, (int, float)) or x is None for x in vals):
            out[name] = vals
    return out


async def collect_platform(which: str) -> dict:
    import sys
    sys.path.insert(0, str(common.ROOT / "scripts" / "pub" / "vendor"))
    from patchright.async_api import async_playwright

    conf = TARGETS[which]
    cookie_file = PUB_COOKIES / f"{which}.json"
    if not cookie_file.exists():
        raise RuntimeError(f"cookie 不存在: {cookie_file.name}")

    captured: list[dict] = []
    urls: list[str] = []

    async def on_response(resp):
        try:
            u = resp.url
            if not any(m in u for m in conf["match_sub"]):
                return
            if any(s in u for s in NOISE):
                return
            captured.append(await resp.json())
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
                break
            except Exception:
                continue
        for cand in conf.get("fetch_candidates", []):
            ep, post = (cand["ep"], cand.get("post", False)) if isinstance(cand, dict) else (cand, False)
            try:
                body = await page.evaluate(
                    """async (args) => {
                        const opt = {credentials: 'include'};
                        if (args.post) {
                            opt.method = 'POST';
                            opt.headers = {'Content-Type': 'application/json'};
                            opt.body = JSON.stringify({timestamp: String(Date.now())});
                        }
                        const r = await fetch(args.ep, opt);
                        return await r.json();
                    }""", {"ep": ep, "post": post})
                captured.append(body)
                urls.append(ep)
            except Exception:
                continue
        await browser.close()

    raw_dir = SNAP_DIR / "fans_insight_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_name = f"{which}-{today()}-{now_iso().replace(':', '').replace('-', '')[-10:]}.json"
    (raw_dir / raw_name).write_text(json.dumps(
        {"urls": urls, "bodies": captured}, ensure_ascii=False), encoding="utf-8")

    fields: dict[str, object] = {}
    named: dict[str, object] = {}
    series: dict[str, list] = {}
    unwrapped = _unwrap_respjson(captured)
    for body in unwrapped:
        for p, v in _deep_find(body, keywords=SCALAR_KW):
            if isinstance(v, bool):
                continue
            fields[p] = v
        for p, v in _find_series(body).items():
            series.setdefault(p, v)
        _find_named(body, named)
    named = {k: v for k, v in list(named.items())[:40]}
    hour_series = _hour_series_from(named) or {p: v for p, v in series.items()
                                               if "hour" in p.lower() and len(v) == 24}
    if not fields and not named and not hour_series:
        raise RuntimeError(f"未挖到画像字段（证据已留 {raw_name}，按其迭代关键字）")
    return {
        "platform": which, "date": today(), "fetched_at": now_iso(),
        "fields": {k: v for k, v in list(fields.items())[:60]},
        "metrics": named,
        "hour_series": hour_series,
        "series_paths": list(series.keys())[:20],
        "raw_evidence": raw_name,
    }


def _peak_hours(hour_series: dict[str, list]) -> list[int] | None:
    """24 点活跃直方图 → top3 峰值小时。多序列取第一条非全零的。"""
    for vals in hour_series.values():
        clean = [x or 0 for x in vals]
        if len(clean) == 24 and sum(clean) > 0:
            ranked = sorted(range(24), key=lambda h: -clean[h])
            return ranked[:3]
    return None


def build_report() -> str:
    setup_utf8()
    snap_dir = SNAP_DIR / "fans_insight"
    platforms = {}
    latest: dict[str, dict] = {}
    if snap_dir.exists():
        for f in sorted(snap_dir.glob("*.jsonl")):
            recs = [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]
            if recs:
                latest[f.stem] = recs[-1]

    directives = []
    lines = [f"# 粉丝画像与发布档校准（生成 {datetime.now().strftime('%Y-%m-%d %H:%M')}）", "",
             f"现行发布档：{' / '.join(f'{h:02d}:00' for h in CURRENT_SLOTS)}（双窗口定规 + 轮换实验）。"
             f"校准只出建议，改档走台账人工确认。", ""]

    for plat, rec in sorted(latest.items()):
        peaks = _peak_hours(rec.get("hour_series") or {})
        lines += [f"## {PLATFORM_NAME.get(plat, plat)}（数据 {rec.get('date')}）", ""]
        metrics = rec.get("metrics") or {}
        for name, vals in metrics.items():
            if isinstance(vals, list) and vals and all(isinstance(x, (int, float)) for x in vals):
                lines.append(f"- {name}: {' / '.join(str(x) for x in vals[:12])}")
        if peaks:
            peak_str = "、".join(f"{h:02d}:00" for h in peaks)
            near = any(abs(peaks[0] - s) <= 1 for s in CURRENT_SLOTS)
            lines.append(f"- 活跃峰值时段：**{peak_str}**（top3）——现行档位{'已覆盖主峰' if near else '未覆盖主峰'}")
            if not near:
                delta = min(peaks, key=lambda h: min(abs(h - s) for s in CURRENT_SLOTS))
                directives.append({
                    "id": "F1", "priority": "P1", "platform": plat,
                    "evidence": f"{PLATFORM_NAME.get(plat, plat)} 粉丝活跃主峰 {peaks[0]:02d}:00（top3: {peak_str}），现行档 8/12/20 未覆盖",
                    "action": f"主档向粉丝峰值挪 30-60 分钟（向 {delta:02d}:00 方向），改档走台账确认 + 连续 3 支对照数据",
                    "target": "发布后 1h 播放斜率提升",
                })
        else:
            lines.append("- 活跃时段直方图未解析出（看 fans_insight_raw 证据迭代提取器）")
        fields = rec.get("fields") or {}
        show = [f"{k.split('.')[-1]}={v}" for k, v in list(fields.items())[:8]]
        if show:
            lines.append(f"- 画像字段：{'；'.join(show)}")
        lines.append("")

    if not latest:
        lines.append("暂无快照——跑 `make fans-insight` 首采（接口不匹配也会留 raw 证据）。")

    out_json = {
        "generated_at": now_iso(),
        "current_slots": CURRENT_SLOTS,
        "platforms": {p: {"date": r.get("date"), "peaks": _peak_hours(r.get("hour_series") or {})}
                      for p, r in latest.items()},
        "directives": directives,
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "fans_insight.json").write_text(
        json.dumps(out_json, ensure_ascii=False, indent=1), encoding="utf-8")

    if directives:
        lines += ["## 校准建议（F1）", ""]
        for d in directives:
            lines.append(f"- **[{d['priority']}] {d['platform']}**：{d['evidence']} → {d['action']}（目标：{d['target']}）")
        lines.append("")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "fans-insight.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return "\n".join(lines)


def run(do_collect: bool) -> int:
    setup_utf8()
    if do_collect:
        import time
        for plat in TARGETS:
            try:
                rec = asyncio.run(collect_platform(plat))
                added = _append(plat, rec)
                print(f"[{plat}] 画像字段 {len(rec.get('fields') or {})} · 时段序列 {len(rec.get('hour_series') or {})}"
                      + ("" if added else "（当日已采，跳过）"))
            except Exception as e:
                record_error(f"fans_insight_{plat}", f"{type(e).__name__}: {e}")
                print(f"[{plat}] ❌ 画像采集失败（已降级）: {str(e)[:150]}")
            time.sleep(3)
    print(build_report())
    print(f"✅ json → {DATA_DIR / 'fans_insight.json'}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report-only", action="store_true", help="只出报告（用既有快照）")
    args = ap.parse_args()
    return run(do_collect=not args.report_only)


if __name__ == "__main__":
    raise SystemExit(main())
