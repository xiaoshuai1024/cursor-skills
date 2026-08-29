# -*- coding: utf-8 -*-
"""方向过滤 + 双系列 + 潜力分评分（抖音选题 skill）。

输入: fetch_sources 的汇总 dict（a 列表 = 主榜 main + 上升榜 rising）
处理:
  1. A 热榜按 word 去重（主榜优先）
  2. 热榜 ∩ hot_list_match → 🔥热度系列
  3. 上升榜 ∩ challenge_search → 📈涨粉系列
  4. 潜力分 = 0.4×热度 + 0.3×垂直匹配 + 0.2×竞争度(反向) + 0.1×互动
  5. 无命中 → 诚实输出「今日无方向命中」
  6. 系列权重缩放（2026-08-29 video-analytics 反哺接线）: 话题词按 series_keywords
     归属到内容系列后乘 weights（多系列命中取命中词最多者，并列取低权重=歧义不加成）；
     无 weights 块或无命中系列时权重 1.0，行为与旧版一致。

评分口径: 缺失字段记中性 50（不奖不罚）; 两系列内部各自排序（跨系列不可比，成功指标不同）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def load_keywords(keywords_file: str) -> tuple[list[str], list[str]]:
    """读 topic_keywords.json，返回 (hot_list_match, challenge_search)。"""
    conf = json.loads(Path(keywords_file).read_text(encoding="utf-8"))
    return conf.get("hot_list_match") or [], conf.get("challenge_search") or []


def load_series_weights(keywords_file: str) -> tuple[dict, dict]:
    """读 weights（系列名→权重）与 series_keywords（系列名→判定词表），缺块返回空 dict。"""
    conf = json.loads(Path(keywords_file).read_text(encoding="utf-8"))
    return conf.get("weights") or {}, conf.get("series_keywords") or {}


def series_weight(word: str, weights: dict, series_keywords: dict) -> tuple[float, list[str]]:
    """话题词的系列权重。命中词最多的系列胜出；并列取低权重（歧义不加成）。

    返回 (权重, 命中系列名列表)，无命中返回 (1.0, [])。
    """
    lowered = word.lower()
    hits: dict[str, list[str]] = {}
    for ser, kws in series_keywords.items():
        matched = [kw for kw in kws if kw.lower() in lowered]
        if matched:
            hits[ser] = matched
    if not hits:
        return 1.0, []
    best_count = max(len(v) for v in hits.values())
    finalists = [s for s, v in hits.items() if len(v) == best_count]
    weight = min(float(weights.get(s, 1.0)) for s in finalists)
    return weight, list(hits.keys())


def match_keywords(word: str, keywords: list[str]) -> list[str]:
    """返回命中的关键词列表（英文大小写不敏感子串匹配）。"""
    lowered = word.lower()
    return [kw for kw in keywords if kw.lower() in lowered]


def dedup_hot_pool(a_items: list[dict]) -> list[dict]:
    """热榜按 word 去重，主榜条目优先（上升榜同词不覆盖主榜数据）。"""
    merged: dict[str, dict] = {}
    for item in a_items:
        merged.setdefault(item["word"], item)
    return list(merged.values())


def _heat_value(item: dict) -> float:
    """热度原始值：热榜用 view_count/hot_value（上升榜缺 view_count 落到 hot_value）。"""
    return float(item.get("view_count") or item.get("hot_value") or 0)


def _heat_score(item: dict, heat_max: float) -> float:
    """热度得分(0-100)：按系列内最大热度归一化。缺失→中性 50；上升榜加分。"""
    value = _heat_value(item)
    if not value:
        return 50.0
    heat = min(100.0, value / heat_max * 100.0) if heat_max else 50.0
    if item.get("sub_board") == "rising":
        heat = min(100.0, heat + 15.0)
    return heat


def _match_score(matched: list[str]) -> float:
    """垂直匹配得分(0-100)。命中词越多越贴合方向。"""
    count = len(matched)
    if count >= 3:
        return 100.0
    if count == 2:
        return 80.0
    if count == 1:
        return 60.0
    return 0.0


def _competition_score(item: dict) -> float:
    """竞争度得分(0-100)，反向：视频数越多竞争越大分越低。"""
    video_count = item.get("video_count")
    if video_count is None:
        return 50.0
    return max(0.0, 100.0 - min(100.0, float(video_count) * 8.0))


def _interaction_score(item: dict) -> float:
    """互动潜力得分(0-100)：讨论数/播放比。缺字段→中性。"""
    discuss = item.get("discuss_video_count")
    views = item.get("view_count")
    if discuss is None or views is None:
        return 50.0
    ratio = float(discuss) / max(float(views), 1.0)
    return min(100.0, ratio * 5000.0)


def score_item(
    item: dict, heat_max: float, matched: list[str],
    weight: float = 1.0, hit_series: list[str] | None = None,
) -> dict:
    """给单个话题打分，返回带评分字段的副本。heat_max 按系列各自的最大热度值。

    weight 为系列反哺权重（乘在总分上，1.0 = 不缩放）。
    """
    heat = _heat_score(item, heat_max)
    comp = _competition_score(item)
    inter = _interaction_score(item)
    total = (0.4 * heat + 0.3 * _match_score(matched) + 0.2 * comp + 0.1 * inter) * weight
    scored = dict(item)
    scored.pop("_hot_kws", None)
    scored.update({
        "score": round(total, 1),
        "heat": round(heat, 1),
        "match": round(_match_score(matched), 1),
        "comp": round(comp, 1),
        "inter": round(inter, 1),
        "matched_keywords": matched,
        "weight": round(weight, 2),
        "matched_series": hit_series or [],
    })
    return scored


def build_topics(
    summary: dict, hot_kws: list[str], growth_kws: list[str],
    weights: dict | None = None, series_keywords: dict | None = None,
) -> dict:
    """从 fetch 汇总构建双系列选题清单。weights/series_keywords 为可选系列反哺配置。"""
    a_items = summary.get("a") or []
    weights = weights or {}
    series_keywords = series_keywords or {}

    def _score(it: dict, heat_max: float, kws: list[str]) -> dict:
        matched = match_keywords(it["word"], kws)
        weight, hit_series = series_weight(it["word"], weights, series_keywords)
        return score_item(it, heat_max, matched, weight, hit_series)

    hot_pool = dedup_hot_pool(a_items)
    hot_max = max([_heat_value(i) for i in hot_pool] or [0])
    rising_pool = [i for i in a_items if i.get("sub_board") == "rising"]
    growth_max = max([_heat_value(i) for i in rising_pool] or [0])

    # 🔥 热度系列: 热榜 ∩ 方向关键词
    hot_scored = sorted(
        (
            _score(it, hot_max, hot_kws)
            for it in hot_pool if match_keywords(it["word"], hot_kws)
        ),
        key=lambda x: x["score"], reverse=True,
    )

    # 📈 涨粉系列: 上升榜 ∩ 方向搜索词（热度上升期求关注转化）
    growth_scored = sorted(
        (
            _score(it, growth_max, growth_kws)
            for it in rising_pool if match_keywords(it["word"], growth_kws)
        ),
        key=lambda x: x["score"], reverse=True,
    )

    return {
        "date": summary.get("fetched_at", ""),
        "max_heat": round(hot_max),
        "series": {
            "hot": hot_scored,
            "growth": growth_scored,
        },
        "no_hit": {
            "hot": len(hot_scored) == 0,
            "hot_tried_keywords": hot_kws,
            "growth_tried_keywords": growth_kws,
        },
        "notes": summary.get("notes", []),
    }


def _weight_tag(item: dict) -> str:
    """权重标记：≠1.0 时在分数后追加 ×权重（含命中系列）。"""
    w = item.get("weight", 1.0) or 1.0
    if w == 1.0:
        return ""
    series = "/".join(item.get("matched_series") or [])
    return f"(×{w:g} {series})" if series else f"(×{w:g})"


def render_markdown(topics: dict) -> str:
    """可读的 markdown 选题清单。"""
    lines: list[str] = []
    lines.append("━━━ 抖音选题建议 ━━━")
    lines.append(f"数据时间: {topics.get('date')} | 热榜最大热度: {topics.get('max_heat')}")

    hot = topics["series"]["hot"]
    lines.append("\n## 🔥 热度系列（热榜 ∩ 方向，求播放）")
    if not hot:
        lines.append("- 今日无方向命中（已尝试关键词: " + "、".join(topics["no_hit"]["hot_tried_keywords"][:8]) + "）")
    for item in hot[:12]:
        heat = item.get("view_count") or item.get("hot_value") or "-"
        wtag = _weight_tag(item)
        group = f"https://www.douyin.com/video/{item['group_id']}" if item.get("group_id") else "待定位"
        lines.append(
            f"- [{item['score']}]{wtag} {item['word']} | 热度 {heat} | 命中 {','.join(item['matched_keywords'][:2])}\n"
            f"    📼 {group}"
        )

    growth = topics["series"]["growth"]
    lines.append("\n## 📈 涨粉系列（上升榜 ∩ 方向，求关注转化）")
    if not growth:
        lines.append("- 上升榜无方向命中（已尝试关键词: " + "、".join(topics["no_hit"]["growth_tried_keywords"][:8]) + "）")
    for item in growth[:12]:
        heat = item.get("hot_value") or "-"
        wtag = _weight_tag(item)
        lines.append(
            f"- [{item['score']}]{wtag} {item['word']} | 热度 {heat} | 命中 {','.join(item['matched_keywords'][:2])}"
        )

    if topics.get("notes"):
        lines.append("\n## ⚠️ 备注")
        for note in topics["notes"]:
            lines.append(f"- {note}")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="方向过滤 + 双系列评分")
    parser.add_argument("--in", dest="in_file", required=True, help="fetch_sources 输出 JSON")
    parser.add_argument("--out", default=None, help="选题清单 JSON 输出路径")
    parser.add_argument("--keywords-file", default=None, help="方向关键词 JSON")
    parser.add_argument("--markdown", default=None, help="同时输出可读 markdown 到该路径")
    args = parser.parse_args()

    summary = json.loads(Path(args.in_file).read_text(encoding="utf-8"))
    keywords_file = args.keywords_file or str(
        Path(__file__).resolve().parent.parent / "topic_keywords.json"
    )
    hot_kws, growth_kws = load_keywords(keywords_file)
    weights, series_keywords = load_series_weights(keywords_file)

    topics = build_topics(summary, hot_kws, growth_kws, weights, series_keywords)

    if args.out:
        Path(args.out).write_text(
            json.dumps(topics, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"✅ 选题清单已写入 {args.out}")
    else:
        sys.stdout.write(json.dumps(topics, ensure_ascii=False, indent=2) + "\n")

    if args.markdown:
        Path(args.markdown).write_text(render_markdown(topics), encoding="utf-8")
        print(f"✅ markdown 已写入 {args.markdown}")

    if topics["no_hit"]["hot"]:
        print("⚠️ 热度系列今日无方向命中")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
