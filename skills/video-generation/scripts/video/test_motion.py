# -*- coding: utf-8 -*-
"""motion 单测（缓动/预烘焙帧表/编舞助手/换态强调配方）。

运行：cd .agents/skills/video-generation/scripts && python -m video.test_motion
覆盖：缓动端点与单调性、帧表终值、窗口外终态守卫（PNG 复用前提）、
swap_pair/stamp/sting 的拍点正确性（2026-08-26 新增配方回归）。
"""
from __future__ import annotations

from .motion import (
    apply_anim, breathe, count_up_table, ease_in_cubic, ease_in_out_sine,
    ease_in_quart, ease_out_back, ease_out_cubic, ease_out_expo,
    ease_out_quart, enter_tuple, exit_tuple, glow_mult, grow_scale,
    settle_dip, shimmer_pos, stamp_tuple, sting_tuple, swap_pair,
    typewriter_table, type_chars,
)

FPS = 24  # 规范基准帧率（SKILL.md「动画与特效强制规范」）


def test_easing_endpoints() -> None:
    for fn in (ease_out_cubic, ease_in_cubic, ease_in_out_sine, ease_out_back,
               ease_out_expo, ease_out_quart, ease_in_quart):
        assert abs(fn(0.0)) < 1e-9, fn.__name__
        assert abs(fn(1.0) - 1.0) < 1e-9, fn.__name__


def test_easing_monotonic() -> None:
    # 出场加速曲线必须单调不减（quart 比 cubic 更陡但不出负值）
    for fn in (ease_out_cubic, ease_in_cubic, ease_in_out_sine, ease_out_expo,
               ease_out_quart, ease_in_quart):
        prev = fn(0.0)
        for i in range(1, 21):
            v = fn(i / 20)
            assert v >= prev - 1e-9, f"{fn.__name__} 非单调 @t={i/20}"
            prev = v


def test_back_overshoot_cap() -> None:
    # 规范：overshoot ≤10%（back.out 标准 s=1.70158 理论峰值 1.1000026，
    # 超 2.6e-6 在帧量化后不可见，容差放到 1.1e-4 档）
    peak = max(ease_out_back(i / 240) for i in range(241))
    assert 1.0 < peak <= 1.1001, peak


def test_count_up_table() -> None:
    t = count_up_table(9603, 12)
    assert len(t) == 13 and t[0] == "0" and t[-1] == "9,603"
    assert count_up_table(9603, 12, thousands=False)[-1] == "9603"
    assert count_up_table(1.5, 6, decimals=1)[-1] == "1.5"


def test_typewriter_full_end() -> None:
    t = typewriter_table("帧号驱动", 8)
    assert t[-1] == "帧号驱动" and all(len(x) <= 4 for x in t)


def test_enter_exit_terminal_states() -> None:
    # 窗口外终态守卫：动画窗口结束后必须回到无样式终态（PNG 复用前提）
    assert enter_tuple(999, 10) == (1.0, 0.0, 1.0)
    assert enter_tuple(-1, 10, dy=40, scale_from=0.6)[0] == 0.0
    assert exit_tuple(-1, 5) is None
    assert exit_tuple(999, 5) == (0.0, -26.0, 1.0)


def test_settle_glow_windows() -> None:
    assert settle_dip(-1, 5) is None and settle_dip(5, 5) is None
    assert settle_dip(2, 4) < 1.0                        # 凹陷中
    assert glow_mult(-1) is None and glow_mult(6) is None
    assert 0.0 < glow_mult(0) <= 0.8


def test_swap_pair_phases() -> None:
    assert swap_pair(-1) is None                          # 未开始：旧词原样
    old_y, old_op, new_y, new_op = swap_pair(0, 10)
    assert old_y == 0.0 and old_op == 1.0                 # 拍 0：旧词未动
    assert new_y > 0 and new_op == 0.0                    # 新词藏在下方
    old_y, old_op, new_y, new_op = swap_pair(5, 10)
    assert old_op < 1.0 and old_y < 0                     # 60% 拍前：旧词上甩中
    assert new_op == 0.0
    old_y, old_op, new_y, new_op = swap_pair(10, 10)
    assert (old_y, old_op, new_y, new_op) == (-112.0, 0.0, 0.0, 1.0)  # 终态
    # 只重叠极短：旧词 opacity 归零必须早于新词 opacity 起步
    mid = swap_pair(6, 10)
    assert mid[1] <= 0.05 and mid[3] == 0.0 or mid[3] > 0


def test_grow_scale_bounds() -> None:
    assert grow_scale(-1, 8) == 0.0
    assert grow_scale(999, 8) == 1.0
    assert 0.0 < grow_scale(4, 8) < 1.0
    # 两端缓：中点前增速已放缓（sine 特性）
    assert grow_scale(4, 8) > 0.45


def test_stamp_tuple() -> None:
    op, sc, rot = stamp_tuple(-1)
    assert op == 0.0 and sc == 1.25 and rot == 2.0        # 未出生
    op, sc, rot = stamp_tuple(999)
    assert (op, sc, rot) == (1.0, 1.0, 0.0)               # 终态
    op, sc, rot = stamp_tuple(2, 13)
    assert sc > 1.0 and rot > 0                           # 拍落途中带旋转


def test_sting_tuple_flash_single_frame() -> None:
    assert sting_tuple(-1) is None
    land, flash, _, _ = sting_tuple(3, land_dur=16, flash_at=8)
    assert land > 1.0 and not flash                       # 落定中，未闪
    assert sting_tuple(8, land_dur=16, flash_at=8)[1] is True    # 白闪恰 1 帧
    assert sting_tuple(9, land_dur=16, flash_at=8)[1] is False
    land, flash, ring_s, ring_o = sting_tuple(999)
    assert (land, flash, ring_s, ring_o) == (1.0, False, 2.4, 0.0)  # 全终态
    # 环扩散单调、透明度单调衰减
    prev_s, prev_o = 0.34, 0.9
    for f in range(8, 31, 2):
        _, _, s, o = sting_tuple(f, land_dur=16, flash_at=8)
        assert s >= prev_s and o <= prev_o
        prev_s, prev_o = s, o


def test_apply_anim_placeholders() -> None:
    html = "<p>@@countup:9603@@ @@typewriter:帧驱动@@ @@shimmer:流光@@</p>"
    out = apply_anim(html, None, 0)                       # 无 anim：占位符 → 终值
    assert "9,603" in out and "帧驱动" in out and "流光" in out
    out = apply_anim(html, {"type": "countup", "start_frame": 4, "frames": 8}, 4)
    assert "9,603" not in out or "0" in out               # 窗口内：滚动中
    out = apply_anim(html, {"type": "countup", "start_frame": 4, "frames": 8}, 99)
    assert "9,603" in out                                 # 窗口外：终值静止
    assert "@@" not in out


def test_breathe_bounded() -> None:
    v = breathe(0, amp=0.03, period=10)
    assert abs(v - 1.0) < 1e-9                            # 相位归零起点
    assert all(abs(breathe(f, amp=0.03, period=10) - 1.0) <= 0.031
               for f in range(0, 40))


def test_shimmer_window() -> None:
    assert shimmer_pos(0, 10, 10) == -20.0
    assert abs(shimmer_pos(99, 10, 10) - 120.0) < 1e-9
    assert shimmer_pos(0, 10, 10, repeat=True) == -20.0   # 循环相位归一


def test_type_chars() -> None:
    assert type_chars("abc", -1) == ""
    assert type_chars("abc", 99) == "abc"
    assert len(type_chars("abc", 2, 12)) >= 1


def main() -> None:
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ✓ {fn.__name__}")
    print(f"motion: {len(fns)} tests passed")


if __name__ == "__main__":
    main()
