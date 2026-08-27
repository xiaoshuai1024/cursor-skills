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
from .palette import (          # 色板 SSOT（openspec video-color-retention，2026-08-25）
    LIGHT_ACCENT as BLUE,
    LIGHT_ACCENT_DARK as BLUE_DARK,
    TERM_GREEN as GREEN,
    TUTORIAL_INK as INK,
    LIGHT_MUTED as MUTED,
)

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
.term .row.done { color:#64748b; }  /* 终端done行 2026-08-25 升档:#94a3b8 ≈2.7:1 → ≈4.6:1 */
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

/* ---- 卡内镜头舞台（openspec card-shots 2026-08-26）：stage 区按口播节拍轮换素材 ---- */
.shotlayer { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; }
.shot-tag { margin-left:auto; background:#eff6ff; color:__BLUE_DARK__; border:1.5px solid #bfdbfe;
  font-size:19px; font-weight:700; padding:3px 12px; border-radius:6px; letter-spacing:2px; }
.shot-tree { width:94%; background:#fbfcfe; border:1.5px solid #e2e8f0; border-radius:12px; overflow:hidden; }
.shot-tree .term { font-size:29px; }
.trow { padding:2px 12px; white-space:pre; }
.trow .dir { color:__BLUE_DARK__; font-weight:700; }
.trow .note { color:#94a3b8; }
.shot-trow { font-family:Consolas,"JetBrains Mono",monospace; font-size:29px; line-height:1.85;
  white-space:pre-wrap; }
.shot-trow.cmd { color:__BLUE_DARK__; font-weight:700; }
.shot-trow.out { color:#334155; }
.shot-trow.ok { color:#16a34a; }
.shot-trow.err { color:#dc2626; }
.shot-trow.dim { color:#64748b; }
.shot-stat { display:flex; flex-direction:column; align-items:center; gap:20px; }
.shot-stat .big { font-size:118px; font-weight:800; color:__BLUE__; line-height:1;
  font-family:Consolas,"JetBrains Mono",monospace; letter-spacing:2px; }
.shot-stat .label { font-size:36px; font-weight:700; color:#334155; }
.shot-stat .sub { font-size:26px; color:#64748b; }
.shot-table { width:94%; border-collapse:collapse; background:#fff; border:1.5px solid #e2e8f0;
  border-radius:12px; overflow:hidden; box-shadow:0 10px 30px rgba(30,41,59,.07); }
.shot-table th { font-size:29px; color:__BLUE_DARK__; background:#eff6ff; font-weight:700;
  padding:18px 24px; border-bottom:2px solid #bfdbfe; text-align:left; }
.shot-table td { font-size:29px; color:#334155; padding:17px 24px;
  border-bottom:1px solid #eef2f7; }
.shot-table tr.hlrow td { background:#eff6ff; color:__BLUE_DARK__; font-weight:700; }
.shot-quote { display:flex; flex-direction:column; gap:24px; padding:0 40px; max-width:92%; }
.shot-quote .mark { font-size:100px; line-height:.4; color:#bfdbfe; font-family:Georgia,serif; }
.shot-quote .qtext { font-size:44px; font-weight:700; line-height:1.55; color:#1e293b; }
.shot-quote .qsrc { font-size:23px; color:#94a3b8; font-family:Consolas,monospace; }
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

    # ---- 主区（卡内镜头轮换 > 截图 / 终端 / 代码 / 流程图） ----
    if card.get("shots"):
        stage = _shots_stage(card, state, breathe)
    elif kind == "code":
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

    # ---- 要点区（全部可见，active 高亮；纯 flow 卡全宽不显示，shots 模式恒显示） ----
    pt_html = ""
    if points and (card.get("shots") or kind != "flow"):
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


# ---- 卡内镜头舞台（openspec card-shots 2026-08-26）----

def _shots_stage(card: dict, state: dict, breathe: float) -> str:
    """stage 区镜头轮换：按口播句边界切 shots，新镜头浮入 / 旧镜头淡出（帧驱动）。"""
    shots = card.get("shots") or []
    frame = int(state.get("frame", 10**6))
    shot_idx = int(state.get("shot_idx", -1))
    birth = int(state.get("shot_birth") or 0)
    layers = []
    for si, sh in enumerate(shots):
        if shot_idx < 0 or si > shot_idx:
            continue
        if si == shot_idx:
            age = frame - birth
            if age < 0:
                continue
            e = 1 - (1 - min(1.0, age / 8.0)) ** 3
            ty = round(16 * (1 - e), 1)
            style = (f' style="opacity:{e:.3f};transform:translateY({ty}px)"'
                     if e < 0.999 or ty else "")
        else:                            # 刚被替换的镜头：6 帧上移淡出
            age = frame - birth
            if age >= 6:
                continue
            e = 1 - (1 - min(1.0, age / 6.0)) ** 3
            if e >= 0.999:
                continue
            style = f' style="opacity:{1 - e:.3f};transform:translateY({-round(14 * e, 1)}px)"'
        layers.append(f'<div class="shotlayer"{style}>'
                      f'{_shot_content(sh, card, state, breathe)}</div>')
    return f'<div class="stage">{"".join(layers)}</div>'


def _row_style(frame: int, birth: int, i: int, dur: int = 6) -> str:
    """行级 stagger 出生样式；终态空串（静止段 HTML 稳定 → PNG 复用优化保持）。"""
    age = frame - (birth + 2 + 2 * i)
    if 0 <= age < dur:
        e = 1 - (1 - age / dur) ** 3
        if e < 0.999:
            return f' style="opacity:{e:.3f};transform:translateY({round(8 * (1 - e), 1)}px)"'
    return ""


def _hl_lines(shot: dict, state: dict) -> list[int]:
    """当前高亮行：hl_steps 讲到哪行亮哪行（帧外静态 hl 兜底）。"""
    hl = None
    for t, line in (shot.get("hl_steps") or []):
        if state.get("shot_t_ms", 0) >= float(t) * 1000.0:
            hl = line
    if hl is None:
        hl = shot.get("hl", shot.get("data", {}).get("hl"))
    if hl is None:
        return []
    return [hl] if isinstance(hl, int) else [int(x) for x in hl]


def _shot_content(sh: dict, card: dict, state: dict, breathe: float) -> str:
    kind = sh.get("kind", "code")
    data = sh.get("data") or {}
    frame = int(state.get("frame", 10**6))
    birth = int(state.get("shot_birth") or 0)
    if kind == "flow":
        return _flow_stage(card, int(state.get("active_idx", -1)), breathe, 0, 1)
    if kind == "stat":
        return (f'<div class="shot-stat"><div class="big">{_esc(data.get("big", ""))}</div>'
                f'<div class="label">{_esc(data.get("label", ""))}</div>'
                f'<div class="sub">{_esc(data.get("sub", ""))}</div></div>')
    if kind == "table":
        head = "".join(f"<th>{_esc(h)}</th>" for h in data.get("head", []))
        rows = ""
        for r in data.get("rows", []):
            cls, cells = (' class="hlrow"', r[1:]) if r and r[0] == "*" else ("", r)
            rows += f"<tr{cls}>" + "".join(f"<td>{_esc(c)}</td>" for c in cells) + "</tr>"
        return f'<table class="shot-table"><tr>{head}</tr>{rows}</table>'
    if kind == "quote":
        return ('<div class="shot-quote"><div class="mark">\u201c</div>'
                f'<div class="qtext">{_esc(data.get("text", ""))}</div>'
                f'<div class="qsrc">— {_esc(data.get("source", ""))}</div></div>')
    if kind == "code":
        lines = data.get("lines", [])
        hls = _hl_lines(sh, state)
        rows = []
        for i, ln in enumerate(lines):
            cls = "cl hl" if i in hls else "cl"
            rows.append(f'<div class="{cls}"{_row_style(frame, birth, i)}>'
                        f'<span class="no">{i + 1}</span>'
                        f'<span>{_hl_line(str(ln))}</span></div>')
        tag = _esc(data.get("tag", "源码"))
        return (f'<div class="codewin"><div class="codebar">'
                '<span class="dot" style="background:#fb7185"></span>'
                '<span class="dot" style="background:#fbbf24"></span>'
                '<span class="dot" style="background:#34d399"></span>'
                f'<span class="codetab">{_esc(data.get("title", ""))}</span>'
                f'<span class="shot-tag" style="margin-left:auto">{tag}</span></div>'
                f'<div class="codebody">{"".join(rows)}</div></div>')
    if kind == "tree":
        rows = []
        items = data.get("items", [])
        for i, item in enumerate(items):
            depth, typ, name = 0, "file", item
            if isinstance(item, list):
                typ, name = item[0], item[1]
                depth = item[2] if len(item) > 2 else 0
            elif isinstance(item, str) and item.startswith("**"):
                typ, name = "note", item.strip("* ")
            if typ == "note":
                rows.append(f'<div class="trow"{_row_style(frame, birth, i)}>'
                            f'<span class="note">{_esc(name)}</span></div>')
            else:
                glyph, span = ("\u25b8 ", "dir") if typ == "dir" else ("\u25aa ", "")
                marked = (f'<span class="{span}">{_esc(glyph + name)}</span>'
                          if span else _esc(glyph + name))
                rows.append(f'<div class="trow"{_row_style(frame, birth, i)}>'
                            f'{"    " * depth}{marked}</div>')
        return (f'<div class="shot-tree"><div class="termbar">'
                '<span class="dot" style="background:#fb7185"></span>'
                '<span class="dot" style="background:#fbbf24"></span>'
                '<span class="dot" style="background:#34d399"></span>'
                f'<span class="termtitle">{_esc(data.get("title", "结构"))}</span>'
                '<span class="shot-tag" style="margin-left:auto">结构</span></div>'
                f'<div class="term">{"".join(rows)}</div></div>')
    # term：终端演示（cmd/out/ok/err/dim 行色）
    rows = []
    for i, item in enumerate(data.get("lines", [])):
        if isinstance(item, str):
            text, cls = item, "out"
        else:
            text, cls = item.get("t", ""), item.get("c", "out")
        rows.append(f'<div class="shot-trow {cls}"{_row_style(frame, birth, i)}>'
                    f'{_esc(text)}</div>')
    return (f'<div class="termwin"><div class="termbar">'
            '<span class="dot" style="background:#fb7185"></span>'
            '<span class="dot" style="background:#fbbf24"></span>'
            '<span class="dot" style="background:#34d399"></span>'
            f'<span class="termtitle">{_esc(data.get("title", "终端"))}</span>'
            '<span class="shot-tag" style="margin-left:auto">终端</span></div>'
            f'<div class="term">{"".join(rows)}</div></div>')
