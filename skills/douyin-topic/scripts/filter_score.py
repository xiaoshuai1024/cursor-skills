# -*- coding: utf-8 -*-
"""方向过滤 + 双系列 + 潜力分评分 + 低粉爆款代理榜（抖音选题 skill）。

输入: fetch_sources 的汇总 dict
  - a 列表 = A 源（主榜 main + 上升榜 rising，免登录）
  - trend 可选 = B/C 源（fetch_trend 输出）: main=抖音指数实时热点 / rising=飙升热点 / foryou=创作者中心个性化垂类
处理:
  1. 三源按 word 归一合并（A 优先、字段互补、boards 并集、sub_board 按 main>rising>foryou 取代表值）
  2. 热度系列: A 主榜 + B 实时热点 ∩ hot_list_match
  3. 涨粉系列: A 上升榜 + B 飙升热点 ∩ challenge_search；C 个性化条目免关键词直入（personalized 标注）
  4. 潜力分 = 0.4×热度 + 0.3×垂直匹配 + 0.2×竞争度(反向) + 0.1×互动
  5. 低粉爆款代理榜: rising 板证据条目按 0.5×heat+0.5×comp 排序（独立展示维度，不改潜力分）
  6. 无命中 → 诚实输出「今日无方向命中」
  7. 系列权重缩放（2026-08-29 video-analytics 反哺接线）: 话题词按 series_keywords
     归属到内容系列后乘 weights（多系列命中取命中词最多者，并列取低权重=歧义不加成）；
     无 weights 块或无命中系列时权重 1.0，行为与旧版一致。

评分口径: 缺失字段记中性 50（不奖不罚）; 两系列内部各自排序（跨系列不可比，成功指标不同）。
B/C 与 A 源热度值量级不同 → 一律系列内归一化（合并池统一 max），跨源不直比。
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


_BOARD_PRIORITY = {"main": 0, "rising": 1, "foryou": 2}
_SOURCE_TAG = {"a": "A热榜", "trend": "B指数", "foryou": "C垂类"}


def _normalize_item(item: dict) -> dict:
    """统一条目形状：补 boards/sources/personalized 缺省（A 源旧条目兼容）。"""
    base = dict(item)
    base.setdefault("boards", [base.get("sub_board")] if base.get("sub_board") else [])
    base.setdefault("sources", [base.get("source") or "a"])
    base.setdefault("personalized", False)
    base.setdefault("group_id", None)
    return base


def merge_pools(a_items: list[dict], trend: dict | None) -> list[dict]:
    """三源按 word 归一合并。

    A 基础记录优先（有 group_id）；hot_value 取最大；view/video/discuss 取第一个非空；
    boards/sources 取并集；sub_board 按 main > rising > foryou 取代表值。
    trend 为空/None 时退化为 A 源按 word 去重（主榜优先），行为与旧版一致。
    """
    merged: dict[str, dict] = {}

    def _merge_into(slot: dict, item: dict) -> None:
        for field in ("group_id", "view_count", "video_count",
                      "discuss_video_count", "word_cover", "hot_value_display"):
            if slot.get(field) is None and item.get(field) is not None:
                slot[field] = item.get(field)
        slot["sources"] = sorted(set(slot.get("sources", [])) | {item.get("source", "a")})
        slot["boards"] = sorted(
            set(slot.get("boards", [])) | set(item.get("boards", [])),
            key=lambda b: _BOARD_PRIORITY.get(b, 9),
        )
        if item.get("hot_value") is not None:
            slot["hot_value"] = max(float(slot.get("hot_value") or 0),
                                    float(item["hot_value"]))
        slot["personalized"] = bool(slot.get("personalized")) or bool(item.get("personalized"))

    for raw in a_items:
        item = _normalize_item(raw)
        slot = merged.setdefault(item["word"], item)
        if slot is not item:
            _merge_into(slot, item)
    for raw in (trend or {}).get("main", []) + (trend or {}).get("rising", []) \
            + (trend or {}).get("foryou", []):
        item = _normalize_item(raw)
        slot = merged.setdefault(item["word"], item)
        if slot is not item:
            _merge_into(slot, item)

    pool = list(merged.values())
    for slot in pool:
        boards = slot.get("boards") or []
        slot["sub_board"] = boards[0] if boards else slot.get("sub_board")
    return pool


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
    """从 fetch 汇总构建双系列 + 低粉代理榜。weights/series_keywords 为可选系列反哺配置。"""
    trend = summary.get("trend")
    weights = weights or {}
    series_keywords = series_keywords or {}

    def _score(it: dict, heat_max: float, kws: list[str]) -> dict:
        matched = match_keywords(it["word"], kws)
        weight, hit_series = series_weight(it["word"], weights, series_keywords)
        return score_item(it, heat_max, matched, weight, hit_series)

    pool = merge_pools(summary.get("a") or [], trend)
    main_pool = [i for i in pool if "main" in (i.get("boards") or [])]
    growth_pool = [
        i for i in pool
        if "rising" in (i.get("boards") or []) or i.get("personalized")
    ]
    hot_max = max([_heat_value(i) for i in main_pool] or [0])
    growth_max = max([_heat_value(i) for i in growth_pool] or [0])

    # 🔥 热度系列: A 主榜 + B 实时热点 ∩ 方向关键词
    hot_scored = sorted(
        (
            _score(it, hot_max, hot_kws)
            for it in main_pool if match_keywords(it["word"], hot_kws)
        ),
        key=lambda x: x["score"], reverse=True,
    )

    # 📈 涨粉系列: A 上升榜 + B 飙升热点 ∩ 方向搜索词; C 个性化垂类免关键词直入
    growth_scored = sorted(
        (
            _score(it, growth_max, growth_kws)
            for it in growth_pool
            if it.get("personalized") or match_keywords(it["word"], growth_kws)
        ),
        key=lambda x: x["score"], reverse=True,
    )

    # 💥 低粉爆款代理榜: rising 板证据条目按 0.5×heat+0.5×comp 排序（独立展示，不改潜力分）
    lowfan_scored = sorted(
        (
            {**it, "lowfan": round(0.5 * float(it.get("heat") or 0)
                                   + 0.5 * float(it.get("comp") or 0), 1)}
            for it in growth_scored if "rising" in (it.get("boards") or [])
        ),
        key=lambda x: x["lowfan"], reverse=True,
    )

    return {
        "date": summary.get("fetched_at", ""),
        "max_heat": round(hot_max),
        "source_stats": {
            "a_total": len(summary.get("a") or []),
            "trend_main": len((trend or {}).get("main", [])),
            "trend_rising": len((trend or {}).get("rising", [])),
            "foryou": len((trend or {}).get("foryou", [])),
            "merged_total": len(pool),
        },
        "series": {
            "hot": hot_scored,
            "growth": growth_scored,
            "lowfan": lowfan_scored[:8],
        },
        "no_hit": {
            "hot": len(hot_scored) == 0,
            "hot_tried_keywords": hot_kws,
            "growth": len(growth_scored) == 0,
            "growth_tried_keywords": growth_kws,
        },
        "notes": list(summary.get("notes", [])) + list((trend or {}).get("notes", [])),
    }


def _weight_tag(item: dict) -> str:
    """权重标记：≠1.0 时在分数后追加 ×权重（含命中系列）。"""
    w = item.get("weight", 1.0) or 1.0
    if w == 1.0:
        return ""
    series = "/".join(item.get("matched_series") or [])
    return f"(×{w:g} {series})" if series else f"(×{w:g})"


def _source_tags(item: dict) -> str:
    """来源标注：A热榜/B指数/C垂类，多源合并以 + 连接。"""
    return "+".join(_SOURCE_TAG.get(s, s) for s in (item.get("sources") or ["a"]))


def _video_ref(item: dict) -> str:
    """代表视频引用：有 group_id 给直达链接，否则给作品搜索定位提示。"""
    if item.get("group_id"):
        return f"https://www.douyin.com/video/{item['group_id']}"
    return f"待定位 → make topic-works keywords=\"{item['word']}\""


def render_markdown(topics: dict) -> str:
    """可读的 markdown 选题清单。"""
    stats = topics.get("source_stats") or {}
    lines: list[str] = []
    lines.append("━━━ 抖音选题建议 ━━━")
    lines.append(
        f"数据时间: {topics.get('date')} | 热榜最大热度: {topics.get('max_heat')}"
        + (f" | 源: A热榜{stats.get('a_total', 0)}条 B指数{stats.get('trend_main', 0)}+{stats.get('trend_rising', 0)}条 C垂类{stats.get('foryou', 0)}条 合并{stats.get('merged_total', 0)}条"
           if stats else "")
    )

    hot = topics["series"]["hot"]
    lines.append("\n## 🔥 热度系列（A主榜+B实时热点 ∩ 方向，求播放）")
    if not hot:
        lines.append("- 今日无方向命中（已尝试关键词: " + "、".join(topics["no_hit"]["hot_tried_keywords"][:8]) + "）")
    for item in hot[:12]:
        heat = item.get("hot_value_display") or item.get("view_count") or item.get("hot_value") or "-"
        wtag = _weight_tag(item)
        lines.append(
            f"- [{item['score']}]{wtag} {item['word']} | 热度 {heat} | {_source_tags(item)} | 命中 {','.join(item['matched_keywords'][:2])}\n"
            f"    📼 {_video_ref(item)}"
        )

    growth = topics["series"]["growth"]
    lines.append("\n## 📈 涨粉系列（A上升榜+B飙升热点+C垂类，求关注转化）")
    if not growth:
        lines.append("- 涨粉池无命中（已尝试关键词: " + "、".join(topics["no_hit"]["growth_tried_keywords"][:8]) + "）")
    for item in growth[:12]:
        heat = item.get("hot_value_display") or item.get("hot_value") or "-"
        wtag = _weight_tag(item)
        ptag = " | 个性化直入" if item.get("personalized") else ""
        matched = ",".join(item["matched_keywords"][:2]) or "-"
        lines.append(
            f"- [{item['score']}]{wtag} {item['word']} | 热度 {heat} | {_source_tags(item)}{ptag} | 命中 {matched}\n"
            f"    📼 {_video_ref(item)}"
        )

    lowfan = topics["series"].get("lowfan") or []
    if lowfan:
        lines.append("\n## 💥 低粉爆款代理榜（飙升证据 × 低竞争，小号吃流量的机会）")
        lines.append("- 口径: 代理信号（官方低粉爆款榜已随巨量算数升级下线），lowfan = 0.5×热度 + 0.5×低竞争")
        for item in lowfan:
            heat = item.get("hot_value_display") or item.get("hot_value") or "-"
            ptag = " | 个性化直入" if item.get("personalized") else ""
            lines.append(
                f"- [{item['lowfan']}] {item['word']} | 热度 {heat} | {_source_tags(item)}{ptag}\n"
                f"    📼 {_video_ref(item)}"
            )

    if topics.get("notes"):
        lines.append("\n## ⚠️ 备注")
        for note in topics["notes"]:
            lines.append(f"- {note}")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="方向过滤 + 双系列评分 + 低粉代理榜")
    parser.add_argument("--in", dest="in_file", required=True, help="fetch_sources 输出 JSON")
    parser.add_argument("--trend", dest="trend_file", default=None,
                        help="fetch_trend 输出 JSON（B 指数双板 + C 垂类，可选）")
    parser.add_argument("--out", default=None, help="选题清单 JSON 输出路径")
    parser.add_argument("--keywords-file", default=None, help="方向关键词 JSON")
    parser.add_argument("--markdown", default=None, help="同时输出可读 markdown 到该路径")
    args = parser.parse_args()

    summary = json.loads(Path(args.in_file).read_text(encoding="utf-8"))
    if args.trend_file and Path(args.trend_file).exists():
        summary["trend"] = json.loads(Path(args.trend_file).read_text(encoding="utf-8"))
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
    if topics["no_hit"].get("growth"):
        print("⚠️ 涨粉系列今日无命中（上升/飙升/垂类均空）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
