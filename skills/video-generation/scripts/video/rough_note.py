"""手绘强调注记（rough-notation 语义的帧驱动等价实现）。

课件管线无 JS，rough-notation 的 draw-on 用「按帧截断折线」等价落地：
  - seeded 抖动路径（zlib.crc32 种子 → random.Random，跨进程确定性）；
  - circle/underline/box 三型，归一化 viewBox 0-100 +
    preserveAspectRatio="none" 铺满挂点容器外扩；
  - draw-on = 每帧只输出折线前缀（按累计长度切），起笔到收笔逐帧生长，
    窗外输出完整折线（无任何 style 属性，HTML 稳定复用不破）；
    ⚠️ 不用 stroke-dasharray/pathLength 画增长——Chromium 对
    non-scaling-stroke 组合会把 dash 按屏幕单位切开（实测成碎段），
    且 anisotropic 拉伸下 dash 间距不均，效果「断断续续」；
  - 绘制期在折线尖端带一颗引导点（笔尖感），收笔后消失；
  - at_s：起笔相对镜头出生的秒数，对齐口播「讲到圈」的时刻。

颜色三档全部课件色板内：cyan #22d3ee（强调）/ red #f87171（警示）/
green #4ade80（通过）。由 courseware 的 stat 镜头与左栏要点挂点调用。
"""
from __future__ import annotations

import math
import random
import zlib

try:
    from .frames import FPS
except ImportError:                            # 直接脚本运行（单测/调试）
    from frames import FPS

try:
    from .motion import ease_in_out_sine
except ImportError:
    from motion import ease_in_out_sine

# draw-on 总窗（帧，24fps ≈ 1.4s，双笔画串行各半）——快了观众看不出「正在画」
DRAW_DUR = 34
STROKE_W = 5

COLORS = {"cyan": "#22d3ee", "red": "#f87171", "green": "#4ade80"}


def seed_of(key: str) -> int:
    """跨进程确定性种子（禁用内建 hash——PYTHONHASHSEED 盐会漂移）。"""
    return zlib.crc32(key.encode("utf-8"))


# ---------------------------------------------------------------- 路径生成
def _circle_paths(rng: random.Random) -> list[list[tuple[float, float]]]:
    """双笔画椭圆：极坐标采样 + sin 谐波 + 白噪声抖动。"""
    paths = []
    for p in range(2):
        phase = rng.uniform(0, math.tau)
        amp = rng.uniform(0.04, 0.07)
        off = rng.uniform(-2.5, 2.5)
        n = 48
        pts = []
        for i in range(n + 1):
            th = math.tau * i / n + (0.3 if p else 0.0)
            r = 1.0 + amp * math.sin(3 * th + phase) + rng.uniform(-amp, amp)
            pts.append((50 + 47 * r * math.cos(th) + off * 0.3,
                        50 + 43 * r * math.sin(th) + off))
        paths.append(pts)
    return paths


def _underline_paths(rng: random.Random) -> list[list[tuple[float, float]]]:
    """双波浪线：y≈80，幅 2.6，相位/起止错开。"""
    paths = []
    for p in range(2):
        phase = rng.uniform(0, math.tau)
        x0 = 1.0 + p * 2.5
        x1 = 99.0 - p * 3.5
        pts = []
        n = 44
        for i in range(n + 1):
            x = x0 + (x1 - x0) * i / n
            y = 80.0 + 2.6 * math.sin(x / 6.5 + phase) + rng.uniform(-0.8, 0.8)
            pts.append((x, y))
        paths.append(pts)
    return paths


def _box_paths(rng: random.Random) -> list[list[tuple[float, float]]]:
    """手绘矩形：起点顶边中点、四边抖动、收笔过冲 8%。"""
    paths = []
    for p in range(2):
        o = rng.uniform(-1.6, 1.6)
        x0, y0, x1, y1 = 3 + o, 5 + o, 97 + o * 0.5, 95 - o
        corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
        seq = [(corners[0][0] + (corners[1][0] - corners[0][0])
                * rng.uniform(0.3, 0.7), y0)]
        for k in range(4):
            seq.append(corners[(k + 1) % 4] if k < 3 else corners[4 % 4])
        seq.append((x0 + (x1 - x0) * (rng.uniform(0.3, 0.7) + 0.08),
                    y0 + rng.uniform(-1.2, 1.2)))
        pts = []
        for (ax, ay), (bx, by) in zip(seq, seq[1:]):
            n = max(4, int(math.hypot(bx - ax, by - ay) / 9))
            for i in range(n):
                t = i / n
                pts.append((ax + (bx - ax) * t + rng.uniform(-1.1, 1.1),
                            ay + (by - ay) * t + rng.uniform(-1.1, 1.1)))
        paths.append(pts)
    return paths


_GEN = {"circle": _circle_paths, "underline": _underline_paths, "box": _box_paths}


def _poly_d(pts: list[tuple[float, float]]) -> str:
    head = f"M{pts[0][0]:.1f} {pts[0][1]:.1f}"
    return head + "".join(f"L{x:.1f} {y:.1f}" for x, y in pts[1:])


def _prefix(pts: list[tuple[float, float]], frac: float) -> list[tuple[float, float]]:
    """按累计长度取折线前缀（frac∈[0,1]，≥1 返回全折线）。"""
    if frac >= 1.0:
        return pts
    if frac <= 0.0:
        return []
    total = 0.0
    segs = []
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        d = math.hypot(bx - ax, by - ay)
        segs.append(d)
        total += d
    target = total * frac
    acc = 0.0
    out = [pts[0]]
    for d, (bx, by) in zip(segs, pts[1:]):
        if acc + d >= target:
            t = (target - acc) / d if d > 0 else 0.0
            ax, ay = out[-1]
            out.append((ax + (bx - ax) * t, ay + (by - ay) * t))
            return out
        acc += d
        out.append((bx, by))
    return pts


# ---------------------------------------------------------------- 渲染
def _path_el(pts: list[tuple[float, float]], color: str, stroke_w: int,
             tip: bool = False) -> str:
    """一段折线的 path 元素；tip=True 时在末端加引导点（笔尖感）。"""
    if len(pts) < 2:
        return ""
    el = (f'<path d="{_poly_d(pts)}" '
          f'style="fill:none;stroke:{color};stroke-width:{stroke_w};'
          f'stroke-linecap:round;stroke-linejoin:round;'
          f'vector-effect:non-scaling-stroke"/>')
    if tip:
        tx, ty = pts[-1]
        el += (f'<circle cx="{tx:.1f}" cy="{ty:.1f}" r="{stroke_w * 0.7:.1f}" '
               f'style="fill:{color};vector-effect:non-scaling-stroke"/>')
    return el


def note_svg_drawn(style: str, seed_key: str, color: str = "cyan",
                   frame: int = 10 ** 6, birth: int = 0,
                   stroke_w: int = STROKE_W, at_s: float = 0.0,
                   n_paths: int = 2) -> str:
    """带当前帧 draw-on 进度的完整注记 SVG（挂点直用）。

    - 起笔 = birth + at_s * FPS（at_s 对齐口播「讲到圈」）；
    - 双笔画串行各占半窗，画完自动进位下一笔；
    - 窗内：折线前缀 + 笔尖引导点；窗外（含未起笔）：未起笔输出空串、
      已收笔输出完整折线（无 style，HTML 稳定）。
    """
    style = style if style in _GEN else "circle"
    color = COLORS.get(color, COLORS["cyan"])
    rng = random.Random(seed_of(seed_key))
    paths = _GEN[style](rng)
    n_paths = min(n_paths, len(paths))
    draw_birth = birth + int(round(at_s * FPS))
    age = frame - draw_birth
    half = max(1, DRAW_DUR // n_paths)
    parts: list[str] = []
    for i, pts in enumerate(paths):
        local = (age - i * half) / float(half)
        if local <= 0:
            continue                              # 未起笔：该笔不输出
        p = ease_in_out_sine(min(1.0, local))
        if p >= 1.0:
            parts.append(_path_el(pts, color, stroke_w))       # 收笔：完整折线
        else:
            seg = _prefix(pts, p)
            parts.append(_path_el(seg, color, stroke_w, tip=True))
    if not parts:
        return ""
    return (f'<svg class="anno-svg" viewBox="0 0 100 100" '
            f'preserveAspectRatio="none" aria-hidden="true">{"".join(parts)}</svg>')


def self_test() -> None:
    for style in ("circle", "underline", "box"):
        a = note_svg_drawn(style, "demo:key", "cyan", frame=999, birth=0)
        b = note_svg_drawn(style, "demo:key", "cyan", frame=999, birth=0)
        assert a == b, "同种子必须逐字节一致"
        assert "dash" not in a and "dashoffset" not in a, "禁 dash 方案（Chrome 碎段）"
        c999 = note_svg_drawn(style, "demo:key", "cyan", frame=5000, birth=0)
        assert a == c999, "收笔态跨帧逐字节稳定（常量 style 属性允许）"
        assert a.count("<path") == 2
    c = note_svg_drawn("circle", "demo:key", "red", frame=999)
    assert "#f87171" in c
    # 未起笔：空串
    assert note_svg_drawn("circle", "k", frame=0, birth=50) == ""
    # 画中：折线前缀 + 笔尖点，且随帧单调生长
    m10 = note_svg_drawn("underline", "k", frame=10, birth=0)
    m20 = note_svg_drawn("underline", "k", frame=20, birth=0)
    m_end = note_svg_drawn("underline", "k", frame=DRAW_DUR, birth=0)
    assert "<circle" in m10 and "<circle" in m20, "画中应有笔尖引导点"
    assert len(m10) < len(m20), "折线前缀应随帧生长"
    assert "<circle" not in m_end, "整窗结束引导点消失、输出完整折线"
    assert m_end == note_svg_drawn("underline", "k", frame=999, birth=0)
    # at_s 推迟起笔
    assert note_svg_drawn("circle", "k", frame=20, birth=0, at_s=2.0) == ""
    d = note_svg_drawn("circle", "k", frame=20 + int(2.0 * 24), birth=0, at_s=2.0)
    assert "<path" in d
    print("rough_note self_test OK")


if __name__ == "__main__":
    self_test()
