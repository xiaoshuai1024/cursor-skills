#!/usr/bin/env python3
"""Verify rendered Excalidraw SVG alignment: container-bound text centers
should match their container centers.

Parses the exported SVG: shapes are <g> without <text> (rotate rx/ry = half
size), texts are <g> with <text>. ExportToSvg renders single-line text with
text-anchor="middle" (text.x = w/2) and multi-line text with text-anchor=
"start" (text.x = 0); in both cases the text group's visual center equals
translate + (rx, ry) because rx/ry = measured width/height divided by 2.

Pass --scene <file.excalidraw> to skip free-floating texts (containerId null):
SVG text groups are emitted in the same order as elements in the scene JSON,
so the two lists are matched positionally. Exit 0 = all within tolerance.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def parse(svg: str) -> tuple[list[dict], list[dict]]:
    """Return (shapes, texts). Each: {x, y, rx, ry, content}."""
    svg2 = re.sub(r"<style.*?</style>", "<style/>", svg, flags=re.DOTALL)
    shapes, texts = [], []
    for m in re.finditer(
        r'<g[^>]*transform="translate\(([\d.-]+) ([\d.-]+)\) rotate\(0 ([\d.-]+) ([\d.-]+)\)"[^>]*>(.*?)</g>',
        svg2, re.DOTALL,
    ):
        tx, ty, rx, ry = map(float, m.groups()[:4])
        inner = m.group(5)
        t = re.search(r'<text[^>]*x="([\d.-]+)"[^>]*>(.*?)</text>', inner, re.DOTALL)
        if t:
            xa = float(t.group(1))
            content = re.sub(r"<[^>]+>", "", t.group(2))[:20]
            texts.append({"x": tx, "y": ty, "rx": rx, "ry": ry, "xa": xa, "content": content})
        else:
            shapes.append({"x": tx, "y": ty, "rx": rx, "ry": ry})
    return shapes, texts


def scene_bound_text_ids(scene_path: Path) -> list[str] | None:
    """Return ids of container-bound texts in scene order, or None if unreadable."""
    try:
        data = json.loads(scene_path.read_text(encoding="utf-8"))
        ids = []
        for el in data.get("elements", []):
            if isinstance(el, dict) and el.get("type") == "text":
                ids.append(el.get("id") if el.get("containerId") else None)
        return ids
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify text alignment in rendered Excalidraw SVG")
    ap.add_argument("input", type=Path, help="Path to rendered .svg file")
    ap.add_argument("--scene", type=Path, default=None,
                    help="Source .excalidraw JSON to skip free-floating texts")
    ap.add_argument("--tol", type=float, default=4.0, help="Max center deviation in px (default 4)")
    args = ap.parse_args()

    svg = args.input.read_text(encoding="utf-8")
    shapes, texts = parse(svg)
    if not shapes or not texts:
        print(f"❌ {args.input.name}: 未解析到形状/文本（{len(shapes)}形状 {len(texts)}文本）")
        return 2

    # Positional matching against the scene: SVG text groups come out in the
    # same order as scene text elements. Filter to container-bound ones.
    bound_ids = scene_bound_text_ids(args.scene) if args.scene else None
    if bound_ids is not None and len(bound_ids) != len(texts):
        print(
            f"⚠️ {args.input.name}: scene 文本数 {len(bound_ids)} ≠ SVG 文本数 {len(texts)}，"
            "跳过过滤（可能渲染顺序不一致）",
            file=sys.stderr,
        )
        bound_ids = None
    check = []
    for i, t in enumerate(texts):
        if bound_ids is not None and bound_ids[i] is None:
            continue  # free-floating text, not expected to align to a shape
        check.append(t)

    bad = []
    for t in check:
        # Visual center: translate + rotate half size (rx/ry) covers both
        # single-line (text-anchor=middle) and multi-line (text-anchor=start).
        cx, cy = t["x"] + t["rx"], t["y"] + t["ry"]
        best = min(shapes, key=lambda s: (s["x"] + s["rx"] - cx) ** 2 + (s["y"] + s["ry"] - cy) ** 2)
        sx, sy = best["x"] + best["rx"], best["y"] + best["ry"]
        dx, dy = cx - sx, cy - sy
        if abs(dx) > args.tol or abs(dy) > args.tol:
            bad.append((t["content"], dx, dy, cx, cy, sx, sy))

    if not bad:
        print(f"✅ {args.input.name}: {len(check)} 个容器文本全部对齐（容差 {args.tol}px）")
        return 0
    for content, dx, dy, cx, cy, sx, sy in bad:
        print(
            f"❌ 文本 {content!r}: 偏差 dx={dx:.1f} dy={dy:.1f}px "
            f"(文本中心 {cx:.0f},{cy:.0f} vs 容器中心 {sx:.0f},{sy:.0f})"
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
