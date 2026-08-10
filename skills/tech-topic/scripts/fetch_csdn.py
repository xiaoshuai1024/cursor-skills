# -*- coding: utf-8 -*-
"""CSDN 热榜源（tech-topic 多源）。

  GET blog.csdn.net/phoenix/web/blog/hot-rank?type=24h → 统一 schema（source=csdn）
  纯技术社区；无显式分类，direction 由标题关键词命中（topic_keywords.json）。
  无 ctime（hot-rank 不返回发布时间）→ recency 不过滤（同掘金 H 源）。

用法: py -m fetch_csdn --out .tech-topic/latest_csdn.json [--type 24h]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

API = "https://blog.csdn.net/phoenix/web/blog/hot-rank"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def _utf8_stdio() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass


def project_root() -> Path:
    cur = Path(__file__).resolve()
    for p in cur.parents:
        if (p / "hugo.toml").exists() or (p / ".git").exists():
            return p
    return cur.parents[-1]


SCRIPTS_DIR = Path(__file__).resolve().parent


def _kw_direction(title: str) -> str | None:
    """标题命中 topic_keywords.json 的方向（前端/后端/人工智能）。"""
    try:
        kw = json.loads((SCRIPTS_DIR.parent / "topic_keywords.json").read_text(encoding="utf-8"))
    except Exception:
        return None
    t = title.lower()
    for direction, words in kw.items():
        if not isinstance(words, list):
            continue
        if any(w.lower() in t for w in words if len(w) >= 2):
            return direction
    return None


def fetch(pages: int = 1, rank_type: str = "24h") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for page in range(1, pages + 1):
        url = f"{API}?page={page}&pageSize=50&type={rank_type}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            data = json.loads(urllib.request.urlopen(req, timeout=15).read().decode("utf-8"))
        except Exception as exc:
            print(f"⚠️ CSDN 第 {page} 页失败: {exc}")
            break
        if data.get("code") != 200:
            print(f"⚠️ CSDN code={data.get('code')} {data.get('message')}")
            break
        arr = data.get("data") or []
        if not arr:
            break
        for it in arr:
            title = (it.get("articleTitle") or "").strip()
            if not title:
                continue
            direction = _kw_direction(title)
            if direction is None:
                continue  # CSDN 热榜混个人水文/非方向（如「创作128天纪念」），关键词不命中则过滤
            out.append({
                "article_id": f"csdn-{it.get('userName')}-{title[:12]}",
                "title": title,
                "url": it.get("articleDetailUrl") or "",
                "brief": (it.get("hotComment") or "")[:120],
                "digg_count": int(it.get("hotRankScore") or 0),
                "view_count": int(it.get("viewCount") or 0),
                "collect_count": int(it.get("favorCount") or 0),
                "comment_count": int(it.get("commentCount") or 0),
                "hot_rank": int(it.get("hotRankScore") or 0),
                "ctime": 0,
                "rtime": 0,
                "is_original": 0,
                "author": it.get("nickName") or "",
                "tags": [],
                "direction": direction,
                "source": "csdn",
            })
        print(f"  CSDN 第 {page} 页: +{len(arr)}（累计 {len(out)}）")
        time.sleep(1)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="CSDN 热榜源")
    ap.add_argument("--out", required=True)
    ap.add_argument("--pages", type=int, default=1)
    ap.add_argument("--type", default="24h", help="24h / week")
    args = ap.parse_args()
    _utf8_stdio()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    recs = fetch(pages=args.pages, rank_type=args.type)
    out_path.write_text(json.dumps({"fetched_at": int(time.time()), "source": "csdn", "articles": recs}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ CSDN: {len(recs)} 篇 → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
