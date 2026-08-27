"""为 ai-agent-engineering-evolution 视频生成口播。复用 skill 的 video.narrate。

数据来源：文章 ai-agent-engineering-evolution.md（Harness 工程：AI 编程从命令体系到自治体系的演进）。
结构（内容驱动设计）：
  句0 Cover（一年演进四段，harness 是主角）
  句1 四段演进总览（Prompt → Context → Harness → 自治，4 卡）
  句2 模型四个先天缺陷（AntiPatternWall）
  句3 阶段一 Prompt 工程（3 卡 + 天花板）
  句4 阶段二 Context 工程（5 卡：三层处理/渐进式披露/技能化/MCP/知识库）
  句5 阶段三 Harness 工程·命令（4 卡：命令≠脚本/31条/自证/盘问与门禁）
  句6 阶段三 Harness 工程·loop 与 daemon（4 卡）
  句7 阶段四 自治体系（4 卡：人退三件事/信任分级/事故即规范/多 agent）
  句8 五条认知（5 卡）
  句9 数字说话（DataReveal：31 条/15K→3K/512 功能/信任 20 次）
  句10 结论（ConclusionFocus：模型负责聪明 · 环境负责纪律）
  句11 Outro（中性价值钩子，无诱导关注 CTA）
每句分句 ≤24 字、尽量 ≥7 字（目标 ~95 单元 ≈ 4.4 分钟）。
平台合规（platform-compliance）：口播全程规避广告法极限词、诱导引流词与权威冒用词（词库见
platform-compliance/references/word-list.md）；Outro 不用诱导 CTA，用中性价值钩子；发布时勾选 AI 生成声明。
用法：VIDEO_PROJECT_ROOT=<博客根> python scripts/narrate_ai_agent_engineering_evolution.py
"""
import json
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]   # skill 根（video-generation）
sys.path.insert(0, str(SKILL / "scripts"))    # 供 import video 模块

from video.config import OUTPUT_ROOT                          # noqa: E402
from video.narrate import generate_narration_from_sentences  # noqa: E402

VOICE = "zh-CN-YunxiNeural"
RATE = "+8%"
FPS = 60
AUDIO_NAME = "ai-agent-engineering-evolution-narration.mp3"
SLUG = "ai-agent-engineering-evolution"

NARRATION_SENTENCES = [
    # 句0 Cover：一年演进四段，harness 是主角
    "用了一年 AI 编程，我把演进拆成四段：提示词、上下文、harness、自治体系。真正改变效率的，是第三段：harness 工程。",
    # 句1 四段演进总览（4 卡）
    "第一段，把话说清楚，是 Prompt 工程。第二段，管好它看什么，是 Context 工程。第三段，让规矩焊死在流程里，是 Harness 工程。第四段，让 AI 在边界里自己干，是自治体系。每一段，都是被上一段的天花板逼出来的。",
    # 句2 四个先天缺陷（AntiPatternWall）
    "模型天生有四个毛病。有输入就输出，没人喊停就一直干。上下文是稀缺资源，长任务必然掉质量。无状态，每次对话都是新生。指令遵从率，随链路衰减。",
    # 句3 阶段一 Prompt 工程（3 卡）
    "第一段最朴素：把该说的都写进提示词。短任务效果惊艳，规则写清楚几乎不出错。撞墙也快：规则靠自觉，链路一长就失效。知识攒不下来，每次对话重来。长任务不可控，跑到第八步开始自由发挥。结论是别在提示词层面跟注意力较劲了，规则该从让它记住，变成让系统执行。",
    # 句4 阶段二 Context 工程（5 卡）
    "第二段，把提示词升级成上下文工程。大结果外置，摘要替代，历史压缩，三层处理做完，长任务掉质量明显缓解。渐进式披露：规则按需加载，上下文从一万五千 token 降到三千以内。技能化：把重复流程固化成 skill。MCP 把工具接进来，工具能摸到的东西，不让模型想象。知识库用 RAG，跨会话的知识活下来。知识攒起来了，纪律没统一，于是进入第三段。",
    # 句5 阶段三 Harness 工程·命令（4 卡）
    "第三段，关键词是流程契约。命令不是脚本：脚本描述做什么，命令描述做完怎么确认做对。约束行为边界，定义验收条件，违约就阻断。我在项目里攒了 31 条命令，三千四百多行，挂在研发每个环节上。需求环节先盘问，测试环节锁红绿，部署完必须自证。512 个功能能交付，靠的就是自证嵌在每一步里。",
    # 句6 阶段三 Harness 工程·loop 与 daemon（4 卡）
    "还有 loop engineering：审查、修复、验证，自动循环到收敛。人不在循环里，只在出口。夜间巡检 daemon：每天零点自动拉开发分支的代码，跑八步全量测试。挂了按类型分流，环境问题直接告警，代码问题 AI 自己修。只提 MR，不合并。第二天早上，要么全过，要么已修复待审查，要么修不动了快来。",
    # 句7 阶段四 自治体系（4 卡）
    "第四段，把命令、技能、知识、巡检串成一张网。人退到三件事：定规则、审边界、看报告。信任是分级的，不是二元的。新能力先 shadow 状态跑，只记录不生效。再进 probation，结果生效但有人审核。连续验证通过才转 active。多 agent 协调不靠聊天，靠同一个纪律层。",
    # 句8 五条认知（5 卡）
    "最后，五条认知收尾。翻车不怪模型，怪流程里没有停。先减少犯错的机会，再增加做对的能力。纪律不靠人盯，靠系统守。信任是分级的，跳过人工确认，就毁掉整个信任。每一阶段的天花板，都是下一阶段的起点。",
    # 句9 数字说话（DataReveal）
    "数字说话。31 条命令，三千四百多行，焊在流程里。上下文从一万五千 token，压到三千。三个人，两个月，交付 512 个功能。信任建起来要连续二十次正确，毁掉只要一次。",
    # 句10 结论（ConclusionFocus）
    "AI 工程化的每一步，都是在让 AI 稳定地、大规模地干活。模型负责聪明，环境负责纪律。",
    # 句11 Outro（中性价值钩子）
    "看懂 harness 工程，从一条命令开始。",
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
    ts_path = OUTPUT_ROOT / "remotion-videos" / SLUG / "narration.ts"
    ts_path.parent.mkdir(parents=True, exist_ok=True)
    ts_path.write_text(_to_ts(data), encoding="utf-8")
    print(f"[narrate] TS → {ts_path}")
    print(f"[narrate] 共 {len(data['segments'])} 个意群单元，总时长 {data['total_seconds']:.2f}s")
    for i, s in enumerate(data["segments"]):
        print(f"  U{i:03d} [{s['start_frame']:>6}..{s['end_frame']:>6}] {s['text']}")


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
