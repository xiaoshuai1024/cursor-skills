---
name: excalidraw
description: Use when the user wants to create or render hand-drawn style diagrams (flowcharts, architecture diagrams, ER diagrams, sequence diagrams, wireframes) as Excalidraw scenes, and export them to SVG/PNG. Triggers on words like "diagram", "flowchart", "draw", "architecture diagram", "excalidraw", or a request to visualize a system or process.
---

# Excalidraw Diagram Skill

Create Excalidraw scene JSON files and render them to SVG (and optionally PNG)
using the real Excalidraw engine. Output is hand-drawn style, vector, and the
SVG can be dragged back into excalidraw.com for further editing.

## When to use

- User asks for a diagram, flowchart, architecture sketch, ER diagram, or
  sequence diagram in a hand-drawn / sketchy style.
- User says "draw", "visualize", "diagram" and wants an image file out.

## When NOT to use

- The user wants a pixel-perfect / corporate-clean diagram (use a vector tool).
- The user wants to EDIT interactively right now (point them to excalidraw.com).
- The diagram needs automatic layout (this skill does NOT auto-layout; you
  compute coordinates by hand — see Known Limitations).

## How it works (read this once)

1. You write an `.excalidraw` JSON scene file (elements with x/y/size/style).
2. `scripts/render.py` drives headless Chromium, loads the official
   `@excalidraw/excalidraw` package, runs the scene through Excalidraw's
   `restore()` + `convertToExcalidrawElements()` (to normalize fields and
   recompute text metrics), then calls `exportToSvg` — so the render is the
   genuine Excalidraw look, not a reimplementation.
3. It outputs SVG (default) and/or PNG.

## First-time setup

If rendering fails with a playwright/Chromium error, run the installer:

```
bash scripts/install.sh
```

This installs the `playwright` Python package and the Chromium binary
(~150MB, one-time). It does NOT require npm or node — Excalidraw itself is
loaded from the esm.sh CDN at render time (so an internet connection is needed
on render).

## Creating a diagram

1. **Plan the layout.** Decide the shapes and how they connect. Sketch the
   coordinates on paper first — this skill does not auto-layout, so you are
   responsible for non-overlapping positions.

2. **Build the scene JSON.** Use `references/element-templates.md` for
   copy-paste templates of each element type (rectangle, ellipse, diamond,
   arrow, text). Start from `references/examples/flowchart.excalidraw` as a
   working skeleton.

3. **Leave `seed` as `null`.** Do not hardcode seed values. The render script
   injects a random seed per element so identical shapes wobble differently —
   that variation IS the hand-drawn look. Hardcoded seeds make the diagram
   look stamped and dead.

4. **Write the file** with the `.excalidraw` extension, e.g. `login-flow.excalidraw`.

5. **Render it:**

   ```
   python3 scripts/render.py login-flow.excalidraw
   ```

   By default this produces `login-flow.svg` AND `login-flow.png` next to the
   input. Options:
   - `--format svg` or `--format png` to get only one
   - `--output path/stem` to control output location (stem, no extension)
   - `--scale 3` for higher-resolution PNG (SVG is always vector)
   - `--keep-seed` to reproduce a previous render exactly

6. **Open the result** (the SVG is preferred — crisp, editable). If you want
   to revise, edit the `.excalidraw` JSON and re-render. You can also drag the
   SVG back into excalidraw.com to edit interactively.

## Layout tips (since there's no auto-layout)

- Give each shape ~40-80px of padding around it.
- Vertical flowcharts: stack shapes 150px apart vertically.
- Arrows: set `points` relative to the arrow's own `x,y`, and bind both ends
  via `startBinding`/`endBinding` so the arrow tracks the shapes.
- Use free-floating text (containerId null) for titles and section labels
  rather than wrapping everything in boxes.
- See `examples/flowchart.excalidraw` for concrete coordinate values that work.

## Element types at a glance

| Type | Use for |
|------|---------|
| `rectangle` | processes, components, services (rounded via `roundness:{type:3}`) |
| `ellipse` | start/end states, external systems |
| `diamond` | decisions, conditionals |
| `arrow` | directed connections (binds to shapes) |
| `line` | undirected structural lines |
| `text` | labels inside shapes (`containerId`) or free-floating titles |

Full templates + the binding recipe: `references/element-templates.md`.

## Default colors

Unless the user specifies a palette, use Excalidraw defaults:
`#1e1e1e` strokes; fills green `#b2f2bb`, blue `#a5d8ff`, yellow `#ffec99`,
red `#ffc9c9`, purple `#eebefa`. See the palette table in element-templates.md.

## Known limitations (be honest with the user)

- **No auto-layout.** You compute all x/y coordinates. For >10 elements this
  gets tedious; keep diagrams modest or the user should edit in excalidraw.com.
- **Requires network on render** (loads Excalidraw from esm.sh CDN). Offline
  rendering is not supported by this version.
- **No batch rendering.** One file at a time.
- **No built-in overlap detection.** If shapes overlap, the render will show
  it — review the output SVG and adjust coordinates.

## Files

| Path | Purpose |
|------|---------|
| `scripts/render.py` | The renderer (run this) |
| `scripts/render_template.html` | Browser page that loads Excalidraw (don't edit casually) |
| `scripts/install.sh` | One-time dependency installer |
| `references/element-templates.md` | JSON templates for every element type |
| `references/examples/flowchart.excalidraw` | Working example scene |
