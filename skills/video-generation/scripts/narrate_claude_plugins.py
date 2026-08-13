"""为 claude-plugins 视频生成口播。复用 skill 的 video.narrate。

数据来源：文章 claude-code-must-have-plugins.md（真实 star 数据，不编造）
          + 各项目 README 前半段（每个插件的"能做什么"，真实提取）。
Star 数为文章记录的量级（截至 2026-08，GitHub 每天在涨）。
覆盖完整性（skill 强制规则）：文章 12 个插件全部要有专属卡片，观点可简化、重要信息不遗漏。
每句分句 ≤24 字，避免 split_units 硬切中文词。
用法：python scripts/narrate_claude_plugins.py
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

# 口播文案（真实数据，全部来自文章 + 各项目 README 前半部分，不编造）
# 每句 = 一个场景段落；生成后按 units 序号映射到 config 场景
# 12 个插件按排行顺序全覆盖（skill「内容覆盖」强制规则）
NARRATION_SENTENCES = [
    # 句0 Cover
    "装完 Claude Code 还不够，装对插件和 skills 才是放大器。12 个必装开源插件，按 GitHub Star 排行，这篇一次盘清。",
    # 句1 Leaderboard 快速过（排行是什么 / 怎么排）
    "排行榜很简单：按 GitHub Star 从高到低排，Superpowers 26 万第一，后面的星数只作量级参考，每天在涨。",
    # --- 12 个插件卡片（按排行顺序，逐个全覆盖）---
    # 句2 Superpowers（README：方法论 + 先问后做 + 子 agent）
    "Superpowers 是一整套软件开发方法论：先问清你要什么，再拆出规格和实现计划，最后让子 agent 自主执行，能连跑几小时。",
    # 句3 ECC（README：agent harness 操作系统 + 五维度打包）
    # 注：避免顿号碎段（"把记忆、安全…"会被切成悬空"把记忆"字幕），改完整分句，五维度细节由卡片 desc 呈现
    "ECC 是 agent 性能优化系统，一次打包五个维度。",
    # 句4 karpathy-skills（README：单个 CLAUDE.md + Karpathy 观察）
    "karpathy-skills 最轻，就一个 CLAUDE.md 文件，把避坑直觉直接写进项目。",
    # 句5 graphify（README：/graphify 知识图谱 + 多模态 + 省 token）
    "graphify 把代码库转成知识图谱，本地解析、不依赖向量库，项目越大越值钱。",
    # 句6 caveman（README：简短说话 + 65% 少 token）
    "caveman 用穴居人式简短说话，同样答案、少 65% 输出 token。",
    # 句7 OpenSpec（README：spec 框架 + propose 工作流 + 哲学）
    "OpenSpec 走规格驱动：一句 propose，把你的想法落成 spec、设计和任务清单，灵活不僵化，迭代不瀑布。",
    # 句8 Context7（README：最新带版本文档直进上下文）
    "Context7 拉最新、带版本的文档和代码示例，直接放进上下文，专治编造 API 和过时的训练数据。",
    # 句9 Playwright MCP（README：无障碍快照 + 无视觉模型 + 轻量确定）
    "Playwright MCP 让 AI 驱动浏览器，用无障碍快照而非截图，轻量、确定、微软官方维护。",
    # 句10 claude-hud（README：显示上下文/工具/todo，黑盒透明化）
    "claude-hud 实时显示上下文用量、token 消耗，让 agent 不再是黑盒。",
    # 句11 compound-engineering（README：每步工程更轻松 + 工作流固化）
    # 注：避免"把规划/执行"顿号碎段；名称后逗号停顿，完整分句（规划-执行-验证细节由卡片 tagline 呈现）
    "compound-engineering，把复合工程方法论固化成工作流。",
    # 句12 claude-skills（README：技能超市 + 按域分组）
    "claude-skills 是技能超市，300 多个 skills 按域分组、量大管饱。",
    # 句13 pua（README：逼 agent 穷尽方案 + 证据优先）
    "pua 用企业话术逼 agent 穷尽方案，拿结果、贴证据才算完成。",
    # --- 观点段（可简化，不遗漏关键）---
    # 句14 选型三原则
    "选型就三条：按场景补能力、方法论只选一套、可观测和 token 不能省。",
    # 句15 结论（只留三个）
    "如果只留三个，我留 OpenSpec、Playwright MCP、Context7，分别管方向、执行、知识。",
    # 句16 Outro
    "关注，看更多 AI 工程化实践。",
]


def main():
    units = NARRATION_SENTENCES
    print(f"[narrate] {len(units)} 句，交给 split_units 智能断句")

    out_dir = OUTPUT_ROOT / "narration"
    mp3, json_path = generate_narration_from_sentences(
        units, out_dir=out_dir, voice=VOICE, rate=RATE, fps=FPS,
        audio_name="claude-plugins-narration.mp3",
    )

    data = json.loads(json_path.read_text(encoding="utf-8"))
    ts_path = OUTPUT_ROOT / "remotion-videos" / "claude-plugins" / "narration.ts"
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
