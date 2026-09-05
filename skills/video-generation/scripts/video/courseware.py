"""课件渲染调度器（原深色科幻课件渲染已退役删除）。

2026-09-05 用户定规（openspec prism-motion-pipeline）：gpt6-astra-coding 用的
深色 insight/cover/cta 渲染路径整体删除，白色科技感管线 **prism** 设为默认。
本模块只剩两件事：

- `render_frame` 分发：type=="tool" → screencast（屏录感工具窗）；
  type=="tutorial" → tutorial（亮色教程模板，存量 deck 零回归）；
  其余一律 → prism（白色科技感动效管线，新默认）。
- 形象伴随层 mascot（左下角终端小子）：三管线共用外壳，由本模块提供。
"""

from __future__ import annotations


def render_frame(card: dict, state: dict, width: int = 1920, height: int = 1080) -> str:
    """渲染一帧横屏 HTML（按卡类型分发到对应管线）。"""
    if card.get("type") == "tool":
        from . import screencast

        html = screencast.render_frame(card, state, width, height)
        # mascot 伴随层对 tool 卡同样生效（screencast 自身无外壳，注入 </body> 前）
        m = _mascot_html(state)
        return html.replace("</body>", m + "</body>") if m else html
    if card.get("type") == "tutorial":
        from . import tutorial

        html = tutorial.render_frame(card, state, width, height)
        m = _mascot_html(state)
        return html.replace("</body>", m + "</body>") if m else html
    # 默认：prism 白色科技感动效管线（_doc 内自行注入 mascot，勿重复）
    from . import prism

    return prism.render_frame(card, state, width, height)


# ---------- 形象伴随层（mascot，2026-08-25 courseware 补齐 + 当日升级）----------
# skill「形象伴随层」原只接线 Remotion（MascotCompanion）；courseware/screencast
# 侧此前无 mascot（缺口）。本层补齐：左下角常驻终端小子（scripts/video/assets/
# mascot.svg 六表情互斥显隐版，与封面/Remotion 同形象三份实现之一）。
# 动画约束：禁 CSS animation（管线铁律），一切由 state["frame"] 帧驱动；音波/浮动
# 量化到 3 帧一步（HTML 相同即可复用 PNG），表情按句推断（句内不变）。

_MASCOT_H = 240          # 2026-08-25 用户定规放大档（skill 四档标定上限内，270 喧宾夺主）
_MASCOT_REACT_DUR = 10   # 分句出生反应窗口（帧：26px 下落 + squash 落地）
_QUANT = 3               # 讲话动画量化步长（帧）——3 帧一变，PNG 复用保留 1/3

# 表情关键词表（同步自 Remotion mascot-mood.ts::MOOD_KEYWORDS，改一处必须同步另一处）
_MOOD_KEYWORDS = [
    ("huh",   ["为什么", "怎么回事", "怎么才能", "怎么办", "怎么", "凭什么", "你知道吗", "？", "?"]),
    ("money", ["省了", "省一半", "省得多", "省钱", "省下", "成本", "块钱", "美元", "花销",
               "开销", "预算", "免费", "价格", "收费", "降价", "68%", "%成本"]),
    ("dead",  ["踩坑", "翻车", "报错", "崩了", "崩溃", "失败", "事故", "血泪", "教训", "惨"]),
    ("wow",   ["！", "厉害", "离谱的是", "没想到", "竟然", "居然", "震撼", "直接炸", "翻倍",
               "快了一倍", "牛"]),
    ("meh",   ["无语", "就这", "白瞎", "折腾半天", "一顿操作", "有意义吗", "沉默"]),
]


def _infer_mood(text: str):
    """当前字幕句 → 表情（命中才切，未命中 None=保持）。词组优先于单字。"""
    for mood, words in _MOOD_KEYWORDS:
        for w in words:
            if w in text:
                return mood
    return None


def _load_mascot_svg() -> str:
    from pathlib import Path
    from . import config as _C
    # 项目根 scripts/video/assets/mascot.svg——经 config 的 VIDEO_PROJECT_ROOT/cwd
    # 解析（skill 以 junction 外置时 __file__ 落到 skills 仓自身，parents[3] 不可用）
    svg = _C.PROJECT_ROOT / "scripts" / "video" / "assets" / "mascot.svg"
    if not svg.exists():
        svg = Path(__file__).resolve().parent / "assets" / "mascot.svg"
    return svg.read_text(encoding="utf-8") if svg.exists() else ""


_MASCOT_SVG_RAW = _load_mascot_svg()
# 根元素默认显隐组（无类时全 display:none，必须挂一组默认态）
_MASCOT_SVG_TPL = _MASCOT_SVG_RAW.replace(
    "<svg", '<svg class="mood-smile pose-wave" __MASCOT_CLS__', 1
) if _MASCOT_SVG_RAW else ""


def _mascot_bar_h(frame_q: int, i: int) -> float:
    """音波条高度（与 Remotion MascotFigure.barHeight 同式，伪随机无 Math.random）。"""
    t = frame_q / 24.0 * 9.0
    wave = __import__("math").sin(t + i * 1.7) * 0.5 + __import__("math").sin(t * 0.63 + i * 2.9) * 0.5
    return 8 + abs(wave) * 16   # 8-24px（viewBox 320 宽坐标）


def _mascot_html(state: dict) -> str:
    """左下角伴随机器人（2026-08-25 升级：表情/讲话音波/浮动动画）。

    - 表情：当前字幕句关键词推断（句内不变→复用友好），SVG 根 mood-* 类切换
    - 音波：讲话中（cue_birth 在场）波形组画进 SVG 嘴位带（7 根竖条翻动，表情嘴经
      .talking 类隐去——「波形即嘴」互斥，几何同 Remotion MascotFigure），量化 3 帧
    - 动画：讲话浮动 ±4px（量化）；cue 出生 10 帧 26px 下落 + squash 落地
    - 静默句间：完全静止（PNG 复用）
    样式全内联——tool/tutorial/prism 卡走各自模块 CSS，外部类不保证在场。"""
    if not _MASCOT_SVG_TPL:
        return ""
    import math
    frame = state.get("frame")
    cue_birth = state.get("cue_birth")
    sub = state.get("subtitle") or ""
    talking = isinstance(frame, int) and isinstance(cue_birth, int)
    mood = _infer_mood(sub) or "smile"

    # 包袱表情标记（2026-08-29 talkshow 炸场：card.moods 钉表情 + 气泡，覆盖关键词推断）
    mark = state.get("mood_mark")
    bubble_html = ""
    laughing = False
    if mark:
        m = str(mark.get("mood") or "")
        if m == "laugh":                       # 大笑：wow 脸 + 大幅抖动 + 哈哈气泡
            laughing = True
            mood = "wow"
        elif m in ("huh", "money", "dead", "wow", "meh", "smile"):
            mood = m
        age_m = state.get("mood_mark_age")
        b = str(mark.get("bubble") or "")
        if b and isinstance(age_m, (int, float)) and 0 <= age_m < 0.9:
            tt = min(1.0, age_m / 0.28)
            sc = 0.5 + 0.5 * tt + 0.12 * max(0.0, 1.0 - age_m / 0.9)
            bubble_html = (
                f'<div style="position:absolute;left:55%;bottom:{_MASCOT_H - 20}px;'
                f'transform:translateX(-50%) scale({sc:.2f});transform-origin:50% 100%;'
                f'background:#22d3ee;color:#0a0e1a;font-size:30px;font-weight:900;'
                f'padding:5px 16px;border-radius:14px;white-space:nowrap;'
                f'box-shadow:0 0 26px rgba(34,211,238,0.85);z-index:5;'
                f'font-family:inherit;">{b}</div>'
            )

    ty, rot, sq = 0.0, -3.0, 1.0
    if talking:
        age = frame - cue_birth
        if 0 <= age < _MASCOT_REACT_DUR:      # 出生反应：下落 + squash（ease-out back）
            t = age / _MASCOT_REACT_DUR
            c1, c3 = 1.70158, 2.70158
            e = 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2
            ty = -26 * (1 - e)
            rot = -3 + 5 * (1 - e)
            sq = 1.0 - 0.10 * (1 - t) * (1 if t > 0.7 else 0.5)
        elif laughing:                         # 大笑：幅度加倍的快速抖动（量化 2 帧）
            fq = frame // 2
            ty = 8.0 * math.sin(fq / 1.9)
            rot = -3 + 4 * math.sin(fq / 2.7)
        else:                                  # 讲话浮动：量化 3 帧，±4px
            fq = frame // _QUANT
            ty = 4.0 * math.sin(fq / 3.8)

    # 讲话态：SVG 根挂 talking 类（mascot.svg 的 CSS 隐 .m-mouth 表情嘴），波形组画进
    # SVG 嘴位带——几何与 Remotion MascotFigure 讲话组逐 rect 同步（衬板 x94 y146 w132
    # h52、7 条 cx=108+i*17 条心 y172），与脸同坐标系零换算，和表情嘴互斥不并存（skill
    # 定规「波形即嘴」）。2026-08-26 修：旧实现是 HTML 覆盖层手算 px，糊眼睛上且微笑嘴
    # 从衬板下露出半张（一张脸两个嘴）——根因是跨坐标系换算，本修彻底消灭换算。
    svg = _MASCOT_SVG_TPL.replace("__MASCOT_CLS__", " talking" if talking else "")
    if mood != "smile":
        svg = svg.replace("mood-smile", f"mood-{mood}", 1)
    if talking:
        fq = frame // _QUANT
        bars = "".join(
            f'<rect x="{104.5 + i * 17:.1f}" y="{172 - _mascot_bar_h(fq, i) / 2:.1f}" '
            f'width="7" height="{_mascot_bar_h(fq, i):.1f}" rx="3" fill="#22d3ee" opacity="0.95"/>'
            for i in range(7)
        )
        wave = (
            '<g><rect x="94" y="146" width="132" height="52" rx="10" fill="#0a0e1a" '
            'stroke="rgba(34,211,238,0.4)" stroke-width="2"/>' + bars + "</g>"
        )
        svg = svg.replace("</svg>", wave + "</svg>")

    return (
        # left:48/bottom:36 为 skill 四档标定（右下镜像左侧）；高 240 放大档
        f'<div style="position:absolute;left:48px;bottom:36px;z-index:40;pointer-events:none;'
        f'transform-origin:50% 90%;transform:translateY({ty:.1f}px) rotate({rot:.1f}deg) scaleY({sq:.3f});'
        f'filter:drop-shadow(0 6px 10px rgba(0,0,0,0.55)) drop-shadow(0 0 18px rgba(34,211,238,0.28));">'
        f'<div style="height:{_MASCOT_H}px;width:{int(_MASCOT_H * 320 / 470)}px;overflow:visible;">{svg}</div>'
        f'{bubble_html}</div>'
    )
