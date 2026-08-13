"""为 deepseek-cheap-power 视频生成口播。复用 skill 的 video.narrate。

内容：DeepSeek 现在有多便宜（与 Claude / Codex / GLM 对比）→ V4 Flash
能力排行榜 → 基于公开信息的后续价格预测。
类型：新闻速报 + 数据对比 + 观点预测。

数据来源（2026-08-07 联网核实，不编造）：
  现行价（DeepSeek 开放平台官方）——
    V4 Flash：输出 ¥2/百万 Token，缓存命中输入 ¥0.02
    V4-Pro：输出 ¥6/百万 Token
    工作日高峰（9:00-12:00 / 14:00-18:00）价格翻倍
  同行输出价 ——
    GLM-5.2 ¥28（阿里云百炼/360）、GPT-5.6 Luna $1.2≈¥8（7/31 降 80% 后）、
    Codex（GPT-5.3 Codex）$14≈¥99、Claude Opus 4.8 $25≈¥178（1 美元≈7.1 元）
  Terminal-Bench 2.1 —— Opus 4.8 85.0 / DeepSeek V4 Flash 82.7 / GLM-5.2 81.0 /
    V4-Pro 预览 72.1 / V4 Flash 预览 61.8
  AII 智能指数 —— V4 Flash 50 / GPT-5.6 Luna 51（文章+新浪口径）
  调价历史（21财经/界面/新浪）—— 4/25 限时 2.5 折 → 5/23 正式定价降 75% →
    6 月底峰谷计费 → 7/31 V4 Flash 上线 → 8/6 官方预告整体上调 API 价
  行业涨价（21财经/不慌实验室）—— 智谱多次上调、腾讯混元最高涨超 460%、
    阿里云/百度云同步上调、OpenAI 反向给 Luna 降 80%

结构（内容驱动，每句 = 一个场景段落）：
  句0-1  Cover 速报钩子
  句2-6  价格对比（LeaderboardChart 条形，从贵到便宜逐条点亮）
  句7-11 能力排行榜（LeaderboardChart 条形，高亮 V4 Flash）
  句12-16 调价历史（PriceTimeline 时间线，8/6 高亮）
  句17-22 涨价预测（PricePrediction 价格轴 + 预测落点）
  句23-24 Outro 结论

每句分句 ≤24 字，避免 split_units 硬切中文词。
用法：python scripts/narrate_deepseek_cheap_power.py
"""
import json
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]   # skill 根（.agents/skills/video-generation）
sys.path.insert(0, str(SKILL / "scripts"))    # 供 import video 模块

from video.config import OUTPUT_ROOT                          # noqa: E402
from video.narrate import generate_narration_from_sentences  # noqa: E402

VOICE = "zh-CN-YunxiNeural"
RATE = "+8%"
FPS = 60
AUDIO_NAME = "deepseek-cheap-power-narration.mp3"
VIDEO_ID = "deepseek-cheap-power"

# 口播文案。事实全部来自官方/公开报道；「涨价预测」为评论口径（明确标注「我的判断」）。
# 生成后按 units 序号映射到 config 场景（narrate 输出会打印每句的单元区间）：
NARRATION_SENTENCES = [
    # 句0-1 Cover 速报钩子
    "8月6日，DeepSeek官方预告：API价格要大涨。",
    "今天先看三件事：它有多便宜，能力多强，涨价后会到哪。",
    # 句2-6 价格对比（从贵到便宜逐条点亮，Flash 收尾高亮）
    "先看输出价，每百万Token。Claude Opus要178块。",
    "Codex约99块，GLM-5.2是28块。",
    "OpenAI的Luna刚降过价，也要8块。",
    "DeepSeek V4-Pro是6块，V4-Flash只要2块。",
    "比GLM便宜14倍，比Claude Opus便宜近90倍。",
    # 句7-11 能力排行榜
    "便宜不等于弱，Terminal-Bench编程榜它排世界第二。",
    "Claude Opus 4.8拿85分，DeepSeek V4-Flash拿82.7分，只差2.3分。",
    "GLM-5.2是81分，排第三。",
    "自家V4-Pro预览版72分，Flash预览版62分。",
    "综合智能指数50分，只比Luna低1分。",
    # 句12-16 调价历史（价格为什么这么低）
    "这个低价怎么来的？DeepSeek今年刚降过一轮。",
    "四月V4-Pro限时2.5折，五月正式定价砍到四分之一。",
    "六月上峰谷计费，工作日高峰直接翻倍。",
    "七月V4 Flash上线，输出价2块，保持全场最低。",
    "八月六号，官方突然预告整体上调，涨幅较大。",
    # 句17-22 涨价预测（基于公开行业信息 + 明确标注判断）
    "会涨到哪？先看行业信号。",
    "智谱年内多次上调，腾讯混元最高涨460%。",
    "阿里云、百度云跟涨，Agent爆发推高算力成本。",
    "我的判断：Flash涨3倍到6块，还在最便宜的档。",
    "涨10倍到20块，贴近GLM的28块。",
    "大概率落在国产第一梯队附近，GLM就是参照系。",
    # 句23-24 Outro 结论
    "窗口期会关，依赖DeepSeek API的团队，现在就要算账。",
    "缓存命中价只要2分钱，把命中率做上去，成本还能压一截。",
]


def main():
    print(f"[narrate] {len(NARRATION_SENTENCES)} 句，交给 split_units 智能断句")

    out_dir = OUTPUT_ROOT / "narration"
    mp3, json_path = generate_narration_from_sentences(
        NARRATION_SENTENCES, out_dir=out_dir, voice=VOICE, rate=RATE, fps=FPS,
        audio_name=AUDIO_NAME,
    )

    data = json.loads(json_path.read_text(encoding="utf-8"))
    ts_path = OUTPUT_ROOT / "remotion-videos" / VIDEO_ID / "narration.ts"
    ts_path.parent.mkdir(parents=True, exist_ok=True)
    ts_path.write_text(_to_ts(data), encoding="utf-8")
    print(f"[narrate] TS → {ts_path}")
    print(f"[narrate] 共 {len(data['segments'])} 个意群单元，总时长 {data['total_seconds']:.2f}s")


def _to_ts(data):
    segs = data["segments"]
    L = ['interface NarrationData { voice: string; rate: string; fps: number; total_seconds: number; audio: string; segments: Array<{ index: number; text: string; start_ms: number; end_ms: number; start_frame: number; end_frame: number; }>; }',
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
