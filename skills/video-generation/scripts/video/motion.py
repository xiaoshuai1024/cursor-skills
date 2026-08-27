"""帧驱动动画工具库（motion）。

两条管线共用的确定性动画数学：
- Playwright 管线禁 CSS animation（逐帧截图下不可靠），一切动画按
  state["frame"] 用纯函数算数值 → 注入 inline style。
- 借鉴 HyperFrames 的确定性手法：预烘焙帧表（count-up）、显式初态、
  IN → HOLD 信封。同输入同输出，动画窗口结束后画面静止（保住
  frames.py 的 PNG 复用优化）。

用法（在渲染入口）:
    from .motion import count_up_table, typewriter_table, ease_out_cubic
    frame = int(state.get("frame", 0))
    # count-up: 帧表预烘焙, 取表即可, 窗口外静止
    if start <= frame < start + len(table):
        text = table[frame - start]
"""

from __future__ import annotations

import math
import re

__all__ = [
    "ease_out_cubic", "ease_out_back", "ease_in_out_sine", "ease_in_cubic",
    "ease_out_expo", "ease_out_quart", "ease_in_quart",
    "count_up_table", "typewriter_table", "shimmer_pos", "breathe",
    "apply_anim",
    "enter_tuple", "exit_tuple", "settle_dip", "glow_mult", "type_chars",
    "swap_pair", "grow_scale", "stamp_tuple", "sting_tuple",
]


def ease_out_cubic(t: float) -> float:
    """easeOutCubic: 1-(1-t)^3。"""
    return 1 - (1 - t) ** 3


def ease_in_cubic(t: float) -> float:
    """easeInCubic: t^3（加速曲线，出场专用——M3：退场快于入场且用 accelerate）。"""
    return t ** 3


def ease_out_back(t: float, s: float = 1.70158) -> float:
    """easeOutBack: 弹性回弹（对齐 HyperFrames back.out）。"""
    c3 = s + 1
    return 1 + c3 * (t - 1) ** 3 + s * (t - 1) ** 2


def ease_in_out_sine(t: float) -> float:
    """easeInOutSine: -(cos(πt)-1)/2。"""
    return -(math.cos(math.pi * t) - 1) / 2


def ease_out_expo(t: float) -> float:
    """easeOutExpo: 1-2^(-10t)（HyperFrames expo.out）。

    大落差快速落定：logo/签名句落版、印章拍落、结论卡砸入——
    前段速后段骤停，比 cubic 更「拍上去」。
    """
    return 1.0 if t >= 1.0 else 1 - 2 ** (-10 * t)


def ease_out_quart(t: float) -> float:
    """easeOutQuart: 1-(1-t)^4（HyperFrames power4.out）。换词入场：猛进缓收。"""
    return 1 - (1 - t) ** 4


def ease_in_quart(t: float) -> float:
    """easeInQuart: t^4（HyperFrames power4.in）。换词出场：蓄力后整段甩出。"""
    return t ** 4


def count_up_table(end: float, frames: int, start: float = 0.0,
                   decimals: int = 0, thousands: bool = True) -> list[str]:
    """预烘焙 count-up 帧表：每帧的显示文本（sine.inOut 缓动）。

    与 Remotion CountUp 同源算法：滚动窗口外首/尾值静止，
    帧表长度 = frames + 1（含终值帧）。
    """
    table: list[str] = []
    for i in range(frames + 1):
        t = ease_in_out_sine(i / frames) if frames else 1.0
        v = start + (end - start) * t
        if decimals > 0:
            table.append(f"{v:.{decimals}f}")
        elif thousands:
            table.append(f"{v:,.0f}")
        else:
            table.append(f"{v:.0f}")
    return table


def typewriter_table(text: str, frames: int) -> list[str]:
    """预烘焙打字机帧表：每帧显示前 N 个字符（含标点按字符走）。"""
    table = [text[: max(1, round(i / frames * len(text)))] for i in range(1, frames + 1)]
    # 保证末帧 = 完整文本
    table[-1] = text
    return table


def shimmer_pos(frame: int, start: int, duration: int,
                repeat: bool = False) -> float:
    """流光位置百分比：-20 → 120（repeat 时取模循环）。"""
    rel = max(0, frame - start)
    p = (rel % duration) / duration if repeat else min(1, rel / duration)
    return -20 + p * 140


def breathe(frame: int, base: float = 1.0, amp: float = 0.03,
            period: float = 10.0) -> float:
    """呼吸缩放：base + amp * sin(2π * frame / period)。"""
    return base + amp * math.sin(2 * math.pi * frame / period)


# ── 编舞助手（courseware 全元素动画联动，openspec courseware-motion-linkage）──
# 约定：动画一律有界窗口；age >= dur 返回「终态」（opacity 1 / 无位移），
# 渲染层据此不输出 inline style → HTML 与后续帧一致，PNG 复用优化保持。


def enter_tuple(age: int, dur: int, *, dy: float = 0.0, scale_from: float = 1.0,
                ease=None) -> tuple[float, float, float]:
    """入场运动量 → (opacity, translateY, scale)。

    age = 当前帧 - 出生帧。age<0 未出生（隐藏在出生位）；窗口内插值；
    窗口外 → (1, 0, 1) 终态。ease 传 ease_out_back 时 scale 会轻微过冲
    （overshoot，弹性弹出），opacity 始终 clamp 到 [0,1]。
    """
    if age < 0:
        return 0.0, dy, scale_from
    if age >= dur:
        return 1.0, 0.0, 1.0
    t = (ease or ease_out_cubic)(age / dur)
    op = max(0.0, min(1.0, t))
    ty = dy * (1.0 - t)
    sc = scale_from + (1.0 - scale_from) * t
    return op, ty, sc


def exit_tuple(age: int, dur: int = 5, *, dy: float = -26.0,
               scale_to: float = 1.0, ease=None) -> tuple[float, float, float] | None:
    """出场运动量 → (opacity, translateY, scale) | None。

    age = 当前帧 - 出场帧；age<0 → None（未进出场窗，元素保持原样）。
    窗口内 ease-in 加速淡出上移；窗口外 → (0, dy, scale_to) 完全出场
    （HTML 稳定为 opacity:0，段尾几帧保持相等性）。默认 5 帧 ≈ 210ms，
    对齐 M3「退场 150-250ms 且快于入场」。
    """
    if age < 0:
        return None
    if age >= dur:
        return 0.0, dy, scale_to
    t = (ease or ease_in_cubic)(age / dur)
    return 1.0 - t, dy * t, 1.0 + (scale_to - 1.0) * t


def settle_dip(age: int, dur: int = 5, *, depth: float = 0.15) -> float | None:
    """换态交叉过渡的透明度凹陷：1 → 1-depth → 1（sin 半周期）。

    用于「active → done 类切换」的感知平滑：类样式瞬间切换时，元素先轻微
    变淡再回来，观众感知为一次过渡而非跳变。窗口外返回 None（无内联样式）。
    """
    if age < 0 or age >= dur:
        return None
    return 1.0 - depth * math.sin(math.pi * age / dur)


def glow_mult(age: int, dur: int = 6, peak: float = 0.8) -> float | None:
    """辉光脉冲增量：peak → 0（ease-out 衰减）。窗口外 None。

    联动反馈专用：主锚（要点亮起帧）后 0~dur 帧内，关联元素（标题条/
    进度条/边框）的 box-shadow 强度乘 (1 + 增量)。
    """
    if age < 0 or age >= dur:
        return None
    return peak * (1.0 - ease_out_cubic(age / dur))


def type_chars(text: str, age: int, dur: int = 12) -> str:
    """逐字浮现当前可见前缀（线性 reveal，窗口外全文）。"""
    if age < 0:
        return ""
    if age >= dur:
        return text
    n = max(1, round(len(text) * age / dur))
    return text[:min(len(text), n)]


# ── 换态强调类配方（2026-08-26，源 HyperFrames catalog，见 references/motion-patterns.md）──
# 入场/出场之外的第三类动词：槽内换词、划线/标记带生长、印章拍落、落版白闪。
# 约定与编舞助手一致：age = 当前帧 - 出生帧，有界窗口，窗口外 None/终态。


def swap_pair(age: int, dur: int = 10) -> tuple[float, float, float, float] | None:
    """槽内换词（HyperFrames kinetic-type-swap）→
    (旧词位移%, 旧词opacity, 新词位移%, 新词opacity) | None。

    旧词 ease_in_quart 整体上甩（-112%＝自身高度甩出槽外），到 60% 拍点后
    新词 ease_out_quart 从下方顶入，前后只重叠极短窗口（视觉上「替换」而非
    「先后」）。age<0 → None（旧词原样静止）；age≥dur → 旧词 0、新词就位。
    适用：口播讲「A 变成 B」的身份/状态演变（前端→全栈→AI、手动→自动）。
    渲染层把位移写进 translateY(%)，两词同槽绝对定位叠放。
    """
    if age < 0:
        return None
    cut = max(1, round(dur * 0.6))
    if age >= dur:
        return -112.0, 0.0, 0.0, 1.0
    if age < cut:
        t = ease_in_quart(age / cut)
        return -112.0 * t, 1.0 - t, 112.0, 0.0
    t = ease_out_quart((age - cut) / max(1, dur - cut))
    return -112.0, 0.0, 112.0 * (1.0 - t), t


def grow_scale(age: int, dur: int = 8, ease=None) -> float:
    """线/带生长进度 → scaleX / background-size 百分比（0→1）。

    一函数两用（HyperFrames caption-highlight / strike 系）：
    - 删除线/下划线：transform: scaleX(p)，transform-origin: left center
    - 标记带高亮：background-size: p*100% 100%（渐变只在字后生长，
      跨行配 box-decoration-break: clone）
    age<0 → 0（藏住）；age≥dur → 1（终态静止）。默认 sine.inOut——
    生长类要两端缓，别用 back（会倒缩出负长度）。
    """
    if age < 0:
        return 0.0
    if age >= dur:
        return 1.0
    return (ease or ease_in_out_sine)(age / dur)


def stamp_tuple(age: int, dur: int = 13, *, scale_from: float = 1.25,
                rotate: float = 2.0) -> tuple[float, float, float]:
    """印章/结论卡拍落（expo.out）→ (opacity, scale, rotate_deg)。

    HyperFrames stamp/logo-sting 系的「官方盖章」感：从 1.25 缩到 1 落定、
    带轻微旋转（rotate≤3°，过了像事故），expo.out 前段速后段骤停。
    age<0 → (0, scale_from, rotate)；窗口外 → (1, 1, 0) 终态。
    适用：结论卡、验证戳、口号定帧——讲完一段话的「锤一下」节拍。
    """
    if age < 0:
        return 0.0, scale_from, rotate
    if age >= dur:
        return 1.0, 1.0, 0.0
    t = ease_out_expo(age / dur)
    return (max(0.0, min(1.0, t * 1.6)),            # opacity 提前到位
            scale_from + (1.0 - scale_from) * t,
            rotate * (1.0 - t))


def sting_tuple(age: int, land_dur: int = 16, flash_at: int = 8,
                ring_dur: int = 22) -> tuple[float, bool, float, float] | None:
    """品牌/签名句落版（HyperFrames logo-sting）→
    (scale, flash_on, ring_scale, ring_opacity) | None。

    三拍一体的收尾定帧：字标 scale 1.15→1（expo.out 落定）→ flash_at 帧处
    **单帧白闪**（flash_on 仅 1 帧为 True——多帧就廉价了）→ 辉光环
    scale 0.34→2.4 扩散同时淡出（ease-out）。age<0 → None；落定后窗口外
    → (1, False, 2.4, 0) 全终态。ring 用 accent 色描边圆环居中于字标。
    """
    if age < 0:
        return None
    land = 1.0 if age >= land_dur else 1.15 - 0.15 * ease_out_expo(age / max(1, land_dur))
    flash = age == flash_at
    if age < flash_at:
        ring_s, ring_o = 0.34, 0.0
    else:
        rt = min(1.0, (age - flash_at) / max(1, ring_dur))
        ring_s = 0.34 + 2.06 * ease_out_cubic(rt)
        ring_o = 0.9 * (1.0 - rt)
    return land, flash, ring_s, ring_o


# ── deck anim 字段（占位符替换协议）─────────────────────────────
# deck 卡内容里写占位符，渲染入口按帧替换为当前值：
#   @@countup:9603@@        数字滚动（终值 9603，anim 参数控制窗口）
#   @@countup:9603:1@@      同上但 1 位小数（9603.0）
#   @@typewriter:文本@@     打字机逐字 reveal
#   @@shimmer:文本@@        流光渐变文字（background-clip:text）
# anim 字段（可选）控制动画参数：
#   {"type": "countup", "start_frame": 10, "frames": 12}
# 占位符替换规则：动画窗口外显示终值（静止 → PNG 复用优化保住）。

_RE_COUNTUP = re.compile(r"@@countup:([0-9.]+)(?::(\d))?@@")
_RE_TYPEWRITER = re.compile(r"@@typewriter:([^@]+)@@")
_RE_SHIMMER = re.compile(r"@@shimmer:([^@]+)@@")

_SHADES = ("#e2e8f0", "#ffffff", "#94a3b8")  # 流光渐变（浅色系，深浅主题通用）


def apply_anim(html: str, anim: dict | None, frame: int) -> str:
    """按 anim 字段把占位符替换为当前帧值。

    anim 形如 {"type": "countup", "start_frame": 10, "frames": 12}；
    缺省 start_frame=0、frames=12。动画窗口外一律显示终值（静止）。
    """
    if not anim:
        # 无 anim 字段时仍替换为终值（占位符不能裸出）
        html = _RE_COUNTUP.sub(lambda m: _fmt_num(m.group(1), m.group(2)), html)
        html = _RE_TYPEWRITER.sub(lambda m: m.group(1), html)
        html = _RE_SHIMMER.sub(lambda m: _shimmer_span(m.group(1), 120.0), html)
        return html

    start = int(anim.get("start_frame", 0))
    n_frames = int(anim.get("frames", 12))
    rel = frame - start

    if anim.get("type") == "countup":
        html = _finalize_others(html, _RE_COUNTUP)   # 其余占位符 → 终值，不裸出
        def _count(m: re.Match) -> str:
            end = float(m.group(1))
            dec = int(m.group(2)) if m.group(2) else 0
            if 0 <= rel <= n_frames:
                table = count_up_table(end, n_frames, decimals=dec)
                return table[rel] if rel < len(table) else _fmt_num(m.group(1), m.group(2))
            return _fmt_num(m.group(1), m.group(2))
        return _RE_COUNTUP.sub(_count, html)

    if anim.get("type") == "typewriter":
        html = _finalize_others(html, _RE_TYPEWRITER)
        def _type(m: re.Match) -> str:
            text = m.group(1)
            if 0 < rel <= n_frames:
                return typewriter_table(text, n_frames)[rel - 1]
            return text
        return _RE_TYPEWRITER.sub(_type, html)

    if anim.get("type") == "shimmer":
        html = _finalize_others(html, _RE_SHIMMER)
        def _shimmer(m: re.Match) -> str:
            pos = shimmer_pos(frame, start, n_frames, repeat=anim.get("repeat", False))
            return _shimmer_span(m.group(1), pos)
        return _RE_SHIMMER.sub(_shimmer, html)

    return html


def _finalize_others(html: str, skip: re.Pattern) -> str:
    """把非当前动画类型的占位符替换为终值（占位符不能裸出）。"""
    if skip is not _RE_COUNTUP:
        html = _RE_COUNTUP.sub(lambda m: _fmt_num(m.group(1), m.group(2)), html)
    if skip is not _RE_TYPEWRITER:
        html = _RE_TYPEWRITER.sub(lambda m: m.group(1), html)
    if skip is not _RE_SHIMMER:
        html = _RE_SHIMMER.sub(lambda m: _shimmer_span(m.group(1), 120.0), html)
    return html


def _fmt_num(raw: str, dec: str | None) -> str:
    v = float(raw)
    if dec:
        return f"{v:.{int(dec)}f}"
    return f"{v:,.0f}"


def _shimmer_span(text: str, pos: float) -> str:
    """流光文字 span：背景渐变 + background-clip:text（白→亮白→灰扫过）。"""
    return (
        f'<span style="background-image:linear-gradient(90deg,{_SHADES[0]},'
        f'{_SHADES[1]} 45%,{_SHADES[0]}, {_SHADES[2]} 55%,{_SHADES[0]});'
        f"background-size:200% 100%;background-position:{pos:.1f}% 0;"
        f"-webkit-background-clip:text;background-clip:text;color:transparent;"
        f'">{text}</span>'
    )
