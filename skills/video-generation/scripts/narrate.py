"""为 visual-acceptance 视频生成口播（复用 skill 的 video.narrate）。

把文案按标点拆成意群单元（≤18 字），逐单元合成 + concat。
单元级时间戳供 config 对齐字幕（每次显示一个完整短句，不截断）。

产物：
  .video-generation/narration/va-narration.mp3
  .video-generation/remotion-videos/visual-acceptance/narration.ts

用法：cd skill && python scripts/narrate.py
"""
import json
import re
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]   # skill 根（.agents/skills/video-generation）
sys.path.insert(0, str(SKILL / "scripts"))    # 供 import video 模块

from video.config import OUTPUT_ROOT           # noqa: E402
from video.narrate import generate_narration  # noqa: E402

VOICE = "zh-CN-YunxiNeural"   # 中文男声
RATE = "+15%"   # 提速压缩字母间停顿（缩写逐字母读的 197ms 间隔）
FPS = 60
MAX_UNIT = 18                 # 每个字幕单元最大字数（单行容量）

# 口播原文（按句）。句末保留「。」给 TTS 停顿；拆单元时去标点。
NARRATION_SENTENCES = [
    "一个项目380个页面，每个页面停留十秒就是一个多小时，靠人走UI验收根本不现实。",
    "新功能有高保真原型做锚点，做像素级比对，保证实现和设计稿一致。",
    "老功能没有原型可比对，用vision模型看图找疑点，但vision会幻觉，浅渐变认成白底，红色角标认成客服按钮。",
    "vision报了407个疑点，代码审计交叉验证后，只有4个是真问题，真阳性率不到百分之一。",
    "代码审计才是真相源。",
    "遍历DOM的computed style，扫描有没有写死的旧颜色泄漏，423页走token，只有4个文件硬编码。",
    "两条路互补，新功能走像素diff，老功能走vision加代码审计，380页才能覆盖得过来。",
    "有五个反模式要避开：全量截图丢给vision直接采信、像素diff当结论、没有真相源、商业黑盒AI直接采信、没有token泄漏基线扫描。",
    "整个pipeline并行跑下来，一个版本的视觉验收从人走一周，缩到机器跑两小时加人审30分钟疑点。",
    "视觉验收的瓶颈不是模型够不够强，是有没有一个可确定的真相源。",
    "关注，看懂AI研发。",
]


def split_units(sentences: list[str]) -> list[str]:
    """把句子按标点拆成意群单元（≤MAX_UNIT 字），去标点。

    英文单词不可被切断（按词边界拆）；中文可按字硬切。
    """
    units: list[str] = []
    for sent in sentences:
        parts = re.split(r"[，。、：；]", sent)
        for p in parts:
            p = p.strip()
            if not p:
                continue
            if len(p) <= MAX_UNIT:
                units.append(p)
                continue
            # 超长：按词（英文连读块）+ 中文逐字，凑到 ≤MAX_UNIT
            # 用正则把"连续英文/数字"当一个 token，中文每字一个 token
            tokens = re.findall(r"[A-Za-z0-9.+-]+(?:\s+[A-Za-z0-9.+-]+)*|.", p)
            cur = ""
            for tok in tokens:
                if len(cur) + len(tok) > MAX_UNIT and cur:
                    units.append(cur)
                    cur = tok
                else:
                    cur += tok
            if cur:
                units.append(cur)
    return units


def main() -> None:
    units = split_units(NARRATION_SENTENCES)
    print(f"[narrate] 拆成 {len(units)} 个意群单元（每个 ≤{MAX_UNIT} 字）")

    out_dir = OUTPUT_ROOT / "narration"
    mp3, json_path = generate_narration(
        units,
        out_dir=out_dir,
        voice=VOICE,
        rate=RATE,
        fps=FPS,
        audio_name="va-narration.mp3",
    )

    # 同步生成 TS 模块
    data = json.loads(json_path.read_text(encoding="utf-8"))
    ts_path = OUTPUT_ROOT / "remotion-videos" / "visual-acceptance" / "narration.ts"
    ts_path.write_text(_to_ts(data), encoding="utf-8")
    print(f"[narrate] TS 模块 → {ts_path}")


def _to_ts(data: dict) -> str:
    segs = data["segments"]
    L = ["/** 口播时间戳（scripts/narrate.py 拆意群 + edge-tts 合成）。", " *  重新生成：cd demo && python scripts/narrate.py */", "interface NarrationData {", "  voice: string;", "  rate: string;", "  fps: number;", "  total_seconds: number;", "  audio: string;", "  segments: Array<{", "    index: number;", "    text: string;", "    start_ms: number;", "    end_ms: number;", "    start_frame: number;", "    end_frame: number;", "  }>;", "}", "", "export const narration: NarrationData = {"]
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


if __name__ == "__main__":
    main()
