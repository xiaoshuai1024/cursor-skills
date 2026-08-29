"""code_mm 镜头：代码 token 级形变（shiki-magic-move 语义的帧驱动等价实现）。

课件管线是纯 Python 帧渲染（每帧静态 HTML，无 JS），shiki-magic-move 无法
直接嵌入，这里移植其动画语义：
  - 正则 tokenizer（py/js/ts/go/java 关键词表，教学示例代码足够；
    病态嵌套如字符串内写注释符不在保障范围，deck 约定不写）；
  - token 序列 LCS 匹配（比 SequenceMatcher 块匹配保留更多交错相同 token）；
  - 等宽单元格坐标系：x 用 ch 单位（=字符数），y 用行号×行高 em。
    ⚠️ CJK 宽字符行内后随 token 的 x 会偏窄——CJK 基本只出现在行尾注释，
    且整行替换时视觉近似淡出淡入，偏差不可见；
  - 三阶段：mm_at 前 before 静态行（复用 courseware 行级 stagger）→
    形变窗 MM_DUR 帧（保留 token 位移 / 离开淡出 / 进入淡入，行号双列交叉）→
    之后 after 静态行。窗外 HTML 逐字节稳定（PNG 复用优化不破）。

由 courseware._shot_body_html 的 code_mm 分支调用（依赖注入静态行渲染函数，
避免循环 import）。颜色全部取自课件色板（lint_colors 零漂移）。
"""
from __future__ import annotations

import html
import re
import zlib
from dataclasses import dataclass

try:
    from .frames import FPS
except ImportError:                            # 直接脚本运行（单测/调试）
    from frames import FPS

try:
    from .motion import ease_in_out_sine, ease_out_cubic
except ImportError:
    from motion import ease_in_out_sine, ease_out_cubic

# 形变窗时长（帧，24fps ≈ 1.08s）
MM_DUR = 26

# ---------------------------------------------------------------- tokenizer
_KEYWORDS: dict[str, frozenset[str]] = {
    "py": frozenset(
        "def return import from class if elif else for while try except with as pass "
        "raise yield lambda None True False self async await not in is and or global "
        "nonlocal del assert finally print len range".split()),
    "js": frozenset(
        "function return const let var if else for while try catch finally class extends "
        "new this import export from default async await throw typeof instanceof null "
        "undefined true false switch case break continue do of".split()),
    "ts": frozenset(
        "function return const let var if else for while try catch finally class extends "
        "new this import export from default async await throw typeof instanceof null "
        "undefined true false switch case break continue do of type interface enum "
        "implements public private protected readonly static".split()),
    "go": frozenset(
        "func return package import var const if else for range switch case type struct "
        "interface map chan go defer select break continue fallthrough nil true false "
        "error string int int64 bool byte rune make new".split()),
    "java": frozenset(
        "public private protected class interface extends implements static final void "
        "int long double float boolean String return new this import package try catch "
        "finally throw throws if else for while switch case break continue null true "
        "false record var".split()),
}

_TOKEN_RE = re.compile(
    r"(?P<cmt>#[^\n]*|//[^\n]*)"
    r"|(?P<str>\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`)"
    r"|(?P<num>\d+(?:\.\d+)?)"
    r"|(?P<id>[A-Za-z_$][A-Za-z0-9_$]*)"
    r"|(?P<ws>\s+)"
    r"|(?P<other>.)"
)


def tokenize_line(text: str, lang: str) -> list[tuple[str, str]]:
    """一行 → [(片段文本, 类名)]，类名 ∈ kw/str/num/cmt/空(正文)。"""
    kws = _KEYWORDS.get(lang, _KEYWORDS["js"])
    out: list[tuple[str, str]] = []
    pos = 0
    for m in _TOKEN_RE.finditer(text):
        if m.start() != pos:                   # 正则未覆盖的间隙（不应发生）
            out.append((text[pos:m.start()], ""))
        kind = m.lastgroup
        val = m.group()
        if kind == "id" and val in kws:
            out.append((val, "kw"))
        elif kind in ("cmt", "str", "num"):
            out.append((val, "cmt" if kind == "cmt" else kind))
        else:
            out.append((val, ""))
        pos = m.end()
    if pos < len(text):
        out.append((text[pos:], ""))
    return out


# ---------------------------------------------------------------- LCS 匹配
@dataclass
class _Tok:
    text: str
    cls: str
    line0: int | None = None                  # before 位（行,列）；离开 token 无 line1
    col0: int | None = None
    line1: int | None = None                  # after 位；进入 token 无 line0
    col1: int | None = None


def _flatten(lines: list[str], lang: str) -> list[_Tok]:
    toks: list[_Tok] = []
    for li, ln in enumerate(lines):
        col = 0
        for text, cls in tokenize_line(ln, lang):
            toks.append(_Tok(text=text, cls=cls, line0=li, col0=col))
            col += len(text)
    return toks


def _lcs_pairs(a: list[str], b: list[str]) -> list[tuple[int, int]]:
    """标准 LCS 回溯：相同 token 尽量配对（允许交错匹配）。"""
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        row, nxt = dp[i], dp[i + 1]
        for j in range(m - 1, -1, -1):
            dp[i][j] = nxt[j + 1] + 1 if a[i] == b[j] else max(nxt[j], row[j + 1])
    pairs, i, j = [], 0, 0
    while i < n and j < m:
        if a[i] == b[j]:
            pairs.append((i, j))
            i += 1
            j += 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            i += 1
        else:
            j += 1
    return pairs


def build_plan(before: list[str], after: list[str], lang: str) -> list[_Tok]:
    """形变计划：保留 token 双侧坐标、离开 token 仅 before 位、进入 token 仅 after 位。"""
    ta, tb = _flatten(before, lang), _flatten(after, lang)
    used_a, used_b = set(), set()
    for i, j in _lcs_pairs([t.text for t in ta], [t.text for t in tb]):
        ta[i].line1, ta[i].col1 = tb[j].line0, tb[j].col0
        used_a.add(i)
        used_b.add(j)
    plan = [t for t in ta if t.line1 is not None]      # 保留（含位移）
    plan += [t for i, t in enumerate(ta) if i not in used_a]   # 离开
    for j, t in enumerate(tb):                          # 进入
        if j not in used_b:
            plan.append(_Tok(text=t.text, cls=t.cls, line1=t.line0, col1=t.col0))
    return plan


# ---------------------------------------------------------------- 渲染
def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _gutter(n: int) -> str:
    return "".join(f'<div class="mm-gut">{i + 1}</div>' for i in range(n))


def _tokens_html(plan: list[_Tok], n_before: int, n_after: int, t: float) -> str:
    """t ∈ [0,1] 形变窗进度 → token 绝对定位层 HTML（窗外不调用）。"""
    move_p = ease_in_out_sine(t)
    leave_q = ease_out_cubic(min(1.0, t / 0.6))
    enter_q = ease_out_cubic(max(0.0, (t - 0.4) / 0.6))
    gut_before = 1.0 - ease_in_out_sine(min(1.0, t / 0.4))
    gut_after = ease_in_out_sine(max(0.0, (t - 0.6) / 0.4))
    parts = [f'<div class="mm-gut" style="opacity:{gut_before:.3f}">'
             f'{_gutter(n_before)}</div>',
             f'<div class="mm-gut" style="opacity:{gut_after:.3f}">'
             f'{_gutter(n_after)}</div>']
    for tk in plan:
        cls = f' {tk.cls}' if tk.cls else ""
        if tk.line0 is not None and tk.line1 is not None:   # 保留：位移
            x = tk.col0 + (tk.col1 - tk.col0) * move_p
            y = tk.line0 + (tk.line1 - tk.line0) * move_p
            op = 1.0
        elif tk.line1 is None:                              # 离开：钉 before 淡出
            x, y = tk.col0, tk.line0
            op = 1.0 - leave_q
        else:                                               # 进入：钉 after 淡入
            x, y = tk.col1, tk.line1
            op = enter_q
        if op <= 0.001:
            continue
        st = (f"left:calc(40px + {x:.2f}ch);top:{y:.2f}em;"
              + ("" if op >= 0.999 else f"opacity:{op:.3f};"))
        parts.append(f'<span class="mm-tok{cls}" style="{st.rstrip(";")}">'
                     f'{_esc(tk.text)}</span>')
    return "".join(parts)


def render_shot(data: dict, state: dict, birth: int, static_renderer) -> str:
    """code_mm 入口。static_renderer(lines, hls, frame, birth) 复用 courseware
    的 code 镜头行渲染，保证形变窗外与普通 code 镜头逐字节同构。"""
    before = list(data.get("before") or [])
    after = list(data.get("after") or [])
    lang = str(data.get("lang") or "js")
    hl_before = int(data.get("hl_before", -1))
    hl_after = int(data.get("hl_after", -1))
    frame = int(state.get("frame", 10 ** 6))
    mm_at = float(data.get("mm_at", 0.0))
    mm_birth = birth + int(round(mm_at * FPS))
    t_rel = frame - mm_birth
    hls_b = [hl_before] if hl_before >= 0 else []
    hls_a = [hl_after] if hl_after >= 0 else []
    if t_rel < 0:                              # 阶段一：before 静态（含行级 stagger）
        return static_renderer(before, hls_b, frame, birth)
    if t_rel >= MM_DUR:                        # 阶段三：after 静态（终态，无属性）
        return static_renderer(after, hls_a, 10 ** 6, 10 ** 6)
    t = t_rel / float(MM_DUR)                  # 阶段二：token 形变窗
    plan = build_plan(before, after, lang)
    tokens = _tokens_html(plan, len(before), len(after), t)
    h = max(len(before), len(after)) * 1.62
    return (f'<div class="mm-wrap" style="height:{h:.2f}em">'
            f'{tokens}</div>')


# ---------------------------------------------------------------- 单测钩子
def self_test() -> None:
    before = [
        "async function fetchUser(id) {",
        "  const res = await fetch(`/api/users/${id}`);",
        "  return res.json();",
        "}",
    ]
    after = [
        "async function fetchUser(id) {",
        "  const res = await fetch(`/api/users/${id}`, {",
        "    signal: AbortSignal.timeout(3000),",
        "  });",
        "  if (!res.ok) throw new Error(`HTTP ${res.status}`);",
        "  return res.json();",
        "}",
    ]
    plan = build_plan(before, after, "js")
    keep = [t for t in plan if t.line0 is not None and t.line1 is not None]
    leave = [t for t in plan if t.line1 is None]
    enter = [t for t in plan if t.line0 is None]
    assert len(keep) + len(leave) == sum(len(tokenize_line(l, "js")) for l in before)
    assert len(keep) + len(enter) == sum(len(tokenize_line(l, "js")) for l in after)
    assert len(keep) > 10 and len(enter) > 4 and not leave, "教学样例应全保留+进入"
    # 窗口端点视觉等价：t=0 只渲染 保留+离开，t≈1 只渲染 保留+进入
    n_keep = sum(1 for t in plan if t.line0 is not None and t.line1 is not None)
    n_leave = sum(1 for t in plan if t.line1 is None)
    n_enter = sum(1 for t in plan if t.line0 is None)
    h0 = _tokens_html(plan, len(before), len(after), 0.0)
    assert h0.count('<span class="mm-tok') == n_keep + n_leave
    h1 = _tokens_html(plan, len(before), len(after), 0.999)
    assert h1.count('<span class="mm-tok') == n_keep + n_enter
    # 确定性：同输入计划逐字段一致
    seed_key = zlib.crc32(b"magic-move")
    assert seed_key == zlib.crc32(b"magic-move")
    plan2 = build_plan(before, after, "js")
    assert [(t.text, t.cls, t.line0, t.col0, t.line1, t.col1) for t in plan] == \
           [(t.text, t.cls, t.line0, t.col0, t.line1, t.col1) for t in plan2]
    print("magic_move self_test OK")


if __name__ == "__main__":
    self_test()
