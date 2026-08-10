"""edge-tts 口播配音生成（通用，供 Remotion / 任意渲染后端复用）。

把文案单元合成成整段 mp3 + 单元级时间戳 JSON。任何渲染引擎
（Remotion / Playwright / FFmpeg）都能用这个 JSON 对齐字幕。

关键设计：单元片段 ffmpeg concat 拼成整段，时间戳基于拼接后的真实位置——
避免「逐句拿时间戳 + 整段重合成」导致的时间戳/音频漂移。

用法（命令行）：
    python -m video.narrate --text-file units.txt --out-dir out/ \\
        --voice zh-CN-YunxiNeural --rate +8% --fps 60
    # units.txt 每行一个单元（短句/意群，≤18 字最佳）

用法（模块导入）：
    from video.narrate import generate_narration
    mp3, json_path = generate_narration(units=[...], out_dir=Path("out"))

产物：
    <out_dir>/narration.mp3     整段口播（单元 concat，无漂移）
    <out_dir>/narration.json    单元级时间戳（含 start_frame/end_frame）

依赖：video.tts.synth_with_boundaries（带 normalize_for_tts + 重试退避）。
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from video.tts import synth_with_boundaries, probe_duration

DEFAULT_VOICE = "zh-CN-YunxiNeural"   # 中文男声（科普/技术）
DEFAULT_RATE = "+8%"
DEFAULT_FPS = 60
DEFAULT_MAX_UNIT = 24   # 意群单元字数上限（接近字幕单行容量，避免切碎完整句）

import re as _re

# 断句标点：中文句逗顿冒分 + 问叹号。问句必须单独成意群——
# 否则「又被封了？不换号」连一起超 24 字被硬切到「不换号」，字幕出现"又问句又半截"。
_UNIT_SPLIT_RE = _re.compile(r"[，。、：；？！]")
# 硬切 token：英文/数字词块（含内部空格）整体切 + 中文数字连续段整体切（保护"零点零二八"不被切成"约零/点零二八"）+ 其余逐字。
_TOKEN_RE = _re.compile(r"[A-Za-z0-9.+-]+(?:\s+[A-Za-z0-9.+-]+)*|[零一二三四五六七八九十百千万亿点]+|.")


def split_units(sentences: list[str], max_unit: int = DEFAULT_MAX_UNIT) -> list[str]:
    """把完整句子拆成口播/字幕意群单元（智能断句，避免误切）。

    经验沉淀（踩坑修复）：
    1. 先按中文标点拆意群（逗号/句号/顿号）—— 这步永远对。
    2. 超长才按字数硬切，阈值用 max_unit（默认 24，接近字幕单行容量）。
       —— 早期用 18 太严，把"DeepSeek发布V4 Flash正式版"(20字)切成两半。
    3. 英文词块整体切（computed style 不可断成 computed+style）。
    4. 尾部短词(<6字)回并上一句 —— 避免"正式版"这类尾巴单独成句、断句不自然。

    返回去标点的意群单元列表，每个 ≤ max_unit（尾部合并例外）。
    """
    units: list[str] = []
    for sent in sentences:
        for part in _UNIT_SPLIT_RE.split(sent):
            part = part.strip()
            if not part:
                continue
            if len(part) <= max_unit:
                units.append(part)
                continue
            # 超长：按英文词块 + 中文数字段 + 中文逐字切
            tokens = _TOKEN_RE.findall(part)
            chunks: list[str] = []
            cur = ""
            for tok in tokens:
                if len(cur) + len(tok) > max_unit and cur:
                    chunks.append(cur)
                    cur = tok
                else:
                    cur += tok
            if cur:
                chunks.append(cur)
            # 去块首尾空格（英文词块整体切可能把尾部空格带进块）
            chunks = [c.strip() for c in chunks]
            # 尾部短词回并（避免"正式版"单独成句）
            if len(chunks) >= 2 and len(chunks[-1]) < 6:
                chunks[-2] = chunks[-2] + chunks[-1]
                chunks.pop()
            units.extend(chunks)
    return units


def generate_narration(
    units: list[str],
    out_dir: Path,
    voice: str = DEFAULT_VOICE,
    rate: str = DEFAULT_RATE,
    fps: int = DEFAULT_FPS,
    audio_name: str = "narration.mp3",
) -> tuple[Path, Path]:
    """逐单元合成 + concat 拼接 + 单元级时间戳。

    units: 口播单元列表（建议调用方先按标点拆成 ≤18 字的意群）。
    返回 (mp3_path, json_path)。时间戳与音频严格一致。
    """
    import os

    out_dir.mkdir(parents=True, exist_ok=True)
    mp3_path = out_dir / audio_name
    json_path = out_dir / "narration.json"

    seg_files: list[Path] = []
    segments: list[dict] = []
    cursor_ms = 0.0

    # 逐单元合成（每个单元独立 mp3 + 精确时长）
    for i, unit in enumerate(units):
        seg = out_dir / f".seg_{i:03d}.mp3"
        synth_with_boundaries(unit, seg, voice, rate)
        dur = probe_duration(seg)
        start_ms = cursor_ms
        end_ms = cursor_ms + dur * 1000
        segments.append({
            "index": i,
            "text": unit,
            "start_ms": round(start_ms),
            "end_ms": round(end_ms),
            "start_frame": round(start_ms / 1000 * fps),
            "end_frame": round(end_ms / 1000 * fps),
        })
        cursor_ms = end_ms
        seg_files.append(seg)
        print(f"  单元 {i + 1:02d}/{len(units)}  {start_ms / 1000:5.2f}-{end_ms / 1000:5.2f}s  {unit[:24]}")

    # concat filter 拼接（样本级精确）。
    # 不用 concat demuxer -c copy：mp3 帧间 encoder padding 会累计，导致音画漂移。
    # concat filter 解码每段为 PCM 再拼接，段间无 gap，时间戳（probe 累加）与音频严格对齐。
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    for f in seg_files:
        cmd += ["-i", f.resolve().as_posix()]
    cmd += [
        "-filter_complex", f"concat=n={len(seg_files)}:v=0:a=1[aout]",
        "-map", "[aout]",
        "-c:a", "libmp3lame", "-q:a", "2",
        mp3_path.resolve().as_posix(),
    ]
    subprocess.run(
        cmd, check=True, capture_output=True, encoding="utf-8",
        env={**os.environ, "LANG": "zh_CN.UTF-8"},
    )

    # 清理临时片段
    for f in seg_files:
        f.unlink(missing_ok=True)

    total = probe_duration(mp3_path)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "voice": voice,
            "rate": rate,
            "fps": fps,
            "total_seconds": total,
            "audio": audio_name,
            "segments": segments,
        }, f, ensure_ascii=False, indent=2)

    print(f"[narrate] concat 音频 {total:.2f}s → {mp3_path}")
    print(f"[narrate] 时间戳 → {json_path}")
    return mp3_path, json_path


def generate_narration_from_sentences(
    sentences: list[str],
    out_dir: Path,
    voice: str = DEFAULT_VOICE,
    rate: str = DEFAULT_RATE,
    fps: int = DEFAULT_FPS,
    audio_name: str = "narration.mp3",
    max_unit: int = DEFAULT_MAX_UNIT,
) -> tuple[Path, Path]:
    """一站式：完整句子 → 智能断句(split_units) → 合成 + 时间戳。

    多数场景用这个，不用自己调 split_units。
    """
    units = split_units(sentences, max_unit=max_unit)
    print(f"[narrate] {len(sentences)} 句 → 拆成 {len(units)} 个意群单元")
    return generate_narration(units, out_dir, voice=voice, rate=rate, fps=fps, audio_name=audio_name)


def _main() -> None:
    ap = argparse.ArgumentParser(description="生成 edge-tts 口播 + 单元级时间戳")
    ap.add_argument("--text-file", required=True, help="文案文件，每行一句完整句子（自动智能断句）")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--voice", default=DEFAULT_VOICE)
    ap.add_argument("--rate", default=DEFAULT_RATE)
    ap.add_argument("--fps", type=int, default=DEFAULT_FPS)
    ap.add_argument("--max-unit", type=int, default=DEFAULT_MAX_UNIT, help="意群单元字数上限")
    args = ap.parse_args()

    text = Path(args.text_file).read_text(encoding="utf-8")
    sentences = [s.strip() for s in text.splitlines() if s.strip()]
    generate_narration_from_sentences(
        sentences,
        Path(args.out_dir),
        voice=args.voice,
        rate=args.rate,
        fps=args.fps,
    )


if __name__ == "__main__":
    _main()
