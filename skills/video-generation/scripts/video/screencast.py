"""屏录感工具界面渲染：把一张卡片渲染成「真实工具窗口」风格的静态横屏 HTML。

设计目标：复刻屏录教程的视觉语言（终端 / settings.json 编辑器 / CcSwitch 窗口 /
GitHub Releases / 成本对比 / 国产阵营清单），`active_idx` 驱动界面内当前操作步骤
高亮 + 光标箭头引导，模拟「讲到哪、点到哪」。底部保留字幕带 + 进度条。

与 courseware 的差异：不做「左栏要点 + 右栏知识卡片」的 PPT 排布，而是整屏一张
真实感工具窗口，信息在「操作」里呈现（对标 Ai小白Lab 屏录教程，26.2 万赞）。
数据全部来自文章 claude-code-ccswitch-domestic-models.md（真实性红线，不编造）。

窗口结构（1920×1080）：
  ┌ ● ● ●  <窗口标题> ─────────────────────┐
  │  <工具内容>（active_idx 高亮热点）       │
  │  [步骤条：✓ ✓ ▶ 当前步骤 · 下一步]      │
  └─────────────────────────────────────────┘
  [字幕带]
  [进度条]

使用：frames.py → courseware.render_frame 分发到本模块（type=="tool"）。
"""
from __future__ import annotations

import base64

_SHOT_CACHE: dict[str, str] = {}
_OUTPUT_ROOT = None


def _shot_b64(slug: str, key: str) -> str | None:
    """从 .video-generation/assets/<slug>/<key>.png 读真实截图，base64 内联（模块级缓存）。

    每帧 set_content 的是自包含 HTML，本地文件引用解析不了，必须内联。
    """
    global _OUTPUT_ROOT
    if not slug or not key:
        return None
    if _OUTPUT_ROOT is None:
        from video.config import OUTPUT_ROOT

        _OUTPUT_ROOT = OUTPUT_ROOT
    path = _OUTPUT_ROOT / "assets" / slug / f"{key}.png"
    if not path.exists():
        return None
    spath = str(path)
    if spath not in _SHOT_CACHE:
        _SHOT_CACHE[spath] = "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()
    return _SHOT_CACHE[spath]


def _esc(text) -> str:
    if text is None:
        return ""
    s = str(text)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _hot(idx: int, active_idx: int, inner: str, tag: str = "div", cls: str = "") -> str:
    """渲染一个热点元素：done(打勾) / active(高亮+光标箭头) / future(暗淡)。"""
    state_cls = "done" if idx < active_idx else ("active" if idx == active_idx else "")
    cls = (cls + " ").strip() + " " if cls else ""
    return f'<{tag} class="hot {state_cls} {cls}">{inner}</{tag}>'


_CSS = """* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { width: __W__px; height: __H__px; }
body {
  font-family: "Microsoft YaHei", "微软雅黑", "PingFang SC", sans-serif;
  background:
    radial-gradient(950px 720px at 0% -12%, rgba(34,211,238,0.24), transparent 62%),
    radial-gradient(1050px 780px at 100% 115%, rgba(139,92,246,0.20), transparent 62%),
    linear-gradient(rgba(34,211,238,0.10) 2px, transparent 2px),
    linear-gradient(90deg, rgba(34,211,238,0.10) 2px, transparent 2px),
    radial-gradient(1300px 800px at 18% 0%, #1e293b 0%, #0f172a 55%), #0f172a;
  background-size: auto, auto, 44px 44px, 44px 44px, auto;
  /* 网格偏移 20px：窗口左右边距 64px、顶部 32px，44px 间隔 + 20px 偏移保证
     网格线落在可见边距内（x=20/64、y=20），不会被窗口盖住；2px 线 + 0.10 透明度
     让网格在 H.264 编码后仍可见（1px 细线会被压缩抹平） */
  background-position: 0 0, 0 0, 0 20px, 20px 0, 0 0;
  color: #e2e8f0; position: relative; overflow: hidden; -webkit-font-smoothing: antialiased;
}
.screencast { position: relative; width: 100%; height: 100%; z-index: 1;
  display: flex; flex-direction: column; padding: 32px 190px 0 64px; }
.window { flex: 1; min-height: 0; display: flex; flex-direction: column;
  background: #0b1220; border: 1px solid #2a3a55; border-radius: 16px;
  box-shadow: 0 30px 80px rgba(0,0,0,0.55), 0 0 0 1px rgba(255,255,255,0.03); overflow: hidden; }
.titlebar { height: 54px; flex: none; display: flex; align-items: center; gap: 12px;
  padding: 0 22px; background: #111c30; border-bottom: 1px solid #22304a; }
.lights { display: flex; gap: 9px; }
.lights i { width: 14px; height: 14px; border-radius: 50%; }
.lights .r { background: #ff5f57; } .lights .y { background: #febc2e; }
.lights .g { background: #28c840; }
.wtitle { margin-left: 8px; font-size: 28px; color: #94a3b8; letter-spacing: 1px; }
.wtag { margin-left: auto; font-size: 24px; color: #64748b; }
.winbody { flex: 1; min-height: 0; position: relative; display: flex; overflow: hidden;
  align-items: center; justify-content: center; padding: 26px 40px; }
/* 顶部步骤条：始终显示全部步骤（done ✓ / active ▶ / future 暗淡） */
.steplist { flex: none; display: flex; gap: 12px; padding: 12px 24px;
  background: #0d1626; border-bottom: 1px solid #22304a; }
.s-step { flex: 1; min-width: 0; display: flex; align-items: center; gap: 12px;
  padding: 10px 16px; border-radius: 10px; background: #0f1a2e; border: 1px solid #22304a; }
.s-step .ix { width: 30px; height: 30px; flex: none; border-radius: 50%; background: #1f2b44;
  color: #64748b; display: flex; align-items: center; justify-content: center;
  font-size: 16px; font-weight: 800; }
.s-step .tx { flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  color: #64748b; font-size: 26px; }
.s-step.done { border-color: rgba(74,222,128,0.45); background: rgba(40,200,72,0.06); }
.s-step.done .ix { background: rgba(40,200,72,0.22); color: #28c840; }
.s-step.done .tx { color: #94a3b8; }
.s-step.active { border-color: #22d3ee; background: rgba(34,211,238,0.10);
  box-shadow: 0 0 26px rgba(34,211,238,0.35); }
.s-step.active .ix { background: #22d3ee; color: #0a0e1a; }
.s-step.active .tx { color: #ffffff; font-weight: 700; }

/* 热点：当前操作高亮（边框发光，不覆盖元素自身背景/渐变）+ 光标箭头 */
.hot { position: relative; }
.hot.active { border-color: #22d3ee !important;
  box-shadow: 0 0 0 3px rgba(34,211,238,0.40), 0 0 55px rgba(34,211,238,0.40) !important; }
.hot.active::before { content: ""; position: absolute; left: -16px; top: 50%;
  transform: translateY(-50%); border: 11px solid transparent; border-left: 15px solid #22d3ee;
  filter: drop-shadow(0 0 6px #22d3ee); z-index: 5; }
.hot.done { opacity: 0.72; }
.hot.done::after { content: "✓"; position: absolute; right: 12px; top: 50%;
  transform: translateY(-50%); color: #28c840; font-size: 22px; font-weight: 800; z-index: 4; }

/* 避坑警告（别注册官方号 / 别买黄牛） */
.warnbox { width: 100%; max-width: 1540px; display: flex; flex-direction: column; gap: 20px; }
.warnbox .wrow { background: #2a1215; border: 1px solid rgba(248,113,113,0.55); border-radius: 14px;
  padding: 26px 34px; font-size: 44px; font-weight: 700; color: #fecaca; display: flex;
  align-items: center; gap: 20px; line-height: 1.4; }
.warnbox .wrow .wmark { color: #f87171; font-size: 48px; flex: none; }
.warnbox .wrow.done { opacity: 0.8; }

/* Claude Code 对话窗（用嘴提需求 → 写代码 → 自动跑） */
.chat { width: 100%; max-width: 1520px; display: flex; flex-direction: column; gap: 20px; }
.cb { border-radius: 14px; padding: 22px 30px; font-size: 40px; line-height: 1.5; max-width: 82%; }
.cb.user { align-self: flex-start; background: #123044; border: 1px solid rgba(34,211,238,0.5);
  color: #e0f2fe; }
.cb.ai { align-self: flex-end; background: #0f1a2e; border: 1px solid #2a3a55; color: #e2e8f0;
  font-family: Consolas, "Courier New", monospace; }
.cb.ai .cbname { color: #67e8f9; font-size: 26px; margin-bottom: 10px;
  font-family: "Microsoft YaHei", "微软雅黑", sans-serif; }

/* 真实截图打底（realshot）：等宽容器 + 热点框 + 箭头标注 */
.shotwrap { position: relative; aspect-ratio: 16 / 9; max-width: 100%; max-height: 100%;
  border-radius: 10px; overflow: hidden; border: 1px solid #2a3a55;
  background: #000; box-shadow: 0 24px 60px rgba(0,0,0,0.5); }
.shotwrap img { display: block; width: 100%; height: 100%; object-fit: fill; }
/* 特写取景：底层整页暗化作参照，上层热点中心 1.6× 放大（内层 img 由内联样式定位） */
.shotctx { filter: brightness(0.42) saturate(0.8); }
.shotzoom { position: absolute; left: 4%; top: 4%; right: 4%; bottom: 4%;
  border-radius: 12px; overflow: hidden; border: 2px solid rgba(34,211,238,0.55);
  box-shadow: 0 0 0 4px rgba(34,211,238,0.18), 0 18px 60px rgba(0,0,0,0.7);
  background: #000; }
.shotzoom img { position: absolute; object-fit: fill; }
.hspot { position: absolute; border: 3px solid #22d3ee; border-radius: 6px;
  box-shadow: 0 0 0 3px rgba(34,211,238,0.35), 0 0 34px rgba(34,211,238,0.45); z-index: 2; }
.hspot.done { border-color: rgba(74,222,128,0.65); opacity: 0.7;
  box-shadow: 0 0 0 2px rgba(74,222,128,0.2); }
.hspot.done::after { content: "✓"; position: absolute; right: 4px; top: 50%;
  transform: translateY(-50%); color: #28c840; font-size: 16px; font-weight: 800; z-index: 4; }
.hspot.fut { border-color: rgba(148,163,184,0.35); opacity: 0.4;
  box-shadow: none; }
.harr { position: absolute; display: flex; align-items: center; gap: 10px;
  transform: translate(calc(-100% - 14px), -50%); z-index: 3; }
.harr.right { transform: translate(14px, -50%); }
.harr i { border: 0 solid transparent; border-top: 11px solid transparent;
  border-bottom: 11px solid transparent; border-left: 16px solid #22d3ee;
  filter: drop-shadow(0 0 5px #22d3ee); }
.harr.right i { border: 0 solid transparent; border-right: 16px solid #22d3ee;
  border-left: 0; border-top: 11px solid transparent; border-bottom: 11px solid transparent; }
.hlab { background: rgba(10,14,26,0.92); border: 1px solid #22d3ee; color: #e0f2fe;
  font-size: 34px; font-weight: 700; padding: 8px 18px; border-radius: 8px;
  white-space: nowrap; box-shadow: 0 0 14px rgba(34,211,238,0.3); }

/* 写实 VSCode 窗口（vscode tool）：拟物化 Claude Code 插件使用界面 */
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
/* 热点：vscode 窗口内也用统一的 active/done 态 */
.vsw .hot { position: relative; }
.vsw .hot.active { border-color: #22d3ee !important;
  box-shadow: 0 0 0 2px rgba(34,211,238,0.45), 0 0 26px rgba(34,211,238,0.4) !important; }
.vsw .hot.active::before { content: ""; position: absolute; left: -14px; top: 50%;
  transform: translateY(-50%); border: 10px solid transparent; border-left: 14px solid #22d3ee;
  z-index: 5; }
.vsw .hot.done { outline: 1px solid rgba(74,222,128,0.5); opacity: 0.8; }

/* 引言（痛点 + 材料 + 前置 CTA） */
.hook { width: 100%; max-width: 1580px; display: flex; flex-direction: column;
  align-items: center; gap: 38px; text-align: center; }
.hook .big { font-size: 86px; font-weight: 800; color: #ffffff; line-height: 1.18;
  text-shadow: 0 0 40px rgba(34,211,238,0.45); }
.hook .big .hl { color: #f87171; }
.hook .mats { display: flex; gap: 18px; flex-wrap: wrap; justify-content: center; }
.hook .mats span { background: #0f1a2e; border: 1px solid #2a3a55; border-radius: 999px;
  padding: 14px 26px; font-size: 24px; color: #e2e8f0; }
.hook .cta { background: linear-gradient(135deg, #22d3ee, #0891b2); color: #0a0e1a;
  font-size: 32px; font-weight: 800; padding: 20px 44px; border-radius: 14px;
  box-shadow: 0 0 50px rgba(34,211,238,0.5); }

/* 步骤① GitHub Releases */
.gh { width: 100%; max-width: 1500px; display: flex; flex-direction: column; gap: 18px; }
.gh .repo { font-size: 22px; color: #94a3b8; padding-bottom: 12px; border-bottom: 1px solid #1f2b44; }
.gh .repo b { color: #e2e8f0; font-size: 26px; }
.gh .rel { background: #0f1a2e; border: 1px solid #2a3a55; border-radius: 14px; padding: 26px 30px; }
.gh .rel .ver { font-size: 30px; font-weight: 800; color: #ffffff; }
.gh .rel .tag { font-size: 18px; color: #64748b; margin-top: 6px; }
.gh .assets { display: flex; gap: 14px; margin-top: 20px; }
.gh .assets span { background: #0b1220; border: 1px solid #2a3a55; color: #cbd5e1;
  border-radius: 8px; padding: 10px 18px; font-size: 19px; font-family: Consolas, monospace; }
.gh .dl { margin-top: 22px; width: 320px; padding: 16px 0; text-align: center;
  background: #22d3ee; color: #0a0e1a; font-size: 24px; font-weight: 800; border-radius: 10px; }
.gh .note { font-size: 21px; color: #94a3b8; }

/* 坑位① 终端 */
.term { width: 100%; max-width: 1560px; background: #05090f; border: 1px solid #1f2b44;
  border-radius: 12px; padding: 32px 40px; font-family: Consolas, "Courier New", monospace;
  font-size: 27px; line-height: 1.9; white-space: pre; }
.term .ps { color: #22d3ee; font-weight: 700; }
.term .warn { color: #f87171; }
.term .ok { color: #4ade80; }
.term .dim { color: #64748b; }

/* 步骤② CcSwitch Provider */
.ccs { width: 100%; max-width: 1500px; display: flex; flex-direction: column; gap: 18px; }
.ccs .appswitch { width: 400px; background: #0f1a2e; border: 1px solid #2a3a55;
  border-radius: 10px; padding: 14px 20px; font-size: 21px; color: #e2e8f0; }
.ccs .appswitch b { color: #67e8f9; }
.ccs .panel { background: #0f1a2e; border: 1px solid #2a3a55; border-radius: 12px;
  padding: 20px 26px; font-size: 22px; color: #e2e8f0; width: 620px; }
.ccs .panel b { color: #67e8f9; }
.ccs .keybox { display: inline-block; background: #05090f; border: 1px solid #33415c;
  color: #a7f3d0; padding: 6px 16px; border-radius: 6px; font-family: Consolas, monospace; }
.ccs .btn { background: #22d3ee; color: #0a0e1a; border: 0; font-size: 20px; font-weight: 800;
  padding: 8px 26px; border-radius: 8px; margin-left: 16px; }
.ccs .providers { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; width: 100%; }
.ccs .prov { background: #0f1a2e; border: 1px solid #2a3a55; border-radius: 12px;
  padding: 20px 26px; display: flex; align-items: center; justify-content: space-between; font-size: 24px; }
.ccs .prov .nm { font-weight: 700; color: #ffffff; }
.ccs .prov .sw { color: #22d3ee; border: 1px solid rgba(34,211,238,0.5); padding: 6px 14px;
  border-radius: 8px; font-size: 18px; }
.ccs .prov .sw.on { color: #4ade80; border-color: rgba(74,222,128,0.5); }

/* 步骤③ settings.json */
.editor { width: 100%; max-width: 1500px; display: flex; flex-direction: column; gap: 18px; }
.editor .code { background: #05090f; border: 1px solid #1f2b44; border-radius: 12px;
  padding: 28px 34px; font-family: Consolas, "Courier New", monospace; font-size: 25px; line-height: 1.85; }
.editor .key { color: #7dd3fc; } .editor .val { color: #a7f3d0; } .editor .cmt { color: #64748b; }
.editor .mini { background: #05090f; border: 1px solid #1f2b44; border-radius: 10px;
  padding: 14px 24px; font-family: Consolas, monospace; font-size: 21px; color: #94a3b8; }
.editor .mini b { color: #4ade80; }

/* 坑位② 国产阵营分工 */
.grid { width: 100%; max-width: 1520px; display: flex; flex-direction: column; gap: 20px; }
.grid .cell { background: #0f1a2e; border: 1px solid #2a3a55; border-radius: 14px;
  padding: 28px 32px; font-size: 30px; font-weight: 700; display: flex; align-items: center; gap: 20px; }
.grid .cell .tag { background: #1f2b44; color: #94a3b8; font-size: 18px; font-weight: 600;
  padding: 6px 14px; border-radius: 999px; flex: none; }
.grid .cell .md { color: #67e8f9; }
.grid .cell .all { color: #4ade80; }

/* 成本对比 */
.cost { width: 100%; max-width: 1500px; display: flex; flex-direction: column; gap: 22px; }
.cost .row { display: flex; align-items: stretch; gap: 24px; }
.cost .col { flex: 1; background: #0f1a2e; border: 1px solid #2a3a55; border-radius: 16px;
  padding: 32px 34px; text-align: center; }
.cost .col .name { font-size: 22px; color: #94a3b8; }
.cost .col .price { font-size: 84px; font-weight: 800; margin-top: 10px; }
.cost .col .unit { font-size: 20px; color: #64748b; margin-top: 6px; }
.cost .col.old .price { color: #f87171; }
.cost .col.new .price { color: #4ade80; }
.cost .badge { width: 150px; flex: none; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #22d3ee, #0891b2); color: #0a0e1a; font-size: 40px;
  font-weight: 800; border-radius: 16px; }
.cost .billing { text-align: center; font-size: 28px; color: #e2e8f0; }
.cost .billing b { color: #22d3ee; font-size: 34px; }

/* 能力排行榜（Terminal-Bench 2.1 真实分数） */
.rank { width: 100%; max-width: 1460px; display: flex; flex-direction: column; gap: 14px; }
.rank .head { font-size: 22px; color: #94a3b8; padding-bottom: 10px; border-bottom: 1px solid #1f2b44; }
.rank .head b { color: #e2e8f0; }
.rank .row { display: flex; align-items: center; gap: 22px; background: #0f1a2e;
  border: 1px solid #2a3a55; border-radius: 12px; padding: 15px 26px; padding-right: 64px; }
.rank .row .rk { width: 52px; height: 52px; flex: none; border-radius: 10px; background: #1f2b44;
  color: #94a3b8; display: flex; align-items: center; justify-content: center;
  font-size: 24px; font-weight: 800; }
.rank .row.top .rk { background: linear-gradient(135deg, #d97706, #fbbf24); color: #0a0e1a; }
.rank .row .nm { width: 260px; flex: none; font-size: 26px; font-weight: 700; color: #ffffff; }
.rank .row.cn .nm { color: #67e8f9; }
.rank .row .bar { flex: 1; height: 18px; background: #0b1220; border-radius: 9px; overflow: hidden; }
.rank .row .bar i { display: block; height: 100%; border-radius: 9px;
  background: linear-gradient(90deg, #155e75, #22d3ee); }
.rank .row.top .bar i { background: linear-gradient(90deg, #92400e, #fbbf24); }
.rank .row .sc { width: 92px; flex: none; text-align: right; font-family: Consolas, monospace;
  font-size: 32px; font-weight: 800; color: #67e8f9; }
.rank .row.top .sc { color: #fbbf24; }
.rank .row .lbl { width: 200px; flex: none; font-size: 18px; color: #64748b; }
.rank .row.mute { opacity: 0.5; }

/* 结语 */
.ctaend { width: 100%; max-width: 1580px; display: flex; flex-direction: column;
  align-items: center; gap: 36px; text-align: center; }
.ctaend .big { font-size: 84px; font-weight: 800; color: #ffffff; text-shadow: 0 0 40px rgba(34,211,238,0.45); }
.ctaend .keep { font-size: 30px; color: #94a3b8; }
.ctaend .follow { background: linear-gradient(135deg, #22d3ee, #0891b2); color: #0a0e1a;
  font-size: 30px; font-weight: 800; padding: 18px 40px; border-radius: 14px;
  box-shadow: 0 0 50px rgba(34,211,238,0.5); }

/* 字幕带 + 进度条 */
.subtitle-band { flex: none; height: 104px; padding: 0 120px 0 36px; margin-top: 16px;
  background: rgba(15,23,42,0.92); border: 1px solid rgba(34,211,238,0.4); border-radius: 12px;
  display: flex; align-items: center; justify-content: center; overflow: hidden;
  box-shadow: 0 0 30px rgba(34,211,238,0.15), inset 0 0 20px rgba(34,211,238,0.05); }
.subtitle { font-size: 48px; line-height: 1; color: #ffffff; text-align: center; max-width: 100%;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  text-shadow: 0 2px 4px rgba(0,0,0,0.95), 0 0 2px #000, -1px -1px 0 #000, 1px 1px 0 #000; }
.subtitle.empty { visibility: hidden; }
.progress-track { position: absolute; left: 0; right: 0; bottom: 0; height: 6px;
  background: rgba(34,211,238,0.12); }
.progress-fill { height: 100%; background: linear-gradient(90deg, #06b6d4, #22d3ee);
  box-shadow: 0 0 25px rgba(34,211,238,1), 0 0 50px rgba(34,211,238,0.6); }"""


_HOOK_MATS = [
    "已装 Claude Code 或 Codex",
    "国产平台 API key · DeepSeek / Qwen / Kimi / GLM",
    "免费切换工具 CcSwitch",
]


def _hook(card, a):
    big_html = card.get("big") or 'Claude Code 官方号又被封了？<span class="hl">别慌，换模型就行</span>'
    mats = card.get("mats") or _HOOK_MATS
    cta_text = card.get("cta") or "评论区扣「省成本」，配置模板和文字教程发你"
    big = _hot(0, a, f'<div class="big">{big_html}</div>')
    m = _hot(1, a, '<div class="mats">' + "".join(
        f"<span>{_esc(x)}</span>" for x in mats
    ) + "</div>")
    c = _hot(2, a, cta_text, cls="cta")
    return '<div class="hook">' + big + m + c + "</div>"


def _install(card, a):
    pts = card.get("points", []) or ["", "", ""]
    repo = card.get("repo") or "farion1231 / cc-switch"
    repo_note = card.get("repo_note") or "MIT 协议 · Tauri + Rust"
    ver = card.get("ver") or pts[0] or ""
    tag = card.get("tag") or "最新 release · farion1231/cc-switch"
    assets = card.get("assets") or ["macOS.dmg", "Windows.msi", "Portable.zip"]
    dl = card.get("dl") or pts[1] or ""
    note = card.get("note") or pts[2] or ""
    rel = _hot(0, a, f'<div class="ver">{_esc(ver)}</div>'
                     f'<div class="tag">{_esc(tag)}</div>', cls="rel")
    dl_h = _hot(1, a, '<div class="assets">' + "".join(
        f"<span>{_esc(x)}</span>" for x in assets
    ) + f'</div><div class="dl">{_esc(dl)} →</div>')
    note_h = _hot(2, a, f"✓ {_esc(note)}")
    return (
        '<div class="gh">'
        f'<div class="repo"><b>{_esc(repo)}</b>　{_esc(repo_note)}</div>'
        + rel + dl_h + note_h +
        "</div>"
    )


def _terminal(card, a):
    """终端窗口：内容可配。card.lines=[{step, text, cls}]，step 对应 steps 序号。"""
    pts = card.get("points", []) or ["", "", ""]
    raw = card.get("lines")
    if raw:
        lines = [(l.get("step", 0), l["text"], l.get("cls", "out")) for l in raw]
    else:  # 向后兼容旧 deck：pts[1]/pts[2] 作为后两行
        lines = [
            (0, '<span class="ps">$</span> claude /status', "out"),
            (0, '<span class="warn">model: Claude Opus 5　← 还是官方模型？</span>', "warn"),
            (1, f"→ {_esc(pts[1])}", "out"),
            (2, f"→ {_esc(pts[2])}", "out"),
        ]
    out = []
    for _i, (step, text, cls0) in enumerate(lines):
        if step < a:
            out.append(f'<span class="dim {cls0}">✓ {text}</span>')
        elif step == a:
            out.append(f'<span class="hot active {cls0}">{text}</span>')
        else:
            out.append(f'<span class="dim {cls0}">{text}</span>')
    return '<pre class="term">' + "\n".join(out) + "</pre>"


def _ccswitch(card, a):
    sw = _hot(0, a, '应用切换器　<b>Claude Code ▾</b>', cls="appswitch")
    panel = _hot(1, a, '预设：<b>DeepSeek</b>（Base URL 已填好）　API key：'
                       '<span class="keybox">••••••••••</span><button class="btn">添加</button>', cls="panel")
    provs = _hot(2, a, '<div class="providers">' + "".join(
        f'<div class="prov"><span class="nm">{_esc(nm)}</span>'
        f'<span class="sw{" on" if i == 0 else ""}">{"✓ 已启用" if i == 0 else "启用"}</span></div>'
        for i, nm in enumerate(["DeepSeek", "Qwen", "Kimi", "GLM"])
    ) + "</div>")
    return '<div class="ccs">' + sw + panel + provs + "</div>"


def _settings(card, a):
    code = card.get("env") or ('<div class="cmt">// ~/.claude/settings.json</div>'
            '{ <span class="key">"env"</span>: {\n'
            '　<span class="key">"ANTHROPIC_BASE_URL"</span>: <span class="val">"https://api.deepseek.com/anthropic"</span>,\n'
            '　<span class="key">"ANTHROPIC_AUTH_TOKEN"</span>: <span class="val">"sk-..."</span>\n'
            '} }')
    status = card.get("status") or '$ claude /model → <b>DeepSeek V4 Flash</b>　选中国产'
    third = card.get("third") or "Codex：auth.json + config.toml 一起写好 · 重启终端 · 原生支持 Responses API"
    env = _hot(0, a, code, cls="code")
    st = _hot(1, a, status, cls="mini")
    th = _hot(2, a, third, cls="mini")
    return '<div class="editor">' + env + st + th + "</div>"


def _map(card, a):
    cells = [
        (0, "日常主力", "V4 Flash", "md"),
        (1, "深思考 / 重活", "Qwen3-Coder · Kimi", "md"),
        (2, "整体", "全量国产 · 官方号不碰", "all"),
    ]
    out = []
    for idx, tag, md, cls in cells:
        out.append(_hot(idx, a, f'<span class="tag">{_esc(tag)}</span>'
                                f'<span class="{cls}">{_esc(md)}</span>', cls="cell"))
    return '<div class="grid">' + "".join(out) + "</div>"


def _cost(card, a):
    old = _hot(0, a, '<div class="name">官方 · Claude Opus 5</div>'
                     '<div class="price">$5</div><div class="unit">/ 百万 token 输入</div>', cls="col old")
    badge = _hot(1, a, "178×", cls="badge")
    new = _hot(1, a, '<div class="name">DeepSeek V4 Flash · 缓存命中</div>'
                     '<div class="price">$0.028</div><div class="unit">再享 98% 缓存折扣</div>', cls="col new")
    bill = _hot(2, a, "重度月账单：<b>$100+ → 个位数</b>，省 99%", cls="billing")
    return '<div class="cost"><div class="row">' + old + badge + new + "</div>" + bill + "</div>"


def _cta(card, a):
    big_html = card.get("big") or "封号没了 · 钱省了"
    keep_text = card.get("keep") or "客户端还是那套 Claude Code · Skills / MCP / subagents 一个不少"
    follow_text = card.get("follow") or "关注我 + 评论区扣「省成本」"
    big = _hot(0, a, f'<div class="big">{big_html}</div>')
    keep = _hot(1, a, f'<div class="keep">{_esc(keep_text)}</div>')
    follow = _hot(2, a, follow_text, cls="follow")
    return '<div class="ctaend">' + big + keep + follow + "</div>"


def _warn(card, a):
    """避坑警告：别注册官方号 / 别买黄牛号 → 直接全国产。"""
    items = card.get("items") or [
        "别注册官方账号 · 地区判断 · 一回国就封",
        "别买黄牛号 · 花大几百 · 说封就封",
        "直接 VSCode + CcSwitch + DeepSeek",
    ]
    out = []
    for idx, txt in enumerate(items):
        out.append(_hot(idx, a, f'<span class="wmark">⚠</span>{_esc(txt)}', cls="wrow"))
    return '<div class="warnbox">' + "".join(out) + "</div>"


def _chat(card, a):
    """Claude Code 对话窗：用嘴提需求 → 它开写保存 → 重复事自动跑。"""
    req = card.get("req") or "帮我做一个网页，记录每周跑步次数，点一下加一"
    code = card.get("code") or '<span class="ok">✓</span> index.html 已保存 · 双击就能用'
    resp = card.get("resp") or "重复超过三次的事，全交给它自动跑"
    user = _hot(0, a, f'<div class="cb user">{_esc(req)}</div>')
    ai = _hot(1, a, f'<div class="cb ai"><div class="cbname">Claude Code</div>{code}</div>')
    auto = _hot(2, a, f'<div class="cb ai"><div class="cbname">Claude Code</div>{_esc(resp)}</div>')
    return '<div class="chat">' + user + ai + auto + "</div>"


def _realshot(card, a):
    """真实网页截图打底 + 热点特写取景 + 箭头标注（拟物化核心）。

    card 字段：slug（资产目录）、shot（截图 key）、hotspots=[{x,y,w,h,label}]，
    坐标均为截图百分比（capture_shots.py 产出）。

    布局（2026-08-24 可读性改造）：有 active 热点时双层呈现——底层整页截图
    暗化 45% 作位置参照，上层以热点为中心 1.6× 特写（截图内文字信息流等效从
    6-8px 提到 10px+）。热点框/箭头画在特写层坐标系（源百分比 v → (v-c)*Z+50）。
    无 active 热点（a<0 或该步无坐标）回退整页呈现（原行为）。
    """
    src = _shot_b64(card.get("slug", ""), card.get("shot", ""))
    if not src:
        return (f'<div style="color:#f87171;font-size:28px;font-weight:700">'
                f'截图缺失: {_esc(card.get("shot", ""))}</div>')
    hotspots = card.get("hotspots") or []
    points = card.get("points") or []

    active_hp = None
    if 0 <= a < len(hotspots) and hotspots[a]:
        active_hp = hotspots[a]

    def spot_divs(zoom: float, cx: float, cy: float) -> list[str]:
        """热点框 + active 箭头标签，画在 zoom 倍特写坐标系。"""
        out = []
        for i in range(len(points)):
            hp = hotspots[i] if i < len(hotspots) else None
            if not hp:
                continue
            x = (hp["x"] - cx) * zoom + 50
            y = (hp["y"] - cy) * zoom + 50
            w, h = hp["w"] * zoom, hp["h"] * zoom
            cls = "hspot done" if i < a else ("hspot active" if i == a else "hspot fut")
            out.append(f'<div class="{cls}" style="left:{x}%;top:{y}%;width:{w}%;height:{h}%"></div>')
            if i == a:
                label = _esc(hp.get("label", ""))
                if x >= 22:  # 热点靠右 → 从左边指进去
                    out.append(
                        f'<div class="harr" style="left:{x}%;top:{y + h / 2}%">'
                        f'<span class="hlab">{label}</span><i></i></div>')
                else:        # 热点贴左 → 从右边指进去
                    out.append(
                        f'<div class="harr right" style="left:{x + w}%;top:{y + h / 2}%">'
                        f'<i></i><span class="hlab">{label}</span></div>')
        return out

    if not active_hp:
        # 回退：整页呈现（原行为），坐标系即源图本身
        parts = [f'<img src="{src}" alt="">'] + spot_divs(1.0, 50.0, 50.0)
        return '<div class="shotwrap">' + "".join(parts) + "</div>"

    Z = 1.6  # 特写放大倍数
    # 热点中心（源百分比）；clamp 保证特写窗四边不越出源图
    half = 50.0 / Z
    cx = min(max(active_hp["x"] + active_hp["w"] / 2, half), 100 - half)
    cy = min(max(active_hp["y"] + active_hp["h"] / 2, half), 100 - half)
    zoom_inner = (
        f'<img src="{src}" alt="" style="width:{Z * 100:.0f}%;height:{Z * 100:.0f}%;'
        f'left:calc(50% - {cx * Z:.1f}%);top:calc(50% - {cy * Z:.1f}%)">'
    )
    parts = [
        f'<img class="shotctx" src="{src}" alt="">',
        '<div class="shotzoom">' + zoom_inner + "".join(spot_divs(Z, cx, cy)) + "</div>",
    ]
    return '<div class="shotwrap">' + "".join(parts) + "</div>"


def _vscode(card, a):
    """写实 VSCode 窗口：Claude Code 插件使用流程（怎么用）。

    layout：activitybar(Claude 图标) + sidebar(Claude 对话面板) + editor(index.html) +
    statusbar(DeepSeek V4 Flash)。active_idx 依次点亮：点开图标 → 输入需求 → 它写代码 →
    点接受。
    """
    req = card.get("req") or "做一个网页，记录每周跑步次数，点一下加一"
    code_lines = card.get("code") or [
        '<span class="c">&lt;!DOCTYPE html&gt;</span>',
        '<span class="t">&lt;html</span> <span class="b">lang</span>=<span class="s">"zh"</span><span class="t">&gt;</span>',
        '<span class="t">&lt;head&gt;</span>',
        '　<span class="t">&lt;title&gt;</span>跑步记录<span class="t">&lt;/title&gt;</span>',
        '<span class="t">&lt;/head&gt;</span>',
        '<span class="t">&lt;body&gt;</span>',
        '　<span class="k">let</span> count = <span class="b">0</span>;',
        '　<span class="c">&lt;!-- 点一下加一 --&gt;</span>',
        '<span class="t">&lt;/body&gt;</span>',
        '<span class="t">&lt;/html&gt;</span>',
    ]
    resp = card.get("resp") or "已生成 index.html · 双击就能用"

    # activitybar 图标列
    icons = [("☰", ""), ("🗁", ""), ("⌕", ""), ("⑂", ""), ("✦", ""), ("◉", "cc")]
    ic_parts = []
    for i, (glyph, cls0) in enumerate(icons):
        if cls0 == "cc":
            cls = "ic cc" + (" active" if a == 0 else (" done" if a > 0 else ""))
            ic_parts.append(f'<div class="hot {cls}"><span>{glyph}</span></div>')
        else:
            ic_parts.append(f'<div class="ic"><span>{glyph}</span></div>')
    actbar = '<div class="actbar">' + "".join(ic_parts) + "</div>"

    # sidebar：Claude 对话面板（点开图标后出现；step0 前半透明占位）
    user_msg = _esc(req)
    ai_ok = f'<b>✓</b> <span class="ok">index.html 已保存</span>'
    accept = '接受全部更改'
    side_msg = ""
    if a >= 1:
        side_msg += f'<div class="msg user">{user_msg}</div>'
    if a >= 2:
        side_msg += f'<div class="msg ai">{ai_ok}</div>'
    if a >= 3:
        side_msg += f'<div class="accept hot active">✓ {accept}</div>'
    if a == 1:
        side_msg += f'<div class="msg user hot active">{user_msg}</div>'
    if a == 2:
        side_msg += f'<div class="msg ai hot active">{ai_ok}</div>'
    placeholder = '<div style="color:#5a5a5a;font-size:13px;padding:6px 4px">点图标打开对话面板</div>'
    in_bar = (f'<div class="inbar"><div class="in">'
              f'<span style="color:#888">描述你想让 Claude 做什么…</span></div>'
              f'<div class="send">发送</div></div>')
    if a == 1:
        in_bar = (f'<div class="inbar"><div class="in hot active">{user_msg}</div>'
                  f'<div class="send">发送</div></div>')
    sidebar = ('<div class="sidebar">'
               f'<div class="sidehead"><span class="logo">✦</span> Claude Code　'
               f'<span style="color:#4d9fff">DeepSeek V4 Flash</span></div>'
               f'<div class="chatbody">{side_msg or placeholder}</div>'
               + in_bar + "</div>")

    # editor：index.html 代码，step2 高亮命中行
    code_html = "".join(line + "\n" for line in code_lines)
    if a == 2:
        code_html = code_html.replace('<span class="c">&lt;!-- 点一下加一 --&gt;</span>',
                                      '<span class="c hit">&lt;!-- 点一下加一 --&gt;</span>')
    editor = ('<div class="editor">'
              f'<div class="code">{code_html}</div>'
              + "</div>")

    # 整体 vsw 窗口
    return (
        '<div class="vsw">'
        f'<div class="tabbar"><div class="tab on"><span class="dot"></span>index.html</div>'
        f'<span class="site">Claude Code · 用嘴说，它动手</span></div>'
        '<div class="mid">' + actbar + sidebar + editor + "</div>"
        f'<div class="statusbar"><span>⎇ master</span><span>✓ 0 ⚠ 0</span>'
        f'<span class="sp">DeepSeek V4 Flash</span></div>'
        "</div>"
    )


def _rank(card, a):
    """能力排行榜：Terminal-Bench 2.1 官方实测分数（Opus 4.8 / V4 Flash / GLM-5.2 / V4 Pro 预览）。"""
    rows = [
        (0, "1", "Opus 4.8", 85.0, "top", "闭源旗舰 · 榜首"),
        (1, "2", "DeepSeek V4 Flash", 82.7, "cn", "国产第一 · 逼近 Opus"),
        (2, "3", "GLM-5.2", 81.0, "cn", "国产第二"),
        (None, "4", "DeepSeek V4 Pro 预览", 72.1, "mute", "预览版"),
    ]
    maxsc = 85.0
    parts = []
    for idx, rk, nm, sc, extra, lbl in rows:
        w = sc / maxsc * 100.0
        inner = (f'<span class="rk">{rk}</span>'
                 f'<span class="nm">{_esc(nm)}</span>'
                 f'<span class="bar"><i style="width:{w:.1f}%"></i></span>'
                 f'<span class="sc">{sc:.1f}</span>'
                 f'<span class="lbl">{_esc(lbl)}</span>')
        if idx is None:
            parts.append(f'<div class="row mute">{inner}</div>')
        else:
            parts.append(_hot(idx, a, inner, cls=f"row {extra}"))
    head = '<div class="head"><b>Terminal-Bench 2.1</b> · 命令行 Agent 基准 · 官方实测分数</div>'
    return '<div class="rank">' + head + "".join(parts) + "</div>"


_CONTENT = {
    "hook": _hook, "install": _install, "terminal": _terminal, "ccswitch": _ccswitch,
    "settings": _settings, "rank": _rank, "map": _map, "cost": _cost, "cta": _cta,
    "warn": _warn, "chat": _chat,
    "realshot": _realshot, "vscode": _vscode,
}


def render_frame(card: dict, state: dict, width: int = 1920, height: int = 1080) -> str:
    """渲染一帧屏录感画面。

    card:  {"type":"tool","tool":"<种类>","title","subtitle"(窗口标题),"points":[步骤]}
    state: {"active_idx","subtitle"(字幕),"progress"}
    """
    tool = card.get("tool", "")
    title = card.get("title", "") or ""
    win_title = card.get("subtitle", "") or title
    active_idx = int(state.get("active_idx", -1))
    state_sub = state.get("subtitle", "") or ""
    progress = float(state.get("progress", 0.0))
    pct = max(0.0, min(1.0, progress)) * 100.0
    css = _CSS.replace("__W__", str(width)).replace("__H__", str(height))

    pts = card.get("points", []) or [title]
    cells = []
    for i, p in enumerate(pts):
        if i < active_idx:
            st = "done"
        elif i == active_idx:
            st = "active"
        else:
            st = "fut"
        cells.append(f'<span class="s-step {st}"><span class="ix">{i + 1}</span>'
                     f'<span class="tx">{_esc(p)}</span></span>')
    steps = '<div class="steplist">' + "".join(cells) + "</div>"

    builder = _CONTENT.get(tool, lambda c, a: f'<div style="color:#64748b">未知 tool: {_esc(tool)}</div>')
    body = builder(card, active_idx)

    sub_cls = "subtitle" if state_sub else "subtitle empty"
    band = f'<div class="subtitle-band"><div class="{sub_cls}">{_esc(state_sub)}</div></div>'
    prog = f'<div class="progress-track"><div class="progress-fill" style="width:{pct:.2f}%"></div></div>'

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>screencast frame</title>
<style>
{css}
</style>
</head>
<body>
<div class="screencast">
  <div class="window">
    <div class="titlebar">
      <span class="lights"><i class="r"></i><i class="y"></i><i class="g"></i></span>
      <span class="wtitle">{_esc(win_title)}</span>
      <span class="wtag">记录中 ●</span>
    </div>
    {steps}
    <div class="winbody">{body}</div>
  </div>
  {band}
  {prog}
</div>
</body>
</html>"""


if __name__ == "__main__":
    # 自测：渲染 8 种 tool 的画面，肉眼检查
    import json
    import os
    import sys
    from pathlib import Path

    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    from video.config import OUTPUT_ROOT

    deck = json.loads(
        (OUTPUT_ROOT / "deck" / "claude-code-ccswitch-domestic-models" / "deck.json")
        .read_text(encoding="utf-8")
    )
    out = OUTPUT_ROOT / "probe" / "screencast_preview"
    out.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1920, "height": 1080})
        for i, c in enumerate(deck["cards"]):
            card = {
                "type": c.get("type", "insight"),
                "tool": c.get("tool", ""),
                "title": c.get("title", ""),
                "subtitle": c.get("subtitle", ""),
                "points": list(c.get("points", [])),
            }
            for st in range(len(card["points"])):
                html = render_frame(card, {"active_idx": st, "subtitle": f"自测字幕 {st}", "progress": 0.4})
                pg.set_content(html)
                pg.wait_for_timeout(60)
                shot = out / f"card{i:02d}_step{st}.png"
                pg.screenshot(path=str(shot))
                print(f"[{shot.name}] {shot.stat().st_size} bytes")
        b.close()
    print("DONE")
