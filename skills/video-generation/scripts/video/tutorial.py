"""教程类模板（type:"tutorial"）——工具类教程专用，亮色干净风。

与 screencast（深色科幻）的差异：
- **全量展示**：步骤条、要点、截图内容默认全部可见（不逐条揭示），
  当前讲解项高亮（active 蓝色 + 呼吸光），过去项绿色 ✓，未来项正常灰显。
- 亮色背景：#f6f8fb 底 + 极淡网格 + 柔光斑，白卡 + 细边框，单主色 #2563eb。
- 动效全部帧驱动（state["frame"]），无 CSS animation（逐帧截图下不可靠）：
  卡片浮入、热点呼吸、active pill 脉冲、要点滑入。

卡字段（normalize_card 全透传）：
  kind: "intro" | "step" | "end"
  steps: [全步骤列表]（顶部步骤条数据源，各卡共享）
  step_idx: 当前卡对应步骤序号（intro=-1；end=len(steps)）
  title / eyebrow（眉题）
  shot + slug + hotspots（kind=step，真实截图打底，坐标百分比）
  lines: [{step, text, cls}]（kind=step，终端卡；step 对应要点序号）
  points: [要点]（右侧要点区，全可见，active_idx 高亮）
  url_note: 截图来源标注（如 github.com/...）
"""
from __future__ import annotations

import math

from .screencast import _shot_b64, _esc

# 主色与主题 token（教程亮色系）
BLUE = "#2563eb"
BLUE_DARK = "#1d4ed8"
GREEN = "#16a34a"
INK = "#1e293b"
MUTED = "#64748b"

_CSS = """
* { margin:0; padding:0; box-sizing:border-box; }
html,body { width:__W__px; height:__H__px; overflow:hidden;
  font-family:"Source Han Sans SC","Noto Sans SC","Microsoft YaHei",sans-serif;
  color:__INK__; }
body {
  background:#f6f8fb;
  background-image:
    radial-gradient(900px 500px at 88% -5%, rgba(37,99,235,.07), transparent 60%),
    radial-gradient(800px 480px at -5% 105%, rgba(139,92,246,.06), transparent 60%),
    linear-gradient(#e8edf4 1px, transparent 1px),
    linear-gradient(90deg, #e8edf4 1px, transparent 1px);
  background-size: 100% 100%, 100% 100%, 44px 44px, 44px 44px;
}
.wrap { width:100%; height:100%; padding:44px 200px 150px 64px; display:flex; flex-direction:column; }

/* 顶栏：眉题 + 标题 */
.top { display:flex; align-items:center; gap:18px; height:58px; }
.eyebrow { background:#fff; border:1.5px solid #dbe3ee; border-radius:999px;
  padding:7px 18px; font-size:26px; font-weight:600; color:__BLUE__; white-space:nowrap; }
.h1 { font-size:48px; font-weight:800; letter-spacing:.5px; }

/* 步骤条：全部可见 */
.steps { display:flex; gap:10px; margin:14px 0 22px; }
.spill { display:flex; align-items:center; gap:8px; border-radius:999px;
  padding:9px 16px; font-size:24px; font-weight:600; white-space:nowrap;
  background:#fff; border:1.5px solid #dbe3ee; color:#475569; }
.spill .n { display:inline-flex; align-items:center; justify-content:center;
  width:30px; height:30px; border-radius:50%; font-size:18px;
  background:#eef2f7; color:#64748b; font-weight:700; }
.spill.done { border-color:#bfe4cd; color:#15803d; background:#f2fbf5; }
.spill.done .n { background:#dcfce7; color:#15803d; }
.spill.active { border-color:__BLUE__; background:__BLUE__; color:#fff;
  box-shadow:0 6px 22px rgba(37,99,235,.38); }
.spill.active .n { background:rgba(255,255,255,.25); color:#fff; }

/* 主区 */
.main { flex:1; display:flex; gap:26px; min-height:0; }
.stage { flex:1.95; background:#fff; border:1.5px solid #e2e8f0; border-radius:16px;
  box-shadow:0 14px 38px rgba(30,41,59,.10); position:relative; overflow:hidden;
  display:flex; align-items:center; justify-content:center; }
.urlnote { position:absolute; right:14px; bottom:10px; font-size:18px; color:#94a3b8;
  font-family:Consolas,monospace; }

/* 截图 + 热点 */
.shotwrap { position:relative; width:94%; aspect-ratio:16/9; border-radius:10px; overflow:hidden; }
.shotwrap img { width:100%; height:100%; object-fit:cover; display:block; border-radius:10px; }
.hspot { position:absolute; border:3.5px solid __BLUE__; border-radius:8px; }
.hspot.active { box-shadow:0 0 0 5px rgba(37,99,235,.18), 0 0 30px rgba(37,99,235,.45); }
.hspot.done { border-color:#86efac; border-style:solid; opacity:.9; }
.hlab { position:absolute; background:__BLUE__; color:#fff; font-size:30px; font-weight:700;
  padding:6px 14px; border-radius:8px; white-space:nowrap; box-shadow:0 4px 14px rgba(37,99,235,.4); }

/* 终端（浅色 mac 窗口） */
.termwin { width:94%; background:#fbfcfe; border:1.5px solid #e2e8f0; border-radius:12px; overflow:hidden; }
.termbar { display:flex; align-items:center; gap:8px; padding:11px 16px;
  background:#f1f5f9; border-bottom:1.5px solid #e2e8f0; }
.dot { width:13px; height:13px; border-radius:50%; }
.termtitle { margin-left:10px; font-size:20px; color:#64748b; }
.term { padding:20px 24px; font-family:Consolas,"JetBrains Mono",monospace;
  font-size:30px; line-height:1.8; color:#334155; }
.term .row { padding:2px 12px; border-radius:8px; border-left:4px solid transparent; }
.term .row.done { color:#94a3b8; }
.term .row.done::before { content:"✓ "; color:#16a34a; font-weight:700; }
.term .row.active { background:#eff6ff; border-left-color:__BLUE__; color:__BLUE_DARK__; font-weight:700; }
.term .ps { color:#16a34a; font-weight:700; }
.term .ok { color:#16a34a; }
.term .warn { color:#dc2626; }

/* 代码窗口（VSCode 风，kind:"code"） */
.codewin { width:96%; background:#1e2433; border-radius:12px; overflow:hidden;
  box-shadow:0 16px 40px rgba(15,23,42,.25); }
.codebar { display:flex; align-items:center; gap:8px; padding:10px 16px; background:#171c29;
  border-bottom:1px solid #2b3347; }
.codetab { margin-left:8px; font-size:22px; color:#9fb0cd; font-family:Consolas,monospace; }
.codebody { padding:14px 0; font-family:Consolas,"JetBrains Mono",monospace;
  font-size:24px; line-height:1.9; color:#d7e0f0; counter-reset:ln; }
.cl { display:flex; padding:0 18px 0 0; white-space:pre; }
.cl .no { width:52px; flex-shrink:0; text-align:right; padding-right:18px; color:#48556e;
  user-select:none; font-size:22px; }
.cl.hl { background:rgba(37,99,235,.22); box-shadow:inset 3px 0 0 __BLUE__; }
.cl.dim { opacity:.82; }
.kw { color:#c792ea; }  .str { color:#a5d6a7; }  .cmt { color:#5c6b85; font-style:italic; }
.num { color:#f0a45d; }  .fn { color:#82aaff; }  .typ { color:#ffcb6b; }

/* 流程图（kind:"flow"，动态点亮） */
.flowwrap { position:relative; width:96%; height:100%; }
.fnode { position:absolute; transform:translate(-50%,-50%); background:#fff;
  border:2px solid #cbd5e1; border-radius:12px; padding:12px 20px; text-align:center;
  font-size:26px; font-weight:700; color:#475569; min-width:190px;
  box-shadow:0 4px 12px rgba(30,41,59,.06); }
.fnode .fsub { display:block; font-size:20px; font-weight:500; color:#94a3b8; margin-top:3px; }
.fnode.lit { border-color:__BLUE__; color:__BLUE_DARK__; background:#eff6ff;
  box-shadow:0 8px 26px rgba(37,99,235,.30); }
.fnode.cur { border-color:__BLUE__; background:__BLUE__; color:#fff; }
.fnode.cur .fsub { color:#dbeafe; }
.fedge { position:absolute; transform-origin:0 0; height:3px; background:#cbd5e1; }
.fedge.lit { background:__BLUE__; box-shadow:0 0 10px rgba(37,99,235,.5); }
.farrow { position:absolute; width:0; height:0; border-left:8px solid transparent;
  border-right:8px solid transparent; }
.farrow.lit { border-top:11px solid __BLUE__; }
.farrow.dim { border-top:11px solid #cbd5e1; }

/* 要点区：全部可见 */
.pts { flex:1; display:flex; flex-direction:column; gap:14px; min-width:430px; }
.pts-h { font-size:24px; font-weight:700; color:#94a3b8; letter-spacing:2px; padding:2px 4px 0; }
.pt { display:flex; align-items:flex-start; gap:14px; background:#fff;
  border:1.5px solid #e2e8f0; border-radius:14px; padding:16px 18px;
  font-size:34px; font-weight:600; color:#475569; line-height:1.45;
  box-shadow:0 4px 14px rgba(30,41,59,.05); }
.pt .ic { flex-shrink:0; display:inline-flex; align-items:center; justify-content:center;
  width:40px; height:40px; border-radius:50%; font-size:20px; font-weight:800;
  background:#eef2f7; color:#64748b; margin-top:1px; }
.pt.done { color:#15803d; background:#f6fdf8; border-color:#d3ecd9; }
.pt.done .ic { background:#dcfce7; color:#15803d; }
.pt.active { color:__BLUE_DARK__; background:#eff6ff; border-color:__BLUE__;
  box-shadow:0 10px 28px rgba(37,99,235,.22); }
.pt.active .ic { background:__BLUE__; color:#fff; }

/* 字幕带 + 进度条 */
.subtitle-band { position:absolute; left:0; right:180px; bottom:44px; height:96px;
  display:flex; align-items:center; justify-content:center; }
.subtitle { font-size:46px; font-weight:700; color:__INK__; background:rgba(255,255,255,.92);
  border:1.5px solid #e2e8f0; padding:10px 34px; border-radius:999px;
  box-shadow:0 6px 20px rgba(30,41,59,.08); max-width:1500px; }
.progress-track { position:absolute; left:0; right:0; bottom:0; height:9px; background:#e6ebf2; }
.progress-fill { height:100%; background:linear-gradient(90deg,__BLUE__,#60a5fa); }
"""


def render_frame(card: dict, state: dict, width: int = 1920, height: int = 1080) -> str:
    """渲染一帧教程模板 HTML（亮色全量展示 + active 高亮）。"""
    frame = int(state.get("frame", 0))
    active_idx = int(state.get("active_idx", -1))
    subtitle = state.get("subtitle", "") or ""
    progress = float(state.get("progress", 0.0))
    pct = max(0.0, min(1.0, progress)) * 100.0

    kind = card.get("kind", "step")
    steps = card.get("steps") or []
    step_idx = int(card.get("step_idx", -1))
    points = card.get("points") or []

    # 入场浮入（帧驱动，前 16 帧）
    p_in = min(1.0, frame / 16.0)
    ease = 1 - (1 - p_in) ** 3
    enter_ty = round(14 * (1 - ease), 1)
    enter_op = round(ease, 3)
    # 呼吸（热点/active pill）
    breathe = 0.5 + 0.5 * math.sin(frame / 9.0)
    pulse = 1 + 0.025 * math.sin(frame / 10.0)

    css = (_CSS.replace("__W__", str(width)).replace("__H__", str(height))
           .replace("__INK__", INK).replace("__BLUE__", BLUE)
           .replace("__BLUE_DARK__", BLUE_DARK))

    # ---- 顶部步骤条（全部可见：done ✓ / active 蓝填充 / future 正常灰显） ----
    pills = []
    for i, s in enumerate(steps):
        short = s if len(s) <= 14 else s[:13] + "…"
        if i < step_idx:
            cls, num = "done", "✓"
        elif i == step_idx:
            cls, num = "active", str(i + 1)
        else:
            cls, num = "", str(i + 1)
        style = f"transform:scale({pulse:.3f});" if cls == "active" else ""
        pills.append(
            f'<div class="spill {cls}" style="{style}">'
            f'<span class="n">{num}</span>{_esc(short)}</div>')
    steps_bar = f'<div class="steps">{"".join(pills)}</div>' if steps else ""

    # ---- 主区（截图 / 终端 / 代码 / 流程图） ----
    if kind == "code":
        stage = _code_stage(card, active_idx, enter_ty, enter_op)
    elif kind == "flow":
        stage = _flow_stage(card, active_idx, breathe, enter_ty, enter_op)
    elif kind == "step" and card.get("shot"):
        src = _shot_b64(card.get("slug", ""), card.get("shot", ""))
        inner = (f'<div style="color:#dc2626;font-size:26px;font-weight:700">'
                 f'截图缺失: {_esc(card.get("shot", ""))}</div>') if not src else f'<img src="{src}" alt="">'
        hotspots = card.get("hotspots") or []
        for i in range(len(points)):
            hp = hotspots[i] if i < len(hotspots) else None
            if not hp:
                continue
            x, y, w, h = hp["x"], hp["y"], hp["w"], hp["h"]
            if i < active_idx:
                cls = "hspot done"
            elif i == active_idx:
                glow = 0.30 + 0.25 * breathe
                cls = "hspot active"
                inner += (f'<div class="hlab" style="left:{min(x, 55):.1f}%;'
                          f'top:{max(y - 11, 2):.1f}%;opacity:{0.85 + 0.15 * breathe:.2f}">'
                          f'{_esc(hp.get("label", ""))}</div>')
            else:
                cls = "hspot"
                glow = 0
            shadow = (f'box-shadow:0 0 0 5px rgba(37,99,235,{glow:.2f}),'
                      f'0 0 {18 + 14 * breathe:.0f}px rgba(37,99,235,{0.25 + 0.2 * breathe:.2f});'
                      if i == active_idx else "")
            inner += (f'<div class="{cls}" style="left:{x}%;top:{y}%;width:{w}%;'
                      f'height:{h}%;{shadow}"></div>')
        stage = f'<div class="stage" style="transform:translateY({enter_ty}px);opacity:{enter_op}">' \
                f'<div class="shotwrap">{inner}</div>' \
                f'<div class="urlnote">{_esc(card.get("url_note", ""))}</div></div>'
    elif kind == "step":
        # 终端卡：行全可见，当前行高亮
        rows = []
        for l in (card.get("lines") or []):
            st, text, cls0 = l.get("step", 0), l["text"], l.get("cls", "out")
            if st < active_idx:
                rc = "row done"
            elif st == active_idx:
                rc = "row active"
            else:
                rc = "row"
            rows.append(f'<div class="{rc}"><span class="{cls0}">{text}</span></div>')
        stage = (f'<div class="stage" style="transform:translateY({enter_ty}px);opacity:{enter_op}">'
                 f'<div class="termwin"><div class="termbar">'
                 f'<span class="dot" style="background:#fb7185"></span>'
                 f'<span class="dot" style="background:#fbbf24"></span>'
                 f'<span class="dot" style="background:#34d399"></span>'
                 f'<span class="termtitle">{_esc(card.get("subtitle", "终端"))}</span></div>'
                 f'<div class="term">{"".join(rows)}</div></div></div>')
    else:
        # intro / end：居中大标题
        stage = (f'<div class="stage" style="align-items:center;justify-content:center;'
                 f'flex-direction:column;gap:26px;transform:translateY({enter_ty}px);opacity:{enter_op}">'
                 f'<div style="font-size:64px;font-weight:800;letter-spacing:1px;">'
                 f'{_esc(card.get("big", card.get("title", "")))}</div>'
                 f'<div style="font-size:28px;color:#64748b;font-weight:600;">'
                 f'{_esc(card.get("sub_big", ""))}</div></div>')

    # ---- 要点区（全部可见，active 高亮；flow 卡全宽不显示） ----
    pt_html = ""
    if points and kind != "flow":
        items = []
        for i, pt in enumerate(points):
            if i < active_idx:
                cls, ic = "done", "✓"
            elif i == active_idx:
                cls, ic = "active", str(i + 1)
            else:
                cls, ic = "", str(i + 1)
            ty = round(8 * (1 - ease), 1) if i == active_idx else 0
            items.append(f'<div class="pt {cls}" style="transform:translateX({-ty}px)">'
                         f'<span class="ic">{ic}</span><span>{_esc(pt)}</span></div>')
        pt_html = (f'<div class="pts"><div class="pts-h">本步要点</div>'
                   f'{"".join(items)}</div>')

    sub_cls = "subtitle" if subtitle else "subtitle empty"
    band = (f'<div class="subtitle-band"><div class="{sub_cls}">{_esc(subtitle)}</div></div>'
            if subtitle else "")
    prog = f'<div class="progress-track"><div class="progress-fill" style="width:{pct:.2f}%"></div></div>'

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{css}</style></head>
<body><div class="wrap">
  <div class="top">
    <div class="eyebrow">{_esc(card.get("eyebrow", "工具教程"))}</div>
    <div class="h1">{_esc(card.get("title", ""))}</div>
  </div>
  {steps_bar}
  <div class="main">{stage}{pt_html}</div>
</div>{band}{prog}</body></html>"""


# ---- 代码窗口（kind:"code"） ----

_TS_KEYWORDS = {
    "const", "let", "var", "function", "return", "if", "else", "for", "while", "break",
    "continue", "new", "class", "extends", "interface", "type", "enum", "import", "from",
    "export", "default", "async", "await", "try", "catch", "finally", "throw", "switch",
    "case", "this", "super", "typeof", "instanceof", "in", "of", "as", "readonly",
    "private", "public", "protected", "static", "implements", "yield", "void", "null",
    "undefined", "true", "false", "string", "number", "boolean", "object", "unknown", "any",
}


def _hl_line(line: str) -> str:
    """极简 TS 语法高亮：注释 / 字符串 / 关键字 / 数字 / 函数调用。"""
    import re as _re

    out, i = [], 0
    n = len(line)
    while i < n:
        ch = line[i]
        if ch == "/" and i + 1 < n and line[i + 1] == "/":
            out.append(f'<span class="cmt">{_esc(line[i:])}</span>')
            break
        if ch in "\"'`":
            j = i + 1
            while j < n and line[j] != ch:
                j += 2 if line[j] == "\\" else 1
            j = min(j + 1, n)
            out.append(f'<span class="str">{_esc(line[i:j])}</span>')
            i = j
            continue
        m = _re.match(r"[A-Za-z_$][A-Za-z0-9_$]*", line[i:])
        if m:
            w = m.group(0)
            rest = line[i + len(w):].lstrip()
            if w in _TS_KEYWORDS:
                out.append(f'<span class="kw">{w}</span>')
            elif rest.startswith("("):
                out.append(f'<span class="fn">{w}</span>')
            elif w[0].isupper():
                out.append(f'<span class="typ">{w}</span>')
            else:
                out.append(_esc(w))
            i += len(w)
            continue
        m = _re.match(r"\d+(\.\d+)?", line[i:])
        if m:
            out.append(f'<span class="num">{m.group(0)}</span>')
            i += len(m.group(0))
            continue
        out.append(_esc(ch))
        i += 1
    return "".join(out)


def _code_stage(card: dict, active_idx: int, ty: float, op: float) -> str:
    """VSCode 风代码窗口：真实源码行 + 行号 + 当前讲解组高亮。

    字段：file（标签页路径）、lines=[源码行]、hl_groups=[[行号...], ...]
    （active_idx 选组，行号从 1 计）。
    """
    file_name = card.get("file", "source.ts")
    lines = card.get("lines") or []
    groups = card.get("hl_groups") or []
    gi = max(0, min(active_idx, len(groups) - 1)) if groups else -1
    lit = set(groups[gi]) if 0 <= gi < len(groups) else set()

    rows = []
    for ln, text in enumerate(lines, 1):
        cls = "cl hl" if ln in lit else "cl dim"
        rows.append(f'<div class="{cls}"><span class="no">{ln}</span>'
                    f'<span>{_hl_line(text) if text.strip() else "&nbsp;"}</span></div>')
    return (f'<div class="stage" style="background:#f2f5fa;transform:translateY({ty}px);opacity:{op}">'
            f'<div class="codewin"><div class="codebar">'
            f'<span class="dot" style="background:#fb7185"></span>'
            f'<span class="dot" style="background:#fbbf24"></span>'
            f'<span class="dot" style="background:#34d399"></span>'
            f'<span class="codetab">{_esc(file_name)}</span></div>'
            f'<div class="codebody">{"".join(rows)}</div></div>'
            f'<div class="urlnote">{_esc(card.get("url_note", ""))}</div></div>')


def _flow_stage(card: dict, active_idx: int, breathe: float, ty: float, op: float) -> str:
    """动态流程图：节点按讲解顺序点亮，边随目标节点点亮。

    字段：nodes=[{id,label,sub?,x,y}]（x,y 为容器百分比 0-100）、
    edges=[{from,to}]（节点 id）。点亮序 = nodes 数组序（deck 排好讲解顺序）。
    """
    nodes = card.get("nodes") or []
    edges = card.get("edges") or []
    pos = {n["id"]: (n["x"], n["y"]) for n in nodes}
    lit_up_to = active_idx if active_idx >= 0 else -1   # -1 = 全暗（开场）

    svg = ['<svg viewBox="0 0 100 100" preserveAspectRatio="none" '
           'style="position:absolute;inset:0;width:100%;height:100%">']
    arrows = []
    for e in edges:
        tgt_i = next((i for i, n in enumerate(nodes) if n["id"] == e.get("to")), -1)
        lit = tgt_i <= lit_up_to
        a, b = pos.get(e.get("from")), pos.get(e.get("to"))
        if not a or not b:
            continue
        color = "#2563eb" if lit else "#cbd5e1"
        w = 0.55 if lit else 0.35
        svg.append(f'<line x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}" '
                   f'stroke="{color}" stroke-width="{w}" '
                   f'style="{"filter:drop-shadow(0 0 1.2px rgba(37,99,235,.7))" if lit else ""}"/>')
    svg.append("</svg>")

    node_html = []
    for i, n in enumerate(nodes):
        sub = f'<span class="fsub">{_esc(n.get("sub", ""))}</span>' if n.get("sub") else ""
        if i < lit_up_to:
            cls, glow = "lit", ""
        elif i == lit_up_to:
            cls = "cur"
            glow = (f'box-shadow:0 10px 34px rgba(37,99,235,{0.35 + 0.2 * breathe:.2f});')
        else:
            cls, glow = "", ""
        node_html.append(f'<div class="fnode {cls}" style="left:{n["x"]}%;top:{n["y"]}%;{glow}">'
                         f'{_esc(n["label"])}{sub}</div>')

    return (f'<div class="stage" style="background:transparent;border:none;box-shadow:none;'
            f'transform:translateY({ty}px);opacity:{op}">'
            f'<div class="flowwrap">{"".join(svg)}{"".join(node_html)}</div></div>')
