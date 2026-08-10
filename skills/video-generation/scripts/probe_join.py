"""探测让缩写字母紧凑连读的分隔方式。

目标:逐字母读(D-O-M 三个 boundary),但字母间停顿尽量短。
候选:空格 / 句点 / 连字符 / 无分隔原样(已知读成单词)。
通过 boundary 间的时间差判断停顿长短。
"""
import sys
from pathlib import Path
SKILL_DIR = Path(__file__).resolve().parents[1]   # skill 根
sys.path.insert(0, str(SKILL_DIR / "scripts"))
from video.config import OUTPUT_ROOT                  # noqa
from video.tts import synth_with_boundaries, probe_duration  # noqa

VOICE = "zh-CN-YunxiNeural"
RATE = "+8%"
OUT = OUTPUT_ROOT / "probe"
OUT.mkdir(parents=True, exist_ok=True)

JOINS = {
    "空格": "D O M",
    "句点": "D.D.M",
    "连字符": "D-O-M",
    "斜杠": "D/O/M",
}

for name, text in JOINS.items():
    p = OUT / f"j_{name}.mp3"
    _, wbs = synth_with_boundaries(f"读取{text}结构", p, VOICE, RATE)
    # 取 DOM 三个字母的 boundary
    letters = [w for w in wbs if w["text"] in ("D", "O", "M", "d", "o", "m") or w["text"] in text.replace("结构", "")]
    # 简化:打印所有 boundary 时间
    dur = probe_duration(p)
    gaps = []
    for i in range(1, len(wbs)):
        gap = wbs[i]["start_ms"] - wbs[i-1]["start_ms"]
        gaps.append(gap)
    # 前2个是"读取",后3个是字母,算字母间平均间隔
    letter_gaps = gaps[1:3] if len(gaps) >= 3 else gaps  # 粗略
    print(f"{name:6} 总{dur:.2f}s boundary数={len(wbs)} 间隔={gaps[1:4]}ms  | {wbs}")


