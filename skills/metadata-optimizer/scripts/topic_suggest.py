#!/usr/bin/env python3
"""话题配比推荐:大词 + 长尾 → 3-5 个话题建议(完全本地,无外部查询)。

公式: 1 大词 + 2 长尾(核心) + 最多 2 长尾(补位),总数 3-5。
- 大词: 方向词表(douyin-topic/topic_keywords.json hot_list_match)命中的核心实体
- 长尾: 实体词 × 场景后缀(教程/配置/实测/避坑…),「动词+场景+问题」型

长尾后缀词表与 blog-src scripts/pub/metadata_lint.py 的 LONGTAIL_MARKERS 同步(改则两处)。

用法:
    python topic_suggest.py --slug <slug>          # 读 build/<slug>/metadata.txt 取主题
    python topic_suggest.py --theme "Codex 自动剪辑"
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

KEYWORDS_PATH = Path(__file__).resolve().parent.parent.parent / "douyin-topic" / "topic_keywords.json"
BLOG_ROOT = Path("D:/codes/blog-src")

# 长尾场景后缀(与 blog-src scripts/pub/metadata_lint.py LONGTAIL_MARKERS 同步)
LONGTAIL_SUFFIXES = ("教程", "配置", "实测", "避坑", "排坑", "对比", "源码", "上手",
                     "实战", "入门", "拆解", "攻略")
BIG_FALLBACK = ("AI编程", "程序员", "大模型")   # 方向词表读不到时的兜底大词


def load_keywords() -> list[str]:
    """方向词表(大词判定用,取高频方向词)。"""
    try:
        data = json.loads(KEYWORDS_PATH.read_text(encoding="utf-8"))
        kws = data.get("challenge_search") or []
        return [k for k in kws if isinstance(k, str)]
    except (OSError, json.JSONDecodeError):
        return ["AI编程", "Claude Code", "大模型"]


# ---------- 主题提取 ----------

def theme_from_slug(slug: str) -> tuple[str, list[str]]:
    """从 build/<slug>/metadata.txt 提取 (主题词串, 实体词列表)。"""
    meta = BLOG_ROOT / "video-generation" / "build" / slug / "metadata.txt"
    if not meta.is_file():
        sys.exit(f"❌ 找不到 {meta}(用 --theme 直接给主题词)")
    title = tags = ""
    for ln in meta.read_text(encoding="utf-8").splitlines():
        if ln.startswith("标题:") and not title:
            title = ln.split(":", 1)[1].strip()
        elif ln.startswith("标签:") and not tags:
            tags = ln.split(":", 1)[1].strip()
    words = [t.strip() for t in tags.split(",") if t.strip()] or title.split()
    return f"{title} {tags}", words


# ---------- 推荐 ----------

def recommend(theme: str, entities: list[str]) -> list[dict]:
    """按 1 大词 + 2 长尾(核心) + 最多 2 长尾(补位)组候选,每组标来源依据。"""
    recs: list[dict] = []

    # 大词: 实体词里最泛的 / 方向词表命中的
    kws = load_keywords()
    big_pool = [w for w in entities if any(w in k or k in w for k in kws)]
    if big_pool:
        big, big_basis = big_pool[0], "方向词表命中,泛流量入口"
    elif entities:
        big, big_basis = entities[0], "核心实体,泛流量入口"
    else:
        big, big_basis = BIG_FALLBACK[0], "兜底大词(未提取到实体)"
    recs.append({"tag": big, "group": "大词", "basis": big_basis})

    # 长尾: 实体 × 场景后缀轮转(外层后缀内层实体,保证实体多样性);
    # 前 2 个是核心位,再多最多补 2 位到总数 5
    pool = entities[:3] or list(BIG_FALLBACK[:1])
    for suf in LONGTAIL_SUFFIXES:
        for ent in pool:
            if len(recs) >= 5:
                break
            cand = f"{ent}{suf}"
            if not any(r["tag"] == cand for r in recs):
                slot = "核心" if len(recs) <= 2 else "补位"
                recs.append({"tag": cand, "group": "长尾",
                             "basis": f"「{ent}×{suf}」组合,精准流量池({slot})"})
        if len(recs) >= 5:
            break
    return recs[:5]


def main() -> int:
    ap = argparse.ArgumentParser(description="话题配比推荐(1 大词+2 长尾核心+最多 2 长尾补位)")
    ap.add_argument("--slug", help="读 build/<slug>/metadata.txt 取主题")
    ap.add_argument("--theme", help="直接给主题词串(与 --slug 二选一)")
    ap.add_argument("--entities", default=None, help="逗号分隔实体词(缺省从主题提取)")
    args = ap.parse_args()

    if not args.slug and not args.theme:
        ap.error("--slug 与 --theme 至少一个")
    if args.slug:
        theme, entities = theme_from_slug(args.slug)
    else:
        theme = args.theme
        entities = [t.strip() for t in (args.entities or theme).split(",") if t.strip()]

    print(f"▶ 主题: {theme}")
    print(f"▶ 实体词: {', '.join(entities) or '(未提取到)'}")

    recs = recommend(theme, entities)
    print(f"\n推荐话题({len(recs)} 个,写入 metadata.txt 的话题: 字段前人工确认):")
    for r in recs:
        print(f"  [{r['group']}] #{r['tag']}  ← {r['basis']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
