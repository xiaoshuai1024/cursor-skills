#!/usr/bin/env python3
"""Check alignment of container-bound text in an .excalidraw scene.

Excalidraw renders container-bound text (containerId != null) with the text's
x/y as its CENTER anchor (textAlign=center / verticalAlign=middle). If the
scene JSON puts top-left coordinates there, the text lands outside the box.

This script prints every container-bound text whose anchor deviates from the
container center by more than `--tol` px, so you can fix the JSON before
rendering. Exit code 0 = all aligned, 1 = deviations found.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify container-bound text anchors equal container centers"
    )
    parser.add_argument("input", type=Path, help="Path to .excalidraw JSON file")
    parser.add_argument(
        "--tol", type=float, default=0.5,
        help="Tolerance in px for center deviation (default 0.5)",
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"ERROR: input file not found: {args.input}", file=sys.stderr)
        return 2
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: invalid JSON in {args.input}: {e}", file=sys.stderr)
        return 2

    elements = data.get("elements", [])
    by_id = {el.get("id"): el for el in elements if isinstance(el, dict)}

    bad: list[tuple[str, str, float, float]] = []
    for el in elements:
        if not isinstance(el, dict) or el.get("type") != "text":
            continue
        cid = el.get("containerId")
        if not cid or cid not in by_id:
            continue
        container = by_id[cid]
        cx = container.get("x", 0) + abs(container.get("width", 0)) / 2
        cy = container.get("y", 0) + abs(container.get("height", 0)) / 2
        dx = abs(el.get("x", 0) - cx)
        dy = abs(el.get("y", 0) - cy)
        if dx > args.tol or dy > args.tol:
            bad.append((el.get("id", "?"), cid, dx, dy))

    if not bad:
        print(f"✅ {args.input.name}: 所有容器文本锚点已对齐（{len(elements)} 元素）")
        return 0
    for tid, cid, dx, dy in bad:
        print(
            f"❌ text {tid} (container {cid}): 中心偏差 dx={dx:.1f} dy={dy:.1f}px "
            f"— 需设为容器中心 (container.x+w/2, container.y+h/2)"
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
