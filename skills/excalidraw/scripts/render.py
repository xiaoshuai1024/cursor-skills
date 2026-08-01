#!/usr/bin/env python3
"""Render an Excalidraw scene JSON file to SVG and/or PNG.

Uses Playwright to drive a headless Chromium that loads the official
@excalidraw/excalidraw package and calls its exportToSvg. This renders with
the real Excalidraw engine, preserving the hand-drawn aesthetic exactly.

Two things this script does that matter for visual quality:
  1. Injects a random `seed` into every element that lacks one. Excalidraw's
     hand-drawn jitter is deterministic per seed; templates that hardcode a
     seed make every identical shape wobble identically (visually dead). A
     random seed restores the natural variation.
  2. Exports SVG (default) in addition to optional PNG. The SVG is vector,
     stays crisp at any zoom, and can be dragged back into excalidraw.com.

Usage:
    python3 render.py <input.excalidraw> [--format svg|png|both] [--output PATH] [--scale N] [--keep-seed]

Setup (first time only):
    bash scripts/install.sh
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

# This script lives in skills/excalidraw/scripts/. The template is a sibling.
TEMPLATE_PATH = Path(__file__).resolve().parent / "render_template.html"


def die(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def load_scene(path: Path) -> dict:
    """Read and structurally validate an .excalidraw file."""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as e:
        die(f"cannot read {path}: {e}")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        die(f"invalid JSON in {path}: {e}")
    if not isinstance(data, dict):
        die(f"top-level JSON must be an object, got {type(data).__name__}")
    if "elements" not in data:
        die(f"missing 'elements' array in {path}")
    if not isinstance(data["elements"], list):
        die(f"'elements' must be an array, got {type(data['elements']).__name__}")
    if len(data["elements"]) == 0:
        die(f"'elements' is empty — nothing to render")
    return data


def inject_seeds(data: dict, keep_existing: bool) -> dict:
    """Give every element a random integer seed (Excalidraw jitter source).

    With --keep-seed, elements that already have an integer seed are left
    alone (useful for reproducing a previous render). Otherwise all seeds
    are randomized so identical shapes wobble differently.
    """
    rng = random.Random()
    for el in data["elements"]:
        if not isinstance(el, dict):
            continue
        existing = el.get("seed")
        if keep_existing and isinstance(existing, int):
            continue
        el["seed"] = rng.randint(1, 2_000_000_000)
        # versionNonce is also part of Excalidraw's identity; give it a
        # random value too so elements don't collide.
        el["versionNonce"] = rng.randint(1, 2_000_000_000)
    return data


def compute_viewport(elements: list, max_width: int = 1920) -> dict:
    """Compute a viewport large enough to contain all elements + padding."""
    min_x = min_y = float("inf")
    max_x = max_y = float("-inf")
    for el in elements:
        if not isinstance(el, dict) or el.get("isDeleted"):
            continue
        x = el.get("x", 0)
        y = el.get("y", 0)
        w = el.get("width", 0)
        h = el.get("height", 0)
        # Arrows/lines define shape via a points array relative to x,y.
        if el.get("type") in ("arrow", "line") and isinstance(el.get("points"), list):
            for pt in el["points"]:
                if isinstance(pt, list) and len(pt) == 2:
                    min_x = min(min_x, x + pt[0])
                    min_y = min(min_y, y + pt[1])
                    max_x = max(max_x, x + pt[0])
                    max_y = max(max_y, y + pt[1])
        else:
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x + abs(w))
            max_y = max(max_y, y + abs(h))
    if min_x == float("inf"):
        return {"width": 800, "height": 600}
    pad = 80
    width = min(int(max_x - min_x + pad * 2), max_width)
    height = max(int(max_y - min_y + pad * 2), 400)
    return {"width": width, "height": height}


def render(
    data: dict,
    output_stem: Path,
    fmt: str,
    scale: int,
) -> list[str]:
    """Render scene to the requested format(s). Returns list of written paths."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        die(
            "playwright is not installed. Run:\n"
            "    bash " + str(Path(__file__).resolve().parent / "install.sh"),
            code=2,
        )

    viewport = compute_viewport(data["elements"])
    template_url = TEMPLATE_PATH.as_uri()

    written = []
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as e:
            msg = str(e)
            if "Executable doesn't exist" in msg or "browserType.launch" in msg:
                die(
                    "Chromium is not installed for Playwright. Run:\n"
                    "    bash " + str(Path(__file__).resolve().parent / "install.sh"),
                    code=2,
                )
            raise

        page = browser.new_page(
            viewport=viewport,
            device_scale_factor=scale,
        )
        try:
            # Load the template (local file URL). It kicks off the Excalidraw
            # module import and exposes window.__excalReady as a Promise.
            page.goto(template_url)

            # Wait until the module import has resolved OR failed. The template
            # sets window.__excalDone (a plain boolean) only AFTER the dynamic
            # import finishes — so polling this flag cannot race, and
            # wait_for_function (which does not support `await`) works.
            try:
                page.wait_for_function(
                    "window.__excalDone === true",
                    timeout=120000,
                )
            except Exception:
                die(
                    "timed out loading Excalidraw module from CDN. "
                    "Check network access to esm.sh.",
                    code=3,
                )
            err = page.evaluate("window.__excalError || null")
            if err:
                die(
                    f"failed to load Excalidraw module from CDN: {err}. "
                    "Check network access to esm.sh.",
                    code=3,
                )

            # Pass the whole scene to renderDiagram; the template runs it
            # through Excalidraw's restore() (fills required fields) and calls
            # exportToSvg with the object form.
            scene = {
                "type": data.get("type", "excalidraw"),
                "version": data.get("version", 2),
                "elements": data["elements"],
                "appState": data.get("appState", {}),
                "files": data.get("files", {}),
            }
            result = page.evaluate(
                "(scene) => window.renderDiagram(scene)",
                scene,
            )

            if not result or not result.get("success"):
                err = result.get("error", "unknown") if result else "renderDiagram returned null"
                die(f"render failed: {err}")

            # --- SVG output (always produce if requested; it is the source) ---
            if fmt in ("svg", "both"):
                svg_str = page.evaluate("window.__lastSvg")
                if not svg_str:
                    die("render produced no SVG (window.__lastSvg empty)")
                svg_path = output_stem.with_suffix(".svg")
                svg_path.write_text(svg_str, encoding="utf-8")
                written.append(str(svg_path))

            # --- PNG output (screenshot the laid-out SVG element) ---
            if fmt in ("png", "both"):
                svg_el = page.query_selector("#root svg")
                if svg_el is None:
                    die("no <svg> element found in #root to screenshot")
                png_path = output_stem.with_suffix(".png")
                svg_el.screenshot(path=str(png_path))
                written.append(str(png_path))
        finally:
            browser.close()

    return written


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render an Excalidraw scene to SVG and/or PNG."
    )
    parser.add_argument("input", type=Path, help="Path to .excalidraw JSON file")
    parser.add_argument(
        "--format", "-f",
        choices=["svg", "png", "both"],
        default="both",
        help="Output format (default: both)",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help="Output path stem (without extension). Default: same name as input.",
    )
    parser.add_argument(
        "--scale", "-s",
        type=int,
        default=2,
        help="PNG device scale factor, 2 = retina (default: 2). SVG is always vector.",
    )
    parser.add_argument(
        "--keep-seed",
        action="store_true",
        help="Keep existing integer seeds; only fill missing ones. "
             "Default: randomize all seeds for natural hand-drawn variation.",
    )
    args = parser.parse_args()

    if not args.input.exists():
        die(f"input file not found: {args.input}")

    data = load_scene(args.input)
    data = inject_seeds(data, keep_existing=args.keep_seed)

    stem = args.output if args.output else args.input.with_suffix("")
    # If user passed a path with an extension, strip it; we add our own.
    if stem.suffix in (".svg", ".png"):
        stem = stem.with_suffix("")

    # Ensure the output directory exists (mkdir -p) before render writes into it.
    if stem.parent and not stem.parent.exists():
        stem.parent.mkdir(parents=True, exist_ok=True)
    written = render(data, stem, args.format, args.scale)
    for path in written:
        print(path)


if __name__ == "__main__":
    main()
