# -*- coding: utf-8 -*-
"""实验台账（openspec ops-hardening）：改进项「假设→落地→验证」闭环。

directives.json 提出假设与目标值，但缺验证归档——三个月后无法回答
「哪条定规真生效」。本模块用 JSONL 台账补上：改动落地登记（applied），
观察期后人工写结论（verified/rejected），验证时自动从 timeseries.db 拉
applied_to slugs 的最新指标辅助判断（结论必须人写，平台无对照流量不硬造 A/B）。

用法:
    python -m va.experiment add --directive H5 --applied-to slugA,slugB \
        --hypothesis "删过渡句后停留句位后移" [--metric avg_play_time_s] [--note "..."]
    python -m va.experiment list
    python -m va.experiment verify exp-20260830-01 --note "中位深度 6%→11%，继续" [--reject]

台账: data/analytics/experiments.jsonl（进 git，时间序列不可再生）
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime

from .common import DATA_DIR, setup_utf8

LEDGER = DATA_DIR / "experiments.jsonl"
DB_PATH = DATA_DIR / "timeseries.db"

METRICS = ("play", "like", "comment", "share", "new_fans",
           "completion_rate", "crash_3s_rate", "cover_ctr", "avg_play_time_s")


def _load() -> list[dict]:
    if not LEDGER.exists():
        return []
    out = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _save(records: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _latest_metric(slug: str, metric: str):
    """timeseries.db 里该 slug（douyin 优先）最新一行 metric 值；无库返回 None。"""
    if not DB_PATH.exists() or metric not in METRICS:
        return None
    try:
        conn = sqlite3.connect(str(DB_PATH))
        row = conn.execute(
            f"SELECT {metric} FROM metrics_ts WHERE slug=? AND {metric} IS NOT NULL "
            "ORDER BY collected_date DESC LIMIT 1", (slug,)).fetchone()
        conn.close()
        return row[0] if row else None
    except sqlite3.Error:
        return None


def _next_id(records: list[dict]) -> str:
    n = sum(1 for r in records if r.get("id", "").startswith("exp-")) + 1
    return f"exp-{datetime.now().strftime('%Y%m%d')}-{n:02d}"


def cmd_add(args) -> int:
    setup_utf8()
    records = _load()
    rec = {
        "id": args.id or _next_id(records),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "directive": args.directive or "",
        "hypothesis": args.hypothesis or "",
        "applied_to": [s.strip() for s in (args.applied_to or "").split(",") if s.strip()],
        "metric": args.metric if args.metric in METRICS else None,
        "status": "applied",
        "note": args.note or "",
        "verified_at": None,
        "result_note": "",
    }
    records.append(rec)
    _save(records)
    print(f"✅ 已登记 {rec['id']}（applied）：{rec['directive']} → {', '.join(rec['applied_to']) or '(无 slug)'}")
    print(f"   观察期后跑: python -m va.experiment verify {rec['id']} --note \"结论\"")
    return 0


def cmd_list(_args) -> int:
    setup_utf8()
    records = _load()
    if not records:
        print("台账为空。第一条: python -m va.experiment add --directive H5 --applied-to slugA,slugB --hypothesis \"...\"")
        return 0
    for r in records:
        mark = {"applied": "🔬 进行中", "verified": "✅ 验证有效", "rejected": "❌ 判定无效"}.get(r["status"], r["status"])
        print(f"{r['id']}  {mark}  [{r['date']}] {r['directive']}")
        print(f"    假设: {r['hypothesis']}")
        print(f"    落地: {', '.join(r['applied_to']) or '—'}")
        if r.get("result_note"):
            print(f"    结论: {r['result_note']}（{r['verified_at']}）")
    return 0


def cmd_verify(args) -> int:
    setup_utf8()
    records = _load()
    rec = next((r for r in records if r["id"] == args.id), None)
    if not rec:
        print(f"❌ 找不到 {args.id}（make experiment ARGS=\"list\" 查看）")
        return 1
    evidence = {}
    metric = rec.get("metric")
    if metric:
        for slug in rec["applied_to"]:
            v = _latest_metric(slug, metric)
            if v is not None:
                evidence[slug] = v
    if evidence:
        print("—— 最新指标（辅助判断，结论你来写）——")
        for slug, v in evidence.items():
            print(f"  {slug}: {metric}={v}")
    rec["status"] = "rejected" if args.reject else "verified"
    rec["result_note"] = args.note or ""
    if evidence:
        rec["latest_metrics"] = evidence
    rec["verified_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    _save(records)
    print(f"✅ {rec['id']} → {rec['status']}")
    return 0


def open_experiments() -> list[dict]:
    """report.py 引用：进行中的实验（供「写下一支脚本前必读」消费）。"""
    return [r for r in _load() if r.get("status") == "applied"]


def verified_recent(n: int = 5) -> list[dict]:
    recs = [r for r in _load() if r.get("status") in ("verified", "rejected")]
    recs.sort(key=lambda r: r.get("verified_at") or "")
    return recs[-n:][::-1]


def main() -> int:
    ap = argparse.ArgumentParser(description="实验台账：改进项假设→落地→验证闭环")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_add = sub.add_parser("add")
    p_add.add_argument("--directive", default="", help="来源 directive id（如 H5/F1）")
    p_add.add_argument("--applied-to", dest="applied_to", default="", help="落地的 slug，逗号分隔")
    p_add.add_argument("--hypothesis", default="", help="假设（期望什么指标怎么变）")
    p_add.add_argument("--metric", default="", help=f"验证指标（{','.join(METRICS)}）")
    p_add.add_argument("--note", default="")
    p_add.add_argument("--id", default="", help="自定义 id（默认自动 exp-日期-序号）")
    sub.add_parser("list")
    p_ver = sub.add_parser("verify")
    p_ver.add_argument("id")
    p_ver.add_argument("--note", default="", help="结论（必须人写）")
    p_ver.add_argument("--reject", action="store_true", help="判定无效")
    args = ap.parse_args()
    return {"add": cmd_add, "list": cmd_list, "verify": cmd_verify}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
