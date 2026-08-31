# -*- coding: utf-8 -*-
"""视频生产全生命周期状态台账（video-pipeline-tracker）。

SSOT: data/video-pipeline/state.json —— 每部视频一条记录（stage/平台定时/平台状态/引用/history）。
写入 tmp+os.replace 原子替换；stage 枚举与必备键校验；每次变更自动重生成 dashboard.md。

用法（py -3.11 -m vpt <cmd>，或 Makefile vpt-* 目标）:
  vpt stage <slug> <stage> [--title T] [--note N] [--schedule 平台=时间 ...] [--block 原因] [--unblock]
  vpt queue                                    排队视图（按定时日期排序，同日多条标冲突）
  vpt sync <slug> [--all]                      从 build|archive 目录/link-map/analytics 快照推导并入（只读外部源）
  vpt report                                   重生成 dashboard.md
  vpt show <slug>                              打印单条记录
  vpt migrate                                  存量录入（一次性）

stage 枚举（有序）: backlog → drafting → article_done → article_published → narration
                    → synthesizing → rendered → scheduled → published → archived
任意 stage 可叠加 blocked 标志（blocked_reason 非空），stage 本身不变。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

STAGES = ["backlog", "drafting", "article_done", "article_published",
          "narration", "synthesizing", "rendered", "scheduled", "published", "archived"]
PLATFORMS = ("douyin", "kuaishou", "bilibili", "shipinhao")
DAILY_SLOT = "20:00"  # 每日一篇原则的档位


def _utf8() -> None:
    try:
        for s in (sys.stdout, sys.stderr):
            s.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass


def project_root() -> Path:
    """定位项目根（state.json 单一事实源所在）。

    2026-08-29 修复双重数据源：tracker 经 .agents/skills junction 挂进项目，
    `Path(__file__).resolve()` 会穿透 junction 落到 skills 仓（那里也有 .git），
    导致 state.json 写进 skills 仓、与项目 data/ 漂移成两份。
    现按「env → cwd 向上找 hugo.toml → __file__ 向上找 hugo.toml（跳过纯 .git 仓）」解析：
    cwd 在项目内时必达 blog-src；__file__ 穿透 junction 后向上也只认 hugo.toml（skills 仓无）。
    """
    env = os.environ.get("VIDEO_PROJECT_ROOT")
    if env and Path(env).exists():
        return Path(env)

    def _walk(base: Path):
        for parent in [base, *base.parents]:
            if (parent / "hugo.toml").exists():
                return parent
        return None

    hit = _walk(Path.cwd())
    if hit:
        return hit
    hit = _walk(Path(__file__).resolve())
    if hit:
        return hit
    for parent in Path(__file__).resolve().parents:
        # 双条件：必须同时有 hugo.toml（项目仓）——防穿透 junction 落进 skills 仓
        if (parent / "hugo.toml").exists() and (parent / "data" / "video-pipeline" / "state.json").exists():
            return parent
    home = Path(os.environ.get("USERPROFILE", str(Path.home())))
    fallback = home / "codes" / "blog-src"
    return fallback if fallback.exists() else Path.cwd()


ROOT = project_root()
DATA_DIR = ROOT / "data" / "video-pipeline"
STATE_PATH = DATA_DIR / "state.json"
DASH_PATH = DATA_DIR / "dashboard.md"
LINK_MAP = ROOT / "content" / "link-map.json"
VG_DIR = ROOT / "video-generation"
SNAP_DIR = ROOT / "data" / "analytics" / "snapshots"
JOBS_PATH = DATA_DIR / "publish-jobs.json"    # pub_guard 发布在途登记（blog-src 侧维护，此处只读呈现）
BACKOFF_PATH = DATA_DIR / "risk-backoff.json"  # 平台风控冷却（scripts.pub.backoff 维护，只读呈现）


def guard_summary() -> str:
    """发布在途 + 风控冷却一行摘要（pub_guard/backoff 的落盘数据；缺文件或坏数据静默为空）。"""
    import time as _t
    segs = []
    try:
        jobs = (json.loads(JOBS_PATH.read_text(encoding="utf-8")).get("jobs")) or {}
        live = [j for j in jobs.values() if j.get("status") == "in_flight"
                and float(j.get("expires_at") or 0) > _t.time()]
        stale = [j for j in jobs.values() if j.get("status") == "stale"]
        if live:
            segs.append("在途 " + "、".join(f"{j.get('platform')}:{j.get('slug')}" for j in live))
        if stale:
            segs.append(f"僵死任务 {len(stale)} 个待清理（py -3.11 -m scripts.pub.pub_guard status）")
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass
    try:
        bk = json.loads(BACKOFF_PATH.read_text(encoding="utf-8"))
        cooling = [f"{p} 剩 {int(max(0, int(r.get('until', 0)) - _t.time())) // 60}min"
                   for p, r in bk.items() if int(r.get("until", 0)) - _t.time() > 0]
        if cooling:
            segs.append("风控冷却 " + "、".join(cooling))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass
    return "；".join(segs)


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {"version": 1, "updated_at": now_iso(), "videos": {}}
    d = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    if d.get("version") != 1 or not isinstance(d.get("videos"), dict):
        raise SystemExit("❌ state.json 结构不合法（version/videos），先修复再操作")
    return d


def save_state(state: dict) -> None:
    state["updated_at"] = now_iso()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, STATE_PATH)  # 同盘原子替换
    write_dashboard(state)


def get_video(state: dict, slug: str, title: str = "") -> dict:
    v = state["videos"].get(slug)
    if v is None:
        v = {"title": title or slug, "stage": "backlog", "stage_ts": now_iso(),
             "blocked_reason": "", "schedule": {}, "platforms": {},
             "refs": {}, "history": [{"ts": now_iso(), "stage": "backlog", "note": "created"}]}
        state["videos"][slug] = v
    if title and v.get("title") in (slug, ""):
        v["title"] = title
    return v


def parse_schedule_items(items: list[str]) -> dict[str, str]:
    out = {}
    for it in items:
        if "=" not in it:
            raise SystemExit(f"❌ --schedule 格式应为 平台=时间（如 douyin=2026-08-29 20:00），收到: {it}")
        k, v = it.split("=", 1)
        if k not in PLATFORMS:
            raise SystemExit(f"❌ 未知平台 {k}（可选: {'/'.join(PLATFORMS)}）")
        out[k] = v
    return out


# ---------- stage ----------

def cmd_stage(args) -> int:
    if args.stage not in STAGES:
        raise SystemExit(f"❌ 非法 stage「{args.stage}」，可选: {' → '.join(STAGES)}")
    state = load_state()
    v = get_video(state, args.slug, args.title or "")
    v["stage"] = args.stage
    v["stage_ts"] = now_iso()
    if args.title:
        v["title"] = args.title
    if args.schedule:
        v.setdefault("schedule", {}).update(parse_schedule_items(args.schedule))
    if args.block:
        v["blocked_reason"] = args.block
    if args.unblock:
        v["blocked_reason"] = ""
    note = args.note or ""
    if args.block:
        note = (note + " | " if note else "") + f"blocked: {args.block}"
    v.setdefault("history", []).append({"ts": now_iso(), "stage": args.stage, "note": note})
    save_state(state)
    print(f"✅ {args.slug} → {args.stage}" + (f"（blocked: {args.block}）" if args.block else ""))
    return 0


# ---------- queue ----------

def _queue_rows(state: dict) -> list[dict]:
    rows = []
    for slug, v in state["videos"].items():
        dates = {p: d for p, d in (v.get("schedule") or {}).items() if d}
        if not dates:
            continue
        earliest = min(dates.values())
        rows.append({"slug": slug, "title": v.get("title", slug), "stage": v.get("stage", ""),
                     "earliest": earliest, "dates": dates,
                     "blocked": bool(v.get("blocked_reason"))})
    rows.sort(key=lambda r: r["earliest"])
    return rows


def cmd_queue(args) -> int:
    state = load_state()
    g = guard_summary()
    if g:
        print(f"🛡️ 发布登记: {g}")
    rows = _queue_rows(state)
    if not rows:
        print("（队列空：没有任何带 schedule 的视频）")
        return 0
    print(f"{'定时':<22} {'slug':<30} {'stage':<14} 平台")
    by_day: dict[str, int] = {}
    for r in rows:
        day = r["earliest"][:10]
        by_day[day] = by_day.get(day, 0) + 1
    for r in rows:
        day = r["earliest"][:10]
        conflict = " ⚠️CONFLICT" if by_day.get(day, 0) > 1 else ""
        blocked = " 🚫" if r["blocked"] else ""
        plats = ",".join(r["dates"].keys())
        print(f"{r['earliest']:<22} {r['slug']:<30} {r['stage']:<14} {plats}{conflict}{blocked}")
    conflict_days = [d for d, n in by_day.items() if n > 1]
    if conflict_days:
        print(f"⚠️ 每日一篇冲突: {', '.join(conflict_days)}")
    return 0


# ---------- sync ----------

def cmd_sync(args) -> int:
    state = load_state()
    slugs = sorted(state["videos"]) if args.all else [args.slug]
    if not args.all and args.slug not in state["videos"]:
        raise SystemExit(f"❌ state 里没有 {args.slug}（先 stage 创建，或用 --all）")
    changed = 0
    promotions: list[str] = []
    for slug in slugs:
        before_stage = (state["videos"].get(slug) or {}).get("stage", "")
        if sync_one(state, slug):
            changed += 1
            after_stage = (state["videos"].get(slug) or {}).get("stage", "")
            if after_stage != before_stage:
                promotions.append(f"  {slug}: {before_stage} → {after_stage}")
    save_state(state)
    print(f"✅ sync 完成，{changed}/{len(slugs)} 条有更新")
    if promotions:
        print(f"stage 晋升 {len(promotions)} 条:")
        for line in promotions:
            print(line)
    return 0


def sync_one(state: dict, slug: str) -> bool:
    v = get_video(state, slug)
    before = json.dumps(v, ensure_ascii=False, sort_keys=True)
    order = {s: i for i, s in enumerate(STAGES)}
    now = datetime.now()

    def _dt(s: str):
        try:
            return datetime.fromisoformat(s) if s else None
        except ValueError:
            return None

    # 0) blocked 记录：人工状态优先，只并入 link-map 平台证据，不动 stage
    sched = v.get("schedule") or {}

    # 1) 平台状态判定：link-map ok 实据优先（已发布平台不可能还有未来定时——有则是残留卡），
    #    其次 schedule 按时间（未来=scheduled/过去=published）
    lm = {}
    if LINK_MAP.exists():
        try:
            lm = json.loads(LINK_MAP.read_text(encoding="utf-8"))
        except Exception:
            lm = {}
    results = ((lm.get(slug) or {}).get("pub_video") or {}).get("results") or {}
    plats = set(sched.keys()) | {k for k in results if k in PLATFORMS}
    for plat in plats:
        t = _dt(sched.get(plat, ""))
        if plat in results and results[plat].get("ok"):
            status = "published"
        elif t and t > now:
            status = "scheduled"
        elif t:
            status = "published"
        else:
            status = v.get("platforms", {}).get(plat, {}).get("status", "unknown")
        prev = v.setdefault("platforms", {}).setdefault(plat, {})
        if prev.get("status") != status:
            prev["status"] = status
            prev["verified_at"] = now_iso()

    # 2) stage 推导（只升不降；blocked 跳过）
    #    发布实据 = link-map results 任一平台 ok（published_at 单独不算——失败的单平台尝试也会盖章）。
    #    published 晋升（pipeline-reconcile）：此前缺这一档，发布后未归档的视频永远停在 scheduled。
    #    晋升时清掉已 ok 平台的 schedule 残留（已发布 ⇒ 定时已消费），防队列幽灵卡。
    if not v.get("blocked_reason"):
        fut_sched = any(t and t > now for t in map(_dt, sched.values()))
        has_past_pub = any(results.get(pl, {}).get("ok") for pl in plats)
        if (VG_DIR / "archive" / slug).is_dir() and has_past_pub:
            if order[v["stage"]] < order["archived"]:
                v["stage"] = "archived"
                v["stage_ts"] = now_iso()
                v.setdefault("refs", {})["archive_dir"] = f"video-generation/archive/{slug}"
        elif has_past_pub:
            if order[v["stage"]] < order["published"]:
                v["stage"] = "published"
                v["stage_ts"] = now_iso()
                v.setdefault("refs", {})["link_map"] = "content/link-map.json"
                for pl in list(sched):
                    if results.get(pl, {}).get("ok"):
                        sched.pop(pl, None)
        elif fut_sched:
            if order[v["stage"]] < order["scheduled"]:
                v["stage"] = "scheduled"
                v["stage_ts"] = now_iso()
        if (VG_DIR / "build" / slug).is_dir() and order[v["stage"]] < order["rendered"]:
            v["stage"] = "rendered"
            v["stage_ts"] = now_iso()

    # 3) analytics 快照最新行 → 数据摘要（douyin 侧）
    snap = SNAP_DIR / "douyin.jsonl"
    if snap.exists():
        last = None
        for line in snap.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("item_id") and slug in json.dumps(rec, ensure_ascii=False):
                last = rec
        if last:
            v.setdefault("analytics", {})["last"] = {
                "ts": last.get("snapshot_at") or last.get("ts") or "",
                "plays": last.get("play_count") or last.get("plays"),
            }

    return json.dumps(v, ensure_ascii=False, sort_keys=True) != before


# ---------- report（dashboard） ----------

def _analytics_plays(slug: str, state: dict) -> str:
    a = ((state["videos"].get(slug) or {}).get("analytics") or {}).get("last") or {}
    plays = a.get("plays")
    return str(plays) if plays not in (None, "") else "-"


def write_dashboard(state: dict) -> None:
    videos = state["videos"]
    now = now_iso()
    lines = [f"# 视频生产看板（自动生成 {now}）", ""]

    # ① 进行中（非 archived）
    lines += ["## 进行中", ""]
    active = [(s, v) for s, v in videos.items() if v.get("stage") != "archived"]
    if not active:
        lines += ["（空）", ""]
    order = {s: i for i, s in enumerate(STAGES)}
    lines += ["| slug | stage | 阻塞 | 定时 | 平台覆盖 |", "|---|---|---|---|---|"]
    for s, v in sorted(active, key=lambda kv: (order.get(kv[1].get("stage"), 0), kv[0])):
        sch = ", ".join(f"{p} {d[-11:]}" for p, d in sorted((v.get("schedule") or {}).items())) or "-"
        blk = "🚫 " + v["blocked_reason"][:30] if v.get("blocked_reason") else ""
        lines.append(f"| {s} | {v.get('stage')} | {blk} | {sch} | {','.join((v.get('platforms') or {}).keys()) or '-'} |")
    lines.append("")

    # ② 发布队列（每日一篇）
    lines += ["## 发布队列（每日一篇 20:00）", ""]
    rows = _queue_rows(state)
    if not rows:
        lines += ["（无定时排期）", ""]
    else:
        by_day: dict[str, list[dict]] = {}
        for r in rows:
            by_day.setdefault(r["earliest"][:10], []).append(r)
        lines += ["| 日期 | slug | stage | 冲突 |", "|---|---|---|---|"]
        for day in sorted(by_day):
            items = by_day[day]
            conflict = "⚠️ CONFLICT" if len(items) > 1 else ""
            for r in items:
                lines.append(f"| {r['earliest'][:16]} | {r['slug']} | {r['stage']} | {conflict} |")
        lines.append("")

    # ③ 已归档近况
    lines += ["## 已归档（最近 8 部）", ""]
    archived = [(s, v) for s, v in videos.items() if v.get("stage") == "archived"]
    archived.sort(key=lambda kv: kv[1].get("stage_ts", ""), reverse=True)
    if not archived:
        lines += ["（空）", ""]
    else:
        lines += ["| slug | 归档时间 | 抖音 | 快手 | B站 | 视频号 | 播放(抖音) |", "|---|---|---|---|---|---|---|"]
        for s, v in archived[:8]:
            p = v.get("platforms") or {}
            cells = [p.get(pl, {}).get("status", "-") for pl in PLATFORMS]
            lines.append(f"| {s} | {v.get('stage_ts','')[:10]} | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} | {_analytics_plays(s, state)} |")
        lines.append("")

    # ④ 阻塞与库存
    lines += ["## 阻塞与库存", ""]
    blocked = [(s, v) for s, v in videos.items() if v.get("blocked_reason")]
    if blocked:
        for s, v in blocked:
            lines.append(f"- 🚫 {s}: {v['blocked_reason']}")
    backlog = [s for s, v in videos.items() if v.get("stage") == "backlog"]
    if backlog:
        lines.append(f"- 库存 backlog（{len(backlog)}）: {'、'.join(sorted(backlog))}")
    if not blocked and not backlog:
        lines += ["（无阻塞、无库存）"]
    lines.append("")

    # ⑤ 发布在途与风控（pub_guard 登记制，只读呈现）
    lines += ["## 发布在途与风控", ""]
    g = guard_summary()
    if g:
        for seg in g.split("；"):
            lines.append(f"- 🛡️ {seg}")
    else:
        lines += ["（无在途任务、无风控冷却）"]
    lines.append("")
    lines.append("> 数据列引用 `data/analytics/snapshots/` 最新快照；发布证据源 `content/link-map.json`（sync 只读并入）；"
                 "在途/冷却源 `publish-jobs.json` + `risk-backoff.json`（`scripts.pub.pub_guard` 维护，只读呈现）。")

    DASH_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = DASH_PATH.with_suffix(".md.tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(tmp, DASH_PATH)


def cmd_report(_args) -> int:
    state = load_state()
    write_dashboard(state)
    print(f"✅ dashboard 已重生成 → {DASH_PATH}")
    return 0


# ---------- show ----------

def cmd_show(args) -> int:
    state = load_state()
    v = state["videos"].get(args.slug)
    if not v:
        print(f"❌ state 里没有 {args.slug}")
        return 1
    print(json.dumps(v, ensure_ascii=False, indent=2))
    return 0


# ---------- migrate ----------

MIGRATE = [
    # slug, title, stage, schedule{平台: 时间}, note
    ("transformer-matrix-internals", "3 份拷贝看懂 QKV：Transformer 1750 亿参数拆到矩阵这一层",
     "archived", {"douyin": "2026-08-27 20:00", "kuaishou": "2026-08-27 20:00",
                  "bilibili": "2026-08-27 20:00", "shipinhao": "2026-08-27 20:00"},
     "今晚已出片（视频号 20:09/B站 49min 前 7723 播放），已归档"),
    ("codex-five-levels", "Codex 用法分 5 级：90% 的人卡在第 2 级，你在哪级",
     "scheduled", {"douyin": "2026-08-28 20:00", "kuaishou": "2026-08-28 20:00",
                   "bilibili": "2026-08-28 20:00", "shipinhao": "2026-08-28 20:00"},
     "四平台定时已逐一验证（管理页实读）"),
    ("token-saving-skills", "5 个开源 skill 省 token：10 万星 Caveman 领衔",
     "synthesizing", {},
     "blocked: v2 合成任务僵死（exec_36b2a2f5 停在 c00_s00），待杀掉重跑；目标档位 08-29 20:00"),
    ("dsh-money-discipline", "同一问题贵30倍？DeepSeek Harness 省钱纪律",
     "scheduled", {"douyin": "2026-08-30 20:00"}, "由今晚改期（每日一篇原则）"),
    ("codex-token-bill-952w", "一个会话吃掉 952 万 token：Codex 账单逐轮拆解",
     "scheduled", {"douyin": "2026-08-31 20:00"}, "由今晚改期（每日一篇原则）"),
]


def cmd_migrate(_args) -> int:
    state = load_state()
    for slug, title, stage, schedule, note in MIGRATE:
        v = get_video(state, slug, title)
        v["title"] = title
        v["stage"] = stage
        v["stage_ts"] = now_iso()
        v.setdefault("schedule", {}).update(schedule)
        v.setdefault("history", []).append({"ts": now_iso(), "stage": stage, "note": f"migrate: {note}"})
    # build 库存 → backlog
    if VG_DIR.is_dir():
        for d in (VG_DIR / "build").glob("*"):
            if d.is_dir() and d.name not in state["videos"]:
                v = get_video(state, d.name)
                v["history"].append({"ts": now_iso(), "stage": "backlog", "note": "migrate: build 库存"})
    save_state(state)
    print(f"✅ migrate 完成，共 {len(state['videos'])} 条记录")
    return 0


# ---------- main ----------

def main() -> int:
    _utf8()
    parser = argparse.ArgumentParser(description="视频生产状态台账（vpt）")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_stage = sub.add_parser("stage", help="推进状态")
    p_stage.add_argument("slug")
    p_stage.add_argument("stage")
    p_stage.add_argument("--title")
    p_stage.add_argument("--note")
    p_stage.add_argument("--schedule", nargs="*", default=[], help="平台=时间，如 douyin=2026-08-29 20:00")
    p_stage.add_argument("--block")
    p_stage.add_argument("--unblock", action="store_true")

    sub.add_parser("queue", help="排队视图")
    p_sync = sub.add_parser("sync", help="现实源推导并入")
    p_sync.add_argument("slug", nargs="?", default="")
    p_sync.add_argument("--all", action="store_true")
    sub.add_parser("report", help="重生成 dashboard")
    p_show = sub.add_parser("show", help="打印单条记录")
    p_show.add_argument("slug")
    sub.add_parser("migrate", help="存量录入")

    args = parser.parse_args()
    try:
        return {"stage": cmd_stage, "queue": cmd_queue, "sync": cmd_sync,
                "report": cmd_report, "show": cmd_show, "migrate": cmd_migrate}[args.cmd](args)
    except SystemExit as e:
        code = e.code
        if isinstance(code, str):
            print(code)
            return 1
        return code or 0


if __name__ == "__main__":
    sys.exit(main())
