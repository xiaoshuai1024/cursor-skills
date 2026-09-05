"""prism——白色科技感动效管线（默认渲染路径，openspec prism-motion-pipeline）。

2026-09-05 用户定规：深色科幻课件（courseware insight/cover/cta 深色渲染）退役删除，
白色版本设为默认。本模块接管全部非 tool/tutorial 卡的渲染。

视觉：亮底 LIGHT_BG + 极光渐变斑（帧驱动漂移）+ 细网格 + 渐变描边玻璃白卡 +
渐变标题条/进度条；代码 / 终端 / flow 等内容窗保留深色拟物 chrome（Stripe/代码频道
质感），magic_move token 形变、rough_note 手绘注记、flowchart 连线生长直接复用。

讲解逻辑（PPT 方法论，见 openspec design.md §1）：断言式标题第一视觉层级、
要点 ≤3 三态（future 降权可见 / active 高亮 / done ✓）、shots 镜头轮换 +
概述轮播、section 章节隔页（大号数字 + mini-agenda 导航）、recap 章末回顾。

卡型：cover / cta（居中收尾）/ section / recap / insight（默认，兼容存量 intro）。
一切动画帧驱动（state["frame"] + 出生帧插值，禁 CSS animation），缓动一律
motion.py；动画窗口外不输出 inline style（PNG 复用优化保持）。
色板：颜色以 palette.py（SSOT）为准，本文件字面量由 lint_colors.py 漂移扫描。
"""

from __future__ import annotations

import math

try:
    from .motion import (                   # 包内运行（python -m video.build）
        ease_out_back,
        ease_out_cubic,
        enter_tuple,
        exit_tuple,
        glow_mult,
        settle_dip,
        stamp_tuple,
        apply_anim,
    )
    from .palette import (
        ACCENT_DEEP,
        LIGHT_ACCENT,
        LIGHT_ACCENT_DARK,
        LIGHT_DONE,
        LIGHT_INK,
        LIGHT_MUTED,
        LIGHT_BG,
        PROGRESS_START,
        SUCCESS_TEXT,
        TUTORIAL_INK,
    )
    from .screencast import _esc
except ImportError:                         # 直接脚本运行（python prism.py）
    from motion import (
        ease_out_back, ease_out_cubic, enter_tuple, exit_tuple,
        glow_mult, settle_dip, stamp_tuple, apply_anim,
    )
    from palette import (
        ACCENT_DEEP, LIGHT_ACCENT, LIGHT_ACCENT_DARK, LIGHT_DONE, LIGHT_INK,
        LIGHT_MUTED, LIGHT_BG, PROGRESS_START, SUCCESS_TEXT, TUTORIAL_INK,
    )
    from screencast import _esc

# 渐变文字（blue→cyan 深端，均过 PAIRS ≥3.0）；纯图形渐变亮端
_GRAD_TEXT = f"linear-gradient(92deg,{LIGHT_ACCENT},{ACCENT_DEEP})"
_GRAD_BAR = f"linear-gradient(90deg,{LIGHT_ACCENT},{PROGRESS_START})"

# 手绘注记白底重映射（rough_note 原色为深底调校：浅色在亮底发灰）
_ANNOTATE_REMAP = {"#22d3ee": "#0891b2", "#f87171": "#dc2626", "#4ade80": "#16a34a"}

# 卡起入场 stagger 锚（帧，24fps）
_ENT_EYEBROW, _ENT_TITLE, _ENT_BAR, _ENT_FOOTER = 2, 4, 8, 10
_ENT_POINT0, _ENT_POINT_STEP, _ENT_POINT_DUR = 6, 2, 8
_POP_DUR, _SETTLE_DUR = 8, 5
_EXIT_DUR = 5
_EXIT_OFFSETS = {"eyebrow": 0, "footer": 0, "title": 1, "bar": 1,
                 "point": 2, "sp": 2, "band": 3, "outline": 0, "shot": 1,
                 "row": 2, "num": 0}
_CUE_OUT_DUR = 4
_SHOT_ENT_DUR, _SHOT_EXIT_DUR = 8, 6
_AURORA_Q = 8            # 极光漂移量化步长（帧）——8 帧一变，PNG 复用保住
_BREATHE_Q = 4           # 常驻微动量化步长（帧）


# ---------------------------------------------------------------------------
# 编舞助手（与原 courseware 同式，缓存于 prism）
# ---------------------------------------------------------------------------

def _attr(style_value: str) -> str:
    """style 值 → 属性片段；空串省略（HTML 相等性 → PNG 复用优化保持）。"""
    return f' style="{style_value}"' if style_value else ""


def _style(op: float, ty: float, sc: float, extra: str = "") -> str:
    """运动量 → style 属性值；全部终态且无附加时返回空串（不输出属性）。"""
    settled = op >= 0.999 and abs(ty) < 0.02 and abs(sc - 1.0) < 0.0015 and not extra
    if settled:
        return ""
    parts = [f"opacity:{max(0.0, op):.3f}",
             f"transform:translateY({ty:.2f}px) scale({sc:.4f})"]
    if extra:
        parts.append(extra.rstrip(";"))
    return ";".join(parts)


def _compose(base: tuple, ex: tuple | None) -> tuple:
    """入场/换态运动量与出场运动量合成（出场乘法叠加透明度、加法叠加位移）。"""
    if ex is None:
        return base
    op, ty, sc = base
    return op * ex[0], ty + ex[1], sc * ex[2]


def _exit(frame: int, out_at, key: str, extra_shift: int = 0,
          dy: float = -26.0) -> tuple | None:
    """按元素错峰偏移取出场运动量；out_at 缺失（旧调用）→ None。"""
    if out_at is None:
        return None
    return exit_tuple(frame - (int(out_at) + _EXIT_OFFSETS.get(key, 0) + extra_shift),
                      _EXIT_DUR, dy=dy)


def _aurora(frame: int) -> tuple[float, float, float, float]:
    """极光斑漂移量（量化 _AURORA_Q 帧一变）→ (dx1, dy1, dx2, dy2) px。"""
    q = (frame or 0) // _AURORA_Q
    return (10.0 * math.sin(q * 0.42), 8.0 * math.cos(q * 0.31),
            12.0 * math.cos(q * 0.27), 9.0 * math.sin(q * 0.38))


def _point_style(frame: int, idx: int, active_idx: int, births: list[int],
                 out_at=None) -> str:
    """单要点合成运动：入场 stagger + active 弹入（back 过冲+辉光）+ done 交叉 + 卡尾出场。"""
    op, ty, sc = enter_tuple(frame - (_ENT_POINT0 + _ENT_POINT_STEP * idx),
                             _ENT_POINT_DUR, dy=20.0)
    extra = ""
    pb = births[idx] if idx < len(births) else None
    if idx == active_idx and pb is not None:
        age = frame - pb
        if 0 <= age < _POP_DUR:
            sc *= enter_tuple(age, _POP_DUR, scale_from=0.94,
                              ease=ease_out_back)[2]
            g = glow_mult(age, 6, 0.8)
            if g is not None:
                m = 1.0 + g
                extra = (f"box-shadow:0 10px {28 * m:.0f}px rgba(37,99,235,{min(1.0, 0.30 * m):.2f}),"
                         f"0 0 0 1px rgba(37,99,235,{min(1.0, 0.35 * m):.2f})")
    elif idx < active_idx and pb is not None:
        nb = births[idx + 1] if idx + 1 < len(births) else None
        if nb is not None:
            dip = settle_dip(frame - nb, _SETTLE_DUR, depth=0.15)
            if dip is not None:
                op = min(op, dip)
                sc *= 0.97 + 0.03 * dip
    op, ty, sc = _compose((op, ty, sc), _exit(frame, out_at, "point"))
    return _style(op, ty, sc, extra)


def _sp_style(frame: int, idx: int, active_idx: int, births: list[int],
              out_at=None) -> str:
    """知识卡运动：active 卡在要点出生帧+2 弹入（spring），前一卡交叉退场 + 卡尾出场。"""
    pb = births[idx] if idx < len(births) else None
    if idx == active_idx and pb is not None:
        op, ty, sc = enter_tuple(frame - (pb + 2), 10, dy=44.0,
                                 scale_from=0.92, ease=ease_out_back)
        op, ty, sc = _compose((op, ty, sc), _exit(frame, out_at, "sp", dy=-34.0))
        return _style(op, ty, sc)
    if idx < active_idx:
        nb = births[idx + 1] if idx + 1 < len(births) else None
        if nb is not None:
            op, ty, sc = enter_tuple(frame - (nb + 2), 8, dy=10.0)
            dip = settle_dip(frame - nb, _SETTLE_DUR, depth=0.25)
            if dip is not None:
                op *= 1.0 - 0.45 * dip
            op, ty, sc = _compose((op, ty, sc), _exit(frame, out_at, "sp", dy=-24.0))
            return _style(op, ty, sc)
    return _style(0.0, 0.0, 1.0) if out_at is None else ""


def _bar_style(frame: int, births: list[int], active_idx: int, out_at=None) -> str:
    """渐变标题条：卡起宽度生长 + 每次换拍辉光脉冲（主锚联动）+ 卡尾淡出上移。"""
    age = frame - _ENT_BAR
    if age < 0:
        return "width:0px"
    parts = []
    if age < 12:
        parts.append(f"width:{160 * ease_out_cubic(age / 12):.1f}px")
    if active_idx >= 0:
        pb = births[active_idx] if active_idx < len(births) else None
        if pb is not None:
            g = glow_mult(frame - pb, 8, 0.9)
            if g is not None:
                m = 1.0 + g
                parts.append(
                    f"box-shadow:0 0 {26 * m:.0f}px rgba(8,145,178,{min(1.0, 0.55 * m):.2f}),"
                    f"0 6px {18 * m:.0f}px rgba(37,99,235,{min(1.0, 0.30 * m):.2f})")
    ex = _exit(frame, out_at, "bar", dy=-18.0)
    if ex is not None:
        parts.append(f"opacity:{ex[0]:.3f};transform:translateY({ex[1]:.2f}px)")
    return ";".join(parts)


def _progress_style(pct: float, frame: int, births: list[int]) -> str:
    """进度条：宽度保持时间连续；要点出生帧辉光跳档脉冲（联动）。"""
    pulse = ""
    for pb in births:
        g = glow_mult(frame - pb, 6, 0.9)
        if g is not None:
            m = 1.0 + g
            pulse = (f"box-shadow:0 0 {22 * m:.0f}px rgba(6,182,212,{min(1.0, 0.7 * m):.2f}),"
                     f"0 0 {44 * m:.0f}px rgba(37,99,235,{min(1.0, 0.45 * m):.2f})")
            break
    return f"width:{pct:.2f}%" + (f";{pulse}" if pulse else "")


def _band_state(frame: int, state_sub: str, cue_birth, cue_out,
                out_at) -> tuple[str, str, str]:
    """字幕带状态 → (文本, class, style)。三层合成：
    分句入场（cue_birth，上滑淡入）→ 分句退场（cue_out，加速上移淡出）
    → 卡尾出场（out_at+3，与其他元素错峰）。"""
    if state_sub:
        text = state_sub
        if cue_birth is not None:
            base = enter_tuple(frame - int(cue_birth), 4, dy=12.0)
        else:
            base = (1.0, 0.0, 1.0)
    elif cue_out:
        text, age = str(cue_out[0]), int(cue_out[1])
        base = exit_tuple(age, _CUE_OUT_DUR, dy=-14.0) or (0.0, -14.0, 1.0)
    else:
        return "", "subtitle empty", ""
    ex = _exit(frame, out_at, "band", dy=-16.0)
    op, ty, sc = _compose(base, ex)
    return text, "subtitle", _style(op, ty, sc)


def _shot_layer_style(frame: int, si: int, shot_idx: int, birth, out_at=None) -> str | None:
    """镜头层三态：当前层右滑入场（slideleft 主流向：新镜头从右缘推进来），
    上一层向左滑出；未开场 / 早已替换的层不渲染。"""
    if shot_idx < 0 or si > shot_idx:
        return None
    birth = int(birth or 0)
    if si == shot_idx:
        age = frame - birth
        if age < 0:
            return None
        if age < _SHOT_ENT_DUR:
            e = ease_out_cubic(age / _SHOT_ENT_DUR)
            return f"opacity:{e:.3f};transform:translateX({36.0 * (1.0 - e):.2f}px)"
        return ""
    if si == shot_idx - 1:                  # 刚被替换：短淡出横移
        age = frame - birth
        if age >= _SHOT_EXIT_DUR:
            return None
        e = ease_out_cubic(min(1.0, age / _SHOT_EXIT_DUR))
        if e >= 0.999:
            return None
        return f"opacity:{1.0 - e:.3f};transform:translateX({-36.0 * e:.2f}px)"
    return None


def _row_style(frame: int, birth: int, i: int, dur: int = 6) -> str:
    """行级 stagger 出生样式；终态空串（静止段 HTML 稳定 → PNG 复用优化保持）。"""
    age = frame - (birth + 2 + 2 * i)
    if 0 <= age < dur:
        e = ease_out_cubic(age / dur)
        if e < 0.999:
            return (f' style="opacity:{e:.3f};'
                    f'transform:translateY({12.0 * (1.0 - e):.2f}px)"')
    return ""


def _hl_lines(shot: dict, state: dict) -> list[int]:
    """当前高亮行：hl_steps 讲到哪行亮哪行（帧外静态 hl 兜底，data.hl 惯例兼容）。"""
    hl = None
    for t, line in (shot.get("hl_steps") or []):
        if state.get("shot_t_ms", 0) >= float(t) * 1000.0:
            hl = line
    if hl is None:
        hl = shot.get("hl")
    if hl is None:
        hl = (shot.get("data") or {}).get("hl")
    if hl is None:
        return []
    return [hl] if isinstance(hl, int) else [int(x) for x in hl]


def _annotate_svg(svg: str) -> str:
    """rough_note SVG 白底重映射（深底浅色 → 亮底深色，语义不变）。"""
    for old, new in _ANNOTATE_REMAP.items():
        svg = svg.replace(old, new)
    return svg


# ---------------------------------------------------------------------------
# 样式（白色科技感；色值全部 palette 注册，lint_colors 漂移扫描）
# ---------------------------------------------------------------------------

_CSS = """* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { width: __W__px; height: __H__px; }
body {
  font-family: "Microsoft YaHei", "微软雅黑", "PingFang SC", sans-serif;
  background-color: __LIGHT_BG__; color: __TUTORIAL_INK__;
  position: relative; overflow: hidden; -webkit-font-smoothing: antialiased;
}
/* ---- 氛围层：极光渐变斑（帧驱动漂移）+ 细网格 + 顶部冷光 ---- */
.aurora { position: absolute; border-radius: 50%; pointer-events: none;
  filter: blur(10px); }
.aurora.a1 { width: 1100px; height: 700px; left: -180px; top: -220px;
  background: radial-gradient(closest-side, rgba(96,165,250,0.10), transparent 70%); }
.aurora.a2 { width: 900px; height: 620px; right: -160px; bottom: -180px;
  background: radial-gradient(closest-side, rgba(34,211,238,0.08), transparent 70%); }
.grid { position: absolute; inset: 0; pointer-events: none;
  background-image:
    linear-gradient(#e8edf4 1px, transparent 1px),
    linear-gradient(90deg, #e8edf4 1px, transparent 1px);
  background-size: 44px 44px; }
.toplight { position: absolute; left: 0; right: 0; top: 0; height: 4px;
  background: __GRAD_BAR__; opacity: 0.85; }
.wrap { position: relative; z-index: 1; width: 100%; height: 100%;
  padding: 44px 200px 150px 64px; display: flex; flex-direction: column; }

/* ---- 顶栏：眉题胶囊 + 断言标题 + 渐变标题条 ---- */
.eyebrow { align-self: flex-start; background: rgba(255,255,255,0.85);
  border: 1.5px solid #dbe4f0; border-radius: 999px; padding: 8px 20px;
  font-size: 24px; font-weight: 700; letter-spacing: 4px; color: __LIGHT_ACCENT__;
  white-space: nowrap; box-shadow: 0 4px 14px rgba(30,41,59,0.06); }
.h1 { font-size: 72px; font-weight: 800; letter-spacing: 1px; line-height: 1.22;
  color: __LIGHT_INK__; margin-top: 14px; word-break: break-word; }
.title-bar { width: 160px; height: 6px; margin-top: 18px; border-radius: 3px;
  background: __GRAD_BAR__; }

/* ---- 步骤条（全量展示三态）---- */
.steps { display: flex; gap: 10px; margin: 14px 0 20px; }
.spill { display: flex; align-items: center; gap: 8px; border-radius: 999px;
  padding: 9px 16px; font-size: 24px; font-weight: 600; white-space: nowrap;
  background: rgba(255,255,255,0.85); border: 1.5px solid #dbe3ee; color: #475569; }
.spill .n { display: inline-flex; align-items: center; justify-content: center;
  width: 30px; height: 30px; border-radius: 50%; font-size: 18px;
  background: #eef2f7; color: #64748b; font-weight: 700; }
.spill.done { border-color: #bfe4cd; color: #15803d; background: #f2fbf5; }
.spill.done .n { background: #dcfce7; color: #15803d; }
.spill.active { border-color: __LIGHT_ACCENT__; background: __LIGHT_ACCENT__;
  color: #ffffff; box-shadow: 0 6px 22px rgba(37,99,235,0.38); }
.spill.active .n { background: rgba(255,255,255,0.25); color: #ffffff; }

/* ---- 主区：左要点（玻璃卡三态）+ 右舞台 ---- */
.main { flex: 1; display: flex; gap: 30px; min-height: 0; }
.pts { width: 40%; display: flex; flex-direction: column; justify-content: center;
  gap: 18px; min-width: 0; }
.pt { display: flex; align-items: flex-start; gap: 14px; background: rgba(255,255,255,0.82);
  border: 1.5px solid transparent;
  background: linear-gradient(rgba(255,255,255,0.86), rgba(255,255,255,0.86)) padding-box,
              linear-gradient(120deg, #dbe4f0, #c7e6f2) border-box;
  border-radius: 14px; padding: 16px 18px; font-size: 48px; font-weight: 600;
  color: __LIGHT_MUTED__; line-height: 1.4;
  box-shadow: 0 4px 14px rgba(30,41,59,0.05); }
.pt .ic { flex-shrink: 0; display: inline-flex; align-items: center; justify-content: center;
  width: 42px; height: 42px; border-radius: 50%; font-size: 21px; font-weight: 800;
  background: #eef2f7; color: #64748b; margin-top: 4px; }
.pt.done { color: __LIGHT_DONE__; }
.pt.done .ic { background: #dcfce7; color: #15803d; }
.pt.done .ic::before { content: "✓"; }
.pt.active { color: __TUTORIAL_INK__; font-size: 56px; font-weight: 700;
  background: linear-gradient(#ffffff, #ffffff) padding-box,
              linear-gradient(120deg, __LIGHT_ACCENT__, rgba(8,145,178,0.55)) border-box;
  box-shadow: 0 10px 30px rgba(37,99,235,0.20); }
.pt.active .ic { background: __LIGHT_ACCENT__; color: #ffffff; }

/* ---- 右舞台：内容窗 / 知识卡 / 概述轮播 ---- */
.stagewrap { flex: 1; position: relative; min-width: 0; }
.shot { position: absolute; inset: 0; display: flex; flex-direction: column; }
.sp-item { position: relative; border-radius: 16px; word-break: break-word; }
.sp-item.done { font-size: 28px; line-height: 1.4; color: __LIGHT_DONE__;
  padding: 10px 18px; background: rgba(255,255,255,0.75); border-left: 4px solid #bfdbfe;
  box-shadow: 0 3px 10px rgba(30,41,59,0.04); }
.sp-item.active { background: linear-gradient(#ffffff, #ffffff) padding-box,
              linear-gradient(120deg, __LIGHT_ACCENT__, rgba(8,145,178,0.55)) border-box;
  border: 1.5px solid transparent; border-radius: 18px; padding: 32px 30px 30px;
  min-height: 260px; box-shadow: 0 16px 40px rgba(37,99,235,0.16); }
.sp-item.active::before { content: "知识卡片"; position: absolute; top: -16px; left: 26px;
  background: __GRAD_BAR__; color: #ffffff; font-size: 24px; font-weight: 700;
  padding: 5px 18px; border-radius: 8px; letter-spacing: 3px;
  box-shadow: 0 6px 18px rgba(37,99,235,0.35); }
.sp-item.active .sp-text { font-size: 48px; line-height: 1.45; color: __LIGHT_INK__;
  font-weight: 600; }
.sp-placeholder { display: flex; align-items: center; justify-content: center;
  height: 100%; color: __LIGHT_MUTED__; font-size: 26px; letter-spacing: 6px; }

/* 概述轮播（左画布白板 6% 定规）：卡片开场先播要点大字轮换 */
.ovl { position: absolute; inset: 0; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 30px; padding: 0 50px; }
.ovl .ovl-eyebrow { font-size: 26px; font-weight: 700; letter-spacing: 6px;
  color: __LIGHT_MUTED__; }
.ovl .ovl-item { font-size: 64px; font-weight: 800; line-height: 1.4;
  color: __LIGHT_INK__; text-align: center; max-width: 94%; }
.ovl .ovl-item .ovl-n { display: inline-flex; align-items: center; justify-content: center;
  width: 62px; height: 62px; border-radius: 50%; background: __GRAD_BAR__;
  color: #ffffff; font-size: 30px; font-weight: 800; margin-right: 22px;
  vertical-align: middle; box-shadow: 0 8px 20px rgba(37,99,235,0.30); }
.ovl .ovl-bar { width: 120px; height: 6px; background: __GRAD_BAR__;
  border-radius: 3px; opacity: 0.85; }

/* ---- 内容窗（深色拟物 chrome：代码 / 终端 / flow 暗画布）---- */
.win { flex: 1; min-height: 0; display: flex; flex-direction: column;
  border-radius: 14px; background: #1e2433; overflow: hidden;
  box-shadow: 0 18px 44px rgba(15,23,42,0.28); border: 1px solid #2b3347; }
.win-bar { display: flex; align-items: center; gap: 8px; padding: 11px 16px;
  background: #171c29; border-bottom: 1px solid #2b3347; flex: none; }
.win-dot { width: 14px; height: 14px; border-radius: 50%; flex: none; }
.win-name { font-size: 22px; color: #9fb0cd; font-family: Consolas, monospace;
  margin-left: 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.win-tag { margin-left: auto; font-size: 19px; color: #ffffff; background: __LIGHT_ACCENT__;
  padding: 3px 14px; border-radius: 6px; font-weight: 700; letter-spacing: 2px; flex: none; }
.win-body { flex: 1; min-height: 0; padding: 22px 0; overflow: hidden;
  font-family: Consolas, "JetBrains Mono", monospace; display: flex;
  flex-direction: column; justify-content: center; }
.cl { font-size: 27px; line-height: 1.62; color: #d7e0f0; white-space: pre;
  display: flex; gap: 18px; padding: 0 20px 0 0; }
.cl .ln { color: #48556e; width: 44px; text-align: right; flex: none;
  user-select: none; }
.cl.hl { color: #ffffff; background: rgba(37,99,235,0.22);
  box-shadow: inset 3px 0 0 __LIGHT_ACCENT__; }
.cl .tok.kw { color: #c792ea; }
.cl .tok.str { color: #a5d6a7; }
.cl .tok.num { color: #f0a45d; }
.cl .tok.cmt { color: #5c6b85; font-style: italic; }
.cl .code-toks { white-space: pre; }
.tl { font-size: 28px; line-height: 1.75; color: #e2e8f0; white-space: pre;
  padding: 0 20px; }
.tl .dir { color: #82aaff; font-weight: 700; }
.tl .dim { color: #64748b; }
.tline { font-size: 27px; line-height: 1.7; white-space: pre-wrap; padding: 0 26px; }
.tline.cmd { color: #82aaff; font-weight: 700; }
.tline.out { color: #cbd5e1; }
.tline.err { color: #f87171; }
.tline.ok { color: #4ade80; }
.tline.dim { color: #64748b; }
.flowcanvas { flex: 1; min-height: 0; border-radius: 16px; background: #0f172a;
  box-shadow: 0 18px 44px rgba(15,23,42,0.30); overflow: hidden; position: relative; }

/* ---- stat / table / quote（白卡亮色）---- */
.shot-stat { flex: 1; display: flex; flex-direction: column; align-items: center;
  justify-content: center; gap: 20px; border-radius: 18px;
  background: linear-gradient(#ffffff, #ffffff) padding-box,
              linear-gradient(135deg, #dbe4f0, #c7e6f2) border-box;
  border: 1.5px solid transparent; box-shadow: 0 16px 40px rgba(30,41,59,0.10); }
.shot-stat .big { font-size: 150px; font-weight: 800; line-height: 1;
  font-family: Consolas, "JetBrains Mono", monospace; letter-spacing: 2px;
  background: __GRAD_TEXT__; -webkit-background-clip: text; background-clip: text;
  color: transparent; }
.shot-stat .label { font-size: 42px; color: __TUTORIAL_INK__; font-weight: 700;
  text-align: center; padding: 0 40px; }
.shot-stat .sub { font-size: 28px; color: __LIGHT_MUTED__; text-align: center; }
.anno-wrap { position: relative; display: inline-block;
  background: __GRAD_TEXT__; -webkit-background-clip: text; background-clip: text; }
/* background-clip:text 对 inline-block 子树失效（Chromium 无头实测大字透明）：
   注记包裹层必须自带渐变并再 clip 一次，否则 stat 大字隐形 */
.anno-svg { position: absolute; left: -4%; top: -14%; width: 108%; height: 128%;
  overflow: visible; pointer-events: none; }
.shot-table { flex: 1; display: flex; flex-direction: column; justify-content: center;
  font-family: inherit; }
.shot-table table { width: 100%; border-collapse: collapse; background: #ffffff;
  border-radius: 14px; overflow: hidden;
  box-shadow: 0 14px 36px rgba(30,41,59,0.09); }
.shot-table th { font-size: 29px; color: __LIGHT_ACCENT_DARK__; background: #eff6ff;
  font-weight: 700; padding: 18px 24px; border-bottom: 2px solid #bfdbfe; text-align: left; }
.shot-table td { font-size: 30px; color: #334155; padding: 18px 24px;
  border-bottom: 1px solid #eef2f7; }
.shot-table tr.hlrow td { color: __LIGHT_ACCENT_DARK__; background: #eff6ff;
  font-weight: 700; }
.shot-quote { flex: 1; display: flex; flex-direction: column; justify-content: center;
  gap: 24px; padding: 34px 44px; border-radius: 18px;
  background: linear-gradient(#ffffff, #ffffff) padding-box,
              linear-gradient(135deg, #dbe4f0, #c7e6f2) border-box;
  border: 1.5px solid transparent; box-shadow: 0 16px 40px rgba(30,41,59,0.10); }
.shot-quote .mark { font-size: 100px; color: #bfdbfe; line-height: 0.4;
  font-family: Georgia, serif; }
.shot-quote .qtext { font-size: 52px; line-height: 1.5; color: __LIGHT_INK__;
  font-weight: 700; }
.shot-quote .qsrc { font-size: 25px; color: __LIGHT_MUTED__;
  font-family: Consolas, monospace; }

/* ---- 字幕带 + 进度条 ---- */
.subtitle-band { position: absolute; left: 0; right: 180px; bottom: 44px; height: 96px;
  display: flex; align-items: center; justify-content: center; z-index: 10; }
.subtitle { font-size: 46px; font-weight: 700; color: __TUTORIAL_INK__;
  background: rgba(255,255,255,0.92); border: 1.5px solid #e2e8f0;
  padding: 10px 34px; border-radius: 999px; max-width: 1500px;
  box-shadow: 0 6px 20px rgba(30,41,59,0.08); }
.progress-track { position: absolute; left: 0; right: 0; bottom: 0; height: 9px;
  background: #e6ebf2; z-index: 11; }
.progress-fill { height: 100%; background: __GRAD_BAR__; border-radius: 0 4px 4px 0; }

/* ---- footer ---- */
.footer-bar { margin-top: 10px; margin-left: 250px; font-size: 24px; font-style: italic;
  color: __LIGHT_ACCENT_DARK__; opacity: 0.9; }

/* ---- section 章节隔页 / recap 回顾 / cover / cta ---- */
.hero { position: absolute; inset: 0; z-index: 1; display: flex;
  flex-direction: column; justify-content: center; padding: 0 220px 90px 96px; }
.hero.center { align-items: center; text-align: center; padding: 0 160px 110px; }
.hero .hook { align-self: flex-start; font-size: 26px; font-weight: 700;
  letter-spacing: 5px; color: __LIGHT_ACCENT__; margin-bottom: 18px; }
.hero.center .hook { align-self: center; }
.hero .big { font-size: 84px; font-weight: 800; line-height: 1.24;
  color: __LIGHT_INK__; letter-spacing: 1px; word-break: break-word; }
.hero .sub { font-size: 30px; color: __LIGHT_MUTED__; font-weight: 600; margin-top: 20px; }
.hero .hint { margin-top: 34px; align-self: flex-start; font-size: 28px; font-weight: 700;
  color: __LIGHT_ACCENT_DARK__; background: #eff6ff; border: 1.5px solid #bfdbfe;
  border-radius: 999px; padding: 12px 30px; }
.hero.center .hint { align-self: center; }
.hero .grad { width: 200px; height: 7px; border-radius: 4px; margin-top: 28px;
  background: __GRAD_BAR__; }
.hero.center .grad { align-self: center; }
.outline { list-style: none; margin-top: 44px; display: flex; flex-direction: column;
  gap: 18px; }
.outline li { display: flex; align-items: center; gap: 20px; font-size: 36px;
  font-weight: 600; color: __TUTORIAL_INK__;
  background: rgba(255,255,255,0.75); border-radius: 14px; padding: 14px 24px;
  box-shadow: 0 4px 16px rgba(30,41,59,0.06); }
.outline li .num { font-size: 44px; font-weight: 800; font-family: Consolas, monospace;
  background: __GRAD_TEXT__; -webkit-background-clip: text; background-clip: text;
  color: transparent; min-width: 76px; }
.secnum { font-size: 200px; font-weight: 800; line-height: 1;
  font-family: Consolas, "JetBrains Mono", monospace; letter-spacing: 4px;
  background: __GRAD_TEXT__; -webkit-background-clip: text; background-clip: text;
  color: transparent; }
.agenda { display: flex; gap: 14px; margin-top: 44px; flex-wrap: wrap; }
.agenda .a { display: flex; align-items: center; gap: 10px; border-radius: 999px;
  padding: 10px 20px; font-size: 25px; font-weight: 600; white-space: nowrap;
  background: rgba(255,255,255,0.85); border: 1.5px solid #dbe3ee; color: __LIGHT_MUTED__; }
.agenda .a .n { display: inline-flex; align-items: center; justify-content: center;
  width: 30px; height: 30px; border-radius: 50%; font-size: 18px; font-weight: 700;
  background: #eef2f7; color: #64748b; }
.agenda .a.done { color: #15803d; border-color: #bfe4cd; background: #f2fbf5; }
.agenda .a.done .n { background: #dcfce7; color: #15803d; }
.agenda .a.cur { background: __LIGHT_ACCENT__; border-color: __LIGHT_ACCENT__;
  color: #ffffff; box-shadow: 0 8px 24px rgba(37,99,235,0.35); }
.agenda .a.cur .n { background: rgba(255,255,255,0.25); color: #ffffff; }
.recap-rows { display: flex; flex-direction: column; gap: 22px; margin-top: 40px; }
.rrow { display: flex; align-items: center; gap: 22px; border-radius: 16px;
  padding: 22px 30px;
  background: linear-gradient(#ffffff, #ffffff) padding-box,
              linear-gradient(120deg, #dbe4f0, #c7e6f2) border-box;
  border: 1.5px solid transparent; box-shadow: 0 10px 30px rgba(30,41,59,0.08); }
.rrow .tick { flex: none; display: inline-flex; align-items: center; justify-content: center;
  width: 52px; height: 52px; border-radius: 50%; background: #dcfce7;
  color: #15803d; font-size: 28px; font-weight: 800; }
.rrow .rtxt { font-size: 42px; font-weight: 700; color: __LIGHT_INK__; line-height: 1.4; }
.sweep { position: absolute; left: 96px; right: 220px; height: 5px; border-radius: 3px;
  background: __GRAD_BAR__; opacity: 0.5; transform-origin: left center; }
"""


# ---------------------------------------------------------------------------
# 镜头舞台（概述轮播 + shots 七种 + code_mm + annotate + flow）
# ---------------------------------------------------------------------------

def _shots_stage(card: dict, state: dict) -> str:
    """右舞台镜头轮换：开场概述轮播（要点大字）→ shots 按口播句边界轮换，
    新镜头右滑入场 / 旧镜头左滑退场（slideleft 主流向）。"""
    shots = [s for s in (card.get("shots") or [])]
    frame = int(state.get("frame", 10**6))
    shot_idx = int(state.get("shot_idx", -1))
    birth = int(state.get("shot_birth") or 0)
    points = [p for p in (card.get("points") or []) if p]
    ov_frames = min(45 + 30 * len(points), 135) if (points and shots) else 0
    if ov_frames and frame < ov_frames:
        items = []
        per = 30
        for pi, pt in enumerate(points):
            st_f = 24 + per * pi
            age = frame - st_f
            if age < 0 or age >= per + 8:
                continue
            e_in = 1 - (1 - min(1.0, age / 8.0)) ** 3
            op = e_in
            ty = round(22 * (1 - e_in), 1)
            tail = age - per
            if tail > 0:
                e_out = min(1.0, tail / 8.0)
                op = 1 - e_out
                ty = round(-16 * e_out, 1)
            items.append(f'<div class="ovl-item" style="opacity:{op:.3f};'
                         f'transform:translateY({ty}px)"><span class="ovl-n">{pi + 1}</span>'
                         f'{_esc(pt)}</div>')
        head = '<div class="ovl-eyebrow">本步概述</div>' if frame < 24 + per * len(points) else ""
        return (f'<div class="shot"><div class="ovl">{head}{"".join(items)}'
                f'<div class="ovl-bar"></div></div></div>')
    if ov_frames and frame >= ov_frames:
        birth = max(birth, ov_frames)
    layers = []
    for si, sh in enumerate(shots):
        st = _shot_layer_style(frame, si, shot_idx, birth)
        if st is None:
            continue
        layers.append(f'<div class="shot"{_attr(st)}>{_shot_html(sh, card, state)}</div>')
    if not layers:
        # 无 shots：flow 画布或知识卡由 insight 主体另行渲染；此处放占位提示
        return '<div class="shot"><div class="sp-placeholder">讲解中…</div></div>'
    return "".join(layers)


def _code_lines_html(lines: list, hls: list[int], frame: int, birth: int,
                     colorize: bool = False, lang: str = "ts") -> str:
    """code 镜头静态行渲染。colorize=True 时行内 token 上色（code_mm 专用）。"""
    from . import magic_move
    out = []
    for i, ln in enumerate(lines):
        cls = "cl"
        if i in hls:
            cls += " hl"
        st = _row_style(frame, birth, i)
        st_attr = st[len(' style="'):-1] if st.startswith(' style="') else ""
        if colorize:
            toks = "".join(
                f'<span class="tok{(" " + c) if c else ""}">{_esc(t)}</span>'
                for t, c in magic_move.tokenize_line(str(ln), lang))
            body = f'<span class="code-toks">{toks}</span>'
        else:
            body = f'<span>{_esc(ln)}</span>'
        out.append(f'<div class="{cls}"{_attr(st_attr)}><span class="ln">{i + 1}</span>'
                   f'{body}</div>')
    return "".join(out)


def _annotate_span(html: str, svg: str) -> str:
    return f'<span class="anno-wrap">{html}{_annotate_svg(svg)}</span>'


def _shot_html(shot: dict, card: dict, state: dict) -> str:
    """单个镜头 → 亮色舞台 HTML（代码/终端/flow 深窗，stat/table/quote 白卡）。"""
    kind = shot.get("kind", "code")
    data = shot.get("data") or {}
    frame = int(state.get("frame", 10**6))
    birth = int(state.get("shot_birth") or 0)
    if kind == "flow":
        from . import flowchart
        return (f'<div class="flowcanvas">'
                f'{flowchart.render_flow(card.get("flow") or {}, state)}</div>')
    if kind == "stat":
        big = _esc(data.get("big", ""))
        ann = data.get("annotate")
        if ann:
            from . import rough_note
            if isinstance(ann, dict):
                ann_style = str(ann.get("style", "circle"))
                ann_color = str(ann.get("color", "cyan"))
                ann_at = float(ann.get("at_s", 0.0))
            else:
                ann_style, ann_color, ann_at = str(ann), "cyan", 0.0
            svg = rough_note.note_svg_drawn(
                ann_style, f"{data.get('title') or data.get('big', '')}:stat",
                ann_color, frame, birth, at_s=ann_at)
            if svg:
                big = _annotate_span(big, svg)
        big = apply_anim(big, data.get("anim") or card.get("anim"), frame)
        return (f'<div class="shot-stat"><div class="big">{big}</div>'
                f'<div class="label">{_esc(data.get("label", ""))}</div>'
                f'<div class="sub">{_esc(data.get("sub", ""))}</div></div>')
    if kind == "table":
        head = "".join(f"<th>{_esc(h)}</th>" for h in data.get("head", []))
        rows = ""
        for r in data.get("rows", []):
            cls = ' class="hlrow"' if r and r[0] == "*" else ""
            cells = r[1:] if r and r[0] == "*" else r
            rows += f'<tr{cls}>' + "".join(f"<td>{_esc(c)}</td>" for c in cells) + "</tr>"
        return f'<div class="shot-table"><table><tr>{head}</tr>{rows}</table></div>'
    if kind == "quote":
        return ('<div class="shot-quote"><div class="mark">\u201c</div>'
                f'<div class="qtext">{_esc(data.get("text", ""))}</div>'
                f'<div class="qsrc">— {_esc(data.get("source", ""))}</div></div>')
    # 带窗口 chrome 的素材（code / code_mm / tree / term）
    fname = _esc(data.get("title", ""))
    tag = _esc({"code": "源码", "code_mm": "源码", "tree": "结构",
                "term": "终端"}.get(kind, kind))
    body = _shot_body_html(kind, data, shot, state)
    return (f'<div class="win"><div class="win-bar">'
            '<div class="win-dot" style="background:#fb7185"></div>'
            '<div class="win-dot" style="background:#fbbf24"></div>'
            '<div class="win-dot" style="background:#34d399"></div>'
            f'<div class="win-name">{fname}</div><div class="win-tag">{tag}</div></div>'
            f'<div class="win-body">{body}</div></div>')


def _shot_body_html(kind: str, data: dict, shot: dict, state: dict) -> str:
    frame = int(state.get("frame", 10**6))
    birth = int(state.get("shot_birth") or 0)
    if kind == "code":
        return _code_lines_html(data.get("lines", []),
                                _hl_lines(shot, state), frame, birth)
    if kind == "code_mm":
        from . import magic_move
        lang = str(data.get("lang") or "ts")
        return magic_move.render_shot(
            data, state, birth,
            lambda lines, hls, fr, b: _code_lines_html(lines, hls, fr, b,
                                                       colorize=True, lang=lang))
    if kind == "tree":
        out = []
        for i, item in enumerate(data.get("items", [])):
            depth, typ, name = 0, "file", item
            if isinstance(item, list):
                typ, name = item[0], item[1]
                depth = item[2] if len(item) > 2 else 0
            elif isinstance(item, str) and item.startswith("**"):
                typ = "note"
                name = item.strip("* ")
            st_attr = _row_style(frame, birth, i)
            inner = st_attr[len(' style="'):-1] if st_attr.startswith(' style="') else ""
            if typ == "note":
                out.append(f'<div class="tl"{_attr(inner)}>'
                           f'<span class="dim">{_esc(name)}</span></div>')
            else:
                glyph, cls = ("\u25b8 ", "dir") if typ == "dir" else ("\u25aa ", "")
                marked = (f'<span class="{cls}">{_esc(glyph + name)}</span>'
                          if cls else _esc(glyph + name))
                out.append(f'<div class="tl"{_attr(inner)}>'
                           f'{"&nbsp;" * (4 * depth)}{marked}</div>')
        return "".join(out)
    if kind == "term":
        out = []
        lines = data.get("lines", [])
        for i, item in enumerate(lines):
            if isinstance(item, str):
                text, cls = item, "out"
            else:
                text, cls = item.get("t", ""), item.get("c", "out")
            st_attr = _row_style(frame, birth, i)
            inner = st_attr[len(' style="'):-1] if st_attr.startswith(' style="') else ""
            cursor = ('<span style="color:#60a5fa">\u2588</span>'
                      if i == len(lines) - 1 and cls in ("cmd", "out") else "")
            out.append(f'<div class="tline {cls}"{_attr(inner)}>{_esc(text)}{cursor}</div>')
        return "".join(out)
    return ""


# ---------------------------------------------------------------------------
# 卡型渲染
# ---------------------------------------------------------------------------

def _top_block(card: dict, state: dict) -> tuple[str, str, str]:
    """眉题 + 断言标题 + 渐变标题条（insight 卡顶栏）。"""
    frame = int(state.get("frame", 10**6))
    out_at = state.get("out_at")
    births = [int(b) for b in (state.get("point_births") or [])]
    active_idx = int(state.get("active_idx", -1))
    card_sub = card.get("subtitle", "") or ""
    st = _style(*_compose(enter_tuple(frame - _ENT_EYEBROW, 6, dy=-16.0),
                          _exit(frame, out_at, "eyebrow", dy=-18.0)))
    eyebrow = (f'<div class="eyebrow"{_attr(st)}>{_esc(card_sub)}</div>'
               if card_sub else "")
    title = card.get("title", "") or ""
    title = apply_anim(_esc(title), card.get("anim"), frame)
    t_st = _style(*_compose(enter_tuple(frame - _ENT_TITLE, 8, dy=24.0),
                            _exit(frame, out_at, "title")))
    bar = (f'<div class="title-bar"{_attr(_bar_style(frame, births, active_idx, out_at))}>'
           f'</div>')
    return eyebrow, f'<div class="h1"{_attr(t_st)}>{title}</div>', bar


def _steps_bar(card: dict, state: dict) -> str:
    """步骤条（deck 提供 steps/step_idx 时）：done ✓ / active 蓝填充 / future 灰。"""
    steps = card.get("steps") or []
    if not steps:
        return ""
    frame = int(state.get("frame", 10**6))
    step_idx = int(card.get("step_idx", -1))
    breathe = 1 + 0.025 * math.sin((frame // _BREATHE_Q) / 2.2)
    pills = []
    for i, s in enumerate(steps):
        short = s if len(s) <= 14 else s[:13] + "…"
        if i < step_idx:
            cls, num = "done", "✓"
        elif i == step_idx:
            cls, num = "active", str(i + 1)
        else:
            cls, num = "", str(i + 1)
        st = _style(*enter_tuple(frame - (6 + 2 * i), 7, scale_from=0.90,
                                 ease=ease_out_back))
        if cls == "active":
            st = (f"{st};transform:scale({breathe:.3f})".lstrip(";")
                  if st else f"transform:scale({breathe:.3f})")
        pills.append(f'<div class="spill {cls}"{_attr(st)}>'
                     f'<span class="n">{num}</span>{_esc(short)}</div>')
    return f'<div class="steps">{"".join(pills)}</div>'


def _insight(card: dict, state: dict, width: int, height: int) -> str:
    """断言标题卡（默认）：左要点三态 + 右舞台（shots/flow/知识卡）。"""
    frame = int(state.get("frame", 10**6))
    active_idx = int(state.get("active_idx", -1))
    births = [int(b) for b in (state.get("point_births") or [])]
    out_at = state.get("out_at")
    points_raw = card.get("points") or []
    sub_points = card.get("sub_points") or []
    ann_cfg = card.get("annotate") or {}

    eyebrow, title_html, bar = _top_block(card, state)
    steps = _steps_bar(card, state)

    point_items = []
    for idx, pt in enumerate(points_raw):
        if idx < active_idx:
            cls = "pt done"
        elif idx == active_idx:
            cls = "pt active"
        else:
            cls = "pt"
        st = _point_style(frame, idx, active_idx, births, out_at)
        inner = apply_anim(_esc(pt), card.get("anim"), frame)
        if ann_cfg.get("point") == idx and ann_cfg.get("style"):
            from . import rough_note
            pb = (births[idx] if idx < len(births) else 0) + 4
            svg = rough_note.note_svg_drawn(
                str(ann_cfg["style"]), f"{card.get('title', '')}:pt{idx}",
                str(ann_cfg.get("color") or "cyan"),
                frame, pb, stroke_w=4,
                at_s=float(ann_cfg.get("at_s", 0.0)))
            if svg:
                inner = _annotate_span(inner, svg)
        point_items.append(f'<div class="{cls}"{_attr(st)}>'
                           f'<span class="ic">{idx + 1}</span><span>{inner}</span></div>')
    pts_block = (f'<div class="pts">{"".join(point_items)}</div>'
                 if point_items else "")

    shots = card.get("shots") or []
    if shots:
        stage = f'<div class="stagewrap">{_shots_stage(card, state)}</div>'
    elif card.get("flow"):
        stage = (f'<div class="stagewrap"><div class="shot">'
                 f'<div class="flowcanvas">'
                 f'{_require_flowchart()(card.get("flow") or {}, state)}'
                 f'</div></div></div>')
    elif sub_points:
        sp_items = []
        for idx, sp in enumerate(sub_points):
            if idx > active_idx:
                continue
            st = _sp_style(frame, idx, active_idx, births, out_at)
            if idx == active_idx:
                sp_items.append(f'<div class="sp-item active"{_attr(st)}>'
                                f'<div class="sp-text">{apply_anim(_esc(sp), card.get("anim"), frame)}</div></div>')
            else:
                sp_items.append(f'<div class="sp-item done"{_attr(st)}>'
                                f'{apply_anim(_esc(sp), card.get("anim"), frame)}</div>')
        stage = (f'<div class="stagewrap">{"".join(sp_items)}</div>'
                 if sp_items else '<div class="stagewrap"><div class="sp-placeholder">讲解中…</div></div>')
    else:
        stage = '<div class="stagewrap"><div class="sp-placeholder">讲解中…</div></div>'

    footer = card.get("footer", "") or ""
    f_st = _style(*_compose(enter_tuple(frame - _ENT_FOOTER, 6, dy=10.0),
                            _exit(frame, out_at, "footer", dy=-14.0)))
    footer_block = (f'<div class="footer-bar"{_attr(f_st)}>{_esc(footer)}</div>'
                    if footer else "")

    body = f"""<div class="wrap">
  {eyebrow}
  {title_html}
  {bar}
  {steps}
  <div class="main">{pts_block}{stage}</div>
  {footer_block}
</div>"""
    return _doc(body, state, width, height)


def _require_flowchart():
    from . import flowchart
    return flowchart


def _cover(card: dict, state: dict, width: int, height: int) -> str:
    """封面 / CTA：大标题 + 渐变条 + 论点列表（outline）或 hint 胶囊。"""
    frame = int(state.get("frame", 10**6))
    out_at = state.get("out_at")
    outline = card.get("outline") or []
    is_cta = bool(card.get("cta"))
    title = card.get("title", "") or ""
    title = apply_anim(_esc(title), card.get("anim"), frame)
    sub = card.get("subtitle", "") or ""

    t_st = _style(*_compose(enter_tuple(frame - _ENT_TITLE, 9, dy=30.0, scale_from=0.97),
                            _exit(frame, out_at, "title")))
    g_st = _style(*_compose(enter_tuple(frame - _ENT_BAR, 12, dy=0.0, scale_from=0.4),
                            _exit(frame, out_at, "bar")))
    grad = f'<div class="grad"{_attr(g_st)}></div>'
    hook = ""
    if sub and not is_cta:
        h_st = _style(*_compose(enter_tuple(frame - _ENT_EYEBROW, 6, dy=-16.0),
                                _exit(frame, out_at, "eyebrow", dy=-18.0)))
        hook = f'<div class="hook"{_attr(h_st)}>{_esc(sub)}</div>'
    if is_cta:
        body_inner = (f'<div class="big"{_attr(t_st)}>{title}</div>{grad}'
                      f'<div class="sub">{_esc(sub)}</div>')
        hint = card.get("footer", "") or ""
        if hint:
            h_st = _style(*_compose(enter_tuple(frame - _ENT_POINT0, 8, dy=18.0),
                                    _exit(frame, out_at, "point")))
            body_inner += f'<div class="hint"{_attr(h_st)}>{_esc(hint)}</div>'
        center = " center"
    else:
        body_inner = f'{hook}<div class="big"{_attr(t_st)}>{title}</div>{grad}'
        center = ""
    ol = ""
    for i, o in enumerate(outline):
        st = _style(*_compose(
            enter_tuple(frame - int(10 + 2.5 * i), 9, dy=26.0,
                        scale_from=0.96, ease=ease_out_back),
            _exit(frame, out_at, "outline", extra_shift=i, dy=-22.0)))
        ol += f'<li{_attr(st)}><span class="num">{i + 1:02d}</span>{_esc(o)}</li>'
    outline_block = f'<ul class="outline">{ol}</ul>' if ol else ""
    body = f'<div class="hero{center}">{body_inner}{outline_block}</div>'
    return _doc(body, state, width, height)


def _section(card: dict, state: dict, width: int, height: int) -> str:
    """章节隔页：大号章节数字（stamp 拍落）+ 断言章标题 + mini-agenda 导航 +
    渐变扫带。deck 字段：section_no（1 起）、sections（章节名列表）。"""
    frame = int(state.get("frame", 10**6))
    out_at = state.get("out_at")
    no = int(card.get("section_no", 0) or 0)
    sections = card.get("sections") or []
    eyebrow = card.get("subtitle", "") or "章节"
    title = card.get("title", "") or ""

    num_age = frame - 4
    op, sc, rot = stamp_tuple(num_age, 13, scale_from=1.25, rotate=2.0)
    ex_num = _exit(frame, out_at, "num", dy=-20.0)
    if ex_num is not None:
        op *= ex_num[0]
    settled = op >= 0.999 and abs(sc - 1.0) < 0.0015 and abs(rot) <= 0.05 and ex_num is None
    num_st = ("" if settled else
              f"opacity:{max(0.0, op):.3f};transform:scale({sc:.3f}) rotate({rot:.2f}deg)")
    t_st = _style(*_compose(enter_tuple(frame - 10, 9, dy=24.0),
                            _exit(frame, out_at, "title")))
    eb_st = _style(*_compose(enter_tuple(frame - _ENT_EYEBROW, 6, dy=-14.0),
                             _exit(frame, out_at, "eyebrow", dy=-16.0)))
    # 渐变扫带：scaleX 0→1 生长（18 帧），再整体淡出（卡尾）
    sweep_age = frame - 6
    sweep_sc = ease_out_cubic(min(1.0, max(0.0, sweep_age / 18.0)))
    sweep_st = f"transform:scaleX({sweep_sc:.3f})"
    ex = _exit(frame, out_at, "bar", dy=0.0)
    if ex is not None:
        sweep_st += f";opacity:{ex[0]:.3f}"

    ag = ""
    for i, s in enumerate(sections):
        idx = i + 1
        if idx < no:
            cls, n = "done", "✓"
        elif idx == no:
            cls, n = "cur", str(idx)
        else:
            cls, n = "", str(idx)
        st = _style(*_compose(enter_tuple(frame - (14 + 2 * i), 7, dy=14.0),
                              _exit(frame, out_at, "point", extra_shift=i)))
        ag += (f'<div class="a {cls}"{_attr(st)}><span class="n">{n}</span>'
               f'{_esc(s)}</div>')
    agenda = f'<div class="agenda">{ag}</div>' if ag else ""
    body = f"""<div class="hero">
  <div class="hook"{_attr(eb_st)}>{_esc(eyebrow)}</div>
  <div class="secnum"{_attr(num_st)}>{no:02d}</div>
  <div class="big"{_attr(t_st)}>{_esc(title)}</div>
  <div class="grad"{_attr(_style(*enter_tuple(frame - _ENT_BAR, 12, scale_from=0.4)))}></div>
  {agenda}
</div>
<div class="sweep" style="top:76%;{sweep_st}"></div>"""
    return _doc(body, state, width, height)


def _recap(card: dict, state: dict, width: int, height: int) -> str:
    """章末回顾：≤3 条 takeaway 逐条 stamp 拍落 + ✓ 绿章 + 渐变左条。"""
    frame = int(state.get("frame", 10**6))
    out_at = state.get("out_at")
    eyebrow, title_html, bar = _top_block(card, state)
    rows = []
    points = (card.get("points") or [])[:3]
    for i, pt in enumerate(points):
        op, sc, rot = stamp_tuple(frame - (8 + 4 * i), 12, scale_from=1.12, rotate=1.2)
        op, sc = _compose((op, sc, 1.0), _exit(frame, out_at, "row", extra_shift=i, dy=-20.0))[:2]
        st = (f"opacity:{op:.3f};transform:translateY(0) scale({sc:.3f}) rotate({rot:.2f}deg)"
              if op < 0.999 or abs(sc - 1.0) > 0.0015 else "")
        rows.append(f'<div class="rrow"{_attr(st)}><span class="tick">✓</span>'
                    f'<span class="rtxt">{apply_anim(_esc(pt), card.get("anim"), frame)}</span></div>')
    footer = card.get("footer", "") or ""
    body = f"""<div class="wrap">
  {eyebrow}
  {title_html}
  {bar}
  <div class="recap-rows">{"".join(rows)}</div>
  {f'<div class="footer-bar">{_esc(footer)}</div>' if footer else ""}
</div>"""
    return _doc(body, state, width, height)


def render_frame(card: dict, state: dict, width: int = 1920,
                 height: int = 1080) -> str:
    """渲染一帧 prism 白色科技感 HTML（默认渲染路径）。"""
    ctype = card.get("type")
    if card.get("is_cover"):
        return _cover(card, state, width, height)
    if ctype == "section":
        return _section(card, state, width, height)
    if ctype == "recap":
        return _recap(card, state, width, height)
    return _insight(card, state, width, height)


def _doc(body: str, state: dict, width: int, height: int) -> str:
    """页面骨架：极光斑（帧驱动漂移）+ 网格 + 顶部冷光条 + mascot 外壳。"""
    frame = int(state.get("frame", 10**6))
    dx1, dy1, dx2, dy2 = _aurora(frame)
    css = (_CSS.replace("__W__", str(width)).replace("__H__", str(height))
           .replace("__LIGHT_BG__", LIGHT_BG)
           .replace("__TUTORIAL_INK__", TUTORIAL_INK)
           .replace("__LIGHT_INK__", LIGHT_INK)
           .replace("__LIGHT_MUTED__", LIGHT_MUTED)
           .replace("__LIGHT_DONE__", LIGHT_DONE)
           .replace("__LIGHT_ACCENT__", LIGHT_ACCENT)
           .replace("__LIGHT_ACCENT_DARK__", LIGHT_ACCENT_DARK)
           .replace("__GRAD_TEXT__", _GRAD_TEXT)
           .replace("__GRAD_BAR__", _GRAD_BAR))
    mascot = ""
    if getattr(state, "get", None) is not None:
        from .courseware import _mascot_html
        mascot = _mascot_html(state)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>prism frame</title>
<style>
{css}
</style>
</head>
<body>
<div class="aurora a1" style="transform:translate({dx1:.1f}px,{dy1:.1f}px)"></div>
<div class="aurora a2" style="transform:translate({dx2:.1f}px,{dy2:.1f}px)"></div>
<div class="grid"></div>
<div class="toplight"></div>
{mascot}
{body}
</body>
</html>"""


if __name__ == "__main__":
    # 冒烟预览：渲两张样例帧（cover / insight shots / section / recap）到 build/
    import json
    from pathlib import Path
    from playwright.sync_api import sync_playwright

    from . import config as _C
    out_dir = _C.build_dir("prism-preview")
    out_dir.mkdir(parents=True, exist_ok=True)
    cases = [
        ("cover", {"title": "一条被删掉的深色管线，和它留下的动效", "subtitle": "PRISM · 白色科技感管线",
                   "points": [], "is_cover": True,
                   "outline": ["全元素动画", "章节导航", "token 形变", "手绘注记"]},
         {"active_idx": -1, "subtitle": "问你一个问题 白色管线长什么样", "progress": 0.04, "frame": 40}),
        ("insight", {"title": "代码改动，token 替你讲", "subtitle": "升级一",
                     "points": ["旧代码先出场站稳", "保留部分滑动归位", "新增分支淡入登场"],
                     "shots": [{"from_s": 0.1, "kind": "code_mm",
                                "data": {"title": "fetchUser.ts", "lang": "ts", "mm_at": 4.5,
                                         "hl_before": 1, "hl_after": 4,
                                         "before": ["async function fetchUser(id) {",
                                                    "  const res = await fetch(`/api/users/${id}`);",
                                                    "  return res.json();", "}"],
                                         "after": ["async function fetchUser(id) {",
                                                   "  const res = await fetch(`/api/users/${id}`, {",
                                                   "    signal: AbortSignal.timeout(3000),", "  });",
                                                   "  if (!res.ok) throw new Error(`HTTP ${res.status}`);",
                                                   "  return res.json();", "}"]}}],
                     "footer": "token 形变 · magic-move"},
         {"active_idx": 1, "subtitle": "改了哪里 一眼看到", "progress": 0.35, "frame": 200,
          "point_births": [30, 150, 190], "shot_idx": 0, "shot_birth": 160,
          "shot_t_ms": 6000, "out_at": 10**6}),
        ("section", {"type": "section", "title": "钱到底省在哪", "subtitle": "第二章",
                     "section_no": 2, "sections": ["能力盘点", "价格结构", "决策纪律"],
                     "points": [], "is_cover": False},
         {"active_idx": -1, "subtitle": "第二个问题 输出价是输入五倍", "progress": 0.5, "frame": 90}),
        ("recap", {"type": "recap", "title": "本章三个可带走结论", "subtitle": "回顾",
                   "points": ["重活配它 零碎活别给", "前缀摆稳吃缓存", "只要结论 控制输出"],
                   "footer": "决策表已进置顶评论", "is_cover": False},
         {"active_idx": 2, "subtitle": "三条纪律 逐条验收", "progress": 0.9, "frame": 120,
          "point_births": [40, 80, 110], "out_at": 10**6}),
    ]
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1920, "height": 1080})
        for name, c, st in cases:
            pg.set_content(render_frame(c, st))
            pg.wait_for_timeout(120)
            shot = out_dir / f"prism_{name}.png"
            pg.screenshot(path=str(shot))
            print(f"[{name}] {shot} {shot.stat().st_size} bytes")
        b.close()
    print("DONE")
