# -*- coding: utf-8 -*-
"""多源方向过滤 + 双视角（🔥热度/🎯垂直）+ 潜力分排序。

  多源（掘金/CSDN/InfoQ/知乎）合并后：
  - 方向：掘金用 category_id；InfoQ 用 topic（fetcher 已设 direction）；CSDN/知乎用关键词
  - in_hot：掘金=category 命中；CSDN/InfoQ/知乎=True（平台已筛技术向/关键词过滤）
  - 互动量分源计算（InfoQ 用 views，其余 digg 系）→ 分源 min-max × 源权重（避免量级淹没）
  - 跨源去重（归一化标题 key）

用法:
  py -m filter_score --in .tech-topic/latest.json --out .tech-topic/topics.json \
      --markdown .tech-topic/topics.md [--top 10] [--recent-days 30]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def _utf8_stdio() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _minmax(values: list[float]) -> list[float]:
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi <= lo:
        return [1.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def _interaction(rec: dict[str, Any]) -> float:
    """分源互动量：InfoQ 用 views（无 digg），其余 digg 系 + collect + comment。"""
    if rec.get("source") == "infoq":
        return float(rec.get("view_count") or 0)
    return (
        (rec.get("digg_count") or 0)
        + (rec.get("collect_count") or 0) * 0.5
        + (rec.get("comment_count") or 0) * 0.3
    )


def _title_key(title: str) -> str:
    """归一化标题 key（去标点/空格/平台水印/大小写）用于跨源去重。"""
    t = re.sub(r"[-_—|：:【】\[\]()（）]", " ", title)
    t = re.sub(r"\s+", "", t).lower()
    t = re.sub(r"(掘金|csdn|infoq|知乎|博客|_blog)$", "", t)
    return t[:20]


_SRC_LABEL = {"A": "掘金", "H": "掘金", "B": "掘金", "A+H": "掘金", "A+H+B": "掘金",
              "juejin": "掘金", "csdn": "CSDN", "infoq": "InfoQ", "zhihu": "知乎"}


def _src_label(s: str) -> str:
    return _SRC_LABEL.get(s, s or "?")


def main() -> int:
    ap = argparse.ArgumentParser(description="多源方向过滤 + 双视角评分")
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--markdown", required=True)
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--recent-days", type=int, default=30)
    args = ap.parse_args()
    _utf8_stdio()

    skill_dir = Path(__file__).resolve().parent.parent
    kw_map: dict[str, list[str]] = {d: w for d, w in _load(skill_dir / "topic_keywords.json").items() if isinstance(w, list)}
    cat_map: dict[str, list[str]] = _load(skill_dir / "category_map.json")
    cat2dir: dict[str, str] = {str(i): d for d, ids in cat_map.items() if isinstance(ids, list) for i in ids}
    try:
        weights: dict[str, float] = {k: v.get("weight", 1.0) for k, v in _load(skill_dir / "sources.json").get("sources", {}).items()}
    except Exception:
        weights = {}
    all_kws = [(d, k) for d, kws in kw_map.items() for k in kws if len(k) >= 2]

    data = _load(Path(args.inp))
    articles: list[dict[str, Any]] = data.get("articles") or []
    now = int(time.time())
    recent_window = args.recent_days * 86400

    enriched: list[dict[str, Any]] = []
    filtered_old = 0
    for rec in articles:
        # 方向 + in_hot：有掘金 category_id 的按 category，其余用 fetcher 预置 direction + 默认 in_hot
        if rec.get("category_id"):
            direction = cat2dir.get(str(rec.get("category_id")))
            in_hot = direction is not None
        else:
            direction = rec.get("direction")
            in_hot = True  # 非掘金源：CSDN/InfoQ 纯技术社区、知乎已关键词过滤
        # 关键词命中（垂直视角）
        title_tags = (rec.get("title") or "") + " " + " ".join(rec.get("tags") or [])
        tl = title_tags.lower()
        hit_kws = [k for d, k in all_kws if k.lower() in tl]
        # B 源预置 matched_keywords 合并
        preset = rec.get("matched_keywords") or []
        all_hit = list(dict.fromkeys(hit_kws + [k for k in preset if k not in hit_kws]))
        in_vertical = bool(all_hit)
        if not in_hot and not in_vertical:
            continue
        # 近期硬过滤（有 ctime 的才算；热榜无 ctime 不滤）
        rtime = int(rec.get("rtime") or rec.get("ctime") or 0)
        has_time = bool(rtime)
        if has_time and (now - rtime) > recent_window:
            filtered_old += 1
            continue
        rec = dict(rec)
        rec["direction"] = direction
        rec["matched_keywords"] = all_hit
        rec["in_hot"] = in_hot
        rec["in_vertical"] = in_vertical
        rec["interaction"] = _interaction(rec)
        rec["age_days"] = round((now - rtime) / 86400, 1) if has_time else None
        rec["title_key"] = _title_key(rec.get("title") or "")
        enriched.append(rec)

    # 跨源去重（同 title_key 保留互动最高，其余进 also_on）
    enriched.sort(key=lambda r: r["interaction"], reverse=True)
    by_key: dict[str, dict[str, Any]] = {}
    for r in enriched:
        key = r["title_key"]
        if not key:
            by_key[id(r)] = r
            continue
        if key in by_key:
            base = by_key[key]
            base.setdefault("also_on", [])
            if r["source"] not in base["also_on"] and r["source"] != base["source"]:
                base["also_on"].append(r["source"])
        else:
            by_key[key] = r
    deduped = list(by_key.values())

    # 分源互动归一 × 权重
    by_src: dict[str, list[dict[str, Any]]] = {}
    for r in deduped:
        by_src.setdefault(r.get("source", "juejin"), []).append(r)
    for src, recs in by_src.items():
        raws = [r["interaction"] for r in recs]
        w = weights.get(src, 1.0)
        if max(raws) <= 0:
            for r in recs:
                r["inter_score"] = 0.0  # 无互动信号（如 InfoQ RSS 无浏览量）
        else:
            for r, n in zip(recs, _minmax(raws)):
                r["inter_score"] = n * w
    # 绝对互动量 log 归一（让真高互动 CSDN👍1688 压过低互动掘金👍3，且 InfoQ 400k views 不无限放大）
    max_raw = max((r["interaction"] for r in deduped), default=0) or 1
    for r in deduped:
        r["abs_inter"] = math.log1p(r["interaction"]) / math.log1p(max_raw)
        r["inter_combined"] = 0.6 * r["inter_score"] + 0.4 * r["abs_inter"]

    for r in deduped:
        direction_score = 1.0 if r["in_hot"] else 0.0
        direction_score += min(0.9, 0.3 * len(r["matched_keywords"]))
        rtime = int(r.get("rtime") or r.get("ctime") or 0)
        recency = min(1.0, max(0.0, 1.0 - (now - rtime) / recent_window)) if rtime else 0.5  # 无时间的热榜文给中位
        original = 1.0 if r.get("is_original") else 0.0
        multi_bonus = 0.1 if r.get("also_on") else 0.0
        r["score"] = round(
            0.60 * r["inter_combined"]
            + 0.15 * min(1.0, direction_score)
            + 0.10 * recency
            + 0.05 * original
            + 0.05 * multi_bonus
            + 0.05 * (1.0 if r["in_vertical"] else 0.0)
            , 3)

    hot = sorted([r for r in deduped if r["in_hot"]], key=lambda x: x["score"], reverse=True)
    vertical = sorted([r for r in deduped if r["in_vertical"]], key=lambda x: x["score"], reverse=True)
    no_hit = not deduped

    result = {
        "fetched_at": data.get("fetched_at"), "candidate_count": len(deduped),
        "no_hit": no_hit, "filtered_old": filtered_old,
        "series": {"hot": hot[: args.top], "vertical": vertical[: args.top]},
    }
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    # markdown
    src_count: dict[str, int] = {}
    for r in deduped:
        _s = _src_label(r.get("source", "?")); src_count[_s] = src_count.get(_s, 0) + 1
    lines = [f"# tech-topic 选题清单（多源）\n",
             f"_候选 {len(deduped)} 篇（因 >{args.recent_days}d 过滤 {filtered_old}）| "
             f"来源: {' '.join(f'{s}×{n}' for s, n in sorted(src_count.items(), key=lambda x: -x[1]))}_\n"]
    if no_hit:
        lines.append("## ⚠️ 无命中\n")
    else:
        # 热门 Top 20：按来源聚合，每源取其最热的若干篇（保各源均有露出），合计 ≤20
        src_groups: dict[str, list] = {}
        for r in hot:
            src_groups.setdefault(_src_label(r.get("source", "")), []).append(r)
        active = {s: rs for s, rs in src_groups.items() if rs}
        try:
            per_top = int(_load(skill_dir / "sources.json").get("per_source_top", 10))
        except Exception:
            per_top = 10
        top20: list = []
        for s, rs in sorted(active.items(), key=lambda kv: -len(kv[1])):
            top20.extend(rs[:per_top])  # 每平台取其最热的 per_top 篇
        grp: dict[str, list] = {}
        for r in top20:
            grp.setdefault(_src_label(r.get("source", "")), []).append(r)
        lines.append(f"## 🔥 热门（每平台 Top {per_top}，按来源聚合，共 {len(top20)} 篇）\n")
        for src_name, recs in sorted(grp.items(), key=lambda kv: -len(kv[1])):
            lines.append(f"\n**{src_name}**（{len(recs)} 篇）\n")
            lines.append("| 分 | 文章 | 方向 | 互动 |")
            lines.append("|---|---|---|---|")
            for r in recs:
                extra = f"榜#{r.get('hot_rank')}" if r.get("hot_rank") else f"{r.get('age_days') or '—'}d"
                also = f" 🔥多平台:{'+'.join(_src_label(s) for s in r.get('also_on', []))}" if r.get("also_on") else ""
                inter = f"👍{r.get('digg_count', 0)} 👁{r.get('view_count', 0)} · {extra}{also}"
                title = (r.get("title", "") or "").replace("|", "/")
                lines.append(f"| {r.get('score')} | [{title}]({r.get('url', '')}) | {r.get('direction') or '技术'} | {inter} |")
        lines.append("")
        lines.append("\n## 🎯 垂直视角（关键词命中）\n")
        if vertical:
            lines.append("| 分 | 文章 | 关键词 | 来源 |")
            lines.append("|---|---|---|---|")
            for r in vertical[: args.top]:
                kws = ",".join(r.get("matched_keywords") or [])
                title = (r.get("title", "") or "").replace("|", "/")
                lines.append(f"| {r.get('score')} | [{title}]({r.get('url', '')}) | {kws} | {_src_label(r.get('source',''))} |")
        else:
            lines.append("_（无关键词命中）_")
    lines.append("\n---\n⚠️ 仅作选题参考；多源扩范围面向技术社区（掘金/CSDN/InfoQ/知乎），不接泛新闻。")
    Path(args.markdown).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"✅ 多源评分完成: 候选 {len(deduped)}（过滤 {filtered_old}）| 🔥{len(hot)} 🎯{len(vertical)} | {src_count}")
    print(f"   {args.markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
