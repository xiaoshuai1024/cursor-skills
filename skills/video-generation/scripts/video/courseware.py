"""课件画面渲染：把一张卡片 + 某时刻状态渲染成一帧静态横屏 HTML。

横屏 16:9 培训讲解课件（1920x1080）。左栏副标题+标题+要点（三态），右栏
sub_points 知识卡片逐条揭示，底部固定高度字幕带（所有卡含封面都显示字幕）
+ 进度条。封面额外展示 outline 论点列表。中明度深蓝灰底（不纯黑），科幻感。
仅产 HTML 字符串，无 JS/外部资源/动画。对应 OpenSpec change: video-horizontal-skill。
"""
from __future__ import annotations


def _esc(text) -> str:
    if text is None:
        return ""
    s = str(text)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


_CSS = """* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { width: __W__px; height: __H__px; }
body {
  font-family: "Microsoft YaHei", "微软雅黑", "PingFang SC", sans-serif;
  background-color: #1e293b; color: #ffffff;        /* 中明度深蓝灰，不纯黑 */
  position: relative; overflow: hidden; -webkit-font-smoothing: antialiased;
}
.grid {
  position: absolute; inset: 0;
  background-image:
    linear-gradient(rgba(34,211,238,0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(34,211,238,0.08) 1px, transparent 1px);
  background-size: 64px 64px; pointer-events: none;
}
.glow {
  position: absolute; inset: 0;
  background:
    radial-gradient(circle at 0% 0%, rgba(34,211,238,0.25), transparent 34%),
    radial-gradient(circle at 100% 0%, rgba(34,211,238,0.22), transparent 32%),
    radial-gradient(circle at 50% 120%, rgba(34,211,238,0.20), transparent 40%);
  pointer-events: none;
}
.stage { position: relative; width: 100%; height: 100%;
  display: flex; flex-direction: column; padding: 50px 190px 40px 72px; z-index: 1; }
.eyebrow { font-size: 24px; color: #22d3ee; font-weight: 700; letter-spacing: 6px;
  margin-bottom: 14px; text-shadow: 0 0 20px rgba(34,211,238,0.8), 0 0 40px rgba(34,211,238,0.4); }
.title { font-size: 72px; font-weight: 800; color: #ffffff; line-height: 1.24;
  letter-spacing: 2px; text-shadow: 0 0 30px rgba(34,211,238,0.6), 0 4px 20px rgba(0,0,0,0.8); word-break: break-word; }
.title-bar { width: 140px; height: 6px; margin-top: 20px; background: #22d3ee;
  box-shadow: 0 0 30px rgba(34,211,238,1), 0 0 60px rgba(34,211,238,0.6); border-radius: 3px; }
.main-row { flex: 1; min-height: 0; display: flex; flex-direction: row; gap: 44px; }
.left-col { width: 50%; display: flex; flex-direction: column; min-width: 0; }
.right-col { flex: 1; min-width: 0; display: flex; flex-direction: column;
  justify-content: flex-end; gap: 14px; padding: 6px 0; }
.points { flex: 1; display: flex; flex-direction: column; justify-content: flex-start; gap: 22px; padding-top: 6px; }
.point { position: relative; font-size: 48px; line-height: 1.4; padding: 12px 18px 12px 28px;
  border-radius: 8px; color: #475569; opacity: 0.5; }
.point.done { color: #ffffff; opacity: 1; }
.point.done::before { content: ""; position: absolute; left: 0; top: 14px; bottom: 14px;
  width: 4px; background: #22d3ee; box-shadow: 0 0 20px rgba(34,211,238,0.9), 0 0 40px rgba(34,211,238,0.5); border-radius: 2px; }
.point.active { color: #22d3ee; opacity: 1; font-size: 56px; font-weight: 700;
  background: rgba(34,211,238,0.12); box-shadow: 0 0 40px rgba(34,211,238,0.7), inset 0 0 20px rgba(34,211,238,0.1);
  border: 1px solid rgba(34,211,238,0.5); text-shadow: 0 0 15px rgba(34,211,238,0.6); }
.sp-item { position: relative; border-radius: 12px; word-break: break-word; }
.sp-item.done { font-size: 28px; line-height: 1.4; color: rgba(203,213,225,0.8);
  padding: 8px 16px; background: rgba(15,23,42,0.5); border-left: 3px solid rgba(34,211,238,0.35); }
.sp-item.active { background: rgba(15,23,42,0.85); border: 1px solid rgba(34,211,238,0.55);
  border-radius: 16px; padding: 34px 32px 32px; min-height: 280px;
  box-shadow: 0 0 60px rgba(34,211,238,0.3), inset 0 0 80px rgba(34,211,238,0.08); }
.sp-item.active::before { content: "知识卡片"; position: absolute; top: -16px; left: 28px;
  background: #22d3ee; color: #0a0e1a; font-size: 24px; font-weight: 700;
  padding: 5px 18px; border-radius: 8px; letter-spacing: 3px; box-shadow: 0 0 25px rgba(34,211,238,0.8), 0 0 50px rgba(34,211,238,0.4); }
.sp-item.active .sp-text { font-size: 48px; line-height: 1.45; color: #ffffff; font-weight: 500;
  text-shadow: 0 0 10px rgba(34,211,238,0.3); }
.sp-placeholder { display: flex; align-items: center; justify-content: center; height: 100%;
  color: rgba(148,163,184,0.5); font-size: 26px; letter-spacing: 6px; }
.footer-bar { margin-top: 10px; font-size: 24px; font-style: italic; color: #22d3ee;
  text-align: center; opacity: 0.9; height: 32px; line-height: 32px; overflow: hidden;
  white-space: nowrap; text-overflow: ellipsis; text-shadow: 0 0 20px rgba(34,211,238,0.7), 0 0 40px rgba(34,211,238,0.3); }
.subtitle-band { height: 112px; padding: 0 150px 0 36px; margin-top: 14px;
  background: rgba(15,23,42,0.92); border: 1px solid rgba(34,211,238,0.4);
  border-radius: 12px; display: flex; align-items: center; justify-content: center; overflow: hidden;
  box-shadow: 0 0 30px rgba(34,211,238,0.15), inset 0 0 20px rgba(34,211,238,0.05); }
.subtitle { font-size: 48px; line-height: 1; color: #ffffff; text-align: center; max-width: 100%;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  text-shadow: 0 2px 4px rgba(0,0,0,0.95), 0 0 2px #000,
    -1px -1px 0 #000, 1px 1px 0 #000, -1px 1px 0 #000, 1px -1px 0 #000; }
.subtitle.empty { visibility: hidden; }
.progress-track { position: absolute; left: 0; right: 0; bottom: 0; height: 6px;
  background: rgba(34,211,238,0.12); }
.progress-fill { height: 100%; background: linear-gradient(90deg, #06b6d4, #22d3ee);
  box-shadow: 0 0 25px rgba(34,211,238,1), 0 0 50px rgba(34,211,238,0.6); }
/* 封面：副标题 + 大标题 + outline 论点列表 + 字幕带 + 进度 */
.stage.cover { justify-content: space-between; padding: 64px 190px 40px 72px; }
.stage.cover .main-row { display: none; }
.cover-head { text-align: center; }
.stage.cover .eyebrow { letter-spacing: 10px; }
.stage.cover .title { font-size: 84px; }
.stage.cover .title-bar { margin: 22px auto 0; }
.outline-wrap { flex: 1; display: flex; align-items: center; justify-content: center; }
.outline { list-style: none; display: grid; grid-template-columns: repeat(5, 1fr);
  gap: 22px; width: 100%; max-width: 1720px; }
.outline li { font-size: 36px; line-height: 1.3; color: #e2e8f0; font-weight: 600;
  padding: 26px 16px; text-align: center;
  background: rgba(34,211,238,0.12); border: 1px solid rgba(34,211,238,0.45);
  border-radius: 14px; box-shadow: 0 0 30px rgba(34,211,238,0.2), inset 0 0 15px rgba(34,211,238,0.05); }
.outline li .num { display: block; font-size: 48px; color: #22d3ee; font-weight: 800;
  margin-bottom: 10px; text-shadow: 0 0 20px rgba(34,211,238,0.8), 0 0 40px rgba(34,211,238,0.4); }"""


def render_frame(card: dict, state: dict, width: int = 1920, height: int = 1080) -> str:
    """渲染一帧横屏 HTML。

    card:  {"title", "subtitle"(副标题), "points":[], "sub_points":[], "footer",
            "is_cover", "outline":[str](仅封面：论点列表)}
    state: {"active_idx", "subtitle"(字幕,已去标点), "progress"}

    type=="tool" 的卡片分发到 screencast 模块（屏录感工具窗口渲染）；
    type=="tutorial" 分发到 tutorial 模块（亮色教程模板：全量展示 + active 高亮）。
    """
    if card.get("type") == "tool":
        from . import screencast

        return screencast.render_frame(card, state, width, height)
    if card.get("type") == "tutorial":
        from . import tutorial

        return tutorial.render_frame(card, state, width, height)
    title = card.get("title", "") or ""
    card_sub = card.get("subtitle", "") or ""
    points_raw = card.get("points") or []
    sub_points = card.get("sub_points") or []
    footer = card.get("footer", "") or ""
    outline = card.get("outline") or []
    is_cover = bool(card.get("is_cover")) or len(points_raw) == 0

    active_idx = int(state.get("active_idx", -1))
    state_sub = state.get("subtitle", "") or ""
    progress = float(state.get("progress", 0.0))
    pct = max(0.0, min(1.0, progress)) * 100.0
    css = _CSS.replace("__W__", str(width)).replace("__H__", str(height))

    eyebrow = f'<div class="eyebrow">{_esc(card_sub)}</div>' if card_sub else ""
    sub_cls = "subtitle" if state_sub else "subtitle empty"
    band = f'<div class="subtitle-band"><div class="{sub_cls}">{_esc(state_sub)}</div></div>'
    prog = f'<div class="progress-track"><div class="progress-fill" style="width:{pct:.2f}%"></div></div>'

    if is_cover:
        if outline:
            ol = "".join(
                f'<li><span class="num">{i + 1:02d}</span>{_esc(o)}</li>'
                for i, o in enumerate(outline)
            )
            outline_block = f'<div class="outline-wrap"><ul class="outline">{ol}</ul></div>'
        else:
            outline_block = '<div class="outline-wrap"></div>'
        body = f"""<div class="stage cover">
  <div class="cover-head">
    {eyebrow}
    <div class="title">{_esc(title)}</div>
    <div class="title-bar"></div>
  </div>
  {outline_block}
  {band}
  {prog}
</div>"""
        return _doc(css, body)

    # 左栏要点（三态）
    point_items = []
    for idx, pt in enumerate(points_raw):
        cls = "point done" if idx < active_idx else ("point active" if idx == active_idx else "point")
        point_items.append(f'        <div class="{cls}">{_esc(pt)}</div>')
    points_block = "\n".join(point_items)

    # 右栏 sub_points：已讲(done) + 当前(active)，未讲不显示
    sp_items = []
    for idx, sp in enumerate(sub_points):
        if idx > active_idx:
            continue
        if idx == active_idx:
            sp_items.append(f'      <div class="sp-item active"><div class="sp-text">{_esc(sp)}</div></div>')
        else:
            sp_items.append(f'      <div class="sp-item done">{_esc(sp)}</div>')
    right_block = "\n".join(sp_items) if sp_items else '<div class="sp-placeholder">讲解中…</div>'

    footer_block = f'<div class="footer-bar">{_esc(footer)}</div>' if footer else ""

    body = f"""<div class="stage">
  <div class="main-row">
    <div class="left-col">
      {eyebrow}
      <div class="title">{_esc(title)}</div>
      <div class="title-bar"></div>
      <div class="points">
{points_block}
      </div>
    </div>
    <div class="right-col">
{right_block}
    </div>
  </div>
  {footer_block}
  {band}
  {prog}
</div>"""
    return _doc(css, body)


def _doc(css: str, body: str) -> str:
    # 科幻风粒子背景（SVG 星尘点阵）
    particles = """
    <svg style="position:absolute;inset:0;width:100%;height:100%;pointer-events:none;opacity:0.4" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="star"><stop offset="0%" stop-color="#22d3ee" stop-opacity="0.8"/><stop offset="100%" stop-color="#22d3ee" stop-opacity="0"/></radialGradient>
      </defs>
      <circle cx="150" cy="200" r="2" fill="url(#star)"/><circle cx="450" cy="120" r="1.5" fill="url(#star)"/>
      <circle cx="780" cy="340" r="2.5" fill="url(#star)"/><circle cx="1200" cy="180" r="1.8" fill="url(#star)"/>
      <circle cx="1500" cy="450" r="2.2" fill="url(#star)"/><circle cx="300" cy="700" r="1.6" fill="url(#star)"/>
      <circle cx="900" cy="800" r="2" fill="url(#star)"/><circle cx="1600" cy="750" r="1.4" fill="url(#star)"/>
      <circle cx="600" cy="500" r="1.8" fill="url(#star)"/><circle cx="1100" cy="600" r="2.3" fill="url(#star)"/>
      <circle cx="200" cy="900" r="1.5" fill="url(#star)"/><circle cx="1400" cy="250" r="2" fill="url(#star)"/>
    </svg>"""

    # 扫描线效果（水平扫描线 overlay）
    scanlines = """
    <div style="position:absolute;inset:0;pointer-events:none;opacity:0.08;
      background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(34,211,238,0.15) 2px,rgba(34,211,238,0.15) 4px);
      z-index:9999;"></div>"""

    # HUD 边角装饰（四角发光边框）
    hud_corners = """
    <div style="position:absolute;top:20px;left:20px;width:60px;height:60px;border-left:3px solid #22d3ee;border-top:3px solid #22d3ee;box-shadow:0 0 20px rgba(34,211,238,0.6);pointer-events:none;z-index:10;"></div>
    <div style="position:absolute;top:20px;right:20px;width:60px;height:60px;border-right:3px solid #22d3ee;border-top:3px solid #22d3ee;box-shadow:0 0 20px rgba(34,211,238,0.6);pointer-events:none;z-index:10;"></div>
    <div style="position:absolute;bottom:20px;left:20px;width:60px;height:60px;border-left:3px solid #22d3ee;border-bottom:3px solid #22d3ee;box-shadow:0 0 20px rgba(34,211,238,0.6);pointer-events:none;z-index:10;"></div>
    <div style="position:absolute;bottom:20px;right:20px;width:60px;height:60px;border-right:3px solid #22d3ee;border-bottom:3px solid #22d3ee;box-shadow:0 0 20px rgba(34,211,238,0.6);pointer-events:none;z-index:10;"></div>"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>courseware frame</title>
<style>
{css}
</style>
</head>
<body>
{particles}
{scanlines}
{hud_corners}
{body}
</body>
</html>"""


if __name__ == "__main__":
    import json
    from pathlib import Path
    from playwright.sync_api import sync_playwright

    root = Path(__file__).resolve().parents[2]
    from config import OUTPUT_ROOT
    deck = json.load(open(OUTPUT_ROOT / "deck" / "ai-dev-claude-code-power-user" / "deck.json", encoding="utf-8"))
    out_dir = OUTPUT_ROOT / "build"; out_dir.mkdir(parents=True, exist_ok=True)
    cov = deck["cards"][0]
    cover_card = {"title": cov.get("hook", "").replace("\n", " "), "subtitle": cov.get("subtitle", ""),
                  "points": [], "sub_points": [], "footer": "", "is_cover": True,
                  "outline": ["命令 · 纪律边界", "Skill · 固化经验", "Subagent · 并行指挥",
                              "打断 · 30秒纠偏", "Workflow · 编排乐谱"]}
    raw = deck["cards"][3]
    ins_card = {"title": raw["title"], "subtitle": raw.get("label", ""), "points": raw["points"],
                "sub_points": raw["sub_points"], "footer": raw.get("footer", ""), "is_cover": False}
    cases = [("cover", cover_card, {"active_idx": -1, "subtitle": "差距不在提示词 在五个习惯", "progress": 0.05}),
             ("ins", ins_card, {"active_idx": 1, "subtitle": "往上一层 是命令", "progress": 0.4})]
    with sync_playwright() as pw:
        b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 1920, "height": 1080})
        for name, c, st in cases:
            pg.set_content(render_frame(c, st)); pg.wait_for_timeout(140)
            shot = out_dir / f"_hw3_{name}.png"; page.screenshot = pg.screenshot
            pg.screenshot(path=str(shot)); print(f"[{name}] {shot.stat().st_size} bytes")
        b.close()
    print("DONE")
