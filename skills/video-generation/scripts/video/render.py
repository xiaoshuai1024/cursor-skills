"""FFmpeg 渲染：单卡动效 → concat 拼接 → 烧录 ASS 字幕 + 混 BGM。"""
import subprocess
from pathlib import Path

from .config import (
    AUDIO_KWARGS, BGM_VOLUME, FADE, FPS, HEAD_PAD, OUT_H, OUT_SIZE, OUT_W,
    SFX_VOLUME_DB, VIDEO_KWARGS,
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


def audio_overlay_chain(
    narration_label: str,
    bgm: Path | None,
    sfx_points: list[tuple[Path, float]],
    total_dur: float,
    next_input_index: int,
    bgm_volume: float = 0.35,
    sfx_volume_db: str = SFX_VOLUME_DB,
) -> tuple[list[str], list[str], str]:
    """构建「BGM 垫底 + 定点音效」滤镜链，叠加在口播音频标签之上。

    装配期同图混入（xfade/acrossfade 的同一条 filter_complex），不是对成片
    二次后混——单 pass 出片，无中间文件。返回 (追加输入参数, 追加滤镜片段,
    最终音频标签)。输入序号从 next_input_index 起（调用方已占 0..n-1）。

    - BGM：-stream_loop -1 整片循环，淡入 1s / 尾部淡出 2s，atrim 对齐总时长
    - 音效：逐点 adelay 定位（毫秒，绝对时间轴）
    - amix duration=first 以口播时长为准；normalize=0 不自动压电平
    """
    extra_inputs: list[str] = []
    parts: list[str] = []
    mix_labels = [narration_label]
    idx = next_input_index

    if bgm is not None:
        fade_out = max(total_dur - 2.0, 0.0)
        extra_inputs += ["-stream_loop", "-1", "-i", str(bgm)]
        parts.append(
            f"[{idx}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,"
            f"volume={bgm_volume},afade=t=in:st=0:d=1,"
            f"afade=t=out:st={fade_out:.3f}:d=2,atrim=0:{total_dur:.3f}[ovbgm]"
        )
        mix_labels.append("[ovbgm]")
        idx += 1

    for i, (sfx_path, t) in enumerate(sfx_points):
        ms = max(0, int(round(t * 1000)))
        extra_inputs += ["-i", str(sfx_path)]
        parts.append(
            f"[{idx}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,"
            f"volume={sfx_volume_db},adelay={ms}|{ms}[ovsfx{i}]"
        )
        mix_labels.append(f"[ovsfx{i}]")
        idx += 1

    if len(mix_labels) == 1:
        return extra_inputs, parts, narration_label

    out_label = "[ovaout]"
    parts.append(
        f"{''.join(mix_labels)}amix=inputs={len(mix_labels)}:duration=first:"
        f"dropout_transition=0:normalize=0{out_label}"
    )
    return extra_inputs, parts, out_label


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


def concat_with_transitions(
    segments: list[Path],
    out: Path,
    transition_dur: float = 0.8,
    bgm: Path | None = None,
    sfx: dict[str, Path] | None = None,
    bgm_volume: float = 0.35,
    transition_sfx_every: int = 4,
    extra_sfx: list[tuple[Path, float]] | None = None,
    transitions: list[str] | None = None,
) -> None:
    """用 FFmpeg xfade 滤镜做段间转场，BGM/音效同图混入（单 pass 装配）。

    转场选择（openspec prism-motion-pipeline）：调用方传 `transitions`（per-boundary
    列表，长度 n-1）则逐边界使用（章节感知三级预算，方向一致性由 build 层规划）；
    不传 → 默认中转场轮换（向后兼容，原 6 种固定轮换退役）。
    transition_dur: 转场持续时间（秒），默认 0.8s。
    bgm: BGM wav 路径（-stream_loop 循环垫底，None 则不加）。
    sfx: {"opening": Path, "transition": Path}（None 则不加）。开场音 @0.08s；
         转场音按段边界稀疏触发（每 transition_sfx_every 段一次，首段只开场音）。
    extra_sfx: 追加定点音效（如提问音，内容感知点位由调用方从口播时间轴提取）。
    """
    if len(segments) == 0:
        return
    if len(segments) == 1:
        # 只有一段，直接复制
        import shutil
        shutil.copy(segments[0], out)
        return

    # 默认转场：中档轮换（slideleft 族方向一致；原 fade/wipeleft/wipeup/
    # slideleft/slideup/fadeblack 固定轮换已退役）
    default_transitions = ["slideleft", "smoothleft", "wipeleft", "fade"]
    n = len(segments)
    if isinstance(transitions, list) and len(transitions) == n - 1:
        trans_seq = [str(t) for t in transitions]
    else:
        if transitions is not None:
            print(f"  [warn] transitions 长度 {len(transitions)} ≠ {n - 1}，回退默认轮换")
        trans_seq = None

    n = len(segments)

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

    # 构建输入参数
    inputs = []
    for seg in segments:
        inputs.extend(["-i", str(seg)])

    # 构建滤镜链
    filter_parts = []
    offset = 0.0
    prev_label = "[0:v]"
    boundaries: list[float] = []

    for i in range(n - 1):
        transition = (trans_seq[i] if trans_seq is not None
                      else default_transitions[i % len(default_transitions)])
        seg_dur = durations[i]
        # offset 是当前输出视频的截止时间点（减去转场重叠）
        xfade_offset = offset + seg_dur - transition_dur
        out_label = f"[v{i}]" if i < n - 2 else "[vout]"

        filter_parts.append(
            f"{prev_label}[{i+1}:v]xfade=transition={transition}:duration={transition_dur}:offset={xfade_offset:.3f}{out_label}"
        )

        boundaries.append(xfade_offset)
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

    # BGM + 音效同图混入（装配期一步完成，非成片二次后混）。
    # 转场音语义与 Remotion SoundLayer 一致：段 k（k>0）且 k % every == 0 时，
    # 在进入段 k 的转场重叠起点（boundaries[k-1]）响。
    total_dur = sum(durations) - (n - 1) * transition_dur
    sfx_points: list[tuple[Path, float]] = []
    if sfx:
        sfx_points.append((sfx["opening"], 0.08))
        every = max(1, transition_sfx_every)
        for k in range(1, n):
            if k % every == 0:
                sfx_points.append((sfx["transition"], max(boundaries[k - 1], 0.0)))
    sfx_points.extend(extra_sfx or [])
    sfx_points.sort(key=lambda p: p[1])

    audio_label = "[aout]"
    extra_inputs, overlay_parts, audio_label = audio_overlay_chain(
        audio_label, bgm, sfx_points, total_dur, n
    )
    filter_parts.extend(overlay_parts)
    inputs.extend(extra_inputs)

    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", audio_label,
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
