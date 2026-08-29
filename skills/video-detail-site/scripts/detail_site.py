#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""视频详情预览站生成器（纯 stdlib）。

扫描 video-generation/build/*/*.mp4 → 生成 video-generation/site/：
  index.html            列表页（封面网格）
  <slug>/index.html     详情页（播放器 + meta + 口播稿 + 分镜脚本）

服务：python -m http.server 8767 --directory video-generation
URL：http://localhost:8767/site/index.html
"""
from __future__ import annotations

import glob
import html
import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

def _find_root() -> Path:
    """项目根 = 向上找含 video-generation/ 的目录（.agents 是 symlink，resolve 会穿透）。"""
    for base in [Path.cwd(), *Path.cwd().parents, Path(__file__).parent,
                 *Path(__file__).parent.parents]:
        if (base / "video-generation").is_dir():
            return base
    raise SystemExit("找不到项目根（含 video-generation/ 的目录）")


ROOT = _find_root()
VG = ROOT / "video-generation"
BUILD = VG / "build"
SITE = VG / "site"
FPS = 30

BLUE = "#2563eb"
INK = "#1e293b"
GRAY = "#64748b"


def _esc(s) -> str:
    return html.escape(str(s), quote=True)


def find_videos() -> list[dict]:
    out = []
    for mp4 in sorted(glob.glob(str(BUILD / "*" / "*.mp4"))):
        p = Path(mp4)
        slug = p.parent.name
        if p.stem != slug:
            continue
        out.append({"slug": slug, "dir": p.parent, "mp4": p})
    out.sort(key=lambda v: v["mp4"].stat().st_mtime, reverse=True)
    return out


def read_meta(d: Path) -> dict:
    meta = {}
    f = d / "metadata.txt"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            if ":" in line and not line.startswith((";", "#")):
                k, _, v = line.partition(":")
                meta[k.strip()] = v.strip()
    return meta


def ffprobe(mp4: Path) -> dict:
    info = {"duration": "?", "size_kb": mp4.stat().st_size // 1024}
    if shutil.which("ffprobe"):
        try:
            r = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "csv=p=0", str(mp4)],
                capture_output=True, text=True, timeout=30)
            sec = float(r.stdout.strip())
            info["duration"] = f"{int(sec // 60)}'{sec % 60:04.1f}\""
        except Exception:
            pass
    return info


def read_narrations(slug: str) -> list[str]:
    f = VG / "narrations" / f"{slug}.json"
    if not f.exists():
        return []
    try:
        return json.loads(f.read_text(encoding="utf-8")).get("cards", [])
    except Exception:
        return []


def read_deck(slug: str) -> dict:
    f = VG / "deck" / slug / "deck.json"
    if not f.exists():
        return {}
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _line_text(ln) -> str:
    if isinstance(ln, str):
        return ln
    if isinstance(ln, dict):
        return str(ln.get("t", ""))
    if isinstance(ln, list):
        return " ".join(_line_text(x) for x in ln)
    return str(ln)


def shot_summary(sh: dict) -> tuple[str, str]:
    kind = sh.get("kind", "?")
    data = sh.get("data") or {}
    if kind == "term":
        body = "\n".join(
            _line_text(ln) for ln in data.get("lines", []))
        head = data.get("title", "终端")
    elif kind == "code":
        body = "\n".join(
            _line_text(ln) for ln in data.get("lines", []))
        head = data.get("title", "源码")
    elif kind == "stat":
        body = " / ".join(x for x in (data.get("big"), data.get("label"), data.get("sub")) if x)
        head = "数据"
    elif kind == "quote":
        body = f'“{data.get("text", "")}” — {data.get("source", "")}'
        head = "金句"
    elif kind == "table":
        rows = data.get("rows", [])
        body = "\n".join(" | ".join(map(str, r)) for r in rows)
        head = data.get("title", "表格")
    elif kind == "flow":
        nodes = " → ".join(n.get("label", n.get("id", "?")) for n in data.get("nodes", []))
        body = nodes
        head = "流程"
    elif kind == "tree":
        body = "\n".join(
            _line_text(ln) for ln in data.get("items", []))
        head = data.get("title", "结构")
    else:
        body = json.dumps(data, ensure_ascii=False)[:400]
        head = kind
    return head, body


def read_series_md(slug: str) -> dict:
    """eng-series 系列：回源到 build/eng-series-202609/<ep>.md 取口播稿/分镜表原文。"""
    if not slug.startswith("eng-series-"):
        return {}
    ep = slug.replace("eng-series-", "")
    for f in (BUILD / "eng-series-202609").glob("*.md"):
        if f.stem == ep or f.stem.startswith(ep):
            t = f.read_text(encoding="utf-8")
            out = {"file": f.name}
            if "## 口播稿" in t:
                seg = t.split("## 口播稿")[1]
                seg = seg.split("\n## ")[0]
                out["script"] = seg.strip()
            if "## 分镜表" in t:
                seg = t.split("## 分镜表")[1]
                seg = seg.split("\n## ")[0]
                out["storyboard"] = seg.strip()
            return out
    return {}


def page(css_extra: str, body: str, title: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(title)} · 视频详情站</title>
<style>
* {{ box-sizing: border-box; }}
body {{ margin:0; font-family:"PingFang SC","Microsoft YaHei",sans-serif;
  background:#f1f5f9; color:{INK}; }}
.wrap {{ max-width:1280px; margin:0 auto; padding:24px 20px 60px; }}
a {{ color:{BLUE}; text-decoration:none; }}
h1 {{ font-size:30px; margin:10px 0 4px; }}
h2 {{ font-size:21px; margin:34px 0 12px; border-left:4px solid {BLUE}; padding-left:12px; }}
.crumb {{ font-size:14px; color:{GRAY}; }}
.chips {{ display:flex; flex-wrap:wrap; gap:8px; margin:10px 0; }}
.chip {{ background:#fff; border:1px solid #e2e8f0; border-radius:999px;
  padding:4px 14px; font-size:14px; color:{GRAY}; }}
.chip b {{ color:{INK}; }}
video {{ width:100%; max-height:640px; background:#000; border-radius:14px; }}
.meta {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(260px,1fr)); gap:8px; }}
.meta div {{ background:#fff; border:1px solid #e2e8f0; border-radius:10px; padding:10px 14px; font-size:15px; }}
.meta b {{ color:{GRAY}; font-weight:600; margin-right:8px; font-size:13px; }}
.card {{ background:#fff; border:1px solid #e2e8f0; border-radius:14px;
  padding:18px 22px; margin-bottom:14px; }}
.card h3 {{ margin:0 0 8px; font-size:18px; }}
.card .pts {{ color:{GRAY}; font-size:14px; margin-bottom:8px; }}
.card pre {{ white-space:pre-wrap; font-size:16px; line-height:1.8;
  font-family:inherit; margin:0; }}
.badge {{ display:inline-block; background:{BLUE}; color:#fff; border-radius:6px;
  font-size:12px; font-weight:700; padding:2px 10px; margin-right:8px; vertical-align:2px; }}
.fs {{ font-size:13px; color:{GRAY}; margin-right:12px; }}
details {{ margin:10px 0; }}
details pre {{ background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px;
  padding:14px; font-size:13px; overflow:auto; }}
summary {{ cursor:pointer; font-weight:700; color:{BLUE}; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(340px,1fr)); gap:18px; }}
.vcard {{ background:#fff; border:1px solid #e2e8f0; border-radius:14px; overflow:hidden;
  transition:box-shadow .15s; }}
.vcard:hover {{ box-shadow:0 10px 30px rgba(30,41,59,.14); }}
.vcard img {{ width:100%; aspect-ratio:16/9; object-fit:cover; display:block; }}
.vcard .pad {{ padding:14px 16px; }}
.vcard .t {{ font-size:17px; font-weight:700; }}
.vcard .d {{ font-size:13px; color:{GRAY}; margin-top:6px; }}
.top {{ display:flex; justify-content:space-between; align-items:center; }}
{css_extra}
</style></head><body>{body}</body></html>"""


def build_detail(v: dict) -> str:
    slug = v["slug"]
    d = v["dir"]
    meta = read_meta(d)
    info = ffprobe(v["mp4"])
    narr = read_narrations(slug)
    deck = read_deck(slug)
    smd = read_series_md(slug)
    title = meta.get("标题") or deck.get("title") or slug
    series = meta.get("系列") or deck.get("series", "")

    chips = f'<div class="chips"><span class="chip">系列 <b>{_esc(series or "—")}</b></span>' \
            f'<span class="chip">时长 <b>{_esc(str(info["duration"]))}</b></span>' \
            f'<span class="chip">体积 <b>{info["size_kb"]} KB</b></span>' \
            f'<span class="chip">slug <b>{_esc(slug)}</b></span></div>'

    meta_rows = "".join(f"<div><b>{_esc(k)}</b>{_esc(vv)}</div>" for k, vv in meta.items())
    meta_html = f'<div class="meta">{meta_rows}</div>' if meta_rows else "<p>无 metadata.txt</p>"

    narr_html = ""
    for i, c in enumerate(narr):
        narr_html += f'<div class="card"><h3><span class="badge">C{i + 1}</span>口播卡</h3>' \
                     f'<pre>{_esc(c)}</pre></div>'

    deck_html = ""
    for i, c in enumerate(deck.get("cards", [])):
        pts = " / ".join(c.get("points", []))
        shots_html = ""
        for si, sh in enumerate(c.get("shots", [])):
            head, body = shot_summary(sh)
            shots_html += (f'<div class="card" style="background:#f8fafc">'
                           f'<span class="badge">{_esc(sh.get("kind", "?"))}</span>'
                           f'<span class="fs">from {sh.get("from_s", "?")}s</span>'
                           f'<b>{_esc(head)}</b>'
                           f'<pre>{_esc(body)}</pre></div>')
        deck_html += (f'<div class="card"><h3><span class="badge">卡 {i + 1}</span>'
                      f'{_esc(c.get("title", ""))}</h3>'
                      + (f'<div class="pts">要点：{_esc(pts)}</div>' if pts else "")
                      + shots_html + "</div>")

    smd_html = ""
    if smd:
        smd_html = (f'<details><summary>系列原始稿（{_esc(smd.get("file", ""))}）</summary>'
                    f'<h3>口播稿</h3><pre>{_esc(smd.get("script", ""))}</pre>'
                    f'<h3>分镜表</h3><pre>{_esc(smd.get("storyboard", ""))}</pre></details>')

    body = f'''<div class="wrap">
<div class="top"><div class="crumb"><a href="../index.html">← 返回列表</a></div>
<div class="crumb">生成于 {datetime.now().strftime("%Y-%m-%d %H:%M")}</div></div>
<h1>{_esc(title)}</h1>
{chips}
<video controls preload="metadata" poster="../build/{_esc(slug)}/{_esc(slug)}_cover.png">
  <source src="../build/{_esc(slug)}/{_esc(slug)}.mp4" type="video/mp4">
</video>
<h2>meta</h2>
{meta_html}
<h2>口播稿（{len(narr)} 卡）</h2>
{narr_html or "<p>无 narrations</p>"}
<h2>分镜脚本（{len(deck.get("cards", []))} 卡）</h2>
{deck_html or "<p>无 deck</p>"}
{smd_html}
</div>'''
    return page("", body, title)


def build_index(videos: list[dict]) -> str:
    cards = []
    for v in videos:
        slug = v["slug"]
        meta = read_meta(v["dir"])
        info = ffprobe(v["mp4"])
        title = meta.get("标题") or slug
        poster = f"../build/{slug}/{slug}_cover.png"
        cover = poster if (v["dir"] / f"{slug}_cover.png").exists() else ""
        img = f'<img src="{_esc(cover)}" alt="">' if cover else ""
        cards.append(
            f'<a class="vcard" href="{_esc(slug)}/index.html">{img}'
            f'<div class="pad"><div class="t">{_esc(title)}</div>'
            f'<div class="d">{_esc(meta.get("系列", ""))} · {_esc(str(info["duration"]))}'
            f' · {info["size_kb"]} KB</div></div></a>')
    body = f'''<div class="wrap">
<div class="top"><h1 style="margin:0">视频详情站</h1>
<div class="crumb">刷新：make video-site · 服务：make video-site-serve</div></div>
<p class="crumb">{len(videos)} 支成片 · 点击卡片进详情页（播放 / 口播稿 / 分镜 / meta）</p>
<div class="grid">{"".join(cards)}</div>
</div>'''
    return page("", body, "视频详情站")


def main() -> int:
    if not BUILD.exists():
        print("video-generation/build 不存在")
        return 1
    videos = find_videos()
    if not videos:
        print("build 下没有成片 mp4")
        return 1
    SITE.mkdir(parents=True, exist_ok=True)
    for v in videos:
        d = SITE / v["slug"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(build_detail(v), encoding="utf-8", newline="\n")
    (SITE / "index.html").write_text(build_index(videos), encoding="utf-8", newline="\n")
    print(f"site 已生成：{len(videos)} 支视频 → {SITE}")
    print("列表页：http://localhost:8767/site/index.html")
    for v in videos:
        print(f"  http://localhost:8767/site/{v['slug']}/index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
