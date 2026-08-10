"""节点图/知识图谱画面渲染：中心辐射式布局 + 动态连线 + 动效。

横屏 16:9（1920x1080）。中心节点为当前讲解概念（放大发光），关联节点环绕。
连线从中心向外延伸，已讲解的节点保持半亮，未讲解的节点暗淡。

两种主题：dark（默认，科幻青蓝）/ light（亮色中性，深蓝主色）。

动效（通过每帧 t_in_segment 参数驱动，保证截图序列连贯）：
  1. 节点入场缩放：新激活节点从 0.3→1.0 缩放
  2. 中心节点呼吸：scale 正弦波动
  3. 脉冲环扩散：active 节点外额外圆环周期扩散
  4. 连线扫描光：stroke-dashoffset 随时间滚动
"""
from __future__ import annotations
import math


def _esc(text) -> str:
    if text is None:
        return ""
    s = str(text)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ========== 主题色板 ==========
_THEMES = {
    "dark": {
        "bg_top": "#0a0e17",
        "bg_bot": "#060a11",
        "grid": "rgba(34,211,238,0.06)",
        "header_bg": "rgba(10,14,23,0.85)",
        "series_color": "#22d3ee",
        "series_shadow": "rgba(34,211,238,0.6)",
        "title_color": "#ffffff",
        "title_shadow": "rgba(34,211,238,0.5)",
        "text_color": "#ffffff",
        "text_shadow": "rgba(34,211,238,0.8)",
        "center_fill": "radial-gradient(circle, rgba(34,211,238,0.25) 0%, rgba(34,211,238,0.08) 60%, transparent 100%)",
        "center_border": "rgba(34,211,238,0.7)",
        "center_glow": "0 0 60px rgba(34,211,238,0.6), inset 0 0 40px rgba(34,211,238,0.2)",
        "sat_fill": "radial-gradient(circle, rgba(34,211,238,0.15) 0%, rgba(34,211,238,0.05) 60%, transparent 100%)",
        "sat_border": "rgba(34,211,238,0.4)",
        "sat_glow": "0 0 30px rgba(34,211,238,0.3)",
        "sat_active_fill": "radial-gradient(circle, rgba(34,211,238,0.35) 0%, rgba(34,211,238,0.12) 60%, transparent 100%)",
        "sat_active_border": "rgba(34,211,238,0.95)",
        "sat_active_glow": "0 0 50px rgba(34,211,238,0.7), inset 0 0 30px rgba(34,211,238,0.15)",
        "sat_done_fill": "radial-gradient(circle, rgba(34,211,238,0.12) 0%, rgba(34,211,238,0.04) 60%, transparent 100%)",
        "sat_done_border": "rgba(34,211,238,0.5)",
        "sat_done_glow": "0 0 25px rgba(34,211,238,0.4)",
        "text_done": "rgba(255,255,255,0.65)",
        "text_future": "rgba(255,255,255,0.25)",
        "edge_color": "rgba(34,211,238,0.45)",
        "edge_active": "rgba(34,211,238,0.95)",
        "edge_active_glow": "drop-shadow(0 0 8px rgba(34,211,238,0.6))",
        "edge_done": "rgba(34,211,238,0.55)",
        "pulse_color": "rgba(34,211,238,0.5)",
        "subtitle_bg": "rgba(10,14,23,0.92)",
        "subtitle_border": "rgba(34,211,238,0.4)",
        "subtitle_text": "#ffffff",
        "progress_track": "rgba(34,211,238,0.12)",
        "progress_fill": "linear-gradient(90deg, #06b6d4, #22d3ee)",
        "progress_glow": "0 0 20px rgba(34,211,238,1), 0 0 40px rgba(34,211,238,0.6)",
        "particle_color": "#22d3ee",
    },
    "light": {
        "bg_top": "#f1f5f9",
        "bg_bot": "#e2e8f0",
        "grid": "rgba(37,99,235,0.07)",
        "header_bg": "rgba(241,245,249,0.85)",
        "series_color": "#2563eb",
        "series_shadow": "rgba(37,99,235,0.4)",
        "title_color": "#0f172a",
        "title_shadow": "rgba(37,99,235,0.3)",
        "text_color": "#0f172a",
        "text_shadow": "rgba(37,99,235,0.5)",
        "center_fill": "radial-gradient(circle, #ffffff 0%, #e0e7ff 60%, #c7d2fe 100%)",
        "center_border": "rgba(37,99,235,0.8)",
        "center_glow": "0 0 40px rgba(37,99,235,0.3), 0 4px 20px rgba(37,99,235,0.15)",
        "sat_fill": "radial-gradient(circle, #ffffff 0%, #f1f5f9 60%, #e2e8f0 100%)",
        "sat_border": "rgba(37,99,235,0.45)",
        "sat_glow": "0 0 20px rgba(37,99,235,0.2), 0 2px 10px rgba(37,99,235,0.1)",
        "sat_active_fill": "radial-gradient(circle, #ffffff 0%, #dbeafe 60%, #bfdbfe 100%)",
        "sat_active_border": "rgba(37,99,235,0.95)",
        "sat_active_glow": "0 0 35px rgba(37,99,235,0.45), 0 0 70px rgba(37,99,235,0.2)",
        "sat_done_fill": "radial-gradient(circle, #ffffff 0%, #f1f5f9 60%, #e2e8f0 100%)",
        "sat_done_border": "rgba(37,99,235,0.55)",
        "sat_done_glow": "0 0 15px rgba(37,99,235,0.2)",
        "text_done": "#475569",
        "text_future": "#94a3b8",
        "edge_color": "rgba(37,99,235,0.35)",
        "edge_active": "rgba(37,99,235,0.95)",
        "edge_active_glow": "drop-shadow(0 0 6px rgba(37,99,235,0.4))",
        "edge_done": "rgba(37,99,235,0.5)",
        "pulse_color": "rgba(37,99,235,0.35)",
        "subtitle_bg": "rgba(15,23,42,0.92)",
        "subtitle_border": "rgba(37,99,235,0.5)",
        "subtitle_text": "#ffffff",
        "progress_track": "rgba(37,99,235,0.12)",
        "progress_fill": "linear-gradient(90deg, #2563eb, #60a5fa)",
        "progress_glow": "0 0 20px rgba(37,99,235,0.8), 0 0 40px rgba(37,99,235,0.4)",
        "particle_color": "#2563eb",
    },
}


def _build_css(theme: dict, w: int, h: int) -> str:
    return f"""* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ width: {w}px; height: {h}px; }}
body {{
  font-family: "Microsoft YaHei", "微软雅黑", "PingFang SC", sans-serif;
  background: radial-gradient(ellipse at center, {theme['bg_top']} 0%, {theme['bg_bot']} 100%);
  color: {theme['text_color']}; position: relative; overflow: hidden;
  -webkit-font-smoothing: antialiased;
}}
.grid {{
  position: absolute; inset: 0;
  background-image:
    linear-gradient({theme['grid']} 1px, transparent 1px),
    linear-gradient(90deg, {theme['grid']} 1px, transparent 1px);
  background-size: 60px 60px; pointer-events: none;
}}
.header {{
  position: absolute; top: 0; left: 0; right: 0; height: 80px;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 60px; z-index: 10;
  background: linear-gradient(180deg, {theme['header_bg']} 0%, transparent 100%);
}}
.series {{ font-size: 22px; color: {theme['series_color']}; letter-spacing: 4px; font-weight: 700;
  text-shadow: 0 0 15px {theme['series_shadow']}; }}
.title {{ font-size: 32px; font-weight: 700; color: {theme['title_color']};
  text-shadow: 0 0 20px {theme['title_shadow']}, 0 2px 10px rgba(0,0,0,0.3); }}
.graph-container {{
  position: absolute; top: 80px; left: 0; right: 0; bottom: 140px;
}}
.center-node {{
  position: absolute; display: flex; align-items: center; justify-content: center;
  text-align: center; z-index: 5;
}}
.center-node .node-bg {{
  position: absolute; inset: 0; border-radius: 50%;
  background: {theme['center_fill']};
  border: 3px solid {theme['center_border']};
  box-shadow: {theme['center_glow']};
}}
.center-node .node-text {{
  position: relative; z-index: 2; padding: 20px;
  font-size: 36px; font-weight: 800; line-height: 1.3; color: {theme['text_color']};
  text-shadow: 0 0 20px {theme['text_shadow']};
}}
.satellite-node {{
  position: absolute; display: flex; align-items: center; justify-content: center;
  text-align: center;
}}
.satellite-node .node-bg {{
  position: absolute; inset: 0; border-radius: 50%;
  background: {theme['sat_fill']};
  border: 2px solid {theme['sat_border']};
  box-shadow: {theme['sat_glow']};
}}
.satellite-node.active .node-bg {{
  background: {theme['sat_active_fill']};
  border: 3px solid {theme['sat_active_border']};
  box-shadow: {theme['sat_active_glow']};
}}
.satellite-node.done .node-bg {{
  background: {theme['sat_done_fill']};
  border: 2px solid {theme['sat_done_border']};
  box-shadow: {theme['sat_done_glow']};
}}
.satellite-node.future .node-bg {{
  opacity: 0.45;
}}
.satellite-node .node-text {{
  position: relative; z-index: 2; padding: 16px;
  font-size: 24px; font-weight: 600; line-height: 1.3; color: {theme['text_color']};
}}
.satellite-node.active .node-text {{
  font-size: 28px; font-weight: 700; color: {theme['text_color']};
  text-shadow: 0 0 15px {theme['text_shadow']};
}}
.satellite-node.done .node-text {{ color: {theme['text_done']}; }}
.satellite-node.future .node-text {{ color: {theme['text_future']}; }}
.edges-svg {{ position: absolute; inset: 0; pointer-events: none; z-index: 1; }}
.edge-line {{ stroke: {theme['edge_color']}; stroke-width: 2; fill: none; stroke-linecap: round; }}
.edge-line.active {{
  stroke: {theme['edge_active']}; stroke-width: 3;
  filter: {theme['edge_active_glow']};
}}
.edge-line.done {{ stroke: {theme['edge_done']}; stroke-width: 2; }}
.pulse-ring {{
  position: absolute; border-radius: 50%; pointer-events: none;
  border: 2px solid {theme['pulse_color']}; opacity: 0;
}}
.subtitle-band {{
  position: absolute; left: 60px; right: 60px; bottom: 40px; height: 80px;
  background: {theme['subtitle_bg']}; border: 1px solid {theme['subtitle_border']};
  border-radius: 12px; display: flex; align-items: center; justify-content: center;
  overflow: hidden; z-index: 10;
  box-shadow: 0 4px 20px rgba(0,0,0,0.3), inset 0 0 20px rgba(0,0,0,0.1);
}}
.subtitle {{
  font-size: 32px; line-height: 1; color: {theme['subtitle_text']}; text-align: center; max-width: 100%;
  padding: 0 30px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  text-shadow: 0 2px 4px rgba(0,0,0,0.95);
}}
.subtitle.empty {{ visibility: hidden; }}
.progress-track {{
  position: absolute; left: 0; right: 0; bottom: 0; height: 5px;
  background: {theme['progress_track']}; z-index: 10;
}}
.progress-fill {{
  height: 100%; background: {theme['progress_fill']};
  box-shadow: {theme['progress_glow']};
}}
.particles {{ position: absolute; inset: 0; pointer-events: none; opacity: 0.35; z-index: 0; }}
"""


def _calc_node_positions(node_count: int, cx: int, cy: int, radius: int) -> list[tuple[int, int]]:
    positions = []
    angle_step = 2 * math.pi / max(node_count, 1)
    # 从顶部开始，顺时针
    for i in range(node_count):
        angle = -math.pi / 2 + i * angle_step
        positions.append((int(cx + radius * math.cos(angle)), int(cy + radius * math.sin(angle))))
    return positions


def render_frame(
    graph_data: dict,
    active_node_idx: int,
    subtitle: str = "",
    progress: float = 0.0,
    width: int = 1920,
    height: int = 1080,
    theme: str = "dark",
    t_in_segment: float = 0.5,
) -> str:
    """渲染一帧节点图 HTML。

    theme: "dark"（科幻青蓝）或 "light"（亮色中性，深蓝主色）
    t_in_segment: 当前段内时间进度 0~1，用于驱动动效
    """
    theme_cfg = _THEMES.get(theme, _THEMES["dark"])
    series = graph_data.get("series", "")
    title = graph_data.get("title", "")
    center = graph_data.get("center", {})
    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])

    css = _build_css(theme_cfg, width, height)

    # 布局
    cx = width // 2
    cy = (height - 140 - 80) // 2 + 80
    radius = min(width, height - 260) // 3

    center_label = center.get("label", "")
    center_size = 280

    # 动效：中心节点呼吸（scale 正弦波动）
    center_breath = 1.0 + 0.04 * math.sin(t_in_segment * math.pi * 2)

    # 顶部标题
    header = f"""<div class="header">
  <div class="series">{_esc(series)}</div>
  <div class="title">{_esc(title)}</div>
</div>"""

    # 中心节点（带呼吸动效）
    cs = int(center_size * center_breath)
    center_node = f"""<div class="center-node" style="left:{cx - cs//2}px;top:{cy - cs//2}px;width:{cs}px;height:{cs}px;">
  <div class="node-bg"></div>
  <div class="node-text">{_esc(center_label)}</div>
</div>"""

    # 卫星节点位置
    node_positions = _calc_node_positions(len(nodes), cx, cy, radius)

    satellites_html_parts = []
    for i, node in enumerate(nodes):
        x, y = node_positions[i]
        label = node.get("label", "")
        size = 180

        if i == active_node_idx:
            state_cls = "active"
        elif i < active_node_idx:
            state_cls = "done"
        else:
            state_cls = "future"

        # 动效 1: 入场缩放（刚激活的节点从 0.3→1.0）
        # 假设节点激活时刻在 t=0.15，从 0.15~0.4 完成入场
        entry_scale = 1.0
        if state_cls == "active":
            entry_t = max(0, (t_in_segment - 0.05) / 0.3)
            entry_t = min(1, entry_t)
            # ease-out-back
            entry_scale = 0.3 + 0.7 * (1 - math.pow(1 - entry_t, 3))

        # 动效 2: 脉冲环（active 节点额外扩散圆环）
        pulse_ring_html = ""
        if state_cls == "active":
            # 脉冲周期 1.5 秒，t_in_segment 0~1 对应约 1 周期
            pulse_phase = (t_in_segment * 1.5) % 1.0
            pulse_radius = size // 2 + pulse_phase * 60
            pulse_opacity = max(0, 0.6 - pulse_phase * 0.7)
            pulse_ring_html = f'''<div class="pulse-ring" style="
                left:{x - pulse_radius}px; top:{y - pulse_radius}px;
                width:{pulse_radius*2}px; height:{pulse_radius*2}px;
                opacity:{pulse_opacity:.2f};"></div>'''

        satellites_html_parts.append(
            f'{pulse_ring_html}'
            f'<div class="satellite-node {state_cls}" style="'
            f'left:{x - size//2}px;top:{y - size//2}px;width:{size}px;height:{size}px;'
            f'transform:scale({entry_scale});transform-origin:center;">'
            f'<div class="node-bg"></div>'
            f'<div class="node-text">{_esc(label)}</div>'
            f'</div>'
        )
    satellites_html = "\n".join(satellites_html_parts)

    # 连线（动效 3: 扫描 dashoffset）
    dash_offset = (t_in_segment * 40) % 24
    edge_lines = []
    for edge in edges:
        from_id = edge.get("from", "")
        to_id = edge.get("to", "")

        if from_id == "center":
            x1, y1 = cx, cy
        else:
            fi = next((i for i, n in enumerate(nodes) if n.get("id") == from_id), None)
            if fi is None:
                continue
            x1, y1 = node_positions[fi]

        if to_id == "center":
            x2, y2 = cx, cy
        else:
            ti = next((i for i, n in enumerate(nodes) if n.get("id") == to_id), None)
            if ti is None:
                continue
            x2, y2 = node_positions[ti]

        # 状态判定
        if to_id != "center":
            ti = next((i for i, n in enumerate(nodes) if n.get("id") == to_id), -1)
            if ti == active_node_idx:
                line_cls = "active"
                dash_style = f'stroke-dasharray: 12 6; stroke-dashoffset: {-dash_offset};'
            elif ti < active_node_idx:
                line_cls = "done"
                dash_style = ""
            else:
                line_cls = ""
                dash_style = f'stroke-dasharray: 8 4; stroke-dashoffset: {-dash_offset * 0.5};'
        else:
            line_cls = ""
            dash_style = ""

        edge_lines.append(
            f'<line class="edge-line {line_cls}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" style="{dash_style}"/>'
        )
    edges_svg = f"""<svg class="edges-svg" viewBox="0 0 {width} {height}">
{chr(10).join(edge_lines)}
</svg>"""

    # 粒子
    color = theme_cfg['particle_color']
    particles = f"""<svg class="particles" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <radialGradient id="star"><stop offset="0%" stop-color="{color}" stop-opacity="0.6"/>
      <stop offset="100%" stop-color="{color}" stop-opacity="0"/></radialGradient>
  </defs>
  <circle cx="180" cy="220" r="2" fill="url(#star)"/>
  <circle cx="520" cy="150" r="1.5" fill="url(#star)"/>
  <circle cx="850" cy="380" r="2.5" fill="url(#star)"/>
  <circle cx="1300" cy="200" r="1.8" fill="url(#star)"/>
  <circle cx="1600" cy="480" r="2.2" fill="url(#star)"/>
  <circle cx="350" cy="750" r="1.6" fill="url(#star)"/>
  <circle cx="980" cy="850" r="2" fill="url(#star)"/>
  <circle cx="1700" cy="780" r="1.4" fill="url(#star)"/>
</svg>"""

    # 字幕 + 进度
    sub_cls = "subtitle" if subtitle else "subtitle empty"
    subtitle_band = f'<div class="subtitle-band"><div class="{sub_cls}">{_esc(subtitle)}</div></div>'
    pct = max(0.0, min(1.0, progress)) * 100.0
    progress_bar = f'<div class="progress-track"><div class="progress-fill" style="width:{pct:.2f}%"></div></div>'

    body = f"""{header}
<div class="graph-container">
  {edges_svg}
  {center_node}
  {satellites_html}
</div>
{particles}
{subtitle_band}
{progress_bar}"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>graph</title>
<style>{css}</style></head>
<body><div class="grid"></div>{body}</body></html>"""


if __name__ == "__main__":
    import json
    from pathlib import Path
    from playwright.sync_api import sync_playwright

    graph_data = {
        "series": "AI 研发实战",
        "title": "4 个人 + AI 交付百万行",
        "center": {"label": "工程体系"},
        "nodes": [
            {"id": "n1", "label": "命令化"},
            {"id": "n2", "label": "评审回路"},
            {"id": "n3", "label": "规范固化"},
            {"id": "n4", "label": "技能库"},
        ],
        "edges": [
            {"from": "center", "to": "n1"},
            {"from": "center", "to": "n2"},
            {"from": "center", "to": "n3"},
            {"from": "center", "to": "n4"},
            {"from": "n1", "to": "n2"},
            {"from": "n2", "to": "n3"},
            {"from": "n3", "to": "n4"},
        ],
    }

    root = Path(__file__).resolve().parents[2]
    from config import OUTPUT_ROOT
    out_dir = OUTPUT_ROOT / "build" / "_graph_theme_test"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 生成暗色 + 亮色对比
    states = [
        (-1, "4 个人加 AI，2 个月交付近百万行", 0.05, 0.5),
        (0, "第一块，命令化工作流", 0.25, 0.5),
        (1, "第二块，自治评审回路", 0.50, 0.3),
        (2, "第三块，规范固化加技能库", 0.75, 0.8),
        (3, "体系的厚度决定 AI 杠杆能放多大", 1.0, 0.6),
    ]

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        for theme in ["dark", "light"]:
            theme_dir = out_dir / theme
            theme_dir.mkdir(exist_ok=True)
            for idx, sub, prog, tseg in states:
                html = render_frame(graph_data, idx, sub, prog, theme=theme, t_in_segment=tseg)
                (theme_dir / "frame.html").write_text(html, encoding="utf-8")
                page.set_content(html)
                page.wait_for_timeout(200)
                shot = theme_dir / f"n{idx+1}.png"
                page.screenshot(path=str(shot))
                print(f"[{theme}] n{idx+1}: {shot} ({shot.stat().st_size} bytes)")
        browser.close()
    print("DONE")
