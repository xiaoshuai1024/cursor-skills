"""为 deepseek-v4 视频生成口播。复用 skill 的 video.narrate。

数据来源：InfoQ 文章 + 用户补充（真实数字，不编造）。
去掉"官方测试验证"部分，补充参数/AII指数/前端/成本/多模态。
用法：python scripts/narrate_deepseek.py
"""
import json
import re
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]   # skill 根（.agents/skills/video-generation）
sys.path.insert(0, str(SKILL / "scripts"))    # 供 import video 模块

from video.config import OUTPUT_ROOT           # noqa: E402
from video.narrate import generate_narration  # noqa: E402

VOICE = "zh-CN-YunxiNeural"
RATE = "+8%"   # 自然语速（英文术语靠单词音保证流畅，不靠提速）
FPS = 60
MAX_UNIT = 24   # 接近字幕单行容量，避免把完整短句硬切（如"DeepSeek发布V4 Flash正式版"）

# 口播文案（真实数据，已删除未经证实的信息）
# 注：V4 Flash 本版本没有多模态能力，不提及。
NARRATION_SENTENCES = [
    "7月31日，DeepSeek发布V4 Flash正式版，总参数2840亿，激活参数130亿。",
    "Terminal-Bench编程榜82.7分，超过GLM，仅低于Opus 4.8。",
    "相比预览版，CyberGym从38.7升到76.7，DeepSWE从7.3暴涨到54.4。",
    "AII智能指数50分，仅落后GPT-5.6 Luna 1分。",
    "前端代码专项1586分，刷新该赛道记录。",
    "成本比降价的Luna还低60%，1.64亿Token只要8.9元。",
    "原生支持Responses接口，可作Codex后端，关注我看V4 Pro。",
]


def split_units(sentences):
    """按标点拆意群；超长才硬切；尾部短词（<6字）回并上一句，避免"正式版"单独成句。"""
    units = []
    for sent in sentences:
        for p in re.split(r"[，。、：；]", sent):
            p = p.strip()
            if not p:
                continue
            if len(p) <= MAX_UNIT:
                units.append(p)
                continue
            # 超长：按英文词块 + 中文逐字切
            tokens = re.findall(r"[A-Za-z0-9.+-]+(?:\s+[A-Za-z0-9.+-]+)*|.", p)
            chunks = []
            cur = ""
            for tok in tokens:
                if len(cur) + len(tok) > MAX_UNIT and cur:
                    chunks.append(cur)
                    cur = tok
                else:
                    cur += tok
            if cur:
                chunks.append(cur)
            # 尾部短词回并（避免"正式版"这类尾巴单独成句）
            if len(chunks) >= 2 and len(chunks[-1]) < 6:
                chunks[-2] = chunks[-2] + chunks[-1]
                chunks.pop()
            units.extend(chunks)
    return units


def main():
    units = split_units(NARRATION_SENTENCES)
    print(f"[narrate] 拆成 {len(units)} 个意群单元")

    out_dir = OUTPUT_ROOT / "narration"
    mp3, json_path = generate_narration(
        units, out_dir=out_dir, voice=VOICE, rate=RATE, fps=FPS,
        audio_name="deepseek-v4-narration.mp3",
    )

    data = json.loads(json_path.read_text(encoding="utf-8"))
    ts_path = OUTPUT_ROOT / "remotion-videos" / "deepseek-v4" / "narration.ts"
    ts_path.parent.mkdir(parents=True, exist_ok=True)
    ts_path.write_text(_to_ts(data), encoding="utf-8")
    print(f"[narrate] TS → {ts_path}")


def _to_ts(data):
    segs = data["segments"]
    L = ['interface NarrationData { voice: string; rate: string; fps: number; total_seconds: number; audio: string; segments: Array<{ index: number; text: string; start_ms: number; end_ms: number; start_frame: number; end_frame: number; no_subtitle?: boolean; }>; }',
         "", "export const narration: NarrationData = {"]
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
    L.append("export type { NarrationData };")
    return "\n".join(L)


if __name__ == "__main__":
    main()
