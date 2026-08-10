# -*- coding: utf-8 -*-
"""两阶段编排（tech-topic 技术文章选题 skill）。

  phase1  选题（不拉正文）:
    fetch_juejin → filter_score → 对 Top 候选生成假设大纲（--rough）
  phase2  深挖（用户确认对标后）:
    fetch_article（渲染取正文）→ analyze → outline --deep   [任务 4.x，待实现]

用法:
  py -m pipeline phase1 [--top 5] [--no-cache] [--pages 2]
  py -m pipeline phase2 --article-id <id>            [待实现]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def _utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass


def project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "hugo.toml").exists() or (parent / ".git").exists():
            return parent
    return current.parents[-1]


SCRIPTS_DIR = Path(__file__).resolve().parent
OUTPUT_ROOT = project_root() / ".tech-topic"


def _run(*args: str) -> int:
    """跑同目录脚本（继承 PYTHONIOENCODING）。"""
    cmd = [sys.executable, "-m"] + list(args)
    print(f"▶ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(SCRIPTS_DIR))
    return result.returncode


def phase1(top: int = 5, no_cache: bool = False, pages: int = 2, no_search: bool = False) -> int:
    latest = OUTPUT_ROOT / "latest.json"
    topics_json = OUTPUT_ROOT / "topics.json"
    topics_md = OUTPUT_ROOT / "topics.md"
    rough_dir = OUTPUT_ROOT / "rough_outlines"

    # 多源拉取（按 sources.json 启用）→ 合并 latest.json
    try:
        sources_cfg = json.loads((SCRIPTS_DIR.parent / "sources.json").read_text(encoding="utf-8")).get("sources", {})
    except Exception:
        sources_cfg = {}
    src_jobs = [
        ("juejin", ["fetch_juejin", "--out", str(OUTPUT_ROOT / "latest_juejin.json"), "--pages", str(pages),
                    *(["--no-cache"] if no_cache else []), *(["--no-search"] if no_search else [])]),
        ("csdn", ["fetch_csdn", "--out", str(OUTPUT_ROOT / "latest_csdn.json")]),
        ("infoq", ["fetch_infoq", "--out", str(OUTPUT_ROOT / "latest_infoq.json"), "--limit", "15"]),
        ("zhihu", ["fetch_zhihu", "--out", str(OUTPUT_ROOT / "latest_zhihu.json"), "--limit", "50"]),
    ]
    merged: list[dict] = []
    degraded: list[str] = []
    for src, cmd in src_jobs:
        if not sources_cfg.get(src, {}).get("enabled", True):
            continue
        c = _run(*cmd)
        out_file = OUTPUT_ROOT / f"latest_{src}.json"
        if c != 0 or not out_file.exists():
            degraded.append(src)
            continue
        try:
            merged += json.loads(out_file.read_text(encoding="utf-8")).get("articles", []) or []
        except Exception:
            degraded.append(src)
    latest.write_text(json.dumps({"fetched_at": int(time.time()), "articles": merged}, ensure_ascii=False, indent=2), encoding="utf-8")
    if degraded:
        print(f"\n⚠️ 降级源: {degraded}（其余源继续）")
    code = _run("filter_score", "--in", str(latest),
                "--out", str(topics_json), "--markdown", str(topics_md))
    if code != 0:
        return code

    topics = json.loads(topics_json.read_text(encoding="utf-8"))
    if topics.get("no_hit"):
        print("\n⚠️ 近期无方向命中（已尝试关键词/category 见 topics.md）")
        print("   可扩大翻页 --pages 或补充 topic_keywords.json")
        return 0

    candidates = sorted(
        topics["series"]["hot"] + topics["series"]["vertical"],
        key=lambda x: x.get("score") or 0, reverse=True,
    )[:top]
    rough_dir.mkdir(parents=True, exist_ok=True)
    index_lines = ["# Phase 1 假设大纲（未拉正文）\n"]
    seen_ids: set[str] = set()
    for item in candidates:
        aid = item.get("article_id")
        if not aid or aid in seen_ids:
            continue
        seen_ids.add(aid)
        item_path = rough_dir / f"{aid}.json"
        item_path.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
        out_path = item_path.with_name(aid + "_rough.md")
        code = _run("outline", "--rough", str(item_path), "--out", str(out_path))
        if code != 0:
            return code
        view = "🎯" if item.get("in_vertical") else "🔥"
        index_lines.append(f"- {view} [{item['score']}] {item['title'][:40]} → {out_path.name}")
    (rough_dir / "INDEX.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")

    print(f"\n✅ Phase 1 完成")
    print(f"   选题清单: {topics_md}")
    print(f"   假设大纲: {rough_dir}/INDEX.md  (共 {len(seen_ids)} 条)")
    print("   确定对标 → make tech-topic-deep id=<article_id>")
    return 0


def phase2(article_id: str, skip_fetch: bool = False) -> int:
    art_dir = OUTPUT_ROOT / "articles" / article_id
    if not skip_fetch:
        code = _run("fetch_article", "--article-id", article_id, "--out-dir", str(art_dir))
        if code != 0:
            return code
    elif not (art_dir / "meta.json").exists():
        print(f"❌ --skip-fetch 但 {art_dir / 'meta.json'} 不存在")
        return 1
    code = _run("analyze", "--dir", str(art_dir))
    if code != 0:
        return code
    print(f"\n✅ Phase 2 完成（原文保存 + 结构分析）")
    print(f"   原文: {art_dir}/article.html (+ .txt + screenshot.png)")
    print(f"   结构分析: {art_dir}/analysis.md")
    print("   → 拿 analysis.md + 原文，用写博客 skill 仿写（禁止照搬）")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="tech-topic 选题两阶段编排")
    sub = parser.add_subparsers(dest="phase", required=True)

    p1 = sub.add_parser("phase1", help="选题（不拉正文）")
    p1.add_argument("--top", type=int, default=5)
    p1.add_argument("--no-cache", action="store_true")
    p1.add_argument("--pages", type=int, default=2)
    p1.add_argument("--no-search", action="store_true", help="跳过 B 源搜索（纯 A 源）")

    p2 = sub.add_parser("phase2", help="拉原文保存 + 结构分析（不生成仿写）")
    p2.add_argument("--article-id", required=True)
    p2.add_argument("--skip-fetch", action="store_true", help="复用已保存的原文")

    args = parser.parse_args()
    _utf8_stdio()
    if args.phase == "phase1":
        return phase1(args.top, args.no_cache, args.pages, args.no_search)
    return phase2(args.article_id, args.skip_fetch)


if __name__ == "__main__":
    raise SystemExit(main())
