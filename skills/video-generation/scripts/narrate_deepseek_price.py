"""为 deepseek-price-increase 视频生成口播。复用 skill 的 video.narrate。

内容：DeepSeek 官方邮件（2026-08-06 20:39 实收）宣布 API 服务大幅调价。
类型：新闻速报 + 深度解读（价格/历史/榜单/预测）。
数据来源（2026-08-07 联网核实，不编造）：
  现行价（官方）—— V4 Flash 输出 ¥2/M、V4 Pro 输出 ¥6/M（平峰）
  降价历史（21财经/界面/新浪）—— 4/25 限时2.5折 → 5/23 正式定价降75% → 6月底峰谷计费
  同行输出价 —— GLM-5.2 ¥28（阿里云百炼）、GPT-5.6 Luna $6、Codex $14、Claude Opus $25
  （美元按 1 美元≈7.1 元换算：Luna≈¥43 / Codex≈¥99 / Opus≈¥178）
  Terminal-Bench 2.1 —— Opus 4.8 85.0 / DeepSeek V4 Flash 82.7 / GLM-5.2 81.0 / V4-Pro 72.1
结构（内容驱动）：
  句0 Cover 速报
  句1-4 邮件要点（NewsNotice 面板）
  句5-8 降价历史（PriceTimeline 时间线）
  句9-11 价格对比（LeaderboardChart 条形，复用）
  句12-13 能力排行榜（LeaderboardChart 条形）
  句14-16 涨价预测（PricePrediction 价格轴）
  句17-18 三件事建议（SelectionPrinciples）
  句19 Outro
每句分句 ≤24 字，避免 split_units 硬切中文词。
用法：python scripts/narrate_deepseek_price.py
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
AUDIO_NAME = "deepseek-price-increase-narration.mp3"
VIDEO_ID = "deepseek-price-increase"

# 口播文案。事实全部来自官方/公开报道；「涨价预测」为评论口径（明确标注「我的判断」）。
# 每句 = 一个场景段落；生成后按 units 序号映射到 config 场景：
#   句0=U0..2        句1-4=U3..14     句5-8=U15..23
#   句9-11=U24..35   句12-13=U36..43  句14-16=U44..53
#   句17-18=U54..59  句19=U60..61
NARRATION_SENTENCES = [
    # 句0 Cover 速报钩子
    "8月6日晚，DeepSeek官方邮件宣布：API服务即将大幅调价。",
    # 句1-4 邮件要点（NewsNotice 面板逐条揭示）
    "计划近期整体上调API服务定价，预计涨幅较大。",
    "具体方案还没公布，以正式通知为准，留意平台公告。",
    "注意一个条款：调价后继续使用，等于同意新计费方式。",
    "不想接受，可以退出使用，并申请退费。",
    # 句5-8 降价历史（PriceTimeline 时间线）
    "先看背景，DeepSeek今年刚降过一轮价。",
    "四月V4-Pro限时2.5折，五月正式定价砍到四分之一，降幅75%。",
    "六月又上峰谷计费，高峰直接翻倍。",
    "八月，突然宣布涨价。",
    # 句9-11 价格对比（LeaderboardChart 条形，越低越好）
    "现在的价格有多低？V4 Flash输出价每百万tokens只要2块钱，V4-Pro是6块。",
    "同级别里，GLM-5.2要28，GPT-5.6 Luna约43，Codex约99，Claude Opus最贵，约178块。",
    "按1美元约7.1元算，DeepSeek比GLM便宜14倍，比Claude Opus便宜89倍。",
    # 句12-13 能力排行榜（LeaderboardChart 条形）
    "便宜不等于弱。Terminal-Bench编程榜，Opus 4.8是85分，DeepSeek V4 Flash是82.7分，只差2.3分，GLM-5.2是81分。",
    "能力第一梯队，价格却差一个数量级。",
    # 句14-16 涨价预测（PricePrediction 价格轴 + 预测落点）
    "涨价后会涨到哪？按3倍算，Flash输出价到6块，还是最便宜的档位。",
    "按10倍算，到20块，正好贴近GLM的28块。",
    "我的判断，大概率涨到国产第一梯队附近，GLM就是参照系。",
    # 句17-18 解读 + 行动建议（SelectionPrinciples 三张卡）
    "对靠DeepSeek API跑业务的团队，这笔账现在就要算。",
    "先做三件事：盘点用量、盯紧公告、评估替代方案。",
    # 句19 Outro
    "关注，第一时间跟进DeepSeek调价方案。",
]


def main():
    units = NARRATION_SENTENCES
    print(f"[narrate] {len(units)} 句，交给 split_units 智能断句")

    out_dir = OUTPUT_ROOT / "narration"
    mp3, json_path = generate_narration_from_sentences(
        units, out_dir=out_dir, voice=VOICE, rate=RATE, fps=FPS,
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
