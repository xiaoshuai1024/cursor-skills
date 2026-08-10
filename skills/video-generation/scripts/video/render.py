"""FFmpeg 渲染：单卡动效 → concat 拼接 → 烧录 ASS 字幕 + 混 BGM。"""
import subprocess
from pathlib import Path

from .config import (
    AUDIO_KWARGS, BGM_VOLUME, FADE, FPS, HEAD_PAD, OUT_H, OUT_SIZE, OUT_W,
    VIDEO_KWARGS,
)


def _run(cmd: list[str], cwd: str | None = None) -> None:
    r = subprocess.run(cmd, capture_output=True, encoding="utf-8", cwd=cwd)
    if r.returncode != 0:
        # 失败时打印命令和末尾日志，便于排查
        raise RuntimeError(
            f"FFmpeg 失败 (code={r.returncode}):\n"
            f"CMD: {' '.join(cmd[:6])} ...\n"
            f"STDERR:\n{r.stderr[-3000:]}"
        )


def build_segment(card: Path, audio: Path, dur: float, out: Path) -> None:
    """单张卡片 → 带动效和配音的视频段，精确 dur 秒。

    - zoompan d=1：输入帧与输出帧一一对应，zoom 跨帧累积不重置（Ken Burns 缓慢放大）
    - 音频 adelay 延迟 HEAD_PAD 毫秒开始，apad+atrim 补齐到 dur，保证段长精确
    """
    head_ms = int(round(HEAD_PAD * 1000))
    fade_out_st = max(dur - FADE, 0.0)
    vf = (
        f"[0:v]scale={OUT_W}:{OUT_H}:force_original_aspect_ratio=increase,"
        f"crop={OUT_W}:{OUT_H},setsar=1,"
        f"zoompan=z='min(zoom+0.0012,1.2)':d=1:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"s={OUT_SIZE}:fps={FPS},"
        f"fade=t=in:st=0:d={FADE},fade=t=out:st={fade_out_st}:d={FADE}[v]"
    )
    af = f"[1:a]adelay={head_ms}|{head_ms},apad,atrim=0:{dur},asetpts=N/SR/TB[a]"

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}", "-i", str(card),
        "-i", str(audio),
        "-filter_complex", f"{vf};{af}",
        "-map", "[v]", "-map", "[a]", "-shortest",
        *VIDEO_KWARGS, *AUDIO_KWARGS, str(out),
    ]
    _run(cmd)


def concat(segments: list[Path], out: Path) -> None:
    """concat demuxer 无损拼接（所有段编码参数一致，可直接 copy）。"""
    list_file = out.with_suffix(".list.txt")
    with open(list_file, "w", encoding="utf-8") as f:
        for s in segments:
            f.write(f"file '{s.resolve().as_posix()}'\n")
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file), "-c", "copy", str(out),
    ]
    _run(cmd)


def concat_with_transitions(segments: list[Path], out: Path, transition_dur: float = 0.8) -> None:
    """用 FFmpeg xfade 滤镜做段间炫酷转场。

    转场类型循环使用：fade, wipeleft, wipeup, slideleft, slideup, fadeblack。
    transition_dur: 转场持续时间（秒），默认 0.8s。
    """
    if len(segments) == 0:
        return
    if len(segments) == 1:
        # 只有一段，直接复制
        import shutil
        shutil.copy(segments[0], out)
        return

    # 转场效果循环列表
    transitions = ["fade", "wipeleft", "wipeup", "slideleft", "slideup", "fadeblack"]

    # 获取每段时长
    durations = []
    for seg in segments:
        cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(seg)
        ]
        r = subprocess.run(cmd, capture_output=True, encoding="utf-8")
        if r.returncode == 0:
            durations.append(float(r.stdout.strip()))
        else:
            # 回退：用 concat
            print(f"  [warn] 无法获取 {seg} 时长，回退到普通 concat")
            concat(segments, out)
            return

    n = len(segments)

    # 构建输入参数
    inputs = []
    for seg in segments:
        inputs.extend(["-i", str(seg)])

    # 构建 xfade 滤镜链（视频）
    filter_parts = []
    offset = 0.0
    prev_label = "[0:v]"

    for i in range(n - 1):
        transition = transitions[i % len(transitions)]
        seg_dur = durations[i]
        # offset 是当前输出视频的截止时间点（减去转场重叠）
        xfade_offset = offset + seg_dur - transition_dur
        out_label = f"[v{i}]" if i < n - 2 else "[vout]"

        filter_parts.append(
            f"{prev_label}[{i+1}:v]xfade=transition={transition}:duration={transition_dur}:offset={xfade_offset:.3f}{out_label}"
        )

        offset = xfade_offset
        prev_label = out_label

    # 音频 acrossfade：与视频 xfade 严格对齐（段 i 尾 与 段 i+1 头 交叉 transition_dur），
    # 总时长 = sum(dur) - (n-1)*d，与视频一致。之前只 -map 0:a 导致只有第一段有声音，
    # 后半段静音——本次修复为完整跨段合并。
    for i in range(n):
        filter_parts.append(
            f"[{i}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[a{i}f]"
        )
    prev_label = "[a0f]"
    for i in range(1, n):
        out_label = f"[a{i-1}o]" if i < n - 1 else "[aout]"
        filter_parts.append(
            f"{prev_label}[a{i}f]acrossfade=d={transition_dur}:c1=tri:c2=tri{out_label}"
        )
        prev_label = out_label

    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "[aout]",
        "-shortest",
        *VIDEO_KWARGS, *AUDIO_KWARGS,
        str(out),
    ]
    _run(cmd)


def finalize(video: Path, ass: Path, bgm: Path | None, total_dur: float, out: Path) -> None:
    """烧录字幕 + 混入 BGM（无 BGM 则只烧字幕）。

    在视频/字幕所在目录执行、filter 里用相对文件名，绕开 Windows 盘符冒号
    （D:）对 filtergraph 选项解析的破坏——`ass='D:/...'` 会被当成 original_size 选项。
    """
    cwd = video.parent
    v_name, a_name, o_name = video.name, ass.name, out.name

    if bgm and Path(bgm).exists():
        bg_fade_out = max(total_dur - 2.0, 0.0)
        fc = (
            f"[0:v]ass={a_name}[v];"
            f"[1:a]volume={BGM_VOLUME},afade=t=in:st=0:d=1,"
            f"afade=t=out:st={bg_fade_out:.3f}:d=2[bg];"
            f"[0:a][bg]amix=inputs=2:duration=first:dropout_transition=0[a]"
        )
        cmd = [
            "ffmpeg", "-y", "-i", v_name, "-i", str(bgm),
            "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
            *VIDEO_KWARGS, *AUDIO_KWARGS, o_name,
        ]
    else:
        fc = f"[0:v]ass={a_name}[v]"
        cmd = [
            "ffmpeg", "-y", "-i", v_name,
            "-filter_complex", fc, "-map", "[v]", "-map", "0:a",
            *VIDEO_KWARGS, *AUDIO_KWARGS, o_name,
        ]
    _run(cmd, cwd=str(cwd))


def mix_bgm(video: Path, bgm: Path, total_dur: float, out: Path) -> None:
    """仅混入 BGM（不烧字幕）——供 courseware 模式使用，字幕已画进画面。

    同样在视频所在目录执行、用相对文件名，避开 Windows 盘符冒号问题。
    """
    cwd = video.parent
    v_name, o_name = video.name, out.name
    bg_fade_out = max(total_dur - 2.0, 0.0)
    fc = (
        f"[1:a]volume={BGM_VOLUME},afade=t=in:st=0:d=1,"
        f"afade=t=out:st={bg_fade_out:.3f}:d=2[bg];"
        f"[0:a][bg]amix=inputs=2:duration=first:dropout_transition=0[a]"
    )
    cmd = [
        "ffmpeg", "-y", "-i", v_name, "-i", str(bgm),
        "-filter_complex", fc, "-map", "0:v", "-map", "[a]",
        *VIDEO_KWARGS, *AUDIO_KWARGS, o_name,
    ]
    _run(cmd, cwd=str(cwd))
