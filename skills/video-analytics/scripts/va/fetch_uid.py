# -*- coding: utf-8 -*-
"""身份映射：平台作品 → slug（join key），回填 link-map.json 的 pub_video。

匹配算法（spike 0.5 定型，两级）：
1. 标题前缀匹配：期望标题 = metadata.txt 标题_平台 override，否则 crop_title(标题, title_max)
   —— 快手 title 常为空/描述风格，抖音/B站 主命中
2. 时长+日期兜底：|平台时长 - 本地视频时长(ffprobe)| ≤ 2s 且发布同日 —— 快手主通道
- 空标题跳过；歧义列候选待人工，不猜

回填字段：pub_video.{platform}_id（douyin_id / kuaishou_id / bilibili_id / shipinhao_id）
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from . import common
from .common import ROOT, crop_title_inline, latest_by_item, setup_utf8

# 与 scripts/pub/config.py 的 title_max 同源（不 import 避免拉 vendor 依赖）
TITLE_MAX = {"douyin": 30, "kuaishou": 50, "shipinhao": 63, "bilibili": 80}
ID_FIELD = {"douyin": "douyin_id", "kuaishou": "kuaishou_id",
            "shipinhao": "shipinhao_id", "bilibili": "bilibili_id"}

_MIN_MATCH_LEN = 8


def _norm(s: str) -> str:
    s = re.sub(r"[\s#【】\[\]（）()]+", "", str(s or ""))
    return s


def load_meta_for(slug: str) -> dict | None:
    try:
        sys.path.insert(0, str(ROOT))
        from scripts.pub.meta import load_meta
        return load_meta(slug)
    except BaseException:  # load_meta 失败会 sys.exit（SystemExit），一并吞掉
        return None


def expected_title(meta: dict, platform: str) -> str | None:
    base = meta.get("title") or ""
    if not base:
        return None
    return meta.get(f"title_{platform}") or crop_title_inline(base, TITLE_MAX.get(platform, 80))


def _lcp(a: str, b: str) -> int:
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


def match_slug(meta: dict, plat: str, items: dict[str, dict]) -> str | None:
    """单平台匹配：期望标题 × 该平台快照 items（item_id -> snapshot）。返回 item_id / None / 'AMBIG'。

    最长公共前缀 ≥12（归一后）：容忍发布后改写标题后半段 / 平台裁剪。
    """
    e = expected_title(meta, plat)
    if not e:
        return None
    ne = _norm(e)
    if len(ne) < _MIN_MATCH_LEN:
        return None
    hits = []
    for iid, snap in items.items():
        nt = _norm(snap.get("title"))
        if len(nt) < _MIN_MATCH_LEN:
            continue
        if _lcp(ne, nt) >= 12:
            hits.append(iid)
    if not hits:
        return None
    return hits[0] if len(set(hits)) == 1 else "AMBIG"


# ---------------------------------------------------------------- 时长+日期兜底

DUR_CACHE = common.DATA_DIR / "duration_cache.json"


def _video_path(slug: str) -> Path | None:
    """与 scripts/pub/publish.py 的 find_video 同规则（内联避免 import 链）。"""
    build = ROOT / "video-generation" / "build" / slug
    if build.exists():
        for name in (f"{slug}_light.mp4", f"{slug}_dark.mp4", f"{slug}.mp4"):
            if (build / name).exists():
                return build / name
        mp4s = sorted(build.glob("*.mp4"))
        if mp4s:
            return mp4s[0]
    out = ROOT / "video-generation" / "out"
    for name in (f"{slug}.mp4", f"{slug}_light.mp4", f"{slug}_dark.mp4"):
        if (out / name).exists():
            return out / name
    return None


def video_duration(slug: str) -> float | None:
    cache = json.loads(DUR_CACHE.read_text(encoding="utf-8")) if DUR_CACHE.exists() else {}
    if slug in cache:
        return cache[slug]
    path = _video_path(slug)
    dur = None
    if path:
        try:
            r = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                 "-of", "csv=p=0", str(path)],
                capture_output=True, text=True, timeout=30)
            dur = round(float(r.stdout.strip()), 1)
        except Exception:
            dur = None
    common.DATA_DIR.mkdir(parents=True, exist_ok=True)
    cache[slug] = dur
    DUR_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    return dur


def item_duration(snap: dict) -> float | None:
    raw = snap.get("raw") or {}
    for k in ("duration_second", "duration", "duration_ms"):
        v = raw.get(k)
        if v:
            return round(int(v) / (1000 if k == "duration_ms" else 1), 1)
    return None


def match_by_duration(slug: str, published_at: str | None, items: dict[str, dict]) -> str | None:
    """时长 ±1.5s（平台侧取整）且发布日 ±1 天（定时发布会跨零点）。
    系列视频时长可能仅差 2-3s，撞车时返回 AMBIG 交给人工。"""
    dur = video_duration(slug)
    if not dur or not published_at:
        return None
    pub_day = str(published_at)[:10]
    hits = []
    for iid, snap in items.items():
        d = item_duration(snap)
        if d is None or abs(d - dur) > 1.5:
            continue
        day = str(snap.get("published_at") or "")[:10]
        if day and abs(_days(day) - _days(pub_day)) > 1:
            continue
        hits.append(iid)
    if not hits:
        return None
    return hits[0] if len(set(hits)) == 1 else "AMBIG"


def _days(day: str) -> int:
    from datetime import date
    y, m, d = (int(x) for x in day.split("-"))
    return date(y, m, d).toordinal()


def run(platforms: list[str] | None = None) -> None:
    setup_utf8()
    plats = platforms or list(TITLE_MAX)
    lm = common.load_link_map()
    slugs = [k for k, v in lm.items() if isinstance(v, dict) and isinstance(v.get("pub_video"), dict)]
    if not slugs:
        print("[uid] link-map 无 pub_video 记录")
        return

    latest: dict[str, dict[str, dict]] = {p: latest_by_item(p) for p in plats}
    have = {p: {i: s for i, s in latest[p].items() if _norm(s.get("title")) or item_duration(s)} for p in plats}

    # 全局认领登记：一个平台 item 只能归属一个 slug（跨 slug 撞车防护）
    claims: dict[tuple[str, str], str] = {}
    for s in slugs:
        pv = lm[s]["pub_video"]
        for plat in plats:
            f = ID_FIELD[plat]
            if pv.get(f):
                claims[(plat, str(pv[f]))] = s

    backfilled = 0
    pending: list[tuple[str, str]] = []

    def claim(plat: str, iid: str, slug: str) -> bool:
        owner = claims.get((plat, iid))
        if owner and owner != slug:
            return False
        claims[(plat, iid)] = slug
        return True

    metas = {}
    for slug in slugs:
        meta = load_meta_for(slug)
        metas[slug] = meta
        if not meta or not meta.get("title"):
            pending.append((slug, "无 metadata（构建目录/front matter 缺失）"))

    # Pass 1: 标题匹配（高置信）
    wants: list[tuple[str, str]] = []
    for slug in slugs:
        meta = metas.get(slug)
        if not meta or not meta.get("title"):
            continue
        pv = lm[slug]["pub_video"]
        for plat in plats:
            if not have.get(plat) or pv.get(ID_FIELD[plat]):
                continue
            iid = match_slug(meta, plat, have[plat])
            if iid and iid != "AMBIG" and claim(plat, iid, slug):
                pv[ID_FIELD[plat]] = iid
                backfilled += 1
            else:
                wants.append((slug, plat))

    # Pass 2: 时长+日期兜底（不得抢占已认领 item）
    for slug, plat in wants:
        pv = lm[slug]["pub_video"]
        if pv.get(ID_FIELD[plat]):
            continue
        iid = match_by_duration(slug, pv.get("published_at"), have[plat])
        if not iid:
            pending.append((slug, f"{plat}: 标题/时长均未匹配（期望「{expected_title(metas[slug], plat)}」）"))
        elif iid == "AMBIG":
            pending.append((slug, f"{plat}: 多个候选，需人工确认"))
        elif claim(plat, iid, slug):
            pv[ID_FIELD[plat]] = iid
            backfilled += 1
        else:
            pending.append((slug, f"{plat}: 时长命中的 item 已被其他 slug 认领，需人工确认"))

    if backfilled:
        common.save_link_map(lm)
    print(f"[uid] 回填 {backfilled} 个平台 ID；待人工 {len(pending)} 条")
    for s, why in pending[:10]:
        print(f"  - {s}: {why[:90]}")


if __name__ == "__main__":
    setup_utf8()
    run()
