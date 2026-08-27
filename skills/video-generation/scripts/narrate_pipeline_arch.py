"""pipeline-arch 口播生成：拆句 → edge-tts 合成 → 单元级时间戳 → narration.ts。

用法（skill 根）：
    cd .agents/skills/video-generation
    VIDEO_PROJECT_ROOT=/d/codes/blog-src python scripts/narrate_pipeline_arch.py
输出：
    <PROJECT_ROOT>/video-generation/narration/pipeline-arch-narration.mp3
    <PROJECT_ROOT>/video-generation/remotion-videos/pipeline-arch/narration.ts
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))          # 使 `video` 包可导入（narrate.py 同款姿势）
sys.path.insert(0, str(SCRIPT_DIR.parent))   # 使 `scripts.narrate` 可导入

from video.config import OUTPUT_ROOT  # noqa: E402
from video.narrate import generate_narration_from_sentences  # noqa: E402

SLUG = "pipeline-arch"
AUDIO_NAME = "pipeline-arch-narration.mp3"
VOICE = "zh-CN-YunxiNeural"
RATE = "+8%"
FPS = 60

# 口播原文（按句）。句号保留给 TTS 停顿；拆单元时去标点。
# 结构：S1 钩子提问 → S2 答案 → S3-S7 架构图主体(先声音侧后画面侧,与场景动画点亮顺序对齐)
#       → S8 中段提问 → S9-S10 对比 → S11 结尾反思 → S12 CTA
NARRATION_SENTENCES = [
    "一篇文章，怎么变成一条带动画讲解的视频？",          # S1 钩子提问
    "不是人剪的，是一条自动管线。",                       # S2 答案
    "入口只有一篇 Markdown 文章。",                       # S3 中心分流点
    "声音侧跑口播合成、字幕对齐，再垫一层轻音乐。",       # S4 左列先亮(声音侧)
    "画面侧把文案拆成场景脚本，一句配一个动画原语。",     # S5 右列后亮(画面侧)
    "两条路并行渲染，动画和转场各自就位。",               # S6 并行
    "音画合成之后，十分钟出一稿成片。",                   # S7 底部结论
    "对比人肉剪辑，它快在哪？",                           # S8 中段提问
    "人肉剪一稿，手调动画、手配音效，半天起步。",         # S9 对比左
    "管线改一句文案，重新渲染，就出一稿新的。",           # S10 对比右
    "下次刷到这类视频，想一想它背后是不是也有一条这样的管线。",  # S11 结尾反思
    "关注我，看懂 AI 研发。",                             # S12 CTA
]


def _to_ts(data: dict) -> str:
    segs = data["segments"]
    L = ["/** 口播时间戳（scripts/narrate_pipeline_arch.py 拆意群 + edge-tts 合成）。",
         " *  重新生成：VIDEO_PROJECT_ROOT=$(CURDIR) python scripts/narrate_pipeline_arch.py */",
         "interface NarrationData {",
         "  voice: string;", "  rate: string;", "  fps: number;", "  total_seconds: number;", "  audio: string;",
         "  segments: Array<{", "    index: number;", "    text: string;",
         "    start_ms: number;", "    end_ms: number;",
         "    start_frame: number;", "    end_frame: number;", "    no_subtitle?: boolean;", "  }>;",
         "}", "", "export const narration: NarrationData = {"]
    L.append(f'  voice: {json.dumps(data["voice"], ensure_ascii=False)},')
    L.append(f'  rate: {json.dumps(data["rate"], ensure_ascii=False)},')
    L.append(f"  fps: {data['fps']},")
    L.append(f"  total_seconds: {data['total_seconds']},")
    L.append(f'  audio: {json.dumps(data["audio"], ensure_ascii=False)},')
    L.append("  segments: [")
    for s in segs:
        L.append("    { " + ", ".join(
            f"{k}: {json.dumps(v, ensure_ascii=False)}" if isinstance(v, str) else f"{k}: {v}"
            for k, v in s.items()) + " },")
    L.append("  ],")
    L.append("};")
    L.append("")
    L.append("export type { NarrationData };")
    return "\n".join(L)


def main() -> None:
    out_dir = OUTPUT_ROOT / "narration"
    out_dir.mkdir(parents=True, exist_ok=True)
    mp3, json_path = generate_narration_from_sentences(
        NARRATION_SENTENCES,
        out_dir=out_dir,
        voice=VOICE,
        rate=RATE,
        fps=FPS,
        audio_name=AUDIO_NAME,
    )

    data = json.loads(json_path.read_text(encoding="utf-8"))
    ts_path = OUTPUT_ROOT / "remotion-videos" / SLUG / "narration.ts"
    ts_path.parent.mkdir(parents=True, exist_ok=True)
    ts_path.write_text(_to_ts(data), encoding="utf-8")

    print(f"[narrate_pipeline_arch] mp3  → {mp3}")
    print(f"[narrate_pipeline_arch] ts   → {ts_path}")
    print(f"[narrate_pipeline_arch] {len(data['segments'])} 个意群，总长 {data['total_seconds']:.1f}s @{FPS}fps")
    # 打印每句首单元 start_frame，便于填 questionFrames
    for i, s in enumerate(data["segments"]):
        if s["index"] == 0 or s["text"].startswith(("对比", "下次")):
            print(f"    seg{s['index']} frame={s['start_frame']}  {s['text']}")


if __name__ == "__main__":
    main()
