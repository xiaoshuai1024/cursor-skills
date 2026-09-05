# -*- coding: utf-8 -*-
"""色彩可读性机检（openspec/changes/video-color-retention，2026-08-25 定规）。

三道检查（run() 返回违规列表，任一非空 = 非零退出）：
1. **对比度分级判定**：palette.PAIRS 逐项计算——正文/字幕 ≥4.5:1，
   ≥24px 大字与「弱化态」（未讲/未来/注释）≥3.0:1（WCAG AA 口径）。
2. **色板外漂移扫描**：courseware/graph/tutorial/screencast + 封面横竖模板里的
   全部 hex / rgb(a) 三元组必须在 palette.REGISTRY（token 或 EXEMPT 豁免）。
   新增颜色先登记 palette.py 再进模板；palette 改 token 值后，模板里的旧
   字面量会因失配被拦下——这就是「单源」的执行机制。
3. **Remotion 同步**：theme.ts defaultTheme 与 palette 逐项相等 +
   全 src 无 #00d9ff（退役默认主色；注释里的历史提及除外）。

用法：
    cd .agents/skills/video-generation/scripts
    python -m video.lint_colors
挂载：lint_font_sizes.main() 自动并入（make video-lint 单一入口）。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from . import palette as P
from . import config as C

SCRIPT_DIR = Path(__file__).resolve().parent
REMOTION_SRC = SCRIPT_DIR.parents[1] / "remotion" / "src"   # scripts/video → video-generation/remotion

# 漂移扫描目标：Python 模板 + 封面横竖模板（palette/lint/cover.py 注入器不扫）
# 2026-09-05：courseware 深色模板退役删除（瘦身为调度器，无 CSS），扫描目标换 prism
_TEMPLATE_FILES = ["prism.py", "graph.py", "tutorial.py", "screencast.py"]

_HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
_RGB_RE = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)")


def _norm_hex(m: re.Match) -> str:
    c = m.group(0).lower()
    if len(c) == 4:  # #abc → #aabbcc
        return "#" + "".join(ch * 2 for ch in c[1:])
    if len(c) > 7:  # #rrggbbaa → #rrggbb（alpha 不影响注册归属）
        return c[:7]
    return c


def scan_colors(text: str) -> set[str]:
    """文本里出现的全部颜色 key（hex 规范 6 位；rgb(a) → 'rgb:r,g,b'，alpha 忽略）。"""
    found = {_norm_hex(m) for m in _HEX_RE.finditer(text)}
    found |= {
        f"rgb:{m.group(1)},{m.group(2)},{m.group(3)}" for m in _RGB_RE.finditer(text)
    }
    return found


def check_pairs() -> list[str]:
    """检查 1：PAIRS 对比度分级判定。"""
    out = []
    for fg, bg, min_ratio, label in P.PAIRS:
        try:
            r = P.contrast_ratio(fg, bg)
        except ValueError as e:
            out.append(f"[配色对] {label}: 声明解析失败 {e}")
            continue
        if r < min_ratio:
            out.append(f"[对比度] {label}: {r:.2f}:1 < 下限 {min_ratio}:1")
    return out


def check_drift() -> list[str]:
    """检查 2：模板色板外漂移扫描。"""
    out = []
    targets: list[Path] = [SCRIPT_DIR / f for f in _TEMPLATE_FILES]
    targets += [
        C.PROJECT_ROOT / "scripts" / "video" / "cover_template.html",
        C.PROJECT_ROOT / "scripts" / "video" / "cover_template_v.html",
    ]
    for path in targets:
        if not path.exists():
            if path.suffix == ".html":
                continue  # skill 独立运行时封面模板不在（blog 仓侧），跳过
            out.append(f"[缺失] 模板 {path.name} 不存在（改名？同步 lint 目标表）")
            continue
        found = scan_colors(path.read_text(encoding="utf-8"))
        unknown = sorted(c for c in found if c not in P.REGISTRY)
        for c in unknown:
            out.append(
                f"[漂移] {path.name}: {c} 未登记 palette（新增颜色先登记 token 或 EXEMPT 豁免）"
            )
    return out


def _strip_comments(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"//[^\n]*", "", src)


def check_remotion_sync() -> list[str]:
    """检查 3：theme.ts 与 palette 同步 + 退役主色残留。"""
    out = []
    theme_ts = REMOTION_SRC / "core" / "theme.ts"
    if not theme_ts.exists():
        return [f"[缺失] {theme_ts} 不存在"]
    src = _strip_comments(theme_ts.read_text(encoding="utf-8"))
    expected = {
        "background": P.BG_DARK, "backgroundAlt": P.BG_ALT, "accent": P.ACCENT,
        "text": P.TEXT, "textMuted": P.TEXT_MUTED, "error": P.ERROR,
        "success": P.SUCCESS, "highlight": P.HIGHLIGHT,
    }
    actual = dict(re.findall(r'(\w+):\s*"(#[0-9a-fA-F]{6})"', src))
    for key, want in expected.items():
        got = actual.get(key)
        if got is None:
            out.append(f"[同步] theme.ts colors.{key} 未找到（改名？）")
        elif got.lower() != want.lower():
            out.append(f"[同步] theme.ts colors.{key} = {got} ≠ palette {want}")
    # 退役默认主色：注释外的任何出现都拦（双主色回归防线）
    for tsx in REMOTION_SRC.rglob("*.tsx"):
        if "#00d9ff" in _strip_comments(tsx.read_text(encoding="utf-8")):
            out.append(f"[退役色] {tsx.relative_to(REMOTION_SRC)} 含 #00d9ff（退役默认，改用 palette/ACCENT）")
    for ts in REMOTION_SRC.rglob("*.ts"):
        if ts.name in ("theme.ts",):
            continue  # theme.ts 已单独校验（注释允许提及历史值）
        if "#00d9ff" in _strip_comments(ts.read_text(encoding="utf-8")):
            out.append(f"[退役色] {ts.relative_to(REMOTION_SRC)} 含 #00d9ff")
    return out


def run() -> list[str]:
    """全部检查，返回违规列表（空 = 通过）。"""
    violations: list[str] = []
    violations += check_pairs()
    violations += check_drift()
    violations += check_remotion_sync()
    return violations


def main() -> None:
    violations = run()
    if violations:
        print(f"❌ 色彩机检 {len(violations)} 项违规：")
        for v in violations:
            print("  " + v)
        sys.exit(1)
    print("✅ 色彩机检通过（对比度分级 + 色板登记漂移 + Remotion 同步）")


if __name__ == "__main__":
    main()
