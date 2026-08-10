"""探测 edge-tts 对技术缩写的读法。

通过 WordBoundary 数量判断：
- 缩写如 DOM，期望 3 个 boundary（D/O/M 逐字母）
- 若只有 1 个 boundary → 读成单词（错误）

测试三种写法，找出让 TTS 逐字母读的正确写法。
用法：python scripts/probe_tts.py
"""
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]   # skill 根（.agents/skills/video-generation）
sys.path.insert(0, str(SKILL / "scripts"))    # 供 import video 模块
from video.config import OUTPUT_ROOT          # noqa: E402
from video.tts import synth_with_boundaries  # noqa: E402

VOICE = "zh-CN-XiaoxiaoNeural"
RATE = "+8%"

# 待测缩写（应逐字母读的）
ABBREVS = ["DOM", "API", "CSS", "HTML", "JSON", "UI", "TTS", "PR", "CI", "IDE", "HTTP", "URL", "SDK"]
# 三种写法
FORMS = {
    "原样": lambda w: w,
    "空格": lambda w: " ".join(w),
    "点号": lambda w: ".".join(w),
}

TMP = OUTPUT_ROOT / "probe"
TMP.mkdir(parents=True, exist_ok=True)


def count_boundaries(text: str) -> int:
    p = TMP / "t.mp3"
    _, wbs = synth_with_boundaries(text, p, VOICE, RATE)
    # 过滤掉纯标点的边界
    return len([w for w in wbs if w["text"].strip() and any(c.isalnum() for c in w["text"])])


def main() -> None:
    print(f"{'缩写':<6} {'原样':<8} {'空格':<8} {'点号':<8}")
    print("-" * 36)
    results = {}
    for ab in ABBREVS:
        row = {}
        cells = []
        for name, fn in FORMS.items():
            n = count_boundaries(f"测试{fn(ab)}渲染")
            # 减去"测试""渲染"2个词的边界
            adjusted = max(0, n - 2)
            row[name] = adjusted
            cells.append(f"{adjusted}")
        results[ab] = row
        expect = len(ab)
        # 标记哪种写法达到逐字母
        mark = "✓" if row["原样"] == expect else " "
        print(f"{ab:<6} {cells[0]:<8} {cells[1]:<8} {cells[2]:<8}  期望{expect} {mark}")

    print("\n说明：数字 = boundary 数（减去前后中文词）。期望=字母数。")
    print("原样列达标(✓)=读法正确；不达标的需要用空格/点号修正。")


if __name__ == "__main__":
    main()
