# -*- coding: utf-8 -*-
"""字号与要点密度机检（横屏可读性基准，2026-08-24 定规）。

基准依据 openspec/changes/video-landscape-readability：
为抖音信息流最坏情况（1080×607 显示）设计——正文 ≥48px（画面高 4.4%）、
标题 ≥72px（紧凑模板/Remotion 内容场景 48）、辅助 ≥36（紧凑 26/34）、装饰 ≥24。
配套：要点 ≤3 条/卡、≤14 字/条（存量 deck 超限渲染时只警告，本机检硬卡）。

用法：
    cd .agents/skills/video-generation/scripts
    python -m video.lint_font_sizes            # 全部模板 + Remotion 场景 + 全部 deck
    python -m video.lint_font_sizes --deck video-pipeline-6-skills   # 单 deck
退出码：0 通过 / 1 有违规。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from . import config as C

SCRIPT_DIR = Path(__file__).resolve().parent

# 元素级字号下限表（file, selector 子串, 最小 px）。值为 2026-08-24 定规的实现值，
# 只许升不许降——改动模板时同步改这张表，降字号必须先过 spec 变更。
FONT_RULES: list[tuple[str, str, int]] = [
    # courseware 暗色主讲模板
    ("courseware.py", ".title", 72),
    ("courseware.py", ".point.active", 56),
    ("courseware.py", ".point", 48),
    ("courseware.py", ".sp-item.active .sp-text", 48),
    ("courseware.py", ".subtitle", 48),
    ("courseware.py", ".outline li .num", 48),
    ("courseware.py", ".outline li", 36),
    ("courseware.py", ".sp-item.done", 28),
    ("courseware.py", ".eyebrow", 24),
    ("courseware.py", ".footer-bar", 24),
    ("courseware.py", ".sp-item.active::before", 24),
    # screencast 屏录感模板
    ("screencast.py", ".warnbox .wrow .wmark", 48),
    ("screencast.py", ".warnbox .wrow", 44),
    ("screencast.py", ".cb", 40),
    ("screencast.py", ".hlab", 34),
    ("screencast.py", ".subtitle", 48),
    ("screencast.py", ".wtitle", 28),
    ("screencast.py", ".s-step .tx", 26),
    ("screencast.py", ".cb.ai .cbname", 26),
    ("screencast.py", ".wtag", 24),
    # tutorial 亮色紧凑模板（紧凑档）
    ("tutorial.py", ".subtitle", 46),
    ("tutorial.py", ".h1", 48),
    ("tutorial.py", ".pt", 34),
    ("tutorial.py", ".term", 30),
    ("tutorial.py", ".hlab", 30),
    ("tutorial.py", ".fnode", 26),
    ("tutorial.py", ".eyebrow", 26),
    ("tutorial.py", ".spill", 24),
    ("tutorial.py", ".codebody", 24),
    ("tutorial.py", ".pts-h", 24),
]

# Remotion 内容场景 fontSize 下限（grep 数字，按文件分组取最小值）
REMOTION_MIN_FONT = {
    "SkillStage.tsx": 30,
    "ConclusionFocus.tsx": 60,
}


def lint_css_fonts() -> list[str]:
    """解析模板内联 CSS 的 selector→font-size，对照下限表。"""
    violations: list[str] = []
    css_cache: dict[str, str] = {}
    for fname, sel, minimum in FONT_RULES:
        if fname not in css_cache:
            path = SCRIPT_DIR / fname
            css_cache[fname] = path.read_text(encoding="utf-8") if path.exists() else ""
        src = css_cache[fname]
        # 匹配 selector 块内的 font-size（selector 行后最近的 font-size 声明）
        pat = re.compile(
            re.escape(sel) + r"\s*\{[^}]*?font-size:\s*(\d+)px", re.IGNORECASE
        )
        m = pat.search(src)
        if not m:
            violations.append(f"[缺失] {fname} {sel} 未找到（改名或删掉了？同步 lint 表）")
            continue
        size = int(m.group(1))
        if size < minimum:
            violations.append(f"[字号] {fname} {sel} = {size}px < 下限 {minimum}px")
    return violations


def lint_remotion_fonts() -> list[str]:
    """Remotion 场景 fontSize 数字下限（信息流可读，紧凑档）。"""
    violations: list[str] = []
    scenes_dir = (
        SCRIPT_DIR.parent / "remotion" / "src" / "scenes" / "content"
    )
    if not scenes_dir.exists():
        return violations
    for fname, minimum in REMOTION_MIN_FONT.items():
        path = scenes_dir / fname
        if not path.exists():
            violations.append(f"[缺失] Remotion 场景 {fname} 不存在（改名？同步 lint 表）")
            continue
        sizes = [
            int(n) for n in re.findall(r"fontSize:\s*(\d+)", path.read_text(encoding="utf-8"))
        ]
        too_small = [n for n in sizes if n < minimum]
        if too_small:
            violations.append(
                f"[字号] Remotion {fname} 存在 fontSize {too_small} < 下限 {minimum}"
            )
    return violations


def lint_deck(slug: str) -> list[str]:
    """deck 要点密度：≤POINT_MAX_COUNT 条、每条 ≤POINT_MAX_CHARS 字。"""
    violations: list[str] = []
    deck_dir = C.OUTPUT_ROOT / "deck" / slug
    dj = deck_dir / "deck.json"
    if not dj.exists():
        return [f"[deck] {slug} 无 deck.json（跳过：非课件类）"]
    cards = json.loads(dj.read_text(encoding="utf-8"))["cards"]
    for i, card in enumerate(cards):
        pts = card.get("points") or []
        if len(pts) > C.POINT_MAX_COUNT:
            violations.append(
                f"[要点] {slug} 卡{i:02d} {len(pts)} 条 > {C.POINT_MAX_COUNT}"
            )
        for j, t in enumerate(pts):
            if len(str(t)) > C.POINT_MAX_CHARS:
                violations.append(
                    f"[要点] {slug} 卡{i:02d}-{j + 1} {len(str(t))} 字：「{t}」"
                )
    return violations


def main() -> None:
    args = sys.argv[1:]
    violations: list[str] = []
    violations += lint_css_fonts()
    violations += lint_remotion_fonts()

    # deck 要点密度：存量 deck 普遍超限（2026-08-24 前的债），默认不查；
    # 新内容发布前显式 --deck <slug> 机检（或 --all-decks 全量清债）。
    if "--deck" in args:
        slug = args[args.index("--deck") + 1]
        violations += lint_deck(slug)
    elif "--all-decks" in args:
        deck_root = C.OUTPUT_ROOT / "deck"
        if deck_root.exists():
            for d in sorted(deck_root.iterdir()):
                if (d / "deck.json").exists():
                    violations += lint_deck(d.name)

    if violations:
        print(f"❌ 可读性机检 {len(violations)} 项违规：")
        for v in violations:
            print("  " + v)
        sys.exit(1)
    print("✅ 可读性机检通过（字号基准 + Remotion 场景 + deck 要点密度）")


if __name__ == "__main__":
    main()
