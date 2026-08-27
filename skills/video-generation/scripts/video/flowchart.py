"""流程图原语（flow）：课件右栏的链式流程画布，帧驱动逐节点动画。

openspec courseware-motion-linkage：节点弹出（ease-out-back）+ 标签逐字浮现 +
连线 dashoffset 生长（ease-in-out）+ 跑线扫光（亮段单程扫过）+ 箭头淡入，
节点出生帧 = 要点亮起帧（point_births[k]，时间接近原则：讲到哪步动到哪步）。
动画窗口外不输出 inline style / 不输出扫光元素 → HTML 相等性保持（PNG 复用）。

deck 卡字段（insight 卡，与 sub_points 互斥，flow 优先）：
    "flow": {"nodes": [{"id": "n1", "label": "口播断句"}, ...],
             "edges": [["n1", "n2"], ["n2", "n3"]]}   # 链式，edges 声明顺序
"""
from __future__ import annotations

from .motion import (
    ease_in_out_sine,
    ease_out_back,
    exit_tuple,
    glow_mult,
    type_chars,
)

_NODE_W, _NODE_H = 560, 112
_EDGE_H = 78
_LINE_Y0, _LINE_Y1 = 4, 64          # 连线起止 y（长度 60）
_L = _LINE_Y1 - _LINE_Y0            # 线长
_GROW_DUR, _SWEEP_DUR = 10, 8       # 生长 10 帧 + 跑线 8 帧
_POP_DUR, _TYPE_DUR = 9, 12         # 节点弹出 / 标签逐字

_FLOW_CSS = f"""
.flow-wrap {{ width:100%; height:100%; display:flex; flex-direction:column;
  align-items:center; justify-content:center; }}
.fnode {{ width:{_NODE_W}px; height:{_NODE_H}px; border-radius:16px;
  display:flex; align-items:center; gap:22px; padding:0 32px;
  background:rgba(15,23,42,0.5); }}
.fnode.future {{ border:2px dashed rgba(148,163,184,0.4); opacity:0.4; }}
.fnode.done {{ border:2px solid rgba(34,211,238,0.35); }}
.fnode.active {{ border:2px solid #22d3ee; background:rgba(15,23,42,0.85);
  box-shadow:0 0 50px rgba(34,211,238,0.35), inset 0 0 40px rgba(34,211,238,0.08); }}
.fnum {{ font-size:30px; font-weight:800; color:#22d3ee; letter-spacing:2px;
  text-shadow:0 0 18px rgba(34,211,238,0.8); }}
.fnode.future .fnum {{ color:rgba(148,163,184,0.6); text-shadow:none; }}
.flabel {{ font-size:40px; font-weight:700; color:#ffffff; letter-spacing:2px;
  white-space:nowrap; overflow:hidden; }}
.fnode.done .flabel {{ color:rgba(203,213,225,0.8); }}
.fnode.future .flabel {{ visibility:hidden; }}
.fedge {{ height:{_EDGE_H}px; display:flex; justify-content:center; }}
.fghost {{ stroke:rgba(148,163,184,0.35); stroke-width:2; stroke-dasharray:6 8; fill:none; }}
.fedge.grow .fghost, .fedge.done .fghost {{ display:none; }}
.fline {{ stroke:#22d3ee; stroke-width:3; fill:none;
  filter:drop-shadow(0 0 6px rgba(34,211,238,0.8)); }}
.fedge.future .fline {{ visibility:hidden; }}
.fsweep {{ stroke:#ffffff; stroke-width:5; fill:none; stroke-linecap:round;
  filter:drop-shadow(0 0 9px rgba(255,255,255,0.9)); }}
.farrow {{ fill:#22d3ee; opacity:0.9; filter:drop-shadow(0 0 6px rgba(34,211,238,0.7)); }}
.fedge.future .farrow {{ opacity:0; }}
"""


def _esc(text) -> str:
    s = str(text if text is not None else "")
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _style_attr(value: str) -> str:
    return f' style="{value}"' if value else ""


def render_flow(flow: dict, state: dict) -> str:
    """渲染流程画布 HTML 片段（含 <style>）。state 需 frame/point_births/active_idx。"""
    frame = int(state.get("frame", 10**6))
    births = [int(b) for b in (state.get("point_births") or [])]
    active_idx = int(state.get("active_idx", -1))
    out_at = state.get("out_at")
    nodes = flow.get("nodes") or []
    if not nodes:
        return ""
    idx_of = {n.get("id", f"n{i}"): i for i, n in enumerate(nodes)}
    # 指向节点 k 的边（按 edges 声明取 to == 节点 k 的 id；链式即第 k-1 条）
    edge_into = {k: None for k in range(len(nodes))}
    for e in flow.get("edges") or []:
        to_idx = idx_of.get(e[1] if isinstance(e, (list, tuple)) else e.get("to"))
        if to_idx is not None:
            edge_into[to_idx] = e

    parts = [f"<style>{_FLOW_CSS}</style>", '<div class="flow-wrap">']
    for k, node in enumerate(nodes):
        if k > 0 and edge_into.get(k) is not None:
            parts.append(_edge_html(k, frame, births, out_at))
        parts.append(_node_html(k, node, frame, births, active_idx, out_at))
    parts.append("</div>")
    return "\n".join(parts)


def _node_html(k: int, node: dict, frame: int, births: list[int],
               active_idx: int, out_at=None) -> str:
    label = node.get("label", "")
    birth = births[k] if k < len(births) else None
    cls = "fnode done" if k < active_idx else ("fnode active" if k == active_idx else "fnode future")
    born = birth is not None and frame >= birth
    op, ty, sc = (0.4, 0.0, 1.0) if not born else (1.0, 0.0, 1.0)  # 幽灵基态 / 实体基态
    extra = ""
    if born and frame - birth < _POP_DUR:
        # 从幽灵态（opacity≈0.4）连续弹到实体：不重置到 0，避免闪没
        t = ease_out_back((frame - birth) / _POP_DUR)
        t_c = max(0.0, min(1.0, t))
        op = 0.42 + 0.58 * t_c
        ty = 16.0 * (1.0 - t)
        sc = 0.85 + 0.15 * t
        if k == active_idx:
            g = glow_mult(frame - birth, 8, 0.8)
            if g is not None:
                m = 1.0 + g
                extra = (f"box-shadow:0 0 {50 * m:.0f}px rgba(34,211,238,{min(1.0, 0.35 * m):.2f}),"
                         f"inset 0 0 40px rgba(34,211,238,{min(1.0, 0.08 * m):.2f})")
    # 卡尾出场：节点按链序错峰（k 帧），幽灵态的 0.4 基础透明度参与合成
    if out_at is not None:
        ex = exit_tuple(frame - (int(out_at) + k), 5, dy=-30.0)
        if ex is not None:
            op *= ex[0]; ty += ex[1]; sc *= ex[2]
    style = ""
    settled = abs(op - (0.4 if not born else 1.0)) < 0.005 and abs(ty) < 0.02 \
        and abs(sc - 1.0) < 0.0015 and not extra
    if not settled:
        segs = [f"opacity:{max(0.0, op):.3f}",
                f"transform:translateY({ty:.2f}px) scale({sc:.4f})"]
        if extra:
            segs.append(extra)
        style = ";".join(segs)
    # 标签逐字浮现（出生帧 +2 起，未出生不显示）
    text = _esc(label)
    if born and frame >= birth + 2:
        text = _esc(type_chars(label, frame - (birth + 2), _TYPE_DUR))
    return (f'<div class="{cls}"{_style_attr(style)}>'
            f'<div class="fnum">{k + 1:02d}</div>'
            f'<div class="flabel">{text}</div></div>')


def _edge_html(k: int, frame: int, births: list[int], out_at=None) -> str:
    """指向节点 k 的连线：ghost 虚线 → 生长 → 跑线 → 定格实线；卡尾随容器淡出。"""
    div_style = ""
    if out_at is not None:
        ex = exit_tuple(frame - (int(out_at) + 2), 4, dy=-24.0)
        if ex is not None:
            div_style = f' style="opacity:{ex[0]:.3f};transform:translateY({ex[1]:.2f}px)"'
    nb = births[k] if k < len(births) else None
    if nb is None:
        cls = "fedge future"
        return (f'<div class="{cls}"{div_style}><svg width="120" height="{_EDGE_H}">'
                f'<path class="fghost" d="M60 {_LINE_Y0} V{_LINE_Y1}"/>'
                f'<path class="fline" d="M60 {_LINE_Y0} V{_LINE_Y1}"/>'
                f'<path class="farrow" d="M60 {_LINE_Y1 + 14} L52 {_LINE_Y1} L68 {_LINE_Y1} Z"/></svg></div>')
    birth = max(0, nb - 4)                     # 先于节点 4 帧开始生长
    age = frame - birth
    if age < 0:
        cls = "fedge future"
        return (f'<div class="{cls}"{div_style}><svg width="120" height="{_EDGE_H}">'
                f'<path class="fghost" d="M60 {_LINE_Y0} V{_LINE_Y1}"/>'
                f'<path class="fline" d="M60 {_LINE_Y0} V{_LINE_Y1}"/>'
                f'<path class="farrow" d="M60 {_LINE_Y1 + 14} L52 {_LINE_Y1} L68 {_LINE_Y1} Z"/></svg></div>')
    if age < _GROW_DUR:                        # 生长期：dashoffset 插值
        cls = "fedge grow"
        t = ease_in_out_sine(age / _GROW_DUR)
        off = _L * (1.0 - t)
        line = (f'<path class="fline" d="M60 {_LINE_Y0} V{_LINE_Y1}" '
                f'style="stroke-dasharray:{_L};stroke-dashoffset:{off:.2f}"/>')
        arrow_op = max(0.0, (age - 8) / 2.0) if age > 8 else 0.0
        arrow = (f'<path class="farrow" d="M60 {_LINE_Y1 + 14} L52 {_LINE_Y1} L68 {_LINE_Y1} Z" '
                 f'style="opacity:{arrow_op:.2f}"/>' if arrow_op > 0.01 else "")
        return (f'<div class="{cls}"{div_style}><svg width="120" height="{_EDGE_H}">'
                f'{line}{arrow or _hidden_arrow()}</svg></div>')
    if age < _GROW_DUR + _SWEEP_DUR:           # 跑线：亮段单程扫过
        cls = "fedge done"
        p = (age - _GROW_DUR) / _SWEEP_DUR
        sweep_off = 114.0 - 82.0 * p           # 亮段从线尾滑入滑出
        line = f'<path class="fline" d="M60 {_LINE_Y0} V{_LINE_Y1}"/>'
        sweep = (f'<path class="fsweep" d="M60 {_LINE_Y0} V{_LINE_Y1}" '
                 f'style="stroke-dasharray:16 82;stroke-dashoffset:{sweep_off:.2f}"/>')
        return (f'<div class="{cls}"{div_style}><svg width="120" height="{_EDGE_H}">'
                f'{line}{sweep}<path class="farrow" d="M60 {_LINE_Y1 + 14} L52 {_LINE_Y1} L68 {_LINE_Y1} Z"/></svg></div>')
    cls = "fedge done"                          # 定格：无 inline（HTML 相等性）
    return (f'<div class="{cls}"{div_style}><svg width="120" height="{_EDGE_H}">'
            f'<path class="fline" d="M60 {_LINE_Y0} V{_LINE_Y1}"/>'
            f'<path class="farrow" d="M60 {_LINE_Y1 + 14} L52 {_LINE_Y1} L68 {_LINE_Y1} Z"/></svg></div>')


def _hidden_arrow() -> str:
    return (f'<path class="farrow" d="M60 {_LINE_Y1 + 14} L52 {_LINE_Y1} L68 {_LINE_Y1} Z" '
            f'style="opacity:0"/>')
