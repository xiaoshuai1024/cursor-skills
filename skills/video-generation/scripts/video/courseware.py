"""课件画面渲染：把一张卡片 + 某时刻状态渲染成一帧静态横屏 HTML。

横屏 16:9 培训讲解课件（1920x1080）。左栏副标题+标题+要点（三态），右栏
sub_points 知识卡片逐条揭示（或 flow 流程图逐节点动画），底部固定高度字幕带
（所有卡含封面都显示字幕）+ 进度条。封面额外展示 outline 论点列表。
中明度深蓝灰底（不纯黑），科幻感。仅产 HTML 字符串，无 JS/外部资源/动画。

帧驱动动效（openspec courseware-motion-linkage）：一切动画由 state["frame"] +
元素出生帧（point_births/cue_birth/卡起 stagger）数学插值，inline style 注入；
动画窗口外不输出 inline style → HTML 与后续帧一致（PNG 复用优化保持）。

色板：颜色以 palette.py（SSOT）为准，本文件 CSS 字面量由 lint_colors.py
做色板外漂移扫描（openspec video-color-retention，2026-08-25）。
"""

from __future__ import annotations

try:
    from .motion import (                      # 包内运行（python -m video.build）
        ease_in_out_sine,
        ease_out_back,
        ease_out_cubic,
        enter_tuple,
        exit_tuple,
        glow_mult,
        settle_dip,
        type_chars,
    )
except ImportError:                            # 直接脚本运行（python courseware.py）
    from motion import (
        ease_in_out_sine,
        ease_out_back,
        ease_out_cubic,
        enter_tuple,
        exit_tuple,
        glow_mult,
        settle_dip,
        type_chars,
    )

# 卡起入场 stagger 锚（帧，24fps ≈ ms/41.7）
_ENT_EYEBROW, _ENT_TITLE, _ENT_BAR, _ENT_FOOTER = 2, 4, 8, 10
_ENT_POINT0, _ENT_POINT_STEP, _ENT_POINT_DUR = 6, 2, 8
_POP_DUR, _SETTLE_DUR = 8, 5
# 卡尾出场错峰（相对 out_at 的偏移）：eyebrow/footer 先走，标题/条/要点/卡片随后
_EXIT_DUR = 5
_EXIT_OFFSETS = {"eyebrow": 0, "footer": 0, "title": 1, "bar": 1,
                 "point": 2, "sp": 2, "band": 3, "outline": 0, "shot": 1}
_CUE_OUT_DUR = 4
# 镜头切换动画窗（帧）：入场横移 / 退场淡出（openspec card-shots）
_SHOT_ENT_DUR, _SHOT_EXIT_DUR = 8, 6


def _esc(text) -> str:
    if text is None:
        return ""
    s = str(text)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _style(op: float, ty: float, sc: float, extra: str = "") -> str:
    """运动量 → style 属性值；全部终态且无附加时返回空串（不输出属性）。"""
    settled = op >= 0.999 and abs(ty) < 0.02 and abs(sc - 1.0) < 0.0015 and not extra
    if settled:
        return ""
    parts = [f"opacity:{max(0.0, op):.3f}",
             f"transform:translateY({ty:.2f}px) scale({sc:.4f})"]
    if extra:
        parts.append(extra.rstrip(";"))
    return ";".join(parts)


def _compose(base: tuple, ex: tuple | None) -> tuple:
    """入场/换态运动量与出场运动量合成（出场乘法叠加透明度、加法叠加位移）。"""
    if ex is None:
        return base
    op, ty, sc = base
    return op * ex[0], ty + ex[1], sc * ex[2]


def _exit(frame: int, out_at, key: str, extra_shift: int = 0,
          dy: float = -26.0) -> tuple | None:
    """按元素错峰偏移取出场运动量；out_at 缺失（旧调用）→ None。"""
    if out_at is None:
        return None
    return exit_tuple(frame - (int(out_at) + _EXIT_OFFSETS[key] + extra_shift),
                      _EXIT_DUR, dy=dy)


def _point_style(frame: int, idx: int, active_idx: int, births: list[int],
                 out_at=None) -> str:
    """单要点合成运动：入场 stagger + active 弹入（back 过冲）+ done 交叉过渡 + 卡尾出场。"""
    op, ty, sc = enter_tuple(frame - (_ENT_POINT0 + _ENT_POINT_STEP * idx),
                             _ENT_POINT_DUR, dy=20.0)
    extra = ""
    pb = births[idx] if idx < len(births) else None
    if idx == active_idx and pb is not None:
        age = frame - pb
        if 0 <= age < _POP_DUR:
            # 弹入只做缩放过冲 + 辉光（要点本已可见，不重置 opacity）
            sc *= enter_tuple(age, _POP_DUR, scale_from=0.94,
                              ease=ease_out_back)[2]
            g = glow_mult(age, 6, 0.8)
            if g is not None:
                m = 1.0 + g
                extra = (f"box-shadow:0 0 {40 * m:.0f}px rgba(34,211,238,{min(1.0, 0.7 * m):.2f}),"
                         f"inset 0 0 20px rgba(34,211,238,{min(1.0, 0.1 * m):.2f})")
    elif idx < active_idx and pb is not None:
        nb = births[idx + 1] if idx + 1 < len(births) else None
        if nb is not None:
            dip = settle_dip(frame - nb, _SETTLE_DUR, depth=0.15)
            if dip is not None:
                op = min(op, dip)
                sc *= 0.97 + 0.03 * dip
    op, ty, sc = _compose((op, ty, sc), _exit(frame, out_at, "point"))
    return _style(op, ty, sc, extra)


def _sp_style(frame: int, idx: int, active_idx: int, births: list[int],
              out_at=None) -> str:
    """知识卡运动：active 卡在要点出生帧+2 弹入（spring），前一卡交叉退场 + 卡尾出场。"""
    pb = births[idx] if idx < len(births) else None
    if idx == active_idx and pb is not None:
        op, ty, sc = enter_tuple(frame - (pb + 2), 10, dy=44.0,
                                 scale_from=0.92, ease=ease_out_back)
        op, ty, sc = _compose((op, ty, sc), _exit(frame, out_at, "sp", dy=-34.0))
        return _style(op, ty, sc)
    if idx < active_idx:
        nb = births[idx + 1] if idx + 1 < len(births) else None
        if nb is not None:
            dip = settle_dip(frame - nb, _SETTLE_DUR, depth=0.2)
            if dip is not None:
                op, ty, sc = _compose((min(1.0, dip), -6.0 * (1.0 - dip), 1.0),
                                      _exit(frame, out_at, "sp", dy=-34.0))
                return _style(op, ty, sc)
    return ""


def _shot_layer_style(frame: int, si: int, shot_idx: int, shot_birth,
                      out_at) -> str | None:
    """镜头层运动量：当前镜头入场（横移 + ease-out）/ 前一镜头交叉退场 + 卡尾出场。

    None = 该层此刻完全不渲染（HTML 等值复用优化在动画窗外生效）。
    """
    if shot_idx < 0 or si > shot_idx:
        return None
    birth = int(shot_birth if shot_birth is not None else 0)
    if si == shot_idx:
        age = frame - birth
        if age < 0:
            return None
        ex = _exit(frame, out_at, "shot", dy=-30.0)
        if age >= _SHOT_ENT_DUR and ex is None:
            return ""                       # 终态：无属性（与 settle 约定一致）
        e = ease_out_cubic(min(1.0, age / _SHOT_ENT_DUR))
        op, dx, dy = e, 56.0 * (1.0 - e), 0.0
        if ex is not None:
            op, dy = op * ex[0], ex[1]
        if op >= 0.999 and abs(dx) < 0.02 and abs(dy) < 0.02:
            return ""
        return f"opacity:{op:.3f};transform:translateX({dx:.2f}px) translateY({dy:.2f}px)"
    if si == shot_idx - 1:                  # 刚被替换：短淡出横移
        age = frame - birth
        if age >= _SHOT_EXIT_DUR:
            return None
        e = ease_out_cubic(min(1.0, age / _SHOT_EXIT_DUR))
        if e >= 0.999:
            return None
        return f"opacity:{1.0 - e:.3f};transform:translateX({-36.0 * e:.2f}px)"
    return None


def _shot_hl_lines(shot: dict, state: dict) -> list[int]:
    """当前高亮行：hl_steps 讲到哪行亮哪行（帧外静态 hl 兜底）。"""
    hl = None
    for t, line in (shot.get("hl_steps") or []):
        if state.get("shot_t_ms", 0) >= float(t) * 1000.0:
            hl = line
    if hl is None:
        hl = shot.get("hl")
    if hl is None:
        return []
    return [hl] if isinstance(hl, int) else [int(x) for x in hl]


def _shot_html(shot: dict, card_flow, state: dict) -> str:
    kind = shot.get("kind", "code")
    data = shot.get("data") or {}
    if kind == "flow":
        from . import flowchart
        return flowchart.render_flow(card_flow or {}, state)
    if kind == "stat":
        return ('<div class="shot-stat">'
                f'<div class="big">{_esc(data.get("big", ""))}</div>'
                f'<div class="label">{_esc(data.get("label", ""))}</div>'
                f'<div class="sub">{_esc(data.get("sub", ""))}</div></div>')
    if kind == "table":
        head = "".join(f"<th>{_esc(h)}</th>" for h in data.get("head", []))
        rows = ""
        for r in data.get("rows", []):
            cls = ' class="hlrow"' if r and r[0] == "*" else ""
            cells = r[1:] if r and r[0] == "*" else r
            rows += f'<tr{cls}>' + "".join(f"<td>{_esc(c)}</td>" for c in cells) + "</tr>"
        return f'<div class="shot-table"><table><tr>{head}</tr>{rows}</table></div>'
    if kind == "quote":
        return ('<div class="shot-quote">'
                '<div class="mark">\u201c</div>'
                f'<div class="qtext">{_esc(data.get("text", ""))}</div>'
                f'<div class="qsrc">— {_esc(data.get("source", ""))}</div></div>')
    if kind == "illus":
        # openspec video-gen-assets：生成式插画镜头（图片 base64 内嵌，规避
        # set_content 场景 file:// 子资源拦截；有界入场后静止，PNG 复用优化保持）
        import base64 as _b64
        from pathlib import Path as _Path
        src = data.get("src", "")
        img_html = '<div class="illus-empty">NO ASSET</div>'
        if str(src).startswith("data:"):
            img_html = f'<img class="illus-img" alt="" src="{src}"/>'
        else:
            try:
                img_p = _Path(src)
                if not img_p.is_absolute():
                    # 相对路径按项目根解析——不能走 __file__（skills 是 symlink，
                    # 向上找不到项目根），复用 config._find_project_root 的结论
                    from .config import PROJECT_ROOT as _proj_root
                    img_p = _proj_root / src
                if img_p.exists():
                    enc = _b64.b64encode(img_p.read_bytes()).decode()
                    img_html = (f'<img class="illus-img" alt="" '
                                f'src="data:image/png;base64,{enc}"/>')
            except OSError:
                pass
        cap = data.get("cap", "")
        frame_i = int(state.get("frame", 10 ** 6))
        birth_i = int(state.get("shot_birth") or 0)
        age_i = frame_i - (birth_i + 8)   # 层浮入结束后进入镜头运动
        img_st = ""
        if 0 <= age_i < 10:
            ease = ease_out_cubic(age_i / 10.0)
            scale = 1.12 - 0.05 * ease
            img_st = f' style="transform:scale({scale:.4f})"'
        elif 10 <= age_i < 46:
            # 有界慢推运镜：26 帧内 scale 1.07→1.10 + 左上向漂移 ≤14px，
            # 窗口外静止（帧驱动铁律/PNG 复用保持）
            pan_t = ease_in_out_sine(min((age_i - 10) / 26.0, 1.0))
            scale = 1.07 + 0.03 * pan_t
            tx, ty = -14.0 * pan_t, 8.0 * pan_t
            img_st = (f' style="transform:translate({tx:.2f}px,{ty:.2f}px)'
                      f' scale({scale:.4f})"')
        cap_html = f'<div class="illus-cap">{_esc(cap)}</div>' if cap else ""
        return (f'<div class="shot-illus">'
                f'<div class="illus-wrap"{img_st}>{img_html}</div>'
                f'{cap_html}</div>')
    # 带窗口 chrome 的素材（code / tree / term）
    fname = _esc(data.get("title", ""))
    tag = _esc({"code": "源码", "tree": "结构", "term": "终端"}.get(kind, kind))
    body = _shot_body_html(kind, data, shot, state)
    return (f'<div class="shot-win"><div class="shot-titlebar">'
            '<div class="shot-dot" style="background:#f87171"></div>'
            '<div class="shot-dot" style="background:#fbbf24"></div>'
            '<div class="shot-dot" style="background:#34d399"></div>'
            f'<div class="shot-fname">{fname}</div>'
            f'<div class="shot-tag">{tag}</div></div>'
            f'<div class="shot-body">{body}</div></div>')


def _shot_body_html(kind: str, data: dict, shot: dict, state: dict) -> str:
    frame = int(state.get("frame", 10**6))
    birth = int(state.get("shot_birth") or 0)
    if kind == "code":
        lines = data.get("lines", [])
        hls = _shot_hl_lines(shot, state)
        out = []
        for i, ln in enumerate(lines):
            cls = "cl"
            if i in hls:
                cls += " hl"
            elif str(ln).strip().startswith("#"):
                cls += " cmt"
            # 行级 stagger 出生（2 帧/行），终态空属性 → 静止段 HTML 稳定
            age = frame - (birth + 2 + 2 * i)
            st = ""
            if 0 <= age < 6:
                e = ease_out_cubic(age / 6.0)
                st = (f"opacity:{e:.3f};" if e < 0.999 else "") + \
                     (f"transform:translateY({12.0 * (1.0 - e):.2f}px);" if e < 0.999 else "")
            st_attr = f' style="{st.rstrip(";")}"' if st else ""
            out.append(f'<div class="{cls}"{st_attr}><span class="ln">{i + 1}</span>'
                       f'<span>{_esc(ln)}</span></div>')
        return "".join(out)
    if kind == "tree":
        out = []
        for i, item in enumerate(data.get("items", [])):
            depth, typ, name = 0, "file", item
            if isinstance(item, list):
                typ, name = item[0], item[1]
                depth = item[2] if len(item) > 2 else 0
            elif isinstance(item, str) and item.startswith("**"):
                typ = "note"
                name = item.strip("* ")
            age = frame - (birth + 2 + 2 * i)
            st = ""
            if 0 <= age < 6:
                e = ease_out_cubic(age / 6.0)
                if e < 0.999:
                    st = f"opacity:{e:.3f};transform:translateX({-14.0 * (1.0 - e):.2f}px)"
            st_attr = f' style="{st}"' if st else ""
            if typ == "note":
                out.append(f'<div class="tl"{st_attr}><span class="dim">{_esc(name)}</span></div>')
            else:
                glyph, cls = ("\u25b8 ", "dir") if typ == "dir" else ("\u25aa ", "")
                marked = f'<span class="{cls}">{_esc(glyph + name)}</span>' if cls else _esc(glyph + name)
                out.append(f'<div class="tl"{st_attr}>'
                           f'{"&nbsp;" * (4 * depth)}{marked}</div>')
        return "".join(out)
    if kind == "term":
        out = []
        for i, item in enumerate(data.get("lines", [])):
            if isinstance(item, str):
                text, cls = item, "out"
            else:
                text, cls = item.get("t", ""), item.get("c", "out")
            age = frame - (birth + 2 + 2 * i)
            st = ""
            if 0 <= age < 6:
                e = ease_out_cubic(age / 6.0)
                if e < 0.999:
                    st = f"opacity:{e:.3f}"
            st_attr = f' style="{st}"' if st else ""
            # 终端行带光标节奏：末行 out 尾随块光标（仅 cmd/ok 语义行）
            cursor = '<span style="color:#22d3ee">\u2588</span>' if i == len(data.get("lines", [])) - 1 and cls in ("cmd", "out") else ""
            out.append(f'<div class="tline {cls}"{st_attr}>{_esc(text)}{cursor}</div>')
        return "".join(out)
    return ""


def _bar_style(frame: int, births: list[int], active_idx: int,
               out_at=None) -> str:
    """标题条：卡起宽度生长 + 每次换拍辉光脉冲（主锚联动）+ 卡尾淡出上移。"""
    age = frame - _ENT_BAR
    if age < 0:
        return "width:0px"
    parts = []
    if age < 12:
        parts.append(f"width:{140 * ease_in_out_sine(age / 12):.1f}px")
    if active_idx >= 0:
        pb = births[active_idx] if active_idx < len(births) else None
        if pb is not None:
            g = glow_mult(frame - pb, 8, 0.9)
            if g is not None:
                m = 1.0 + g
                parts.append(
                    f"box-shadow:0 0 {30 * m:.0f}px rgba(34,211,238,1),"
                    f"0 0 {60 * m:.0f}px rgba(34,211,238,{min(1.0, 0.6 * m):.2f})")
    ex = _exit(frame, out_at, "bar", dy=-18.0)
    if ex is not None:
        parts.append(f"opacity:{ex[0]:.3f};transform:translateY({ex[1]:.2f}px)")
    return ";".join(parts)


def _progress_style(pct: float, frame: int, births: list[int]) -> str:
    """进度条：宽度保持时间连续；要点出生帧辉光跳档脉冲（联动）。"""
    pulse = ""
    for pb in births:
        g = glow_mult(frame - pb, 6, 0.9)
        if g is not None:
            m = 1.0 + g
            pulse = (f"box-shadow:0 0 {25 * m:.0f}px rgba(34,211,238,1),"
                     f"0 0 {50 * m:.0f}px rgba(34,211,238,{min(1.0, 0.6 * m):.2f})")
            break
    return f"width:{pct:.2f}%" + (f";{pulse}" if pulse else "")


def _band_state(frame: int, state_sub: str, cue_birth, cue_out,
                out_at) -> tuple[str, str, str]:
    """字幕带状态 → (文本, class, style)。三层合成：
    分句入场（cue_birth，上滑淡入）→ 分句退场（cue_out，加速上移淡出）
    → 卡尾出场（out_at+3，与其他元素错峰）。"""
    if state_sub:
        text = state_sub
        if cue_birth is not None:
            base = enter_tuple(frame - int(cue_birth), 4, dy=12.0)
        else:
            base = (1.0, 0.0, 1.0)
    elif cue_out:
        text, age = str(cue_out[0]), int(cue_out[1])
        base = exit_tuple(age, _CUE_OUT_DUR, dy=-14.0) or (0.0, -14.0, 1.0)
    else:
        return "", "subtitle empty", ""
    ex = _exit(frame, out_at, "band", dy=-16.0)
    op, ty, sc = _compose(base, ex)
    return text, "subtitle", _style(op, ty, sc)


_CSS = """* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { width: __W__px; height: __H__px; }
body {
  font-family: "Microsoft YaHei", "微软雅黑", "PingFang SC", sans-serif;
  background-color: #1e293b; color: #ffffff;        /* 中明度深蓝灰，不纯黑 */
  position: relative; overflow: hidden; -webkit-font-smoothing: antialiased;
}
/* 形象伴随层（左下角，2026-08-25）：-3° 微倾 + 双层影接地（v4 封面同款规范） */
.mascot {
  position: absolute; left: 48px; bottom: 36px; z-index: 40;
  pointer-events: none; transform-origin: 50% 90%;
  filter: drop-shadow(0 6px 10px rgba(0,0,0,0.55))
          drop-shadow(0 0 18px rgba(34,211,238,0.28));
}
.grid {
  position: absolute; inset: 0;
  background-image:
    linear-gradient(rgba(34,211,238,0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(34,211,238,0.08) 1px, transparent 1px);
  background-size: 64px 64px; pointer-events: none;
}
.glow {
  position: absolute; inset: 0;
  background:
    radial-gradient(circle at 0% 0%, rgba(34,211,238,0.25), transparent 34%),
    radial-gradient(circle at 100% 0%, rgba(34,211,238,0.22), transparent 32%),
    radial-gradient(circle at 50% 120%, rgba(34,211,238,0.20), transparent 40%);
  pointer-events: none;
}
.stage { position: relative; width: 100%; height: 100%;
  display: flex; flex-direction: column; padding: 50px 190px 40px 72px; z-index: 1; }
.eyebrow { font-size: 24px; color: #22d3ee; font-weight: 700; letter-spacing: 6px;
  margin-bottom: 14px; text-shadow: 0 0 20px rgba(34,211,238,0.8), 0 0 40px rgba(34,211,238,0.4); }
.title { font-size: 72px; font-weight: 800; color: #ffffff; line-height: 1.24;
  letter-spacing: 2px; text-shadow: 0 0 30px rgba(34,211,238,0.6), 0 4px 20px rgba(0,0,0,0.8); word-break: break-word; }
.title-bar { width: 140px; height: 6px; margin-top: 20px; background: #22d3ee;
  box-shadow: 0 0 30px rgba(34,211,238,1), 0 0 60px rgba(34,211,238,0.6); border-radius: 3px; }
.main-row { flex: 1; min-height: 0; display: flex; flex-direction: row; gap: 44px; }
/* 左栏收窄为紧凑栏（openspec card-shots 2026-08-26）：标题+要点垂直居中，
   宽区让给右侧镜头舞台，消灭要点下方大空洞 */
.left-col { width: 40%; display: flex; flex-direction: column; min-width: 0; }
.right-col { flex: 1; min-width: 0; display: flex; flex-direction: column;
  justify-content: flex-end; gap: 14px; padding: 6px 0; position: relative; }
.points { flex: 1; display: flex; flex-direction: column; justify-content: center; gap: 22px; padding-top: 6px; }
.point { position: relative; font-size: 48px; line-height: 1.4; padding: 12px 18px 12px 28px;
  border-radius: 8px; color: rgba(255,255,255,0.55); }
/* 未讲弱化态 2026-08-25 升档（openspec video-color-retention）：旧 #475569@0.5 ≈1.9:1
   户外强光不可见 → 白@0.55 ≈5.5:1，与 done 白(14.6:1) 保留 ≥2:1 主次比 */
.point.done { color: #ffffff; opacity: 1; }
.point.done::before { content: ""; position: absolute; left: 0; top: 14px; bottom: 14px;
  width: 4px; background: #22d3ee; box-shadow: 0 0 20px rgba(34,211,238,0.9), 0 0 40px rgba(34,211,238,0.5); border-radius: 2px; }
.point.active { color: #22d3ee; opacity: 1; font-size: 56px; font-weight: 700;
  background: rgba(34,211,238,0.12); box-shadow: 0 0 40px rgba(34,211,238,0.7), inset 0 0 20px rgba(34,211,238,0.1);
  border: 1px solid rgba(34,211,238,0.5); text-shadow: 0 0 15px rgba(34,211,238,0.6); }
.sp-item { position: relative; border-radius: 12px; word-break: break-word; }
.sp-item.done { font-size: 28px; line-height: 1.4; color: rgba(203,213,225,0.8);
  padding: 8px 16px; background: rgba(15,23,42,0.5); border-left: 3px solid rgba(34,211,238,0.35); }
.sp-item.active { background: rgba(15,23,42,0.85); border: 1px solid rgba(34,211,238,0.55);
  border-radius: 16px; padding: 34px 32px 32px; min-height: 280px;
  box-shadow: 0 0 60px rgba(34,211,238,0.3), inset 0 0 80px rgba(34,211,238,0.08); }
.sp-item.active::before { content: "知识卡片"; position: absolute; top: -16px; left: 28px;
  background: #22d3ee; color: #0a0e1a; font-size: 24px; font-weight: 700;
  padding: 5px 18px; border-radius: 8px; letter-spacing: 3px; box-shadow: 0 0 25px rgba(34,211,238,0.8), 0 0 50px rgba(34,211,238,0.4); }
.sp-item.active .sp-text { font-size: 48px; line-height: 1.45; color: #ffffff; font-weight: 500;
  text-shadow: 0 0 10px rgba(34,211,238,0.3); }
.sp-placeholder { display: flex; align-items: center; justify-content: center; height: 100%;
  color: rgba(148,163,184,0.75); font-size: 26px; letter-spacing: 6px; }
/* ---- 卡内镜头舞台（openspec card-shots 2026-08-26）：右栏宽区按口播节拍轮换素材 ---- */
.shot { position: absolute; inset: 0; display: flex; flex-direction: column; }
.shot-win { flex: 1; min-height: 0; display: flex; flex-direction: column; border-radius: 16px;
  background: rgba(10,14,26,0.92); border: 1px solid rgba(34,211,238,0.4);
  box-shadow: 0 0 60px rgba(34,211,238,0.18), inset 0 0 40px rgba(34,211,238,0.05);
  overflow: hidden; }
.shot-titlebar { display: flex; align-items: center; gap: 10px; padding: 14px 22px;
  background: rgba(30,41,59,0.9); border-bottom: 1px solid rgba(34,211,238,0.3); flex: none; }
.shot-dot { width: 16px; height: 16px; border-radius: 50%; flex: none; }
.shot-fname { font-size: 24px; color: #94a3b8; font-family: ui-monospace, Consolas, monospace;
  margin-left: 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.shot-tag { margin-left: auto; font-size: 20px; color: #0a0e1a; background: #22d3ee;
  padding: 3px 14px; border-radius: 6px; font-weight: 700; letter-spacing: 2px; flex: none; }
.shot-body { flex: 1; min-height: 0; padding: 26px 34px; overflow: hidden;
  font-family: ui-monospace, Consolas, monospace; display: flex; flex-direction: column; justify-content: center; }
.shot-body .cl { font-size: 27px; line-height: 1.62; color: #cbd5e1; white-space: pre;
  display: flex; gap: 18px; }
.shot-body .cl .ln { color: #475569; width: 40px; text-align: right; flex: none; user-select: none; }
.shot-body .cl.hl { color: #ffffff; background: rgba(34,211,238,0.14);
  border-left: 4px solid #22d3ee; padding-left: 10px; margin-left: -14px;
  text-shadow: 0 0 12px rgba(34,211,238,0.5); }
.shot-body .cl.cmt { color: #64748b; }
.shot-body .tl { font-size: 28px; line-height: 1.75; color: #e2e8f0; white-space: pre; }
.shot-body .tl .dir { color: #22d3ee; font-weight: 700; }
.shot-body .tl .dim { color: #64748b; }
.shot-body .tline { font-size: 27px; line-height: 1.7; white-space: pre-wrap; }
.shot-body .tline.cmd { color: #22d3ee; }
.shot-body .tline.out { color: #cbd5e1; }
.shot-body .tline.err { color: #f87171; }
.shot-body .tline.ok { color: #4ade80; }
.shot-body .tline.dim { color: #64748b; }
.shot-stat { flex: 1; display: flex; flex-direction: column; align-items: center;
  justify-content: center; gap: 18px; }
.shot-stat .big { font-size: 128px; font-weight: 800; color: #22d3ee; line-height: 1;
  text-shadow: 0 0 40px rgba(34,211,238,0.6), 0 0 80px rgba(34,211,238,0.3);
  font-family: ui-monospace, Consolas, monospace; }
.shot-stat .label { font-size: 34px; color: #ffffff; font-weight: 600; }
.shot-stat .sub { font-size: 26px; color: #94a3b8; }
.shot-table { flex: 1; display: flex; flex-direction: column; justify-content: center; gap: 0;
  font-family: inherit; }
.shot-table table { width: 100%; border-collapse: collapse; }
.shot-table th { font-size: 30px; color: #22d3ee; font-weight: 700; padding: 18px 22px;
  border-bottom: 2px solid rgba(34,211,238,0.5); text-align: left; }
.shot-table td { font-size: 29px; color: #e2e8f0; padding: 18px 22px;
  border-bottom: 1px solid rgba(34,211,238,0.2); }
.shot-table tr.hlrow td { color: #ffffff; background: rgba(34,211,238,0.12);
  font-weight: 600; }
.shot-quote { flex: 1; display: flex; flex-direction: column; justify-content: center;
  gap: 26px; padding: 0 28px; }
.shot-quote .mark { font-size: 110px; color: rgba(34,211,238,0.55); line-height: 0.5;
  font-family: Georgia, serif; }
.shot-quote .qtext { font-size: 42px; line-height: 1.55; color: #ffffff; font-weight: 600;
  text-shadow: 0 0 20px rgba(34,211,238,0.3); }
.shot-quote .qsrc { font-size: 24px; color: #64748b; font-family: ui-monospace, Consolas, monospace; }
/* illus 镜头（openspec video-gen-assets）：生成式插画 + 说明行 */
.shot-illus { flex: 1; min-height: 0; display: flex; flex-direction: column;
  border-radius: 16px; background: rgba(10,14,26,0.92);
  border: 1px solid rgba(34,211,238,0.4);
  box-shadow: 0 0 60px rgba(34,211,238,0.18), inset 0 0 40px rgba(34,211,238,0.05);
  overflow: hidden; padding: 18px; gap: 12px; }
.illus-wrap { flex: 1; min-height: 0; border-radius: 10px; overflow: hidden;
  display: flex; align-items: center; justify-content: center; }
.illus-img { width: 100%; height: 100%; object-fit: cover; transform-origin: center; }
.illus-cap { flex: none; font-size: 24px; color: #94a3b8; text-align: center;
  letter-spacing: 2px; padding: 2px 6px 4px; }
.illus-empty { width: 100%; height: 100%; display: flex; align-items: center;
  justify-content: center; color: rgba(148,163,184,0.5); font-size: 26px;
  letter-spacing: 6px; border: 2px dashed rgba(248,113,113,0.5); border-radius: 10px; }
.footer-bar { margin-top: 10px; font-size: 24px; font-style: italic; color: #22d3ee;
  text-align: center; opacity: 0.9; height: 32px; line-height: 32px; overflow: hidden;
  white-space: nowrap; text-overflow: ellipsis; text-shadow: 0 0 20px rgba(34,211,238,0.7), 0 0 40px rgba(34,211,238,0.3); }
.subtitle-band { height: 112px; padding: 0 150px 0 36px; margin-top: 14px;
  background: rgba(15,23,42,0.92); border: 1px solid rgba(34,211,238,0.4);
  border-radius: 12px; display: flex; align-items: center; justify-content: center; overflow: hidden;
  box-shadow: 0 0 30px rgba(34,211,238,0.15), inset 0 0 20px rgba(34,211,238,0.05); }
.subtitle { font-size: 48px; line-height: 1; color: #ffffff; text-align: center; max-width: 100%;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  text-shadow: 0 2px 4px rgba(0,0,0,0.95), 0 0 2px #000,
    -1px -1px 0 #000, 1px 1px 0 #000, -1px 1px 0 #000, 1px -1px 0 #000; }
.subtitle.empty { visibility: hidden; }
.progress-track { position: absolute; left: 0; right: 0; bottom: 0; height: 6px;
  background: rgba(34,211,238,0.12); }
.progress-fill { height: 100%; background: linear-gradient(90deg, #06b6d4, #22d3ee);
  box-shadow: 0 0 25px rgba(34,211,238,1), 0 0 50px rgba(34,211,238,0.6); }
/* 封面：副标题 + 大标题 + outline 论点列表 + 字幕带 + 进度 */
.stage.cover { justify-content: space-between; padding: 64px 190px 40px 72px; }
.stage.cover .main-row { display: none; }
.cover-head { text-align: center; }
.stage.cover .eyebrow { letter-spacing: 10px; }
.stage.cover .title { font-size: 84px; }
.stage.cover .title-bar { margin: 22px auto 0; }
.outline-wrap { flex: 1; display: flex; align-items: center; justify-content: center; }
.outline { list-style: none; display: grid; grid-template-columns: repeat(5, 1fr);
  gap: 22px; width: 100%; max-width: 1720px; }
.outline li { font-size: 36px; line-height: 1.3; color: #e2e8f0; font-weight: 600;
  padding: 26px 16px; text-align: center;
  background: rgba(34,211,238,0.12); border: 1px solid rgba(34,211,238,0.45);
  border-radius: 14px; box-shadow: 0 0 30px rgba(34,211,238,0.2), inset 0 0 15px rgba(34,211,238,0.05); }
.outline li .num { display: block; font-size: 48px; color: #22d3ee; font-weight: 800;
  margin-bottom: 10px; text-shadow: 0 0 20px rgba(34,211,238,0.8), 0 0 40px rgba(34,211,238,0.4); }"""


def render_frame(card: dict, state: dict, width: int = 1920, height: int = 1080) -> str:
    """渲染一帧横屏 HTML。

    card:  {"title", "subtitle"(副标题), "points":[], "sub_points":[], "footer",
            "flow"(可选 {"nodes":[...], "edges":[[from,to],...]}，与 sub_points 互斥),
            "is_cover", "outline":[str](仅封面：论点列表)}
    state: {"active_idx", "subtitle"(字幕,已去标点), "progress", "frame",
            "point_births"(要点出生帧), "cue_birth"(当前分句出生帧)}
           —— 缺 frame/births 时按已 settle 处理，输出与旧静态渲染一致（兼容）

    type=="tool" 的卡片分发到 screencast 模块（屏录感工具窗口渲染）；
    type=="tutorial" 分发到 tutorial 模块（亮色教程模板：全量展示 + active 高亮）。
    """
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
    title = card.get("title", "") or ""
    card_sub = card.get("subtitle", "") or ""
    points_raw = card.get("points") or []
    sub_points = card.get("sub_points") or []
    flow = card.get("flow")
    footer = card.get("footer", "") or ""
    outline = card.get("outline") or []
    is_cover = bool(card.get("is_cover")) or len(points_raw) == 0

    active_idx = int(state.get("active_idx", -1))
    state_sub = state.get("subtitle", "") or ""
    progress = float(state.get("progress", 0.0))
    pct = max(0.0, min(1.0, progress)) * 100.0
    frame = int(state.get("frame", 10**6))            # 缺省 = 全部 settle
    births = [int(b) for b in (state.get("point_births") or [])]
    cue_birth = state.get("cue_birth")
    cue_out = state.get("cue_out")
    out_at = state.get("out_at")
    css = _CSS.replace("__W__", str(width)).replace("__H__", str(height))

    # 卡起入场（eyebrow 下滑 / 标题上浮）+ 卡尾错峰出场
    eyebrow = ""
    if card_sub:
        st = _style(*_compose(enter_tuple(frame - _ENT_EYEBROW, 6, dy=-18.0),
                              _exit(frame, out_at, "eyebrow", dy=-20.0)))
        eyebrow = f'<div class="eyebrow"{_attr(st)}>{_esc(card_sub)}</div>'
    title_st = _style(*_compose(enter_tuple(frame - _ENT_TITLE, 8, dy=26.0),
                                _exit(frame, out_at, "title")))
    bar_st = _bar_style(frame, births, active_idx, out_at)
    # 字幕带三层合成：分句入场（cue_birth）→ 分句退场（cue_out，加速上移）
    # → 卡尾出场（out_at+3）
    band_text, band_cls, band_st = _band_state(
        frame, state_sub, cue_birth, cue_out, out_at)
    band = (f'<div class="subtitle-band"><div class="{band_cls}"'
            f'{_attr(band_st)}>{_esc(band_text)}</div></div>')
    prog = (f'<div class="progress-track"><div class="progress-fill" '
            f'style="{_progress_style(pct, frame, births)}"></div></div>')

    if is_cover:
        if outline:
            ol = ""
            for i, o in enumerate(outline):
                st = _style(*_compose(
                    enter_tuple(frame - int(10 + 2.5 * i), 9, dy=26.0,
                                scale_from=0.96, ease=ease_out_back),
                    _exit(frame, out_at, "outline", extra_shift=i, dy=-22.0)))
                ol += f'<li{_attr(st)}><span class="num">{i + 1:02d}</span>{_esc(o)}</li>'
            outline_block = f'<div class="outline-wrap"><ul class="outline">{ol}</ul></div>'
        else:
            outline_block = '<div class="outline-wrap"></div>'
        body = f"""<div class="stage cover">
  <div class="cover-head">
    {eyebrow}
    <div class="title"{_attr(title_st)}>{_esc(title)}</div>
    <div class="title-bar"{_attr(bar_st)}></div>
  </div>
  {outline_block}
  {band}
  {prog}
</div>"""
        return _doc(css, body, state)

    # 左栏要点（三态 + 入场 stagger / active 弹入 / done 交叉过渡 / 卡尾出场）
    point_items = []
    for idx, pt in enumerate(points_raw):
        cls = "point done" if idx < active_idx else ("point active" if idx == active_idx else "point")
        st = _point_style(frame, idx, active_idx, births, out_at)
        point_items.append(f'        <div class="{cls}"{_attr(st)}>{_esc(pt)}</div>')
    points_block = "\n".join(point_items)

    # 右栏：shots 镜头舞台优先（openspec card-shots：按口播节拍轮换素材），
    # 旧 deck 回退 flow 流程图 / sub_points 知识卡
    shots = [s for s in (card.get("shots") or []) if not is_cover]
    shot_idx = int(state.get("shot_idx", -1))
    shot_birth = state.get("shot_birth")
    if shots:
        layers = []
        for si, sh in enumerate(shots):
            st = _shot_layer_style(frame, si, shot_idx, shot_birth, out_at)
            if st is None:
                continue
            layers.append(f'<div class="shot"{_attr(st)}>'
                          f'{_shot_html(sh, flow, state)}</div>')
        right_block = "\n".join(layers)
    elif flow:
        from . import flowchart
        right_block = flowchart.render_flow(flow, state)
    else:
        sp_items = []
        for idx, sp in enumerate(sub_points):
            if idx > active_idx:
                continue
            st = _sp_style(frame, idx, active_idx, births, out_at)
            if idx == active_idx:
                sp_items.append(
                    f'      <div class="sp-item active"{_attr(st)}><div class="sp-text">{_esc(sp)}</div></div>')
            else:
                sp_items.append(f'      <div class="sp-item done"{_attr(st)}>{_esc(sp)}</div>')
        right_block = "\n".join(sp_items) if sp_items else '<div class="sp-placeholder">讲解中…</div>'

    footer_st = _style(*_compose(enter_tuple(frame - _ENT_FOOTER, 6, dy=10.0),
                                 _exit(frame, out_at, "footer", dy=-16.0)))
    footer_block = (f'<div class="footer-bar"{_attr(footer_st)}>{_esc(footer)}</div>'
                    if footer else "")

    body = f"""<div class="stage">
  <div class="main-row">
    <div class="left-col">
      {eyebrow}
      <div class="title"{_attr(title_st)}>{_esc(title)}</div>
      <div class="title-bar"{_attr(bar_st)}></div>
      <div class="points">
{points_block}
      </div>
    </div>
    <div class="right-col">
{right_block}
    </div>
  </div>
  {footer_block}
  {band}
  {prog}
</div>"""
    return _doc(css, body, state)


def _attr(style_value: str) -> str:
    """style 值 → 属性片段；空串省略（HTML 相等性 → PNG 复用优化保持）。"""
    return f' style="{style_value}"' if style_value else ""


def _doc(css: str, body: str, state: dict | None = None) -> str:
    # 科幻风粒子背景（SVG 星尘点阵）
    particles = """
    <svg style="position:absolute;inset:0;width:100%;height:100%;pointer-events:none;opacity:0.4" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="star"><stop offset="0%" stop-color="#22d3ee" stop-opacity="0.8"/><stop offset="100%" stop-color="#22d3ee" stop-opacity="0"/></radialGradient>
      </defs>
      <circle cx="150" cy="200" r="2" fill="url(#star)"/><circle cx="450" cy="120" r="1.5" fill="url(#star)"/>
      <circle cx="780" cy="340" r="2.5" fill="url(#star)"/><circle cx="1200" cy="180" r="1.8" fill="url(#star)"/>
      <circle cx="1500" cy="450" r="2.2" fill="url(#star)"/><circle cx="300" cy="700" r="1.6" fill="url(#star)"/>
      <circle cx="900" cy="800" r="2" fill="url(#star)"/><circle cx="1600" cy="750" r="1.4" fill="url(#star)"/>
      <circle cx="600" cy="500" r="1.8" fill="url(#star)"/><circle cx="1100" cy="600" r="2.3" fill="url(#star)"/>
      <circle cx="200" cy="900" r="1.5" fill="url(#star)"/><circle cx="1400" cy="250" r="2" fill="url(#star)"/>
    </svg>"""

    # 扫描线效果（水平扫描线 overlay）
    scanlines = """
    <div style="position:absolute;inset:0;pointer-events:none;opacity:0.08;
      background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(34,211,238,0.15) 2px,rgba(34,211,238,0.15) 4px);
      z-index:9999;"></div>"""

    # HUD 边角装饰（四角发光边框）
    hud_corners = """
    <div style="position:absolute;top:20px;left:20px;width:60px;height:60px;border-left:3px solid #22d3ee;border-top:3px solid #22d3ee;box-shadow:0 0 20px rgba(34,211,238,0.6);pointer-events:none;z-index:10;"></div>
    <div style="position:absolute;top:20px;right:20px;width:60px;height:60px;border-right:3px solid #22d3ee;border-top:3px solid #22d3ee;box-shadow:0 0 20px rgba(34,211,238,0.6);pointer-events:none;z-index:10;"></div>
    <div style="position:absolute;bottom:20px;left:20px;width:60px;height:60px;border-left:3px solid #22d3ee;border-bottom:3px solid #22d3ee;box-shadow:0 0 20px rgba(34,211,238,0.6);pointer-events:none;z-index:10;"></div>
    <div style="position:absolute;bottom:20px;right:20px;width:60px;height:60px;border-right:3px solid #22d3ee;border-bottom:3px solid #22d3ee;box-shadow:0 0 20px rgba(34,211,238,0.6);pointer-events:none;z-index:10;"></div>"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>courseware frame</title>
<style>
{css}
</style>
</head>
<body>
{particles}
{scanlines}
{hud_corners}
{_mascot_html(state or {})}
{body}
</body>
</html>"""


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
    样式全内联——tool/tutorial 卡走各自模块 CSS，外部类不保证在场。"""
    if not _MASCOT_SVG_TPL:
        return ""
    import math
    frame = state.get("frame")
    cue_birth = state.get("cue_birth")
    sub = state.get("subtitle") or ""
    talking = isinstance(frame, int) and isinstance(cue_birth, int)
    mood = _infer_mood(sub) or "smile"

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
        f'<div style="height:{_MASCOT_H}px;width:{int(_MASCOT_H * 320 / 470)}px;overflow:visible;">{svg}</div></div>'
    )


if __name__ == "__main__":
    import json
    from pathlib import Path
    from playwright.sync_api import sync_playwright

    root = Path(__file__).resolve().parents[2]
    from config import OUTPUT_ROOT
    deck = json.load(open(OUTPUT_ROOT / "deck" / "ai-dev-claude-code-power-user" / "deck.json", encoding="utf-8"))
    out_dir = OUTPUT_ROOT / "build"; out_dir.mkdir(parents=True, exist_ok=True)
    cov = deck["cards"][0]
    cover_card = {"title": cov.get("hook", "").replace("\n", " "), "subtitle": cov.get("subtitle", ""),
                  "points": [], "sub_points": [], "footer": "", "is_cover": True,
                  "outline": ["命令 · 纪律边界", "Skill · 固化经验", "Subagent · 并行指挥",
                              "打断 · 30秒纠偏", "Workflow · 编排乐谱"]}
    raw = deck["cards"][3]
    ins_card = {"title": raw["title"], "subtitle": raw.get("label", ""), "points": raw["points"],
                "sub_points": raw["sub_points"], "footer": raw.get("footer", ""), "is_cover": False}
    cases = [("cover", cover_card, {"active_idx": -1, "subtitle": "差距不在提示词 在五个习惯", "progress": 0.05}),
             ("ins", ins_card, {"active_idx": 1, "subtitle": "往上一层 是命令", "progress": 0.4})]
    with sync_playwright() as pw:
        b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 1920, "height": 1080})
        for name, c, st in cases:
            pg.set_content(render_frame(c, st)); pg.wait_for_timeout(140)
            shot = out_dir / f"_hw3_{name}.png"; page.screenshot = pg.screenshot
            pg.screenshot(path=str(shot)); print(f"[{name}] {shot.stat().st_size} bytes")
        b.close()
    print("DONE")
