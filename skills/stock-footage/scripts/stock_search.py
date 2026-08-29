#!/usr/bin/env python3
"""stock_search — 免费素材源统一检索 CLI（stock-footage skill）。

方法与 16 源适配器搬运自 OpenMontage（github.com/calesthio/OpenMontage, AGPL-3.0）；
stock_sources/ 目录按 AGPL-3.0-only 单独许可（见该目录 LICENSE），本 CLI 为本仓
新写、按仓库 MIT 许可。

三命令：
    python stock_search.py sources                      # 列出全部源与可用状态
    python stock_search.py search "query 词组" [选项]    # 多源并发搜索
    # search 加 --download-dir 即边搜边下载（快路径：每 query 每源取前 N 条）

零强制依赖：免 key 的 JSON API 源（archive_org/wikimedia/nasa/nara/loc/pond5_pd/
coverr）纯 stdlib 即可跑；mixkit/esa/noaa/dareful/jaxa 为页面解析源，需
`pip install requests beautifulsoup4`；pexels/pixabay_video/unsplash/videvo 需在
环境变量配对应 key（PEXELS_API_KEY / PIXABAY_API_KEY / UNSPLASH_ACCESS_KEY /
VIDEOVO_API_KEY / COVERR_API_KEY）。

示例：
    # 列源
    python stock_search.py sources
    # 免 key 源搜卫星发射，横屏 ≥1280，每源前 4 条
    python stock_search.py search "satellite launch night sky" --per-source 4 --min-width 1280 --orientation landscape
    # 年代档案感：只走档案源，单独成批
    python stock_search.py search "1990s computer room vintage" --sources archive_org,wikimedia,loc,nara
    # 搜并下载到 assets/stock/
    python stock_search.py search "rain city neon" --download-dir assets/stock --download-limit 6
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from stock_sources import all_sources, get_source  # noqa: E402
from stock_sources.base import Candidate, SearchFilters  # noqa: E402

# 免 key 的政府/档案源：稳定、缺省优先。年代向（vintage）检索收敛到这一档的档案子集。
ARCHIVE_SOURCES = {"archive_org", "wikimedia", "loc", "nara"}


def _json_safe(c: Candidate) -> dict:
    d = asdict(c)
    d["clip_id"] = c.clip_id
    return d


def cmd_sources(args: argparse.Namespace) -> int:
    rows = []
    for src in sorted(all_sources(), key=lambda s: (getattr(s, "priority", 100), s.name)):
        rows.append({
            "name": src.name,
            "display_name": getattr(src, "display_name", src.name),
            "available": src.is_available(),
            "supports": list(getattr(src, "supports", ["video"]) or ["video"]),
            "install": getattr(src, "install_instructions", "") or "",
        })
    print(json.dumps({
        "available": [r["name"] for r in rows if r["available"]],
        "sources": rows,
    }, ensure_ascii=False, indent=1))
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

    wanted = None
    if args.sources:
        wanted = {s.strip() for s in args.sources.split(",") if s.strip()}
    filters = SearchFilters(
        kind=args.kind,
        min_duration=args.min_duration,
        max_duration=args.max_duration,
        orientation=args.orientation,
        min_width=args.min_width,
        per_page=max(args.per_source * 4, 20),
    )

    results: list[dict] = []
    warnings: list[str] = []
    per_source_counts: dict[str, int] = {}
    skipped: dict[str, str] = {}

    for src in all_sources():
        if wanted is not None and src.name not in wanted:
            continue
        if not src.is_available():
            skipped[src.name] = getattr(src, "install_instructions", "") or "needs key/deps"
            continue
        try:
            cands = src.search(args.query, filters)
        except Exception as exc:  # 单源故障不污染整轮
            warnings.append(f"{src.name}: search failed: {exc}")
            continue
        kept = 0
        for c in cands[: args.per_source]:
            if not (c.source_url and c.license):
                # 溯源三件套缺一不可（license + 素材页；download_url 不算溯源页）
                warnings.append(f"{src.name}: dropped candidate missing provenance: {c.source_id}")
                continue
            results.append(_json_safe(c))
            kept += 1
        per_source_counts[src.name] = kept

    # 下载（快路径：搜索后按序下载前 N 条，缓存语义由调用方目录承担）
    downloaded: list[dict] = []
    if args.download_dir:
        out_dir = Path(args.download_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        budget = args.download_limit
        for c in results:
            if budget <= 0:
                break
            src = get_source(c["source"])
            ext = ".mp4" if c["kind"] == "video" else ".jpg"
            dest = out_dir / f"{c['clip_id']}{ext}"
            try:
                src.download(Candidate(**{k: v for k, v in c.items() if k != "clip_id"}), dest)
                c["local_path"] = str(dest)
                downloaded.append(c["clip_id"])
                budget -= 1
            except Exception as exc:
                warnings.append(f"{c['clip_id']}: download failed: {exc}")

    payload = {
        "query": args.query,
        "filters": {
            "kind": args.kind,
            "orientation": args.orientation,
            "min_width": args.min_width,
            "min_duration": args.min_duration,
            "max_duration": args.max_duration,
        },
        "per_source": per_source_counts,
        "total": len(results),
        "skipped_sources": skipped,
        "downloaded": downloaded,
        "warnings": warnings,
        "results": results,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=1)
    if args.json:
        Path(args.json).write_text(text, encoding="utf-8")
        print(f"wrote {args.json} ({len(results)} candidates)", file=sys.stderr)
    else:
        print(text)
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="免费素材源统一检索（stock-footage）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("sources", help="列出全部源与可用状态").set_defaults(func=cmd_sources)

    s = sub.add_parser("search", help="多源并发搜索")
    s.add_argument("query", help="检索词组：具体名词+视觉特征，如 'rain city neon night'")
    s.add_argument("--sources", help="逗号分隔源名单；缺省=全部可用源。vintage 向建议 archive_org,wikimedia,loc,nara")
    s.add_argument("--kind", choices=["video", "image", "any"], default="video")
    s.add_argument("--orientation", choices=["landscape", "portrait", "square"])
    s.add_argument("--min-width", type=int)
    s.add_argument("--min-duration", type=float)
    s.add_argument("--max-duration", type=float)
    s.add_argument("--per-source", type=int, default=4, help="每源保留条数（缺省 4；经验值 4-8）")
    s.add_argument("--download-dir", help="设置则按序下载到该目录")
    s.add_argument("--download-limit", type=int, default=6, help="下载总条数上限（缺省 6）")
    s.add_argument("--json", help="结果写文件（utf-8）而非 stdout")
    s.set_defaults(func=cmd_search)

    args = ap.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
