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


def state_at(t_ms: float, timeline: dict, progress: float) -> dict:
    """该帧状态。t_ms = 配音内时间(毫秒)；progress = 整体进度 0~1。

    active_idx：取最后一个 start_ms <= t_ms 的要点（讲完后停留在最后一个要点高亮）；
    无要点(cover/cta)时为 -1。subtitle：t_ms 落在哪个 cue 就显示哪句，否则空。
    """
    active_idx = -1
    for pt in timeline["point_timings"]:
        if pt["start_ms"] <= t_ms:
            active_idx = pt["point_idx"]
    subtitle = ""
    for cue in timeline["subtitle_cues"]:
        if cue["start_ms"] <= t_ms <= cue["end_ms"]:
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

    last_html = None
    for fi in range(n_frames):
        t_s = fi / FPS
        audio_t_ms = max(0.0, (t_s - HEAD_PAD) * 1000.0)
        progress = min(max((seg_start_ms + t_s * 1000.0) / total_ms, 0.0), 1.0)
        # 进度条量化到 0.25%（4px 一档）：相邻帧 HTML 完全相同，直接复用上一帧 PNG，
        # 避免每帧都走 Playwright 截图（课件画面静态，截图是渲染耗时大头）。
        progress = round(progress * 400.0) / 400.0
        state = state_at(audio_t_ms, timeline, progress)
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
