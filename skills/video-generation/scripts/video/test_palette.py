# -*- coding: utf-8 -*-
"""palette / lint_colors 单测（openspec video-color-retention）。

运行：cd .agents/skills/video-generation/scripts && python -m video.test_palette
覆盖：对比度计算（含 alpha 混合与双层底）、parse_color、PAIRS 全过、
注册表完整性、封面 :root 注入、弱化态升档回归守卫。
"""
from __future__ import annotations

import sys

from . import palette as P
from . import lint_colors as L
from . import config as C


def test_parse_color() -> None:
    assert P.parse_color("#ffffff") == (255, 255, 255, 1.0)
    assert P.parse_color("#abc") == (170, 187, 204, 1.0)      # 3 位展开
    assert P.parse_color("rgb(34, 211, 238)") == (34, 211, 238, 1.0)
    assert P.parse_color("rgba(255,255,255,0.55)") == (255, 255, 255, 0.55)
    for bad in ("#12", "notacolor", "rgba(1,2)"):
        try:
            P.parse_color(bad)
        except ValueError:
            continue
        raise AssertionError(f"parse_color({bad!r}) 应抛 ValueError")


def test_contrast_ratio() -> None:
    r = P.contrast_ratio("#ffffff", "#000000")
    assert abs(r - 21.0) < 0.01
    r = P.contrast_ratio("#ffffff", "#0a0e1a")
    assert 19.0 < r < 19.5
    # alpha 混合：白@0.55 压课件底 ≈5.5:1（升档目标值）
    r = P.contrast_ratio("rgba(255,255,255,0.55)", "#1e293b")
    assert 5.3 < r < 5.7
    # 双层底：字幕带半透明底先叠页面底
    r = P.contrast_ratio("#ffffff", "rgba(15,23,42,0.92)|#1e293b")
    assert r > 15
    # 对称性
    assert abs(P.contrast_ratio("#22d3ee", "#0a0e1a")
               - P.contrast_ratio("#0a0e1a", "#22d3ee")) < 1e-9


def test_pairs_all_pass() -> None:
    for fg, bg, min_ratio, label in P.PAIRS:
        r = P.contrast_ratio(fg, bg)
        assert r >= min_ratio, f"{label}: {r:.2f} < {min_ratio}"


def test_registry_covers_tokens() -> None:
    for hexc in ("#0a0e1a", "#22d3ee", "#94a3b8", "#2563eb", "#64748b", "#1e293b"):
        assert P._norm_hex(hexc) in P.REGISTRY, hexc
    assert "rgb:34,211,238" in P.REGISTRY   # ACCENT rgb
    assert "rgb:255,255,255" in P.REGISTRY  # TEXT rgb
    assert "rgb:0,0,0" in P.REGISTRY        # 阴影黑


def test_scan_colors() -> None:
    found = L.scan_colors(
        'color:#22d3ee;background:rgba(34,211,238,0.4);border:1px solid #abc;'
        "box-shadow:0 0 10px rgba(0,0,0,.5);outline:#ff5f56dd none"
    )
    assert found == {"#22d3ee", "rgb:34,211,238", "#aabbcc", "rgb:0,0,0", "#ff5f56"}


def test_dim_upgrade_regressions() -> None:
    """弱化态升档回归守卫：模板回到旧值时立刻红。"""
    from . import graph, prism, tutorial
    css = prism._CSS
    assert "color: __LIGHT_MUTED__" in css           # prism 未讲要点走 LIGHT_MUTED（4.47:1）
    assert "opacity: 0.4" not in css                  # 旧深色弱化写法不许回归
    assert "rgba(148,163,184,0.75)" not in css        # 占位符弱化走 token 不走旧字面量
    assert graph._THEMES["dark"]["text_future"] == P.DIM_GRAPH_DARK
    assert graph._THEMES["dark"]["text_future"].endswith("0.45)")
    assert graph._THEMES["light"]["text_future"] == P.LIGHT_MUTED == "#64748b"
    assert "color:#64748b; }" in tutorial._CSS        # 终端 done 行升档值


def test_remotion_sync() -> None:
    violations = L.check_remotion_sync()
    assert violations == [], violations


def test_drift_clean() -> None:
    violations = L.check_drift()
    assert violations == [], violations


def test_cover_root_css() -> None:
    css = P.cover_root_css()
    for var in ("--bg:", "--bg-deep:", "--accent:", "--accent2:", "--accent3:",
                "--warn-red:", "--marker-y:", "--text:", "--text-sub:",
                "--text-brand:", "--grid:"):
        assert var in css, var
    assert P.ACCENT in css and P.BG_DARK in css and "{{" not in css


def test_cover_injection() -> None:
    """blog 仓侧：build_cover_html 注入 :root 且无占位符残留。"""
    cover_py = C.PROJECT_ROOT / "scripts" / "video" / "cover.py"
    if not cover_py.exists():
        return  # skill 独立运行（无 blog 仓），跳过
    sys.path.insert(0, str(cover_py.parent))
    try:
        import cover  # noqa
        html = cover.build_cover_html({"MAIN_TITLE": "t"})
        assert "--accent:" in html and "{{PALETTE_CSS}}" not in html
        assert "--bg-deep:   #050810" in html
        # :root 块不得被吞进 /* */ 注释（模板注释含占位符字样的坑，2026-08-25 踩过）
        i = html.find(":root {")
        assert i > 0, "注入后 :root 块缺失"
        last_open = html.rfind("/*", 0, i)
        last_close = html.rfind("*/", 0, i)
        assert not (last_open != -1 and last_close < last_open), ":root 被注释吞掉"
    finally:
        sys.path.remove(str(cover_py.parent))


def main() -> None:
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  ✓ {name}")
        except AssertionError as e:
            failed += 1
            print(f"  ✗ {name}: {e}")
    print(f"{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
