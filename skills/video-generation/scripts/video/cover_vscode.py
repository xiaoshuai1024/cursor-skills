"""拟物化视频封面：深色底 + 左侧大标题 + 右侧复用 vscode tool 的写实窗口。

与 screencast 的「拟物化」方向一致：封面主体用视频卡 8 的 VSCode 窗口
（Claude 对话面板 + index.html 代码），而非抽象 CSS 假窗口。左半标题区
大字号双行 + 青色高亮，满足 video-cover-standard 验收锚点（1920x1080 /
青色≥0.8% / 字形≥2.0% / 中央双行）。

用法：
  cd .agents/skills/video-generation/scripts
  PYTHONIOENCODING=utf-8 python -m video.cover_vscode --slug <slug>

产物：
  .video-generation/build/<slug>/<slug>_cover.png
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
from video.config import OUTPUT_ROOT  # noqa: E402
from video.screencast import _vscode, _esc  # noqa: E402

VSW_CSS = """
.vsw { width: 100%; height: 100%; display: flex; flex-direction: column;
  background: #1e1e1e; border: 1px solid #333; border-radius: 10px; overflow: hidden;
  font-size: 15px; color: #cccccc; box-shadow: 0 24px 60px rgba(0,0,0,0.5); }
.vsw .tabbar { height: 40px; flex: none; display: flex; align-items: center;
  background: #2d2d2d; padding-left: 14px; gap: 2px; }
.vsw .tabbar .tab { background: #1e1e1e; color: #cccccc; padding: 8px 18px;
  font-size: 14px; border-radius: 6px 6px 0 0; display: flex; align-items: center; gap: 7px; }
.vsw .tabbar .tab.on { color: #ffffff; box-shadow: inset 0 2px 0 #22d3ee; }
.vsw .tabbar .tab .dot { width: 7px; height: 7px; border-radius: 50%; background: #4d9fff; }
.vsw .tabbar .site { margin-left: auto; padding: 0 16px; color: #888; font-size: 13px; }
.vsw .mid { flex: 1; min-height: 0; display: flex; }
.vsw .actbar { width: 48px; flex: none; display: flex; flex-direction: column;
  align-items: center; padding-top: 8px; gap: 10px; background: #333333; }
.vsw .actbar .ic { width: 40px; height: 40px; border-radius: 8px; display: flex;
  align-items: center; justify-content: center; font-size: 18px; color: #858585;
  position: relative; }
.vsw .actbar .ic span { font-size: 20px; }
.vsw .actbar .ic.cc { color: #4d9fff; background: #232323; }
.vsw .actbar .ic.cc.active { color: #22d3ee; box-shadow: 0 0 18px rgba(34,211,238,0.5);
  background: #1f2b44; }
.vsw .sidebar { width: 340px; flex: none; background: #252526; display: flex;
  flex-direction: column; border-right: 1px solid #2b2b2b; min-width: 0; }
.vsw .sidehead { padding: 12px 14px; font-size: 14px; color: #e0e0e0;
  border-bottom: 1px solid #2b2b2b; display: flex; align-items: center; gap: 8px; }
.vsw .sidehead .logo { width: 18px; height: 18px; border-radius: 50%;
  background: #d97706; color: #fff; font-size: 11px; font-weight: 800;
  display: flex; align-items: center; justify-content: center; }
.vsw .chatbody { flex: 1; overflow: hidden; padding: 12px; display: flex;
  flex-direction: column; gap: 10px; }
.vsw .msg { border-radius: 8px; padding: 8px 12px; font-size: 14px; line-height: 1.5;
  max-width: 92%; word-break: break-word; }
.vsw .msg.user { align-self: flex-end; background: #2b5876; color: #e8f4fd; }
.vsw .msg.ai { align-self: flex-start; background: #333333; color: #d4d4d4; }
.vsw .msg.ai b { color: #4d9fff; }
.vsw .msg .ok { color: #4ec9b0; }
.vsw .accept { margin-top: 2px; align-self: flex-start; background: #0e639c;
  color: #fff; font-size: 13px; padding: 5px 14px; border-radius: 4px;
  font-weight: 600; }
.vsw .inbar { flex: none; display: flex; align-items: center; gap: 8px;
  padding: 10px 12px; border-top: 1px solid #2b2b2b; background: #252526; }
.vsw .inbar .in { flex: 1; background: #1e1e1e; border: 1px solid #3c3c3c;
  color: #ddd; font-size: 14px; padding: 7px 10px; border-radius: 4px; }
.vsw .inbar .send { background: #0e639c; color: #fff; font-size: 13px;
  padding: 7px 14px; border-radius: 4px; font-weight: 600; }
.vsw .editor { flex: 1; min-width: 0; background: #1e1e1e; display: flex;
  flex-direction: column; }
.vsw .code { flex: 1; font-family: Consolas, "Courier New", monospace; font-size: 16px;
  line-height: 1.7; padding: 16px 20px; color: #d4d4d4; white-space: pre;
  overflow: hidden; }
.vsw .code .t { color: #9cdcfe; } .vsw .code .s { color: #ce9178; }
.vsw .code .k { color: #c586c0; } .vsw .code .c { color: #6a9955; }
.vsw .code .b { color: #dcdcaa; }
.vsw .code .hit { background: rgba(34,211,238,0.16); box-shadow: 0 0 0 2px rgba(34,211,238,0.35); }
.vsw .statusbar { flex: none; height: 26px; background: #0e639c; color: #fff;
  display: flex; align-items: center; padding: 0 12px; font-size: 12px; gap: 18px; }
.vsw .statusbar .sp { margin-left: auto; }
.vsw .hot { position: relative; }
.vsw .hot.active { border-color: #22d3ee !important;
  box-shadow: 0 0 0 2px rgba(34,211,238,0.45), 0 0 26px rgba(34,211,238,0.4) !important; }
.vsw .hot.active::before { content: ""; position: absolute; left: -14px; top: 50%;
  transform: translateY(-50%); border: 10px solid transparent; border-left: 14px solid #22d3ee;
  z-index: 5; }
.vsw .hot.done { outline: 1px solid rgba(74,222,128,0.5); opacity: 0.8; }
"""


def build_cover_html(vsw_html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: 1920px; height: 1080px; overflow: hidden; position: relative;
    font-family: "Microsoft YaHei", "微软雅黑", "PingFang SC", "Noto Sans SC", sans-serif;
    -webkit-font-smoothing: antialiased;
    background:
      radial-gradient(950px 720px at 0% -12%, rgba(34,211,238,0.24), transparent 62%),
      radial-gradient(1050px 780px at 100% 115%, rgba(139,92,246,0.20), transparent 62%),
      radial-gradient(1300px 800px at 18% 0%, #1e293b 0%, #0f172a 55%), #0f172a;
  }}
  /* 拟物化窗口背后的青色光晕，让窗口在深底上跳出来 */
  .window-glow {{
    position: absolute; right: 120px; top: 50%; transform: translateY(-50%);
    width: 720px; height: 540px; border-radius: 24px; z-index: 1;
    background: radial-gradient(ellipse, rgba(34,211,238,0.16) 0%, transparent 70%);
  }}
  .vsw-wrap {{
    position: absolute; right: 150px; top: 50%; transform: translateY(-50%);
    width: 640px; z-index: 2; border-radius: 12px;
    border: 1px solid rgba(34,211,238,0.35);
    box-shadow: 0 30px 90px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.04);
    overflow: hidden;
  }}
  .left {{
    position: absolute; left: 110px; top: 51%; transform: translateY(-50%);
    width: 900px; z-index: 3; display: flex; flex-direction: column; gap: 26px;
  }}
  .ep {{
    display: flex; align-items: center; gap: 16px;
  }}
  .ep .num {{
    background: #22d3ee; color: #0a0e1a; font-size: 26px; font-weight: 800;
    padding: 5px 18px; border-radius: 6px; letter-spacing: 2px; font-style: italic;
  }}
  .ep .lab {{
    color: #22d3ee; font-size: 22px; font-weight: 600; letter-spacing: 5px;
  }}
  .title {{
    font-size: 92px; font-weight: 800; color: #ffffff; line-height: 1.38;
    letter-spacing: 5px;
    text-shadow: 0 4px 24px rgba(0,0,0,0.6);
  }}
  /* 第二行关键词：实心青色圆角框（拟物化关键词芯片），暗色文字 */
  .title .hlbox {{
    display: inline-block; vertical-align: baseline;
    background: linear-gradient(135deg, #22d3ee 0%, #0891b2 100%);
    color: #0a0e1a; padding: 6px 34px 12px; border-radius: 20px;
    letter-spacing: 4px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.35);
  }}
  .sub {{
    font-size: 34px; color: #94a3b8; letter-spacing: 3px; line-height: 1.5;
  }}
  .sub b {{ color: #e2e8f0; font-weight: 600; }}
  .sub .pill {{
    display: inline-block; background: #22d3ee; color: #0a0e1a;
    font-size: 26px; font-weight: 700; letter-spacing: 2px;
    padding: 3px 18px 6px; border-radius: 10px; vertical-align: middle;
  }}
  .tags {{ display: flex; gap: 18px; }}
  .tag {{
    font-size: 24px; font-weight: 500; color: #22d3ee; letter-spacing: 2px;
    padding: 9px 26px; border: 1.5px solid rgba(34,211,238,0.35);
    border-radius: 30px; background: rgba(34,211,238,0.06);
  }}
  .tag.violet {{ color: #a78bfa; border-color: rgba(167,139,250,0.35); background: rgba(167,139,250,0.06); }}
  .tag.orange {{ color: #f59e0b; border-color: rgba(245,158,11,0.35); background: rgba(245,158,11,0.06); }}
  .play {{
    display: flex; align-items: center; gap: 14px;
    font-size: 26px; color: #22d3ee; letter-spacing: 4px; font-weight: 600;
  }}
  .play .tri {{
    width: 0; height: 0; border-left: 18px solid #22d3ee;
    border-top: 11px solid transparent; border-bottom: 11px solid transparent;
    filter: drop-shadow(0 0 8px #22d3ee);
  }}
  .play .dur {{ color: #64748b; font-size: 22px; letter-spacing: 2px; font-weight: 400; }}
  {VSW_CSS}
</style>
</head>
<body>
  <div class="window-glow"></div>
  <div class="left">
    <div class="ep"><div class="num">EP.07</div><div class="lab">AI 编程系列</div></div>
    <div class="title">4分钟零基础装好<br><span class="hlbox">Claude Code</span></div>
    <div class="sub"><b>VSCode + 插件 + DeepSeek</b> · <span class="pill">全程免费</span><br>不用注册官方账号 · 不买黄牛号</div>
    <div class="tags">
      <div class="tag">免费工具</div>
      <div class="tag violet">国产模型</div>
      <div class="tag orange">零基础</div>
    </div>
    <div class="play"><span class="tri"></span>看完整流程<span class="dur">· 143秒</span></div>
  </div>
  <div class="vsw-wrap">{vsw_html}</div>
</body>
</html>"""


def main() -> None:
    ap = argparse.ArgumentParser(description="拟物化 VSCode 封面")
    ap.add_argument("--slug", required=True)
    args = ap.parse_args()

    slug = args.slug
    deck_path = OUTPUT_ROOT / "deck" / slug / "deck.json"
    if not deck_path.exists():
        sys.exit(f"❌ 找不到 deck: {deck_path}")
    deck = json.loads(deck_path.read_text(encoding="utf-8"))

    # 取 vscode tool 卡片作为窗口主体（active_idx=2：输入需求→它写代码→存进电脑）
    vcard = next((c for c in deck["cards"] if c.get("tool") == "vscode"), None)
    if not vcard:
        sys.exit("❌ deck 中没有 tool=vscode 的卡片")
    vsw_html = _vscode(vcard, 2)

    out_dir = OUTPUT_ROOT / "build" / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{slug}_cover.png"

    from playwright.sync_api import sync_playwright
    html = build_cover_html(vsw_html)
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1920, "height": 1080})
        pg.set_content(html)
        pg.wait_for_timeout(120)
        pg.screenshot(path=str(out), full_page=False)
        b.close()

    print(f"✅ 封面已生成: {out}")


if __name__ == "__main__":
    main()
