# -*- coding: utf-8 -*-
"""权威画面色板（SSOT）—— openspec/changes/video-color-retention 定规。

全部画面渲染管线的颜色以此文件为唯一权威：
- tutorial.py 常量直接 import 本模块；graph/courseware/screencast 的 CSS 字面量
  由 lint_colors.py 做「色板外漂移」扫描（不在 REGISTRY 的色值直接 FAIL，
  改本文件 token 后模板里的旧字面量也会因失配而被拦下）；
- 封面横竖模板 :root 由 cover_root_css() 构建期注入（blog 仓 cover.py）；
- Remotion theme.ts 默认值与本表对齐（lint_colors 同步校验 + 全 src 禁 #00d9ff）。

分级对比度下限（WCAG 口径，lint_colors 按 PAIRS 逐项机检）：
- 正文/字幕 ≥4.5:1；≥24px 大字与「弱化态」（未讲/未来/注释）≥3.0:1
- 弱化态「未讲 ≠ 不可见」：升档值压在 4~5.5:1，与正常态保持 ≥2:1 主次比
- 装饰性元素（网格线/光晕/阴影）不设对比度要求

新增颜色的规矩：先在本文件登记（品牌色进 token 区，或 EXEMPT 豁免并写明理由），
文字色同时进 PAIRS 声明配对与分级阈值，再进模板——lint_colors 拦截未登记色值。

强调色用量规约（防高饱和青刺眼，管用量不改色值）：
主青 #22d3ee 限强调用途（高亮态/边框/图表系列色/进度条），禁做正文长文本色、
禁大面积实填充（单屏 ≤15%）、同屏辉光元素 ≤2 个。
"""
from __future__ import annotations

import re as _re

# ============ 深色系（Remotion / graph dark / 封面 / screencast） ============
BG_DARK = "#0a0e1a"        # 主深底（不纯黑）
BG_ALT = "#0a1929"         # 暗蓝（渐变/过渡，Remotion backgroundAlt）
BG_DARKER = "#050810"      # 封面径向渐变暗角端
ACCENT = "#22d3ee"         # 品牌主青：强调专用（唯一主强调，禁紫橙进主标题区）
ACCENT_RGB = "34,211,238"  # ACCENT 的 rgb 三元组（rgba() 场景）
ACCENT_DEEP = "#0891b2"    # 青渐变深端（CTA/徽章渐变第二stop）
ACCENT_LIGHT = "#67e8f9"   # 亮青（拟物窗口内强调文字 cyan-300）
PROGRESS_START = "#06b6d4" # 进度条渐变起点（cyan-500）
TEXT = "#ffffff"           # 正文白
TEXT_RGB = "255,255,255"
TEXT_MUTED = "#94a3b8"     # 弱化灰（slate-400）；Remotion 代码注释同用此值
TEXT_MUTED_RGB = "148,163,184"

# graph 渐变底（暗端做对比度最坏情况）
GRAPH_BG_TOP = "#0a0e17"
GRAPH_BG_BOT = "#060a11"

# ============ 课件底（中明度深蓝灰，抗强光既定设计，不纯黑） ============
BG_COURSEWARE = "#1e293b"  # slate-800；兼作 tutorial 正文墨色

# ============ 弱化态（2026-08-25 升档：户外强光下低对比文字最先消失） ============
DIM_ON_COURSEWARE = "rgba(255,255,255,0.55)"  # 课件未讲要点（旧 #475569@0.5 ≈1.9:1 → ≈5.5:1）
DIM_GRAPH_DARK = "rgba(255,255,255,0.45)"     # graph dark future 文字（旧 @0.25 ≈2.1:1 → ≈4.4:1）

# ============ 亮色系（tutorial / graph light） ============
LIGHT_BG = "#f6f8fb"           # tutorial 底
GRAPH_LIGHT_BG_TOP = "#f1f5f9" # graph light 渐变亮端
GRAPH_LIGHT_BG_BOT = "#e2e8f0" # graph light 渐变暗端
LIGHT_ACCENT = "#2563eb"       # 亮底主蓝（blue-600）
LIGHT_ACCENT_RGB = "37,99,235"
LIGHT_ACCENT_DARK = "#1d4ed8"  # blue-700（active 文字加深）
LIGHT_ACCENT_LIGHT = "#60a5fa" # blue-400（进度条渐变亮端）
LIGHT_INK = "#0f172a"          # graph light 标题/正文墨色（slate-900）
LIGHT_MUTED = "#64748b"        # 亮底弱化态（graph light future / tutorial 终端 done；slate-500）
LIGHT_DONE = "#475569"         # 亮底 done 态文字（slate-600）
TUTORIAL_INK = "#1e293b"       # tutorial 正文墨色（slate-800）

# ============ 副色（封面主次制延伸到正片：紫/橙仅标签位，红/黄受惊吓色预算约束） ============
PURPLE = "#a78bfa"
ORANGE = "#f59e0b"
WARN_RED = "#ef4444"
MARKER_YELLOW = "#facc15"

# ============ 语义状态（双通道强制：颜色必配 ✗/✓ 或形状差异，不许仅靠颜色传义） ============
ERROR = "#dc2626"      # Remotion theme.error
SUCCESS = "#0f766e"    # Remotion theme.success（teal-700）
HIGHLIGHT = "#dbeafe"  # Remotion theme.highlight（面板浅蓝底）
SUCCESS_TEXT = "#15803d"  # 亮底成功文字（green-700，tutorial done）
TERM_GREEN = "#16a34a"    # 终端提示符/输出绿（green-600）
TERM_OK = "#4ade80"       # 深底终端 ok 绿（green-400）
TERM_WARN_RED = "#f87171" # 深底终端/代码警示红（red-400）

# ============ 代码块（GitHub Dark 风，Remotion CodeBlock / 各模板代码窗共用） ============
CODE_BG = "#0d1117"
CODE_HEAD = "#161b22"
CODE_LINENO = "#484f58"
CODE_TEXT = "#e2e8f0"
CODE_GREEN = "#34d399"    # 合规 token 绿（配 ✓）
CODE_RED = "#f87171"      # 写死违规红（配 ✗；与 TERM_WARN_RED 同值同注册）

# ============ 拟物/中性豁免（非品牌色；登记理由，改版需同步改理由） ============
# key 规范：hex 小写 6 位；rgba 用 "rgb:r,g,b"（alpha 任意，归属同一注册项）
EXEMPT: dict[str, str] = {
    # --- slate 中性阶（面板底/边框/次要文字，深色系配套） ---
    "#0f172a": "slate-900 面板底（字幕带/知识卡/终端，rgba(15,23,42,*) 同项）",
    "rgb:15,23,42": "slate-900 面板底（字幕带/知识卡，alpha 随层次）",
    "#1e2433": "tutorial 代码窗底（深蓝面板）",
    "#171c29": "tutorial 代码窗标题栏",
    "#2b3347": "tutorial 代码窗边框",
    "#9fb0cd": "tutorial 代码窗标签文字",
    "#48556e": "tutorial 代码行号",
    "#d7e0f0": "tutorial 代码正文",
    "#05090f": "screencast 终端/代码窗底（近黑，窗口内容非画面底）",
    "#33415c": "screencast keybox 边框",
    # --- screencast 工具窗 chrome（窗口底/标题栏/边框系） ---
    "#0b1220": "screencast 窗口底",
    "#111c30": "screencast 标题栏",
    "#0d1626": "screencast 步骤条底",
    "#0f1a2e": "screencast 面板/气泡底",
    "#2a3a55": "screencast 窗框/边框",
    "#22304a": "screencast 分隔线/边框",
    "#1f2b44": "screencast 徽章底/分隔线",
    "#123044": "screencast 用户气泡底（青调深底）",
    "#cbd5e1": "slate-300（徽章文字/done 卡文字 rgba(203,213,225,*) 同项）",
    "rgb:203,213,225": "slate-300 done 知识卡文字",
    "#a7f3d0": "screencast keybox 值文字（薄荷绿）",
    "#7dd3fc": "screencast settings key 色（sky-300）",
    "#2a1215": "screencast 警告行底（红调深底）",
    "rgb:248,113,113": "red-300 警示描边/文字",
    "#fecaca": "red-200 警告行文字（screencast warnbox）",
    "rgb:40,200,72": "green done 步骤底 rgba（screencast steplist）",
    "#334155": "slate-700 tutorial 终端正文",
    "#f2f5fa": "tutorial 代码窗舞台底",
    "#dddddd": "VS Code 输入文字（拟物）",
    "rgb:74,222,128": "green-350 done 边框",
    "#86efac": "tutorial 热点 done 边框（green-300）",
    "#bfe4cd": "tutorial 步骤 done 边框",
    "#dcfce7": "tutorial done 徽章底（green-100）",
    "#f2fbf5": "tutorial done 步骤底（green-50）",
    "#f6fdf8": "tutorial done 要点底",
    "#d3ecd9": "tutorial done 要点边框",
    "#eff6ff": "blue-50 active 底（tutorial/code 高亮行）",
    "#dbe3ee": "tutorial 亮色卡片边框",
    "#e8edf4": "tutorial 网格线（浅）",
    "#eef2f7": "tutorial 序号圆底",
    "#e2e8f0": "slate-200（封面要点文字/浅网格/graph light 渐变暗端）",
    "#e6ebf2": "tutorial 进度条轨道",
    "#fbfcfe": "tutorial 终端窗底（近白）",
    "#e0f2fe": "screencast 用户气泡文字（sky-100）",
    "rgb:139,92,246": "紫光晕 rgba(violet-500)（screencast 右下/tutorial 左下）",
    # --- Mac 红绿灯/浏览器 chrome（拟物仿真，随仿真对象走） ---
    "#ff5f57": "Mac 关闭灯（拟物）",
    "#febc2e": "Mac 最小化灯（拟物）",
    "#28c840": "Mac 绿灯（拟物，兼 screencast done ✓）",
    "#ff5f56": "Mac 关闭灯（hero HUD 窗变体）",
    "#ffbd2e": "Mac 最小化灯（hero HUD 窗变体）",
    "#27c93f": "Mac 绿灯（hero HUD 窗变体）",
    "#fb7185": "tutorial 终端窗红绿灯 rose-400（拟物）",
    "#fbbf24": "tutorial 终端窗黄灯 amber-400（拟物，兼排行榜金）",
    "#34d399": "tutorial 终端窗绿灯 emerald-400（拟物，与 CODE_GREEN 同值）",
    # --- VS Code 拟物窗口（screencast vscode / tutorial codewin） ---
    "#1e1e1e": "VS Code 编辑器底（拟物）",
    "#2d2d2d": "VS Code 标签栏（拟物）",
    "#333333": "VS Code 侧栏/消息底（拟物，3 位 hex）",
    "#252526": "VS Code 侧栏（拟物）",
    "#2b2b2b": "VS Code 边框（拟物）",
    "#3c3c3c": "VS Code 输入框边框（拟物）",
    "#232323": "VS Code 图标底（拟物）",
    "#0e639c": "VS Code 状态栏/按钮蓝（拟物）",
    "#2b5876": "VS Code 用户消息底（拟物）",
    "#4d9fff": "VS Code 高亮蓝（拟物）",
    "#9cdcfe": "VS Code 语法蓝（拟物）",
    "#ce9178": "VS Code 语法橙（拟物）",
    "#c586c0": "VS Code 语法紫（拟物）",
    "#6a9955": "VS Code 注释绿（拟物）",
    "#dcdcaa": "VS Code 函数黄（拟物）",
    "#d4d4d4": "VS Code 正文灰（拟物）",
    "#4ec9b0": "VS Code ok 绿（拟物）",
    "#cccccc": "VS Code 正文（拟物）",
    "#e0e0e0": "VS Code 面板头文字（拟物）",
    "#e8f4fd": "VS Code 消息文字（拟物）",
    "#858585": "VS Code 活动栏图标（拟物）",
    "#888888": "VS Code 输入占位（拟物，3 位 hex）",
    "#5a5a5a": "VS Code 面板占位文字（拟物）",
    # --- tutorial 代码语法高亮（codewin 内嵌高亮色） ---
    "#c792ea": "tutorial 代码关键字紫",
    "#a5d6a7": "tutorial 代码字符串绿",
    "#5c6b85": "tutorial 代码注释灰蓝",
    "#f0a45d": "tutorial 代码数字橙",
    "#82aaff": "tutorial 代码函数蓝",
    "#ffcb6b": "tutorial 代码类型黄",
    # --- 排行榜金色系（screencast rank，语义=榜首徽章） ---
    "#d97706": "排行榜榜首徽章 amber-600",
    "#92400e": "排行榜金条渐变深端 amber-800",
    "#155e75": "排行榜青条渐变深端 cyan-800",
    # --- 阴影/描边黑（纯功能色） ---
    "#000000": "字幕黑描边/窗口黑底（功能色）",
    "rgb:0,0,0": "阴影黑（任意 alpha）",
    # --- graph light 节点渐变（白系渐变中间档） ---
    "#e0e7ff": "graph light 中心节点渐变（indigo-100）",
    "#c7d2fe": "graph light 中心节点渐变深端（indigo-200）",
    "#bfdbfe": "graph light active 节点渐变（blue-200）",
    "#dbeafe": "同 HIGHLIGHT（blue-100），此处独立注册避免歧义",
    # --- prism 白色科技感管线（openspec prism-motion-pipeline，非文字氛围/描边） ---
    "#dbe4f0": "prism 玻璃卡渐变描边端1（非文字装饰）",
    "#c7e6f2": "prism 玻璃卡渐变描边端2（非文字装饰）",
    "#eaf1fb": "prism 隔页/recap 装饰带浅底（非文字）",
    "rgb:96,165,250": "prism 极光斑 blue（rgba(96,165,250,≤.10) 氛围层，非文字）",
    "rgb:8,145,178": "prism 渐变大字青端 ACCENT_DEEP 的 rgb 形态（含 alpha 渐变）",
}


# ---------------------------------------------------------------------------
# 注册表：token 自动注册 + EXEMPT 手工登记。lint_colors 用它做漂移扫描。
# ---------------------------------------------------------------------------
def _norm_hex(color: str) -> str:
    c = color.strip().lower()
    if len(c) == 4:  # #abc → #aabbcc
        c = "#" + "".join(ch * 2 for ch in c[1:])
    return c


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    c = _norm_hex(color)
    return int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)


def _rgb_key(r: int, g: int, b: int) -> str:
    return f"rgb:{r},{g},{b}"


def _build_registry() -> dict[str, str]:
    reg: dict[str, str] = {}
    tokens = {
        "BG_DARK": BG_DARK, "BG_ALT": BG_ALT, "BG_DARKER": BG_DARKER,
        "ACCENT": ACCENT, "ACCENT_DEEP": ACCENT_DEEP, "ACCENT_LIGHT": ACCENT_LIGHT,
        "PROGRESS_START": PROGRESS_START, "TEXT": TEXT, "TEXT_MUTED": TEXT_MUTED,
        "GRAPH_BG_TOP": GRAPH_BG_TOP, "GRAPH_BG_BOT": GRAPH_BG_BOT,
        "BG_COURSEWARE": BG_COURSEWARE,
        "LIGHT_BG": LIGHT_BG, "GRAPH_LIGHT_BG_TOP": GRAPH_LIGHT_BG_TOP,
        "GRAPH_LIGHT_BG_BOT": GRAPH_LIGHT_BG_BOT, "LIGHT_ACCENT": LIGHT_ACCENT,
        "LIGHT_ACCENT_DARK": LIGHT_ACCENT_DARK, "LIGHT_ACCENT_LIGHT": LIGHT_ACCENT_LIGHT,
        "LIGHT_INK": LIGHT_INK, "LIGHT_MUTED": LIGHT_MUTED, "LIGHT_DONE": LIGHT_DONE,
        "TUTORIAL_INK": TUTORIAL_INK,
        "PURPLE": PURPLE, "ORANGE": ORANGE, "WARN_RED": WARN_RED,
        "MARKER_YELLOW": MARKER_YELLOW,
        "ERROR": ERROR, "SUCCESS": SUCCESS, "HIGHLIGHT": HIGHLIGHT,
        "SUCCESS_TEXT": SUCCESS_TEXT, "TERM_GREEN": TERM_GREEN,
        "TERM_OK": TERM_OK, "TERM_WARN_RED": TERM_WARN_RED,
        "CODE_BG": CODE_BG, "CODE_HEAD": CODE_HEAD, "CODE_LINENO": CODE_LINENO,
        "CODE_TEXT": CODE_TEXT, "CODE_GREEN": CODE_GREEN, "CODE_RED": CODE_RED,
    }
    for name, val in tokens.items():
        reg[_norm_hex(val)] = f"token {name}"
        r, g, b = _hex_to_rgb(val)
        reg.setdefault(_rgb_key(r, g, b), f"token {name} (rgb)")
    for key, reason in EXEMPT.items():
        if reason is None:  # 占位/误写守卫
            continue
        if key.startswith("#"):
            reg[_norm_hex(key)] = reason
        elif key.startswith("rgb:"):
            reg[key.replace(" ", "")] = reason
    return reg


REGISTRY: dict[str, str] = _build_registry()


# ---------------------------------------------------------------------------
# WCAG 对比度计算（支持 alpha 混合与「半透明底叠实底」两层解析）
# ---------------------------------------------------------------------------
def parse_color(spec: str) -> tuple[int, int, int, float]:
    """'#hex' / '#abc' / 'rgb(r,g,b)' / 'rgba(r,g,b,a)' → (r,g,b,alpha)。"""
    s = spec.strip()
    if s.startswith("#"):
        r, g, b = _hex_to_rgb(s)
        return r, g, b, 1.0
    m = _RGBA_RE.match(s)
    if m:
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        a = float(m.group(4)) if m.group(4) is not None else 1.0
        return r, g, b, a
    raise ValueError(f"无法解析颜色: {spec!r}")


_RGBA_RE = _re.compile(r"^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*([\d.]+))?\s*\)$")


def _blend(fg: tuple[int, int, int, float], bg: tuple[int, int, int, float]) -> tuple[int, int, int]:
    """fg 带 alpha 压到 bg 上（bg 需不透明；多层用叠次调用）。"""
    r, g, b, a = fg
    return (round(r * a + bg[0] * (1 - a)),
            round(g * a + bg[1] * (1 - a)),
            round(b * a + bg[2] * (1 - a)))


def _rel_lum(r: int, g: int, b: int) -> float:
    def lin(c: float) -> float:
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast_ratio(fg_spec: str, bg_spec: str) -> float:
    """两颜色 WCAG 对比度。bg_spec 支持 'A|B' 语法 = 半透明 A 先叠到 B 上。"""
    if "|" in bg_spec:
        top, base = bg_spec.split("|", 1)
        bg = _blend(parse_color(top), parse_color(base))
    else:
        t = parse_color(bg_spec)
        bg = _blend(t, (0, 0, 0, 1.0)) if t[3] < 1.0 else t[:3]
    fg = _blend(parse_color(fg_spec), (*bg, 1.0))
    l1, l2 = sorted((_rel_lum(*fg), _rel_lum(*bg)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


# ---------------------------------------------------------------------------
# 对比度配对声明（lint_colors 逐项机检）
# min_ratio 分级：4.5 = 正文/字幕；3.0 = ≥24px 大字与弱化态（WCAG 大字 AA 口径）
# bg 取「最坏情况」底色（渐变取暗端、字幕带按不透明混色）
# ---------------------------------------------------------------------------
PAIRS: list[tuple[str, str, float, str]] = [
    # --- courseware（底 #1e293b） ---
    (TEXT, BG_COURSEWARE, 4.5, "课件 标题/要点done/卡active 正文白"),
    (ACCENT, BG_COURSEWARE, 3.0, "课件 eyebrow(24px)/active要点(56px) 主青大字"),
    (DIM_ON_COURSEWARE, BG_COURSEWARE, 3.0, "课件 未讲要点（升档后弱化态）"),
    ("rgba(203,213,225,0.8)", "rgba(15,23,42,0.5)|#1e293b", 3.0, "课件 done知识卡文字(28px)"),
    (TEXT, "rgba(15,23,42,0.92)|#1e293b", 4.5, "课件 字幕白"),
    ("#e2e8f0", BG_COURSEWARE, 3.0, "课件 封面outline论点(36px)"),
    # --- graph dark（底渐变取暗端 #060a11） ---
    (TEXT, GRAPH_BG_BOT, 4.5, "图谱dark 标题/中心节点白"),
    ("rgba(255,255,255,0.65)", GRAPH_BG_BOT, 3.0, "图谱dark done节点(24px)"),
    (DIM_GRAPH_DARK, GRAPH_BG_BOT, 3.0, "图谱dark future节点(24px,升档后)"),
    (TEXT, "rgba(10,14,23,0.92)|#060a11", 4.5, "图谱dark 字幕白"),
    # --- graph light（底渐变取暗端 #e2e8f0） ---
    (LIGHT_INK, GRAPH_LIGHT_BG_BOT, 4.5, "图谱light 标题/正文墨色"),
    (LIGHT_DONE, GRAPH_LIGHT_BG_BOT, 3.0, "图谱light done节点(24px)"),
    (LIGHT_MUTED, GRAPH_LIGHT_BG_BOT, 3.0, "图谱light future节点(24px,升档后)"),
    (TEXT, "rgba(15,23,42,0.92)|#e2e8f0", 4.5, "图谱light 字幕白（深底字幕带）"),
    # --- tutorial（底 #f6f8fb） ---
    (TUTORIAL_INK, LIGHT_BG, 4.5, "教程 正文墨色/字幕"),
    (LIGHT_ACCENT, LIGHT_BG, 3.0, "教程 eyebrow(26px加粗)/h1 主蓝大字"),
    (SUCCESS_TEXT, "#f6fdf8", 3.0, "教程 done步骤/要点绿字(24px+)"),
    (LIGHT_MUTED, "#fbfcfe", 3.0, "教程 终端done行(30px,升档后)"),
    ("#334155", "#fbfcfe", 4.5, "教程 终端正文"),
    # --- prism 白色科技感管线（底 #f6f8fb；2026-09-05 openspec prism-motion-pipeline） ---
    (TUTORIAL_INK, LIGHT_BG, 4.5, "prism 标题/要点/字幕墨色"),
    (LIGHT_ACCENT, LIGHT_BG, 3.0, "prism eyebrow/要点active 主蓝(34px+)"),
    (ACCENT_DEEP, LIGHT_BG, 3.0, "prism 渐变大字青端(section章节数字/hero,≥40px)"),
    (LIGHT_MUTED, LIGHT_BG, 3.0, "prism mini-agenda未讲章节/eyebrow弱化(24px+)"),
    (LIGHT_DONE, LIGHT_BG, 3.0, "prism done要点次态文字(28px)"),
    (SUCCESS_TEXT, LIGHT_BG, 3.0, "prism recap✓/done绿字(28px)"),
    (TUTORIAL_INK, "rgba(255,255,255,0.92)|#f6f8fb", 4.5, "prism 字幕（白胶囊叠亮底）"),
    (TUTORIAL_INK, "#eaf1fb", 4.5, "prism 隔页/recap 装饰带上墨色"),
    # --- Remotion / screencast（底 #0a0e1a 系） ---
    (TEXT, BG_DARK, 4.5, "Remotion 正文白"),
    (ACCENT, BG_DARK, 3.0, "Remotion 主青大字/强调"),
    (TEXT_MUTED, BG_DARK, 3.0, "Remotion 辅助灰(24px+)"),
    ("#e2e8f0", "#0f172a", 4.5, "screencast 窗外正文"),
    (TEXT, "rgba(15,23,42,0.92)|#0f172a", 4.5, "screencast 字幕白"),
    (LIGHT_MUTED, "#0f1a2e", 3.0, "screencast 步骤条future文字(26px)"),
    (LIGHT_MUTED, "#05090f", 3.0, "screencast 终端done行(27px)"),
    (TERM_WARN_RED, "#05090f", 3.0, "screencast 终端警示红(27px)"),
    (TERM_OK, "#05090f", 3.0, "screencast 终端ok绿(27px)"),
    # --- Remotion CodeBlock（底 #0d1117） ---
    (CODE_TEXT, CODE_BG, 4.5, "CodeBlock 正文"),
    (TEXT_MUTED, CODE_BG, 3.0, "CodeBlock 注释（升档后=TEXT_MUTED）"),
    (CODE_GREEN, CODE_BG, 3.0, "CodeBlock token绿(配✓)"),
    (CODE_RED, CODE_BG, 3.0, "CodeBlock 违规红(配✗)"),
    # --- 封面（像素验收另有 cover_check，此处保底两对） ---
    (TEXT, BG_DARK, 4.5, "封面 主标题白"),
    (TEXT_MUTED, BG_DARK, 3.0, "封面 副标题灰(36px)"),
]


# ---------------------------------------------------------------------------
# 封面 :root 构建期注入（横竖模板唯一色板源；视觉与 v3/v4 完全一致）
# ---------------------------------------------------------------------------
def cover_root_css() -> str:
    return f""":root {{
    --bg:        {BG_DARK};
    --bg-deep:   {BG_DARKER};
    --accent:    {ACCENT};
    --accent2:   {ORANGE};              /* 橙:仅第 3 个标签与极小点缀(主标题区禁用) */
    --accent3:   {PURPLE};              /* 紫:仅第 2 个标签与左下光晕(主标题区禁用) */
    --warn-red:  {WARN_RED};            /* 红:仅 glitch 影/marker 圈,合计红黄 ≤ 2% */
    --marker-y:  {MARKER_YELLOW};       /* 荧光黄:仅 marker 划线 */
    --text:      {TEXT};
    --text-sub:  {TEXT_MUTED};
    --text-brand:{ACCENT};
    --grid:      rgba(34, 211, 238, 0.04);
  }}"""


def export_json() -> dict[str, str]:
    """token 导出（Remotion/HTML 侧同步用；python -m video.palette --json）。"""
    return {
        k: v for k, v in {
            "bgDark": BG_DARK, "bgAlt": BG_ALT, "bgDarker": BG_DARKER,
            "accent": ACCENT, "accentDeep": ACCENT_DEEP, "accentLight": ACCENT_LIGHT,
            "progressStart": PROGRESS_START, "text": TEXT, "textMuted": TEXT_MUTED,
            "bgCourseware": BG_COURSEWARE, "lightBg": LIGHT_BG,
            "lightAccent": LIGHT_ACCENT, "lightInk": LIGHT_INK, "lightMuted": LIGHT_MUTED,
            "purple": PURPLE, "orange": ORANGE, "warnRed": WARN_RED,
            "markerYellow": MARKER_YELLOW, "error": ERROR, "success": SUCCESS,
        }.items()
    }


if __name__ == "__main__":
    import json as _json
    import sys as _sys
    if "--json" in _sys.argv:
        print(_json.dumps(export_json(), ensure_ascii=False, indent=2))
    else:
        for fg, bg, min_r, label in PAIRS:
            r = contrast_ratio(fg, bg)
            mark = "PASS" if r >= min_r else "FAIL"
            print(f"[{mark}] {r:5.2f}:1 (≥{min_r}) {label}")
