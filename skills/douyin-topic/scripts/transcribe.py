# -*- coding: utf-8 -*-
"""faster-whisper 本地中文转写 → 逐字稿（抖音选题 skill）。

spike 0.2 实证: `small` 模型 60s 音频 CPU 转写 ~21s，准确率优于 base。
模型尺寸可用环境变量 WHISPER_MODEL 覆盖（默认 small，base 作快速回退）。
initial_prompt 偏置技术词汇，提升 AI/编程术语识别率。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

DEFAULT_MODEL = "small"
TECH_PROMPT = "以下是一段中文科技视频的口播内容，涉及 AI、编程、大模型、开发者、代码、工具等话题。"


def extract_audio(video_path: Path, out_path: Path) -> bool:
    """从视频抽 16k 单声道 wav（音频轨缺失时用）。"""
    result = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(video_path),
         "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(out_path)],
        capture_output=True,
    )
    return result.returncode == 0 and out_path.exists()


def transcribe(audio_path: Path, model_name: str = DEFAULT_MODEL) -> dict[str, Any]:
    """转写音频，返回 {model, language, duration, segments, full_text}。"""
    from faster_whisper import WhisperModel

    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments_iter, info = model.transcribe(
        str(audio_path),
        language="zh",
        beam_size=5,
        initial_prompt=TECH_PROMPT,
    )
    segments: list[dict] = []
    for seg in segments_iter:
        segments.append({
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": seg.text.strip(),
        })
    full_text = "".join(item["text"] for item in segments)
    return {
        "model": model_name,
        "language": info.language,
        "duration": round(info.duration, 2) if info.duration else None,
        "segments": segments,
        "full_text": full_text,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="本地中文转写 → 逐字稿")
    parser.add_argument("--audio", default=None, help="音频文件（mp4/m4a/wav）")
    parser.add_argument("--video", default=None, help="视频文件（无音频轨时 ffmpeg 抽取）")
    parser.add_argument("--out-dir", default=None, help="输出目录（默认同音频目录）")
    parser.add_argument("--model", default=None, help="whisper 模型尺寸（默认 small）")
    args = parser.parse_args()

    if not args.audio and not args.video:
        sys.exit("❌ 需提供 --audio 或 --video")

    model_name = args.model or os.environ.get("WHISPER_MODEL", DEFAULT_MODEL)

    if args.audio:
        audio_path = Path(args.audio)
    else:
        video_path = Path(args.video)
        out_dir = Path(args.out_dir) if args.out_dir else video_path.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        audio_path = out_dir / "extracted_audio.wav"
        print("🎧 从视频抽取音频...")
        if not extract_audio(video_path, audio_path):
            sys.exit("❌ 音频抽取失败")

    out_dir = Path(args.out_dir) if args.out_dir else audio_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"🎙️ 转写中（model={model_name}，CPU）...")
    result = transcribe(audio_path, model_name)

    (out_dir / "transcript.txt").write_text(result["full_text"], encoding="utf-8")
    (out_dir / "transcript.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"✅ 逐字稿 {len(result['full_text'])} 字 → {out_dir / 'transcript.txt'}")
    print("--- 前 200 字 ---")
    print(result["full_text"][:200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
