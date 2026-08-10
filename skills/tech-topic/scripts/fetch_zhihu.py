# -*- coding: utf-8 -*-
"""知乎热榜源（tech-topic 多源，关键词过滤）。

  GET api.zhihu.com/topstory/hot-list → **关键词过滤**（只留技术向）→ 统一 schema（source=zhihu）
  全站热榜是泛话题（新闻/社会），不过滤全是噪音。命中 topic_keywords.json 才留。
  无 ctime（热榜不返回）→ recency 不过滤；热度从 detail_text 拘认。

用法: py -m fetch_zhihu --out .tech-topic/latest_zhihu.json [--limit 50]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

API = "https://api.zhihu.com/topstory/hot-list"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

SCRIPTS_DIR = Path(__file__).resolve().parent


def _utf8_stdio() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass


def _load_keywords() -> dict[str, list[str]]:
    try:
        return {d: w for d, w in json.loads((SCRIPTS_DIR.parent / "topic_keywords.json").read_text(encoding="utf-8")).items() if isinstance(w, list)}
    except Exception:
        return {}


def _match_direction(title: str, kw_map: dict[str, list[str]]) -> tuple[str | None, list[str]]:
    """返回 (方向, 命中关键词)；无命中 → (None, [])，该条目应被过滤掉。"""
    t = title.lower()
    hit: list[str] = []
    direction: str | None = None
    for d, words in kw_map.items():
        for w in words:
            if len(w) >= 2 and w.lower() in t:
                if w not in hit:
                    hit.append(w)
                if direction is None:
                    direction = d
    return direction, hit


def _hot_from_detail(text: str) -> int:
    """'1636 万热度' → 1636（万为单位的热度分）。"""
    m = re.search(r"([\d.]+)\s*万", text or "")
    return int(float(m.group(1))) if m else 0


def fetch(limit: int = 50) -> list[dict[str, Any]]:
    kw_map = _load_keywords()
    url = f"{API}?limit={limit}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        data = json.loads(urllib.request.urlopen(req, timeout=15).read().decode("utf-8"))
    except Exception as exc:
        print(f"⚠️ 知乎请求失败: {exc}")
        return []
    out: list[dict[str, Any]] = []
    dropped = 0
    for it in data.get("data") or []:
        tgt = it.get("target") or {}
        title = (tgt.get("title") or "").strip()
        if not title:
            continue
        direction, hit = _match_direction(title, kw_map)
        if direction is None:
            dropped += 1
            continue  # 非技术向，过滤
        qid = tgt.get("id") or ""
        out.append({
            "article_id": f"zhihu-{qid}",
            "title": title,
            "url": tgt.get("url") or (f"https://www.zhihu.com/question/{qid}" if qid else ""),
            "brief": (tgt.get("excerpt") or "")[:120],
            "digg_count": _hot_from_detail(it.get("detail_text", "")),
            "view_count": 0,
            "collect_count": 0,
            "comment_count": 0,
            "hot_rank": _hot_from_detail(it.get("detail_text", "")),
            "ctime": 0,
            "rtime": 0,
            "is_original": 0,
            "author": "",
            "tags": hit,
            "direction": direction,
            "source": "zhihu",
        })
    print(f"  知乎: 热榜取 {len(out)+dropped} 条，关键词过滤留 {len(out)}（丢 {dropped} 泛新闻/社会）")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="知乎热榜源（关键词过滤）")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=50)
    args = ap.parse_args()
    _utf8_stdio()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    recs = fetch(limit=args.limit)
    out_path.write_text(json.dumps({"fetched_at": int(time.time()), "source": "zhihu", "articles": recs}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 知乎: {len(recs)} 篇 → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
