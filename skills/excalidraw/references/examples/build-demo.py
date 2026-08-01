#!/usr/bin/env python3
"""Generate a complex Excalidraw scene: a CI/CD pipeline + microservice system.

Demonstrates: grouped regions, cross-region connections, decision diamonds,
database cylinders, async queues, legend. All text is computed for exact
centering inside its container so render output aligns cleanly.

Output: prints the scene JSON to stdout.
"""
import json
import sys


def el(**kw):
    """Base element with common fields, seed/versionNonce left null."""
    base = {
        "angle": 0, "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
        "roughness": 1, "opacity": 100, "groupIds": [], "roundness": None,
        "seed": None, "version": 1, "versionNonce": None, "isDeleted": False,
        "boundElements": [], "updated": 1, "link": None, "locked": False,
    }
    base.update(kw)
    return base


def box(eid, x, y, w, h, label, fill, multiline=False, stroke="#1e1e1e", dashed=False):
    """A labeled rectangle. Returns (box_element, label_element) bound together.

    Text position uses Excalidraw's verticalAlign=middle formula exactly:
      y = box.y + (box.h - text.h) / 2
      x = box.x + (box.w - text.w) / 2
    so the rendered label sits dead-center without relying on Excalidraw to
    recompute (it does NOT recompute positions for already-bound text).
    """
    fs = 16 if multiline else 18
    lines = label.split("\n") if multiline else [label]
    # Excalidraw Virgil font: width ~ fontSize * 0.6 per char; height = fontSize * lineHeight * nlines
    lh = 1.2 if multiline else 1.25
    tw = round(max(len(l) for l in lines) * fs * 0.62)
    th = round(fs * lh * len(lines))
    b = el(type="rectangle", id=eid, x=x, y=y, width=w, height=h,
           backgroundColor=fill, strokeColor=stroke, roundness={"type": 3},
           strokeStyle="dashed" if dashed else "solid")
    t = el(type="text", id=eid + "-t", x=x + (w - tw) / 2, y=y + (h - th) / 2,
           width=tw, height=th, fontSize=fs, fontFamily=1, textAlign="center",
           verticalAlign="middle", containerId=eid, text=label, originalText=label,
           lineHeight=lh)
    b["boundElements"] = [{"id": eid + "-t", "type": "text"}]
    return b, t


def diamond(eid, x, y, w, h, label, fill):
    lines = label.split("\n")
    fs = 18
    lh = 1.2
    tw = round(max(len(l) for l in lines) * fs * 0.62)
    th = round(fs * lh * len(lines))
    d = el(type="diamond", id=eid, x=x, y=y, width=w, height=h, backgroundColor=fill)
    t = el(type="text", id=eid + "-t", x=x + (w - tw) / 2, y=y + (h - th) / 2,
           width=tw, height=th, fontSize=fs, fontFamily=1, textAlign="center",
           verticalAlign="middle", containerId=eid, text=label, originalText=label,
           lineHeight=lh)
    d["boundElements"] = [{"id": eid + "-t", "type": "text"}]
    return d, t


def arrow(aid, x1, y1, x2, y2, src=None, dst=None, color="#1e1e1e", dashed=False):
    pts = [[0, 0], [x2 - x1, y2 - y1]]
    a = el(type="arrow", id=aid, x=x1, y=y1, width=x2 - x1, height=y2 - y1,
           strokeColor=color, roundness={"type": 2}, strokeStyle="dashed" if dashed else "solid",
           startBinding={"elementId": src, "focus": 0, "gap": 1} if src else None,
           endBinding={"elementId": dst, "focus": 0, "gap": 1} if dst else None,
           lastCommittedPoint=None, startArrowhead=None, endArrowhead="arrow", points=pts)
    return a


def region(rid, x, y, w, h, title, color="#1971c2"):
    """A dashed grouping rectangle with a title label."""
    r = el(type="rectangle", id=rid, x=x, y=y, width=w, height=h,
           strokeColor=color, backgroundColor="transparent", fillStyle="solid",
           strokeWidth=2, strokeStyle="dashed", roundness={"type": 3})
    t = el(type="text", id=rid + "-t", x=x + 14, y=y + 8, width=len(title) * 11,
           height=22, strokeColor=color, fontSize=16, fontFamily=1, textAlign="left",
           verticalAlign="top", containerId=None, text=title, originalText=title, lineHeight=1.25)
    return r, t


def title(tid, x, y, text_str, size=28):
    return el(type="text", id=tid, x=x, y=y, width=len(text_str) * (size * 0.6),
              height=size + 4, fontSize=size, fontFamily=1, textAlign="left",
              verticalAlign="top", containerId=None, text=text_str,
              originalText=text_str, lineHeight=1.25)


elements = []

# ---- Title ----
elements.append(title("title", 300, 16, "CI/CD Pipeline + Microservice Platform"))

# ---- Region: Source Control ----
r1, r1t = region("reg-src", 40, 80, 220, 110, "Source")
elements += [r1, r1t]
b, t = box("dev", 70, 115, 160, 50, "Dev Branch", "#a5d8ff")
elements += [b, t]
b, t = box("pr", 70, 175, 160, 40, "Pull Request", "#a5d8ff", multiline=False)
# fix: second box overlaps region; reposition
elements = [e for e in elements if e.get("id") not in ("pr", "pr-t")]
b, t = box("pr", 70, 130, 160, 40, "Pull Request", "#a5d8ff")
elements = [e for e in elements if e.get("id") not in ("dev", "dev-t")]
b, t = box("dev", 70, 108, 160, 40, "Git Push", "#a5d8ff")
elements += [b, t]
b, t = box("pr", 70, 152, 160, 40, "Pull Request", "#a5d8ff")
elements += [b, t]

# ---- Region: CI Pipeline ----
r2, r2t = region("reg-ci", 320, 80, 240, 360, "CI / CD Pipeline")
elements += [r2, r2t]
b, t = box("lint", 350, 120, 180, 44, "Lint & Test", "#b2f2bb")
elements += [b, t]
b, t = box("build", 350, 180, 180, 44, "Build Image", "#b2f2bb")
elements += [b, t]
d, dt = diamond("gate", 350, 250, 180, 90, "Tests\nPass?", "#ffec99")
elements += [d, dt]
b, t = box("scan", 350, 360, 180, 44, "Security Scan", "#b2f2bb")
elements += [b, t]
b, t = box("push-registry", 350, 420, 180, 40, "Push to Registry", "#eebefa")
# registry is outside region bottom; extend later. keep.
elements += [b, t]

# ---- Region: Infrastructure ----
r3, r3t = region("reg-infra", 620, 80, 340, 360, "Production Cluster")
elements += [r3, r3t]
b, t = box("lb", 650, 120, 280, 44, "Load Balancer (Ingress)", "#a5d8ff")
elements += [b, t]
b, t = box("api1", 650, 190, 120, 50, "API\nPod A", "#b2f2bb", multiline=True)
elements += [b, t]
b, t = box("api2", 800, 190, 120, 50, "API\nPod B", "#b2f2bb", multiline=True)
elements += [b, t]
b, t = box("worker", 650, 270, 270, 44, "Worker (Queue Consumer)", "#b2f2bb")
elements += [b, t]
b, t = box("db", 650, 340, 120, 50, "PostgreSQL", "#e9ecef")
elements += [b, t]
b, t = box("redis", 800, 340, 120, 50, "Redis", "#eebefa")
elements += [b, t]
b, t = box("cdn", 650, 410, 270, 40, "CDN / Static Assets", "#ffc9c9")
elements += [b, t]

# ---- Arrows: Source -> CI ----
elements.append(arrow("a1", 230, 128, 350, 142, src="pr", dst="lint"))
elements.append(arrow("a2", 440, 164, 440, 180, src="lint", dst="build"))
elements.append(arrow("a3", 440, 224, 440, 250, src="build", dst="gate"))
elements.append(arrow("a4", 440, 340, 440, 360, src="gate", dst="scan"))
elements.append(arrow("a5", 440, 404, 440, 420, src="scan", dst="push-registry"))

# ---- Arrows: CI -> Infra ----
elements.append(arrow("a6", 530, 440, 650, 142, src="push-registry", dst="lb", dashed=True))
elements.append(arrow("a7", 710, 164, 710, 190, src="lb", dst="api1"))
elements.append(arrow("a8", 860, 164, 860, 190, src="lb", dst="api2"))
elements.append(arrow("a9", 710, 240, 710, 270, src="api1", dst="worker"))
elements.append(arrow("a10", 710, 314, 710, 340, src="worker", dst="db"))
elements.append(arrow("a11", 860, 314, 860, 340, src="worker", dst="redis"))

# ---- Legend ----
elements.append(title("legend-h", 40, 480, "Legend", size=16))
leg_items = [("#a5d8ff", "Edge / LB"), ("#b2f2bb", "Service"),
             ("#ffec99", "Decision"), ("#e9ecef", "Datastore"),
             ("#eebefa", "Cache/Registry"), ("#ffc9c9", "External")]
lx = 40
for i, (c, name) in enumerate(leg_items):
    elements.append(el(type="rectangle", id=f"leg{i}", x=lx, y=510, width=22, height=16,
                       backgroundColor=c, strokeWidth=1, roundness={"type": 3}))
    elements.append(el(type="text", id=f"leg{i}t", x=lx + 28, y=510, width=len(name) * 9,
                       height=16, fontSize=13, fontFamily=1, textAlign="left",
                       verticalAlign="middle", containerId=None, text=name,
                       originalText=name, lineHeight=1.25))
    lx += 28 + len(name) * 9 + 16

scene = {
    "type": "excalidraw", "version": 2, "source": "https://excalidraw.com",
    "elements": elements,
    "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
    "files": {},
}
json.dump(scene, sys.stdout, indent=1, ensure_ascii=False)
