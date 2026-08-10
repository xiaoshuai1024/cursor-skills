# -*- coding: utf-8 -*-
"""掘金文章拉取（tech-topic skill）。

A 源（匿名，已实测可用 2026-08-08）:
  POST api.juejin.cn/recommend_api/v1/article/recommend_all_feed
  item_type==2 即文章；article_info 含 digg_count/view_count/collect_count/comment_count/
  category_id/ctime/rtime/is_original；tags[].tag_name；author_user_info.user_name。

B 源（搜索，需登录态）:
  匿名返回空 → 需 msedge 弹窗登录后 in-browser fetch（任务 0.7 / 1.6-1.7 实现）。
  当前为 stub，返回空并提示，Phase 1 仅靠 A 源也能跑通。

用法:
  py -m fetch_juejin --out .tech-topic/latest.json [--no-cache] [--pages 2]
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

API_FEED = "https://api.juejin.cn/recommend_api/v1/article/recommend_all_feed"
API_RANK = "https://api.juejin.cn/content_api/v1/content/article_rank"  # 全站热榜
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
CACHE_TTL = 600  # 10 分钟


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


def _post(url: str, payload: dict[str, Any], timeout: int = 15) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": UA},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _parse_article(item_info: dict[str, Any]) -> dict[str, Any] | None:
    """从 item_info 抽取扁平文章记录。字段缺失按可选处理，不崩。"""
    ai = item_info.get("article_info") or {}
    aid = ai.get("article_id")
    if not aid:
        return None
    author = item_info.get("author_user_info") or {}
    tags = [t.get("tag_name") for t in (item_info.get("tags") or []) if t.get("tag_name")]
    return {
        "article_id": aid,
        "title": (ai.get("title") or "").strip(),
        "brief": (ai.get("brief_content") or "").strip(),
        "category_id": ai.get("category_id"),
        "digg_count": ai.get("digg_count") or 0,
        "view_count": ai.get("view_count") or 0,
        "collect_count": ai.get("collect_count") or 0,
        "comment_count": ai.get("comment_count") or 0,
        "ctime": ai.get("ctime") or 0,
        "rtime": ai.get("rtime") or 0,
        "is_original": ai.get("is_original") or 0,
        "author": author.get("user_name") or "",
        "tags": tags,
        "url": f"https://juejin.cn/post/{aid}",
        "source": "A",
    }


def fetch_feed(pages: int = 2) -> list[dict[str, Any]]:
    """A 源：翻页拉近期文章（匿名）。"""
    articles: list[dict[str, Any]] = []
    seen: set[str] = set()
    cursor = "0"
    for page in range(pages):
        payload = {
            "cursor": cursor,
            "id_type": 4,
            "limit": 40,
            "sort_type": 200,  # 综合热门
            "client_type": 2608,
        }
        try:
            data = _post(API_FEED, payload)
        except urllib.error.URLError as exc:
            print(f"⚠️ A 源第 {page + 1} 页请求失败: {exc}")
            break
        if data.get("err_no") != 0:
            print(f"⚠️ A 源 err_no={data.get('err_no')} msg={data.get('err_msg')}")
            break
        items = [it for it in (data.get("data") or []) if it.get("item_type") == 2]
        if not items:
            break
        new_count = 0
        for it in items:
            rec = _parse_article(it.get("item_info") or {})
            if rec and rec["article_id"] not in seen:
                seen.add(rec["article_id"])
                articles.append(rec)
                new_count += 1
        print(f"  A 源第 {page + 1} 页: +{new_count} 篇（累计 {len(articles)}）")
        if new_count == 0:
            break
        # cursor 用末篇 article_id（掘金推荐流游标启发式）；翻不动就停
        cursor = items[-1].get("item_info", {}).get("article_id") or cursor
        time.sleep(1)
    return articles


def fetch_search(keywords: list[str]) -> list[dict[str, Any]]:
    """B 源：登录态搜索（in-browser GET，headless 复用 profile，未登录降级返回空）。"""
    import browser_login
    return browser_login.search(keywords)


def _tech_category_ids() -> set[str]:
    """从 category_map.json 取技术方向 category_id 集合（热榜按此过滤）。"""
    try:
        cm = json.loads((SCRIPTS_DIR.parent / "category_map.json").read_text(encoding="utf-8"))
        return {str(i) for v in cm.values() if isinstance(v, list) for i in v}
    except Exception:
        return set()


def fetch_hot() -> list[dict[str, Any]]:
    """H 源：全站热榜（匿名 GET，category_id=1&type=hot，50 篇当前高互动）。

    只取技术方向（按 category_map 过滤）。互动字段来自 content_counter（view/like/collect/
    comment_count/hot_rank）。注意：热榜无 ctime（juejin 不返回），但热榜本身即「当前热度」。
    """
    import urllib.parse
    params = urllib.parse.urlencode(
        {"category_id": "1", "type": "hot", "aid": "2608", "uuid": "7671511306126149155", "spider": "0"}
    )
    try:
        req = urllib.request.Request(API_RANK + "?" + params, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        print(f"⚠️ H 源热榜请求失败: {exc}")
        return []
    if data.get("err_no") != 0:
        print(f"⚠️ H 源 err_no={data.get('err_no')} {data.get('err_msg')}")
        return []
    tech_ids = _tech_category_ids()
    out: list[dict[str, Any]] = []
    for it in data.get("data") or []:
        c = it.get("content") or {}
        cid = str(c.get("category_id") or "")
        if tech_ids and cid not in tech_ids:
            continue  # 非技术方向（社会/职场等）跳过
        cnt = it.get("content_counter") or {}
        aid = c.get("content_id")
        if not aid:
            continue
        out.append({
            "article_id": str(aid),
            "title": (c.get("title") or "").strip(),
            "brief": (c.get("brief") or "").strip(),
            "category_id": cid,
            "digg_count": cnt.get("like") or 0,
            "view_count": cnt.get("view") or 0,
            "collect_count": cnt.get("collect") or 0,
            "comment_count": cnt.get("comment_count") or 0,
            "hot_rank": cnt.get("hot_rank") or 0,
            "ctime": 0,
            "rtime": 0,
            "is_original": 0,
            "author": (it.get("author") or {}).get("user_name") or "",
            "tags": [],
            "url": f"https://juejin.cn/post/{aid}",
            "source": "H",
        })
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="掘金文章拉取")
    parser.add_argument("--out", required=True, help="输出 latest.json 路径")
    parser.add_argument("--no-cache", action="store_true", help="忽略缓存强制刷新")
    parser.add_argument("--pages", type=int, default=2, help="A 源翻页数")
    parser.add_argument("--no-search", action="store_true", help="跳过 B 源搜索（纯 A 源，快）")
    parser.add_argument("--search-keywords", default=None, help="B 源搜索词（逗号分隔；默认取 topic_keywords.json 每方向前 2 个）")
    args = parser.parse_args()
    _utf8_stdio()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not args.no_cache and out_path.exists():
        age = time.time() - out_path.stat().st_mtime
        if age < CACHE_TTL:
            print(f"⏭ 命中缓存（{int(age)}s < {CACHE_TTL}s），直接用 {out_path}")
            return 0

    articles = fetch_feed(pages=args.pages)
    by_id: dict[str, dict[str, Any]] = {a["article_id"]: a for a in articles}
    b_hits: list[dict[str, Any]] = []

    # H 源：全站热榜（匿名 GET，高互动）—— 与 A 合并，热榜互动量补全
    print("\nH 源：全站热榜（匿名 GET）")
    hot = fetch_hot()
    h_new = 0
    for h in hot:
        aid = h["article_id"]
        if aid in by_id:
            for k in ("digg_count", "view_count", "collect_count", "comment_count"):
                by_id[aid][k] = max(int(by_id[aid].get(k, 0) or 0), int(h.get(k, 0) or 0))
            by_id[aid]["hot_rank"] = h.get("hot_rank", 0)
            by_id[aid]["source"] = (by_id[aid].get("source", "A") + "+H")
        else:
            by_id[aid] = h
            h_new += 1
    print(f"  热榜技术向 {len(hot)} 篇，净增 {h_new}（A+H 共 {len(by_id)}）")

    if not args.no_search:
        if args.search_keywords:
            kws = [k.strip() for k in args.search_keywords.split(",") if k.strip()]
        else:
            try:
                kw_map = json.loads((SCRIPTS_DIR.parent / "topic_keywords.json").read_text(encoding="utf-8"))
                kws = [k for ks in kw_map.values() if isinstance(ks, list) for k in ks[:2]]
            except Exception:
                kws = []
        if kws:
            print(f"\nB 源搜索 {len(kws)} 个关键词: {kws}")
            b_hits = fetch_search(kws)
            a_ids = {a["article_id"] for a in articles}
            for h in b_hits:
                aid = h["article_id"]
                if aid in by_id:
                    mk = by_id[aid].get("matched_keywords") or []
                    by_id[aid]["matched_keywords"] = sorted(set(mk) | set(h.get("matched_keywords", [])))
                    by_id[aid]["source"] = "A+B"
                else:
                    by_id[aid] = h
            new_b = sum(1 for h in b_hits if h["article_id"] not in a_ids)
            print(f"B 源净增 {new_b} 篇（A+B 合并后共 {len(by_id)} 篇）")

    merged = list(by_id.values())
    result = {
        "fetched_at": int(time.time()),
        "source_a_count": len(articles),
        "source_h_count": len(hot),
        "source_b_count": len(b_hits),
        "articles": merged,
    }
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 拉取完成: A {len(articles)} + B {len(b_hits)} → 合并 {len(merged)} 篇 → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
