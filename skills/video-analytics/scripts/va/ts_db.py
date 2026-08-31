# -*- coding: utf-8 -*-
"""平台数据时间序列库（analytics-timeseries-db）。

SQLite 单文件 data/analytics/timeseries.db；metrics_ts 表以
(slug, platform, collected_date) 为主键，每日每视频每平台 UPSERT 一行。
JSONL 快照（snapshots/*.jsonl，采集器产物）为原始层，本库为派生查询层——
db 可随时删库由 import 重建。

用法（Makefile: make analytics-ts）:
  py -m va.ts import                 # snapshots/*.jsonl 全量按 fetched_at 日期 UPSERT
  py -m va.ts report [--recent 5]    # 最近 N 条发布视频：今日 + 昨日Δ + 累计 → markdown
  py -m va.ts query "SELECT ..."     # 只读 SQL 逃生舱
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

from va.common import ROOT, SNAP_DIR  # noqa: E402  复用 VA_PROJECT_ROOT 解析（junction 安全）
DB_PATH = ROOT / "data" / "analytics" / "timeseries.db"
REPORT_PATH = ROOT / "data" / "analytics" / "timeseries-report.md"

SCHEMA = """
CREATE TABLE IF NOT EXISTS metrics_ts (
  slug TEXT NOT NULL,
  platform TEXT NOT NULL,
  item_id TEXT,
  title TEXT,
  collected_date TEXT NOT NULL,
  fetched_at TEXT,
  play INTEGER, like INTEGER, comment INTEGER, share INTEGER,
  new_fans INTEGER,
  completion_rate REAL, crash_3s_rate REAL, cover_ctr REAL,
  avg_play_time_s REAL, home_visits INTEGER, first_hour_share REAL,
  duration_s REAL,
  PRIMARY KEY (slug, platform, collected_date)
);
"""

METRIC_COLS = ["play", "like", "comment", "share", "new_fans",
               "completion_rate", "crash_3s_rate", "cover_ctr",
               "avg_play_time_s", "home_visits", "first_hour_share"]
REPORT_METRICS = [("play", "播放"), ("like", "点赞"), ("comment", "评论"),
                  ("new_fans", "涨粉"), ("completion_rate", "完播率"),
                  ("crash_3s_rate", "3秒跳出")]


def _num(v):
    try:
        return None if v in (None, "", "-") else int(float(v))
    except (TypeError, ValueError):
        return None


def _fnum(v):
    try:
        return None if v in (None, "", "-") else round(float(v), 4)
    except (TypeError, ValueError):
        return None


def _slug_from_raw(rec: dict, raw: dict) -> str:
    """快照行没有 slug 字段——用标题反查 link-map，退化为 item_id。

    deep/fans 采集行自带 rec.slug（采集时已按 link-map 映射），直接优先采用——
    B站/快手/视频号标题是中文、不含 slug 串，纯标题反查会把整平台 deep 数据
    全部退化成 item-* 被 import 跳过（2026-08-31 openspec
    platform-content-variant-research P0-1 修复）。
    """
    if rec.get("slug"):
        return str(rec["slug"])
    title = rec.get("title") or raw.get("title") or ""
    lm_path = ROOT / "content" / "link-map.json"
    try:
        lm = json.loads(lm_path.read_text(encoding="utf-8"))
        for slug, e in lm.items():
            if not isinstance(e, dict):
                continue
            pv = e.get("pub_video") or {}
            if title and slug in title.replace(" ", "-") or \
               any(rec.get("item_id") is not None and rec.get("item_id") == str(pv.get(f) or "")
                   for f in ("douyin_id", "kuaishou_id", "bilibili_id", "shipinhao_id")):
                return slug
            for md in (e.get("metadata") or {}).get("titles", []) if isinstance(e.get("metadata"), dict) else []:
                pass
    except Exception:
        pass
    # 标题相似度兜底：slug 与标题的弱匹配（去连字符含于标题）
    t_norm = re.sub(r"[\s\-：:，,]", "", title).lower()
    for slug in (lm or {}):
        s_norm = re.sub(r"[\-]", "", slug).lower()
        if len(s_norm) > 8 and (s_norm in t_norm or t_norm in s_norm):
            return slug
    return f"item-{rec.get('item_id') or 'unknown'}"


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(SCHEMA)
    return conn


# 量纲表（2026-08-31 openspec platform-content-variant-research P0-2）：rate 字段的原始
# 量纲随平台/来源不同——抖音 summarize 的 play_finish_ratio/cover_click_ratio、快手作品
# 分析 fpr、视频号列表 fullPlayRate 都是 fraction(0-1)；B站 archive_diagnose 经
# deep_collect::pick()/100 后是 percent(0-100)。原始快照保持平台原样，入库统一成 percent，
# 显式声明各字段的候选键与量纲——禁止再用「值<=1 即 fraction」猜测（percent 值 <=1 的
# 弱视频完播/CTR 会被错乘 100）。改字段先对齐 deep_collect 的 raw 键名注释。
_RATE_FRACTION = {  # fraction(0-1) → 入库 ×100 成 percent
    "completion_rate": ("play_finish_ratio", "completion_rate"),
    "cover_ctr": ("cover_click_ratio",),
}
_RATE_PERCENT = {  # percent(0-100) → 入库原值
    "completion_rate": ("full_play_ratio",),
    "crash_3s_rate": ("crash_rate_3s", "crash_3s_rate"),
    "cover_ctr": ("cover_ctr",),
}


def _rate_field(raw: dict, col: str):
    for k in _RATE_FRACTION.get(col, ()):
        v = raw.get(k)
        if v is not None:
            return round(float(v) * 100, 2)
    for k in _RATE_PERCENT.get(col, ()):
        v = raw.get(k)
        if v is not None:
            return round(float(v), 2)
    return None


def _row_from_snapshot(rec: dict) -> dict | None:
    """快照行（platform/item_id/title/published_at/fetched_at/raw）→ metrics 行。"""
    plat = rec.get("platform")
    if plat not in ("douyin", "kuaishou", "bilibili", "shipinhao"):
        return None
    if not rec.get("item_id"):
        rec["item_id"] = f"deep-{rec.get('slug', '')[:20]}"  # deep/fans 行以 slug 兜底
    raw = rec.get("raw") or {}
    fetched = rec.get("fetched_at") or ""
    try:
        day = fetched[:10]
        dt = datetime.fromisoformat(day)
    except ValueError:
        return None
    slug = _slug_from_raw(rec, raw)
    return {
        "slug": slug, "platform": plat,
        "item_id": str(rec.get("item_id") or raw.get("aweme_id") or ""),
        "title": (rec.get("title") or raw.get("title") or "")[:80],
        "collected_date": dt.strftime("%Y-%m-%d"),
        "fetched_at": fetched,
        "play": _num(raw.get("play_count") or raw.get("play") or raw.get("view")),
        "like": _num(raw.get("digg_count") or raw.get("like_count") or raw.get("like") or raw.get("attitude_count")),
        "comment": _num(raw.get("comment_count") or raw.get("comment")),
        "share": _num(raw.get("share_count") or raw.get("share")),
        "new_fans": _num(raw.get("new_fans_count") or raw.get("new_fans")),
        "completion_rate": _rate_field(raw, "completion_rate"),
        "crash_3s_rate": _rate_field(raw, "crash_3s_rate"),
        "cover_ctr": _rate_field(raw, "cover_ctr"),
        "avg_play_time_s": _fnum(raw.get("play_avg_time") or raw.get("avg_play_time") or raw.get("avg_play_sec")),
        "home_visits": _num(raw.get("home_page_view_count") or raw.get("home_visits")),
        "first_hour_share": _fnum(raw.get("first_hour_share")),
        "duration_s": _fnum(raw.get("duration_second") or raw.get("duration")),
    }


def cmd_import(_args) -> int:
    conn = connect()
    total = inserted = skipped = 0
    jsonls = sorted(SNAP_DIR.glob("*.jsonl")) + sorted((SNAP_DIR / "deep").glob("*.jsonl"))         + sorted((SNAP_DIR / "fans").glob("*.jsonl"))
    for f in jsonls:
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue
            row = _row_from_snapshot(rec)
            if not row or not row["item_id"] or row["slug"].startswith("item-"):
                skipped += 1
                continue
            total += 1
            cols = list(row.keys())
            sql = (f"INSERT INTO metrics_ts ({','.join(cols)}) VALUES ({','.join('?' * len(cols))}) "
                   "ON CONFLICT (slug, platform, collected_date) DO UPDATE SET "
                   + ",".join(f"{c}=excluded.{c}" for c in cols if c not in ("slug", "platform", "collected_date")))
            conn.execute(sql, [row[c] for c in cols])
            inserted += 1
    conn.commit()
    n = conn.execute("SELECT COUNT(*) FROM metrics_ts").fetchone()[0]
    days = conn.execute("SELECT COUNT(DISTINCT collected_date) FROM metrics_ts").fetchone()[0]
    conn.close()
    print(f"✅ import: 处理 {total} 行（跳过 {skipped}），库内 {n} 行 / {days} 个采集日")
    return 0


def _recent_slugs(conn: sqlite3.Connection, recent: int) -> list[dict]:
    """最近发布的 N 个 slug（按首次入库日期倒序，去重）。"""
    rows = conn.execute(
        """SELECT slug, MAX(title) title, MIN(collected_date) first_day, MAX(collected_date) last_day,
                  MAX(published_hint, '') published_hint
           FROM (SELECT slug, title, collected_date,
                        '' AS published_hint FROM metrics_ts)
           GROUP BY slug ORDER BY last_day DESC, slug LIMIT ?""",
        (recent,)).fetchall()
    return [{"slug": r[0], "title": r[1], "first_day": r[2], "last_day": r[3]} for r in rows]


def cmd_report(args) -> int:
    conn = connect()
    recents = _recent_slugs(conn, args.recent)
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    lines = [f"# 时间序列报表（生成 {datetime.now().strftime('%Y-%m-%d %H:%M')}）", "",
             f"范围：最近 {len(recents)} 条视频 ｜ 今日 {today} vs 昨日 {yesterday} ｜ 库 `{DB_PATH.name}`", ""]
    for r in recents:
        slug = r["slug"]
        lines += [f"## {slug}", ""]
        plat_rows = conn.execute(
            "SELECT DISTINCT platform FROM metrics_ts WHERE slug=?", (slug,)).fetchall()
        for (plat,) in plat_rows:
            row_t = conn.execute(
                "SELECT * FROM metrics_ts WHERE slug=? AND platform=? AND collected_date=?",
                (slug, plat, today)).fetchone()
            row_y = conn.execute(
                "SELECT * FROM metrics_ts WHERE slug=? AND platform=? AND collected_date=?",
                (slug, plat, yesterday)).fetchone()
            row_first = conn.execute(
                "SELECT * FROM metrics_ts WHERE slug=? AND platform=? ORDER BY collected_date ASC LIMIT 1",
                (slug, plat,)).fetchone()
            if not (row_t or row_y):
                continue
            cols = [d[0] for d in conn.execute("SELECT * FROM metrics_ts LIMIT 1").description]
            t = dict(zip(cols, row_t)) if row_t else None
            y = dict(zip(cols, row_y)) if row_y else None
            f0 = dict(zip(cols, row_first)) if row_first else None
            lines += [f"### {plat}（{r.get('title','')[:40]}）", "",
                      "| 指标 | 今日 | 昨日 | Δ | 发布以来 |", "|---|---|---|---|---|"]
            for col, label in REPORT_METRICS:
                tv = t.get(col) if t else None
                yv = y.get(col) if y else None
                fv = f0.get(col) if f0 else None
                delta = ""
                if tv is not None and yv is not None:
                    d = tv - yv
                    delta = f"+{d}" if d > 0 else str(d)
                fmt = (lambda v: f"{v}%" if v is not None and col in ("completion_rate", "crash_3s_rate") and v <= 100 else (str(v) if v is not None else "-"))
                lines.append(f"| {label} | {fmt(tv)} | {fmt(yv)} | {delta or '-'} | {fmt(fv)} |")
            lines.append("")
    lines += ["> 每日一行/视频/平台（UPSERT 幂等）；今日无行 = 当天未采集。趋势判断建议累积 ≥7 个采集日后进行。"]
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"✅ 报表 → {REPORT_PATH}")
    conn.close()
    return 0


def cmd_query(args) -> int:
    sql = args.sql.strip().rstrip(";")
    if not re.match(r"^(SELECT|WITH)\b", sql, re.I):
        print("❌ 只读限制：仅允许 SELECT/WITH 语句")
        return 1
    conn = connect()
    cur = conn.execute(sql)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    print(" | ".join(cols))
    print("-" * (len(" | ".join(cols))))
    for r in rows:
        print(" | ".join(str(x) for x in r))
    conn.close()
    return 0


def main() -> int:
    _utf8 = None
    try:
        for s in (sys.stdout, sys.stderr):
            s.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass
    parser = argparse.ArgumentParser(description="平台数据时间序列库")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("import", help="snapshots JSONL → SQLite（幂等）")
    p_rep = sub.add_parser("report", help="最近 N 条视频趋势报表")
    p_rep.add_argument("--recent", type=int, default=5)
    p_q = sub.add_parser("query", help="只读 SQL 逃生舱")
    p_q.add_argument("sql")
    args = parser.parse_args()
    return {"import": cmd_import, "report": cmd_report, "query": cmd_query}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
