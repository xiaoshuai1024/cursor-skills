"""逐帧渲染：把一张卡的 timeline + 配音渲染成视频段。

流程（design.md D3）：timeline 算出每帧 state → courseware 渲染 HTML →
Playwright 截图 → FFmpeg 把帧序列 + 配音合成 seg.mp4。

状态由本模块按时间点计算，courseware 只画静态帧，无 JS 时序、无动画等待。
"""
from __future__ import annotations

import shutil
from pathlib import Path

from . import config as C
from . import render as R
from .courseware import render_frame

FPS = 24
HEAD_PAD = 0.3   # 配音前画面留白
TAIL_PAD = 0.3   # 配音后画面留白
EXIT_LEAD = 8    # 卡尾出场编舞提前量（帧）：末 8 帧内各元素错峰加速出场
CUE_OUT_DUR = 4  # 分句字幕退场窗口（帧）


def state_at(t_ms: float, timeline: dict, progress: float) -> dict:
    """该帧状态。t_ms = 配音内时间(毫秒)；progress = 整体进度 0~1。

    active_idx：取最后一个 start_ms <= t_ms 的要点（讲完后停留在最后一个要点高亮）；
    无要点(cover/cta)时为 -1。subtitle：t_ms 落在哪个 cue 就显示哪句，否则空。
    cue 带 no_subtitle=True（〖无字幕〗标记句）时该窗口字幕为空（有声无字幕）。
    """
    active_idx = -1
    for pt in timeline["point_timings"]:
        if pt["start_ms"] <= t_ms:
            active_idx = pt["point_idx"]
    subtitle = ""
    for cue in timeline["subtitle_cues"]:
        if cue["start_ms"] <= t_ms <= cue["end_ms"]:
            if not cue.get("no_subtitle"):
                subtitle = cue["text"]
            break
    return {"active_idx": active_idx, "subtitle": subtitle, "progress": progress}


def render_card_segment(
    card: dict,
    timeline: dict,
    audio_dur: float,
    audio_path: Path,
    seg_progress_start: float,
    total_dur: float,
    out_seg: Path,
    page,
) -> tuple[Path, float]:
    """渲染一张卡的视频段，返回 (seg.mp4 路径, seg 时长)。

    seg 时长 = audio_dur + HEAD_PAD + TAIL_PAD；配音延迟 HEAD_PAD 开始。
    page 为复用的 Playwright Page（由调用方传入，避免每帧重启浏览器）。
    """
    seg_dur = audio_dur + HEAD_PAD + TAIL_PAD
    n_frames = int(round(seg_dur * FPS))
    frames_dir = out_seg.parent / (out_seg.stem + "_frames")
    frames_dir.mkdir(parents=True, exist_ok=True)
    for old in frames_dir.glob("*.png"):           # 清理旧帧，避免残留帧数错乱
        old.unlink()

    total_ms = total_dur * 1000.0
    seg_start_ms = seg_progress_start * 1000.0

    # 动画出生帧（openspec courseware-motion-linkage）：要点亮起 / 分句 cue
    # 出现时刻 → 段内帧号。配音延迟 HEAD_PAD 开始，故出生帧含该偏移。
    def _birth_frame(start_ms: float) -> int:
        return max(0, int(round((HEAD_PAD * 1000.0 + start_ms) / 1000.0 * FPS)))

    point_births = [
        _birth_frame(pt["start_ms"]) for pt in timeline.get("point_timings", [])
    ]
    cue_births = [
        (cue["start_ms"], cue["end_ms"], _birth_frame(cue["start_ms"]),
         _birth_frame(cue["end_ms"]), cue["text"])
        for cue in timeline.get("subtitle_cues", [])
    ]
    out_at = n_frames - EXIT_LEAD            # 卡尾出场编舞锚（元素错峰出场）

    last_html = None
    for fi in range(n_frames):
        t_s = fi / FPS
        audio_t_ms = max(0.0, (t_s - HEAD_PAD) * 1000.0)
        progress = min(max((seg_start_ms + t_s * 1000.0) / total_ms, 0.0), 1.0)
        # 进度条量化到 0.25%（4px 一档）：相邻帧 HTML 完全相同，直接复用上一帧 PNG，
        # 避免每帧都走 Playwright 截图（动画窗口外的静止段仍享受该优化）。
        progress = round(progress * 400.0) / 400.0
        state = state_at(audio_t_ms, timeline, progress)
        state["frame"] = fi          # 帧号（模板内帧驱动动效用：呼吸/浮入等）
        state["point_births"] = point_births   # 每要点出生帧（主锚联动）
        state["out_at"] = out_at               # 卡尾出场编舞锚
        cue_birth = None
        cue_out = None              # (text, age)：最近结束的 cue 在退场窗口内
        for c_start, c_end, c_bf, c_ef, c_text in cue_births:
            if c_start <= audio_t_ms <= c_end:
                cue_birth = c_bf
            elif audio_t_ms > c_end and cue_birth is None and cue_out is None:
                age = fi - c_ef
                if 0 <= age < CUE_OUT_DUR:
                    cue_out = (c_text, age)
        state["cue_birth"] = cue_birth          # 当前分句 cue 出生帧（字幕上滑）
        state["cue_out"] = cue_out              # 分句字幕退场（加速上移淡出）
        # 卡内镜头（openspec card-shots）：shots[].from_s → 当前镜头索引 + 出生帧 + 卡内时间
        shot_idx, shot_birth = -1, None
        for si, sh in enumerate(card.get("shots") or []):
            bf = _birth_frame(float(sh.get("from_s", 0)) * 1000.0)
            if bf <= fi:
                shot_idx, shot_birth = si, bf
        state["shot_idx"] = shot_idx            # 当前镜头索引（-1 = 未开始）
        state["shot_birth"] = shot_birth        # 当前镜头出生帧（镜头层入场/行级 stagger 锚）
        state["shot_t_ms"] = audio_t_ms         # 卡内口播时间（hl_steps 讲到哪行亮哪行）
        html = render_frame(card, state, C.COURSEWARE_W, C.COURSEWARE_H)
        frame_png = frames_dir / f"frame_{fi:05d}.png"
        if last_html is not None and html == last_html:
            shutil.copyfile(frames_dir / f"frame_{fi-1:05d}.png", frame_png)
        else:
            page.set_content(html)
            page.screenshot(path=str(frame_png))
        last_html = html

    print(f"    渲染 {n_frames} 帧 → 合成段")

    # 帧序列 + 配音（延迟 HEAD_PAD、补齐 seg_dur）→ seg.mp4
    head_ms = int(round(HEAD_PAD * 1000))
    pattern = str((frames_dir / "frame_%05d.png").resolve().as_posix())
    af = (
        f"[1:a]adelay={head_ms}|{head_ms},apad,"
        f"atrim=0:{seg_dur:.3f},asetpts=N/SR/TB[a]"
    )
    cmd = [
        "ffmpeg", "-y", "-framerate", str(FPS), "-i", pattern,
        "-i", str(audio_path),
        "-filter_complex", af,
        "-map", "0:v", "-map", "[a]",
        "-r", str(FPS), "-shortest",
        *C.VIDEO_KWARGS, *C.AUDIO_KWARGS, str(out_seg),
    ]
    R._run(cmd)
    return out_seg, seg_dur
