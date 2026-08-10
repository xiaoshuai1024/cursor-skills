# -*- coding: utf-8 -*-
"""InfoQ 源（tech-topic 多源）—— RSS /feed（近期 + 合规）。

  InfoQ 的 getList 接口 id/type 语义不透明（id=1 返回 2023 老文、高 id 返回空），
  拿不到「近期 + 浏览量」。改用 RSS /feed 取近期文章（title/url/pubDate），
  方向靠关键词（RSS 无 topic 标签），浏览量置 0（无互动信号 → 热度视角不计，仅作近期信号）。

用法: py -m fetch_infoq --out .tech-topic/latest_infoq.json [--limit 15]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

FEED = "https://www.infoq.cn/feed"
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


def _kw_direction(title: str) -> tuple[str | None, list[str]]:
    try:
        kw = {d: w for d, w in json.loads((SCRIPTS_DIR.parent / "topic_keywords.json").read_text(encoding="utf-8")).items() if isinstance(w, list)}
    except Exception:
        kw = {}
    t = title.lower()
    hit, direction = [], None
    for d, words in kw.items():
        for w in words:
            if len(w) >= 2 and w.lower() in t:
                if w not in hit:
                    hit.append(w)
                if direction is None:
                    direction = d
    return direction, hit


def fetch(limit: int = 15) -> list[dict[str, Any]]:
    try:
        req = urllib.request.Request(FEED, headers={"User-Agent": UA})
        xml = urllib.request.urlopen(req, timeout=15).read().decode("utf-8")
    except Exception as exc:
        print(f"⚠️ InfoQ RSS 失败: {exc}")
        return []
    root = ET.fromstring(xml)
    out: list[dict[str, Any]] = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip().split("?")[0]
        if not title or not link:
            continue
        ctime = 0
        pub = item.findtext("pubDate")
        if pub:
            try:
                ctime = int(parsedate_to_datetime(pub).timestamp())
            except Exception:
                pass
        direction, hit = _kw_direction(title)
        out.append({
            "article_id": f"infoq-{link.rsplit('/', 1)[-1][:12]}",
            "title": title,
            "url": link,
            "brief": (item.findtext("description") or "")[:120],
            "digg_count": 0,
            "view_count": 0,
            "collect_count": 0,
            "comment_count": 0,
            "hot_rank": 0,
            "ctime": ctime,
            "rtime": ctime,
            "is_original": 1,
            "author": "InfoQ",
            "tags": hit,
            "direction": direction,
            "source": "infoq",
        })
        if len(out) >= limit:
            break
    print(f"  InfoQ RSS: {len(out)} 篇近期")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="InfoQ RSS 源")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=15)
    args = ap.parse_args()
    _utf8_stdio()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    recs = fetch(limit=args.limit)
    out_path.write_text(json.dumps({"fetched_at": int(time.time()), "source": "infoq", "articles": recs}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ InfoQ: {len(recs)} 篇 → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
