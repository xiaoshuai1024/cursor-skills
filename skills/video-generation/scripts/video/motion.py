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
    "ease_out_cubic", "ease_out_back", "ease_in_out_sine",
    "count_up_table", "typewriter_table", "shimmer_pos", "breathe",
    "apply_anim",
]


def ease_out_cubic(t: float) -> float:
    """easeOutCubic: 1-(1-t)^3。"""
    return 1 - (1 - t) ** 3


def ease_out_back(t: float, s: float = 1.70158) -> float:
    """easeOutBack: 弹性回弹（对齐 HyperFrames back.out）。"""
    c3 = s + 1
    return 1 + c3 * (t - 1) ** 3 + s * (t - 1) ** 2


def ease_in_out_sine(t: float) -> float:
    """easeInOutSine: -(cos(πt)-1)/2。"""
    return -(math.cos(math.pi * t) - 1) / 2


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
        def _count(m: re.Match) -> str:
            end = float(m.group(1))
            dec = int(m.group(2)) if m.group(2) else 0
            if 0 <= rel <= n_frames:
                table = count_up_table(end, n_frames, decimals=dec)
                return table[rel] if rel < len(table) else _fmt_num(m.group(1), m.group(2))
            return _fmt_num(m.group(1), m.group(2))
        return _RE_COUNTUP.sub(_count, html)

    if anim.get("type") == "typewriter":
        def _type(m: re.Match) -> str:
            text = m.group(1)
            if 0 < rel <= n_frames:
                return typewriter_table(text, n_frames)[rel - 1]
            return text
        return _RE_TYPEWRITER.sub(_type, html)

    if anim.get("type") == "shimmer":
        def _shimmer(m: re.Match) -> str:
            pos = shimmer_pos(frame, start, n_frames, repeat=anim.get("repeat", False))
            return _shimmer_span(m.group(1), pos)
        return _RE_SHIMMER.sub(_shimmer, html)

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
