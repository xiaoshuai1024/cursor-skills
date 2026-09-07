# -*- coding: utf-8 -*-
"""变现门槛进度表 + 收益摘要（openspec monetize-tracking）。

输入: data/analytics/monetize-thresholds.json（门槛配置，进 git）
      data/analytics/snapshots/fans/*.jsonl（va.fans_collect 产物）
      data/analytics/snapshots/revenue/*.jsonl（va.revenue_collect 产物）
输出: data/analytics/monetize-report.md（进 git，同 timeseries-report.md 地位）

用法: python -m va.monetize
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timedelta

from .common import DATA_DIR, setup_utf8

THRESHOLD_PATH = DATA_DIR / "monetize-thresholds.json"
REPORT_PATH = DATA_DIR / "monetize-report.md"
FANS_DIR = DATA_DIR / "snapshots" / "fans"
REVENUE_DIR = DATA_DIR / "snapshots" / "revenue"
WECHAT_ACCOUNT_SNAP = DATA_DIR.parent / "wechat-analytics" / "snapshots" / "account.jsonl"

PLATFORM_NAME = {"douyin": "抖音", "kuaishou": "快手", "bilibili": "B站",
                 "shipinhao": "视频号", "weixin": "公众号"}


def _jsonl(path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _fans_records(platform: str) -> list[dict]:
    if platform == "weixin":
        # wechat-analytics 用户增长序列（openspec wechat-fans-growth-channel）：日粒度 cumulate_user
        dedup: dict[str, dict] = {}
        for r in _jsonl(WECHAT_ACCOUNT_SNAP):
            if r.get("kind") != "user_growth":
                continue
            for row in r.get("list") or []:
                if row.get("date"):
                    dedup[row["date"]] = {
                        "date": row["date"],
                        "follower_total": row.get("cumulate_user"),
                        "net": row.get("netgain_user"),
                    }
        return sorted(dedup.values(), key=lambda r: r.get("date") or "")
    return sorted(_jsonl(FANS_DIR / f"{platform}.jsonl"), key=lambda r: r.get("date") or "")


def _fans_current(platform: str) -> tuple[int | None, str]:
    """返回 (当前粉丝数, 数据日期说明)。公众号现有采集无粉丝累计通道，如实报缺。"""
    if platform == "weixin" and not _fans_records("weixin"):
        return None, "未采集，跑 make wechat-analytics"
    recs = _fans_records(platform)
    if not recs:
        return None, "未采集，跑 make analytics"
    last = recs[-1]
    cur = last.get("follower_total")
    return (int(cur) if cur is not None else None), f"截至 {last.get('date')}"


def _fans_speed7(platform: str, records: list[dict]) -> int | None:
    """近 7 日净增：douyin 用序列差分；其余用快照区间差分。无数据返回 None。"""
    if not records:
        return None
    last = records[-1]
    if platform == "douyin" and last.get("daily"):
        daily = [d for d in last["daily"] if d.get("net") is not None][-7:]
        return int(sum(d["net"] for d in daily)) if daily else None
    cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    window = [r for r in records if (r.get("date") or "") >= cutoff] or records
    if len(window) < 2:
        return None
    first, lastw = window[0], window[-1]
    if first.get("follower_total") is None or lastw.get("follower_total") is None:
        return None
    return int(lastw["follower_total"]) - int(first["follower_total"])


def _revenue_latest(platform: str) -> dict | None:
    recs = _jsonl(REVENUE_DIR / f"{platform}.jsonl")
    return recs[-1] if recs else None


def build_report() -> str:
    setup_utf8()
    cfg = json.loads(THRESHOLD_PATH.read_text(encoding="utf-8"))
    lines = [f"# 变现门槛进度表（生成 {datetime.now().strftime('%Y-%m-%d %H:%M')}）", "",
             f"> 门槛数值为公开条件快照，以各平台创作者后台当前页面为准（配置：`monetize-thresholds.json`）。", ""]

    rows = []
    for item in cfg["items"]:
        plat = item["platform"]
        cur, cur_note = _fans_current(plat)
        speed = _fans_speed7(plat, _fans_records(plat))
        thr = int(item["threshold"])
        gap = None if cur is None else max(0, thr - cur)
        eta = ""
        if gap == 0:
            eta = "✅ 已达标，去后台开通"
        elif cur is not None and speed is not None and speed > 0:
            daily = speed / 7  # speed 是近7日净增总量，换算日均再外推
            days = math.ceil(gap / daily)
            eta_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
            eta = f"约 {days} 天（{eta_date}，按近7日 +{speed}→日均 +{daily:.1f} 外推）"
        elif cur is not None:
            eta = "净增 ≤0，暂无法外推"
        rows.append({
            "id": item["id"], "name": item["name"], "plat": PLATFORM_NAME.get(plat, plat),
            "requirement": item["requirement"], "thr": thr,
            "cur": cur, "cur_note": cur_note, "speed": speed, "eta": eta,
            "status_note": item.get("status_note") or "",
        })

    lines += ["## 门槛进度", "",
              "| 项目 | 平台 | 门槛 | 现状 | 差距 | 近7日净增 | 预计达标 |",
              "|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda x: (x["cur"] is None, -(x["cur"] or 0) / max(1, x["thr"]))):
        cur = f"{r['cur']}" if r["cur"] is not None else "—"
        speed = f"+{r['speed']}" if (r["speed"] or 0) > 0 else (str(r["speed"]) if r["speed"] is not None else "—")
        gap_v = "—" if r["cur"] is None else max(0, r["thr"] - r["cur"])
        lines.append(f"| {r['name']} | {r['plat']} | {r['thr']} | {cur}（{r['cur_note']}） "
                     f"| {gap_v} | {speed} | {r['eta']} |")
    lines.append("")

    hit = [r for r in rows if r["cur"] is not None and r["cur"] >= r["thr"]]
    if hit:
        lines += ["## 已达标待开通", ""]
        for r in hit:
            note = f"（{r['status_note']}）" if r.get("status_note") else ""
            lines.append(f"- **{r['name']}**（{r['plat']}）：当前 {r['cur']} ≥ 门槛 {r['thr']}——后台开通入口核对后登记收益采集。{note}")
        lines.append("")

    lines += ["## 收益采集状态", "", "| 平台 | 最近采集 | 字段摘要 |", "|---|---|---|"]
    rev_plats = sorted(p.name[:-6] for p in REVENUE_DIR.glob("*.jsonl")) if REVENUE_DIR.exists() else []
    if not rev_plats:
        lines.append("| （暂无） | 跑 `make analytics-revenue` 首采 | 接口不匹配时留 raw 证据迭代 |")
    for p in rev_plats:
        rec = _revenue_latest(p)
        fields = rec.get("fields") or {}
        summary = "；".join(f"{k.split('.')[-1]}={v}" for k, v in list(fields.items())[:5]) or "—"
        lines.append(f"| {PLATFORM_NAME.get(p, p)} | {rec.get('date')} | {summary[:120]} |")
    lines += ["", "> 收益归因不做视频级分摊（平台后台无此粒度）；接口改版看 `snapshots/revenue_raw/` 证据迭代提取器。"]

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return "\n".join(lines)


def main() -> int:
    report = build_report()
    print(report.split("## 收益采集状态")[0][-600:])
    print(f"✅ 报表 → {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
