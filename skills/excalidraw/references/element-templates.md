# Element Templates

Copy-paste JSON building blocks for each Excalidraw element type. Use these
when constructing a scene. **Leave `seed` and `versionNonce` as `null`** — the
render script injects random values. Hardcoding them makes every identical
shape wobble identically (Excalidraw's jitter is deterministic per seed).

A complete scene is:

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "https://excalidraw.com",
  "elements": [ /* ...elements below... */ ],
  "appState": { "viewBackgroundColor": "#ffffff" },
  "files": {}
}
```

## Common fields (every element)

| Field | Value | Notes |
|-------|-------|-------|
| `id` | unique string | Stable handle for bindings/labels |
| `x`, `y` | number | Top-left position in pixels |
| `width`, `height` | number | Size |
| `angle` | 0 | Rotation; leave 0 unless rotating |
| `strokeColor` | hex | Border color |
| `backgroundColor` | hex or `"transparent"` | Fill |
| `fillStyle` | `"solid"` | `solid` / `hachure` / `cross-hatch` |
| `strokeWidth` | 1 / 2 / 4 | Border weight |
| `strokeStyle` | `"solid"` | `solid` / `dashed` / `dotted` |
| `roughness` | 1 | 0 = smooth, 1 = default hand-drawn, 2 = rough |
| `opacity` | 100 | 0-100 |
| `seed` | `null` | **Always null** — render.py randomizes it |
| `versionNonce` | `null` | **Always null** — render.py randomizes it |
| `isDeleted` | false | |
| `groupIds` | `[]` | Put element ids here to group |
| `boundElements` | `[]` or list | Arrows/labels bound to this shape |
| `link` | null | |
| `locked` | false | |
| `updated` | 1 | |

## Rectangle (process / component)

```json
{
  "type": "rectangle", "id": "r1",
  "x": 100, "y": 100, "width": 180, "height": 80, "angle": 0,
  "strokeColor": "#1e1e1e", "backgroundColor": "#a5d8ff",
  "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
  "roughness": 1, "opacity": 100, "groupIds": [],
  "roundness": { "type": 3 },
  "seed": null, "version": 1, "versionNonce": null,
  "isDeleted": false, "boundElements": [], "link": null, "locked": false, "updated": 1
}
```

`roundness: {type: 3}` gives rounded corners. Omit `roundness` (set to `null`)
for sharp corners.

## Ellipse (start / end / external system)

```json
{
  "type": "ellipse", "id": "e1",
  "x": 100, "y": 100, "width": 160, "height": 80, "angle": 0,
  "strokeColor": "#1e1e1e", "backgroundColor": "#b2f2bb",
  "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
  "roughness": 1, "opacity": 100, "groupIds": [],
  "roundness": null,
  "seed": null, "version": 1, "versionNonce": null,
  "isDeleted": false, "boundElements": [], "link": null, "locked": false, "updated": 1
}
```

## Diamond (decision)

```json
{
  "type": "diamond", "id": "d1",
  "x": 100, "y": 100, "width": 160, "height": 100, "angle": 0,
  "strokeColor": "#1e1e1e", "backgroundColor": "#ffec99",
  "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
  "roughness": 1, "opacity": 100, "groupIds": [],
  "roundness": null,
  "seed": null, "version": 1, "versionNonce": null,
  "isDeleted": false, "boundElements": [], "link": null, "locked": false, "updated": 1
}
```

## Arrow (connection, with binding)

Connects two shapes. The `points` array is **relative to the element's `x,y`**.
`startBinding`/`endBinding` snap the arrow to shapes so it tracks them.

```json
{
  "type": "arrow", "id": "ar1",
  "x": 280, "y": 140, "width": 120, "height": 0, "angle": 0,
  "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
  "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
  "roughness": 1, "opacity": 100, "groupIds": [],
  "roundness": { "type": 2 },
  "seed": null, "version": 1, "versionNonce": null,
  "isDeleted": false, "boundElements": [], "link": null, "locked": false, "updated": 1,
  "startBinding": { "elementId": "r1", "focus": 0, "gap": 1 },
  "endBinding": { "elementId": "r2", "focus": 0, "gap": 1 },
  "lastCommittedPoint": null,
  "startArrowhead": null, "endArrowhead": "arrow",
  "points": [[0, 0], [120, 0]]
}
```

- `focus`: 0 = center of the bound edge. Range -1..1 to offset along the edge.
- `gap`: small pixel gap between the arrow tip and the shape edge (1 is fine).
- Add the arrow's id to each bound shape's `boundElements`:
  `[{ "id": "ar1", "type": "arrow" }]`.

## Line (structural, no arrowhead)

Same as arrow but `type: "line"` and no `startArrowhead`/`endArrowhead`.

## Text inside a shape (label)

Centered label bound to a shape via `containerId`.

```json
{
  "type": "text", "id": "t1",
  "x": 140, "y": 130, "width": 100, "height": 25, "angle": 0,
  "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
  "fillStyle": "solid", "strokeWidth": 1, "strokeStyle": "solid",
  "roughness": 1, "opacity": 100, "groupIds": [],
  "roundness": null,
  "seed": null, "version": 1, "versionNonce": null,
  "isDeleted": false, "boundElements": [], "link": null, "locked": false, "updated": 1,
  "text": "API Server",
  "fontSize": 20, "fontFamily": 1,
  "textAlign": "center", "verticalAlign": "middle",
  "containerId": "r1",
  "originalText": "API Server",
  "lineHeight": 1.25
}
```

- `fontFamily`: 1 = hand (Virgil), 2 = normal, 3 = mono, 4 = Sri Lanka.
- `containerId` = id of the shape this label sits in. The shape's
  `boundElements` must list `{"id":"t1","type":"text"}`.

## Free-floating text (title, section header)

Same as text-inside-shape but `containerId: null`. Used for titles, group
labels, and notes that don't belong to a shape.

## Default color palette

Use Excalidraw's defaults unless the user asks for specific colors:

| Use | Color |
|-----|-------|
| Stroke / text default | `#1e1e1e` |
| Green (start / success) | `#b2f2bb` |
| Blue (process / info) | `#a5d8ff` |
| Yellow (decision / warn) | `#ffec99` |
| Red (end / error) | `#ffc9c9` |
| Purple (external) | `#eebefa` |
| Gray (muted) | `#e9ecef` |

## Binding cheat sheet

To connect shape A → shape B with an arrow that tracks both:

1. Create arrow with `startBinding.elementId = "A"`, `endBinding.elementId = "B"`.
2. Add `{"id": "arrowId", "type": "arrow"}` to A's `boundElements` AND B's `boundElements`.
3. Set arrow `points` from A's right/bottom edge to B's left/top edge (relative to arrow `x,y`).

See `examples/flowchart.excalidraw` for a working start→process→decision→end example.
