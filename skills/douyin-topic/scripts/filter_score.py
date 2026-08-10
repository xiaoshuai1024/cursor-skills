# -*- coding: utf-8 -*-
"""方向过滤 + 双系列 + 潜力分评分（抖音选题 skill）。

输入: fetch_sources 的汇总 dict（a/b/c 列表）
处理:
  1. 合并 A+B 热榜（按 word 去重，优先 B：B 有真实播放量）
  2. 热榜 ∩ 方向关键词 → 🔥热度系列
  3. C 源（方向内话题）→ 📈涨粉系列（存在性信号）
  4. 潜力分 = 0.4×热度 + 0.3×垂直匹配 + 0.2×竞争度(反向) + 0.1×互动
  5. 无命中 → 诚实输出「今日无方向命中」

评分口径: 缺失字段记中性 50（不奖不罚）; 两系列内部各自排序（跨系列不可比，成功指标不同）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def load_keywords(keywords_file: str) -> tuple[list[str], list[str]]:
    """读 topic_keywords.json，返回 (hot_list_match, challenge_search)。"""
    conf = json.loads(Path(keywords_file).read_text(encoding="utf-8"))
    return conf.get("hot_list_match") or [], conf.get("challenge_search") or []


def match_keywords(word: str, keywords: list[str]) -> list[str]:
    """返回命中的关键词列表（英文大小写不敏感子串匹配）。"""
    lowered = word.lower()
    return [kw for kw in keywords if kw.lower() in lowered]


def merge_hot_pool(a_items: list[dict], b_items: list[dict]) -> list[dict]:
    """合并 A+B 热榜。按 word 去重，优先 B（真实播放量）。"""
    merged: dict[str, dict] = {}
    for item in a_items:
        merged[item["word"]] = item
    for item in b_items:
        merged[item["word"]] = item  # B 覆盖 A（B 有真实 view_count）
    return list(merged.values())


def _heat_value(item: dict) -> float:
    """热度原始值：C 源用 viewNum（相对活跃度），热榜用 view_count/hot_value。"""
    if item.get("source") == "c":
        return float(item.get("viewNum") or 0)
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


def score_item(item: dict, heat_max: float, matched: list[str]) -> dict:
    """给单个话题打分，返回带评分字段的副本。heat_max 按系列各自的最大热度值。"""
    heat = _heat_score(item, heat_max)
    match = _match_score(matched)
    comp = _competition_score(item)
    inter = _interaction_score(item)
    total = 0.4 * heat + 0.3 * match + 0.2 * comp + 0.1 * inter
    scored = dict(item)
    scored.pop("_hot_kws", None)
    scored.update({
        "score": round(total, 1),
        "heat": round(heat, 1),
        "match": round(match, 1),
        "comp": round(comp, 1),
        "inter": round(inter, 1),
        "matched_keywords": matched,
    })
    return scored


def build_topics(summary: dict, hot_kws: list[str], growth_kws: list[str]) -> dict:
    """从 fetch 汇总构建双系列选题清单。"""
    a_items = summary.get("a") or []
    b_items = summary.get("b") or []
    c_items = summary.get("c") or []

    hot_pool = merge_hot_pool(a_items, b_items)
    hot_max = max([_heat_value(i) for i in hot_pool] or [0])
    c_max = max([_heat_value(i) for i in c_items] or [0])

    # 🔥 热度系列: 热榜 ∩ 方向关键词
    hot_scored = sorted(
        (
            score_item(it, hot_max, match_keywords(it["word"], hot_kws))
            for it in hot_pool if match_keywords(it["word"], hot_kws)
        ),
        key=lambda x: x["score"], reverse=True,
    )

    # 📈 涨粉系列: C 源方向内话题（按 match_keyword 计垂直匹配，viewNum 相对活跃度）
    growth_scored = sorted(
        (
            score_item(it, c_max, [it.get("match_keyword") or ""])
            for it in c_items
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
        group = f"https://www.douyin.com/video/{item['group_id']}" if item.get("group_id") else "待定位"
        lines.append(
            f"- [{item['score']}] {item['word']} | 热度 {heat} | 命中 {','.join(item['matched_keywords'][:2])}\n"
            f"    📼 {group}"
        )

    growth = topics["series"]["growth"]
    lines.append("\n## 📈 涨粉系列（方向内话题，求关注转化）")
    if not growth:
        lines.append("- 方向内无话题（已尝试关键词: " + "、".join(topics["no_hit"]["growth_tried_keywords"][:8]) + "）")
    for item in growth[:12]:
        lines.append(
            f"- [{item['score']}] {item['word']} | 匹配词 {item.get('match_keyword', '')} | 存在性 {item.get('viewNum', '-')}"
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

    topics = build_topics(summary, hot_kws, growth_kws)

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
