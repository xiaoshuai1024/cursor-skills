"""为 claude-code-ccswitch-domestic-models 视频生成口播。复用 skill 的 video.narrate。

数据来源：文章 claude-code-ccswitch-domestic-models.md（真实经历 + 有来源的成本数字，不编造）。
口径（用户强调，2026-08-02）：封号后全量切到国产模型，切一次不再回官方。
  不是「重的用官方、批量用国产」；国产阵营内部可以换更强的（Qwen3-Coder/Kimi），官方号不碰。
结构（内容驱动设计）：
  句0 Cover（痛点钩子 + 方案承诺）
  句1 核心概念（Claude Code 强在框架层，模型是发动机）
  句2 成本账（差 178 倍 + 98% 缓存折扣）
  句3 步骤① 装 CcSwitch
  句4 步骤② 加国产供应商（50+ 预设 + DeepSeek/Qwen/Kimi/GLM）
  句5 步骤③ 一键切换并验证（Claude Code 热重载即时生效 / Codex 重启终端）
  句6 Codex 适配（Responses API 官方点名 + 命令行 Agent 82.7 分）
  句7 两个坑位（热重载口径修正 / 别死扛一个国产模型）
  句8 结论（全量国产，切一次不再回官方）
  句9 Outro
每句分句 ≤24 字，避免 split_units 硬切中文词。AI 用「子代理」替代，规避读音问题。
口径修正（2026-08-03 三校，对齐改稿后文章）：Claude Code 是热重载即时生效，只有 Codex 需要重启终端；
  原二轮稿「重启会话/缓存旧配置」与文章矛盾，已修正。
用法：python scripts/narrate_ccswitch.py
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
AUDIO_NAME = "claude-code-ccswitch-domestic-models-narration.mp3"

# 口播文案（真实数据，全部来自文章 + 用户真实使用口径，不编造）
# 每句 = 一个场景段落；生成后按 units 序号映射到 config 场景
# 断句规范：只用中文标点（split_units 认 ，。、：；？！），每分句 ≤24 字避免硬切；问句单独成段
# 去 AI 味 + 抖音化（2026-08-03 二轮）：黄金 3 秒钩子（开头抛冲突）、口语化 + 情绪词（白装/省下/掉到）、
#   具体数字前置、短句节奏、悬念结尾。口号「全量国产/切一次不回官方」全文只说一次（结论场景）。
NARRATION_SENTENCES = [
    # 句0 Cover 黄金 3 秒：官方号被封是最大痛点，直接抛冲突 + 方案
    "Claude Code 官方号又被封了？别慌，换模型就行。开源免费的 CcSwitch，把国产模型接进同一个客户端，账单直接省九成九。",
    # 句1 核心概念（框架层 vs 发动机，删教学腔「先理解一件事」）
    "Claude Code 强在框架层：Skills 封装工作流，MCP 接外部工具，子代理按角色并行干活，全都在客户端里。模型是发动机，客户端是底盘，底盘好用，换个发动机照样开。",
    # 句2 成本账（数字前置 + 反差 + 98% 缓存折扣）
    "价格差到离谱：官方 Opus 输入五美元每百万 token，V4 Flash 缓存命中零点零二八，差一百七十八倍。缓存命中折扣给到百分之九十八，批量任务命中缓存，成本再降一个量级。重度用户月账单，从上百美元直接掉到个位数。",
    # 句3 步骤① 装 CcSwitch（动词驱动 + 类比「装 QQ」拉近距离）
    "第一步装 CcSwitch，GitHub 搜 cc-switch 下载，跟装 QQ 一样简单。",
    # 句4 步骤② 添加国产供应商（覆盖 50+ 预设 + DeepSeek/Qwen/Kimi/GLM 四模型名）
    "第二步加供应商，Provider 页点添加，内置五十多家预设，DeepSeek、Qwen、Kimi、GLM，选一个粘个 key 就能用。",
    # 句5 步骤③ 切换 + 验证（修正：Claude Code 热重载即时生效，Codex 才重启终端）
    "第三步切过去验证，选中 DeepSeek 点切换，地址密钥原子写进 env 段，不用手改一个字符。Claude Code 热重载，斜杠 status 立刻变 V4 Flash。Codex 要重启终端，认证和模型配置一起写好了。",
    # 句6 Codex 适配（Responses API 官方点名 + 命令行 Agent 82.7 分）
    "为什么 Codex 也能直接跑？V4 Flash 官方适配了 Codex，原生支持 Responses 协议，国产模型里第一个被官方点名。别的国产模型要本地代理转协议，它不用，命令行 Agent 基准测试还拿了八十二点七分。",
    # 句7 两个坑位（修正热重载口径：查 env 段 + Codex 重启终端）
    "两个坑最常踩：第一个，切换后 status 还是官方模型。Claude Code 热重载，不该这样，八成 env 段被别的工具改回去，查配置就行；Codex 那边记得重启终端。第二个，国产模型偶尔抽风，别死扛一个，Qwen3-Coder、Kimi 换着来。",
    # 句8 结论（金句 + 全量国产口号唯一一次）
    "封号之后我全量跑国产，切一次不回官方。国产内部怎么换都行，官方号不碰了。",
    # 句9 Outro（悬念钩子引导关注）
    "关注我，下期教你国产阵营里怎么挑更合适的模型。",
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
    ts_path = OUTPUT_ROOT / "remotion-videos" / "claude-code-ccswitch-domestic-models" / "narration.ts"
    ts_path.parent.mkdir(parents=True, exist_ok=True)
    ts_path.write_text(_to_ts(data), encoding="utf-8")
    print(f"[narrate] TS → {ts_path}")
    print(f"[narrate] 共 {len(data['segments'])} 个意群单元，总时长 {data['total_seconds']:.2f}s")


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
