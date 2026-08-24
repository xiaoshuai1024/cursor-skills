# -*- coding: utf-8 -*-
"""指标标准化：快照 raw → 统一指标（跨平台可比）。

原则：平台缺失字段置 null 不造数；近似计算显式标注 approx。
产出 data/analytics/metrics.json：
    videos.<slug>.<platform> = {play, like, ..., *_rate, duration_s, ...}
"""
from __future__ import annotations

import json

from . import common
from .common import DATA_DIR, setup_utf8


def _num(v):
    return v if isinstance(v, (int, float)) else None


def _rate(a, b):
    a, b = _num(a), _num(b)
    if not a or not b:
        return None
    return round(a / b, 4)


def std_metrics(platform: str, raw: dict) -> dict:
    """平台原生字段 → 标准名。缺失置 None。"""
    if platform == "bilibili":
        return {
            "play": _num(raw.get("view")),
            "like": _num(raw.get("like")),
            "comment": _num(raw.get("reply")),
            "share": _num(raw.get("share")),
            "fav": _num(raw.get("favorite")),
            "coin": _num(raw.get("coin")),
            "danmaku": _num(raw.get("danmaku")),
            "forward": None,
        }
    if platform == "douyin":
        return {
            "play": _num(raw.get("play_count")),
            "like": _num(raw.get("digg_count")),
            "comment": _num(raw.get("comment_count")),
            "share": _num(raw.get("share_count")),
            "fav": _num(raw.get("collect_count")),
            "coin": None,
            "danmaku": None,
            "forward": _num(raw.get("forward_count")),
        }
    if platform == "kuaishou":
        return {
            "play": _num(raw.get("play_count")),
            "like": _num(raw.get("like_count")),
            "comment": _num(raw.get("comment_count")),
            "share": None,
            "fav": None,
            "coin": None,
            "danmaku": None,
            "forward": None,
        }
    if platform == "shipinhao":
        return {"play": _num(raw.get("play_count")), "like": None, "comment": None,
                "share": None, "fav": None, "coin": None, "danmaku": None, "forward": None}
    raise ValueError(f"unknown platform {platform}")


def duration_seconds(platform: str, raw: dict):
    v = raw.get("duration_second") or raw.get("duration") or raw.get("duration_ms")
    if not _num(v):
        return None
    return round(_num(v) / (1000 if raw.get("duration_ms") else 1), 1)


def build() -> dict:
    setup_utf8()
    lm = common.load_link_map()
    id_field = {"douyin": "douyin_id", "kuaishou": "kuaishou_id",
                "bilibili": "bilibili_id", "shipinhao": "shipinhao_id"}
    platforms = list(id_field)

    # slug -> [(plat, snapshot)]
    by_slug: dict[str, list[tuple[str, dict]]] = {}
    unmatched: list[dict] = []
    for plat in platforms:
        latest = common.latest_by_item(plat)
        claimed = {}
        for slug, v in lm.items():
            pv = v.get("pub_video") if isinstance(v, dict) else None
            if not isinstance(pv, dict):
                continue
            iid = pv.get(id_field[plat])
            if iid and iid in latest:
                claimed[iid] = slug
        for iid, snap in latest.items():
            if iid in claimed:
                by_slug.setdefault(claimed[iid], []).append((plat, snap))
            else:
                st = snap.get("raw") or {}
                if st.get("play_count") or st.get("view"):  # 只记有数据的未匹配项
                    unmatched.append({"platform": plat, "item_id": iid, "title": snap.get("title")})

    videos = {}
    for slug, pairs in by_slug.items():
        entry = {}
        for plat, snap in pairs:
            raw = snap.get("raw") or {}
            m = std_metrics(plat, raw)
            inter = sum(x for x in (m["like"], m["comment"], m["share"], m["fav"], m["coin"], m["forward"]) if x)
            m["interactions"] = inter
            m["engagement_rate"] = _rate(inter, m["play"])
            m["like_rate"] = _rate(m["like"], m["play"])
            m["comment_rate"] = _rate(m["comment"], m["play"])
            m["share_rate"] = _rate(m["share"], m["play"])
            m["fav_rate"] = _rate(m["fav"], m["play"])
            m["duration_s"] = duration_seconds(plat, raw)
            m["published_at"] = snap.get("published_at")
            m["fetched_at"] = snap.get("fetched_at")
            m["title"] = snap.get("title")
            m["completion_rate"] = None  # 深度快照存在时下方覆盖
            m["retention_5s"] = None
            entry[plat] = m
        videos[slug] = entry

    # 深度过程锚点合并（deep_collect 产物）
    for plat in ("douyin", "bilibili"):
        deep_file = common.SNAP_DIR / "deep" / f"{plat}.jsonl"
        if not deep_file.exists():
            continue
        latest = {}
        for line in deep_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            s = r.get("slug")
            if s and (s not in latest or (r.get("fetched_at") or "") > (latest[s].get("fetched_at") or "")):
                latest[s] = r
        for slug, r in latest.items():
            raw = r.get("raw") or {}
            entry = videos.setdefault(slug, {})
            m = entry.setdefault(plat, {"play": None, "title": None})
            m["completion_rate"] = raw.get("play_finish_ratio") if raw.get("play_finish_ratio") is not None else raw.get("full_play_ratio")
            m["avg_play_time_s"] = raw.get("play_avg_time") or raw.get("avg_play_time")
            m["crash_3s_rate"] = raw.get("crash_rate_3s")
            m["cover_ctr"] = raw.get("cover_click_ratio") or raw.get("cover_ctr")
            m["new_fans"] = raw.get("new_fans_count")
            m["follow_rate"] = _rate(raw.get("new_fans_count"), raw.get("play_count") or m.get("play"))
            m["home_visits"] = raw.get("home_page_view_count")
            if raw.get("play_count"):
                m["play"] = m["play"] or raw["play_count"]
            hv = raw.get("hourly_views") or []
            if hv and m.get("play"):
                first_hour = sum(v for _, v in hv[:2])
                m["first_hour_share"] = round(first_hour / max(1, m["play"]), 4)
            if not m.get("duration_s") and raw.get("duration"):
                m["duration_s"] = float(raw["duration"])
            m["retention_5s"] = None
            if m.get("avg_play_time_s") and m.get("duration_s"):
                m["watch_depth"] = round(m["avg_play_time_s"] / m["duration_s"], 4)

    out = {"generated_at": common.now_iso(), "videos": videos, "unmatched_items": unmatched,
           "account": _account_fans()}
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "metrics.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    n_plat = sum(len(v) for v in videos.values())
    print(f"[standardize] slug={len(videos)} 平台记录={n_plat} 未匹配有数据项={len(unmatched)} -> metrics.json")
    return out


def _account_fans() -> dict:
    """账号级粉丝数据（fans_collect 产物，B站净增由快照差分）。"""
    account = {}
    for plat in ("douyin", "bilibili"):
        p = common.SNAP_DIR / "fans" / f"{plat}.jsonl"
        if not p.exists():
            continue
        recs = []
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    recs.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        if not recs:
            continue
        latest = max(recs, key=lambda r: r.get("fetched_at") or "")
        acc = {
            "follower_total": latest.get("follower_total"),
            "follower_total_eod": latest.get("follower_total_eod"),
            "series_net": latest.get("series_net"),
            "date": latest.get("date"),
            "daily": latest.get("daily") or [],
        }
        if plat == "bilibili" and len(recs) >= 2:
            prev = recs[-2].get("follower_total")
            if prev is not None and latest.get("follower_total") is not None:
                acc["net_since_last"] = latest["follower_total"] - prev
        account[plat] = acc
    return account


if __name__ == "__main__":
    build()
