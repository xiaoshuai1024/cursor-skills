"""为 openspec-superpowers 视频生成口播。复用 skill 的 video.narrate。

数据来源：文章 ai-dev-openspec-superpowers-workflow.md（OpenSpec 四件套/六个 skill、
Superpowers plan 结构、真实仓库分布、5 条反模式，不编造）。
结构（内容驱动设计，对比/分工型文章）：
  句0 Cover（黄金 3 秒：装了还乱 → 两件不同的事）
  句1 为什么一个规格工具不够（OpenSpec 管变更规格 vs 项目目标不是 change 粒度）
  句2 双流水线并行（ParallelPipeline：两套并行，缺一半）
  句3 分工对比（粒度/产物/驱动方式 三维对照）
  句4 衔接（plan 是地图，change 是施工令）
  句5 决策表（要不要长期积累 一条判断）
  句6 反模式（5 条）
  句7 结论（3D 粒子汇聚：装完 OpenSpec 再补 Superpowers）
  句8 Outro
每句分句 ≤24 字，避免 split_units 硬切中文词。AI 读音由 tts 白名单展开（逐字母 A I）。
用法：python scripts/narrate_openspec_superpowers.py
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
AUDIO_NAME = "openspec-superpowers-narration.mp3"

# 口播文案（真实内容，全部来自文章，不编造）
# 每句 = 一个场景段落；生成后按 units 序号映射到 config 场景
# 去 AI 味：无禁词（兜底/铁证/说白了/先说/根子/扎眼）；「两件事」是观点锚点且后文明确展开（项目计划+变更规格）
NARRATION_SENTENCES = [
    # 句0 Cover 黄金 3 秒：装了还乱 → 不是工具的问题
    "OpenSpec 装了，Superpowers 也装了，项目照样乱。目录里两个都在，AI 还是直接改。问题不在工具，在没搞清它们管的是两件不同的事：一个管项目计划，一个管变更规格。",
    # 句1 为什么一个规格工具不够（OpenSpec 管变更规格）
    "OpenSpec 管一次变更的规格。改动固化成 change，放进仓库，proposal、spec、design、tasks 四件套，六个 skill 走流水线：explore 想清楚，propose 生成，apply 施工，archive 归档。它管到的最小单位，是一次变更。",
    "但一整个项目目标不是 change 的粒度。把公众号自动发布做出来，拆开是几十个变更。谁管这几十个怎么排、阶段怎么分、整个目标收敛没有？那是项目计划层的事。",
    # 句2 双流水线并行（Superpowers 管项目计划）
    "Superpowers 管一个项目的计划。plans 目录下一个 plan 一份：Goal 定目标，Architecture 定架构，Tech Stack 定技术栈，最后是 checkbox 任务清单，subagent 按计划逐条执行，勾完一个推进一个。",
    "两套并行，一条管项目目标，一条管每次变更。只上 OpenSpec，项目级的目标没人拆解跟踪；只上 Superpowers，变更级的行为没人定义验收。这不是二选一，是缺一半。",
    # 句3 分工对比（粒度/产物/驱动方式）
    "分工看三样：粒度、产物、驱动方式。OpenSpec，粒度一次变更，产物 changes 四件套，六个 skill 驱动，规格增量，归档合并进主规格。Superpowers，粒度一个项目，产物 plans 计划文件，subagent 逐条执行，计划全局，任务用 checkbox 跟踪。",
    # 句4 衔接（plan 是地图，change 是施工令）
    "两套怎么接？plan 是地图，change 是施工令。plan 拆出来的大块任务，细化成具体的变更规格。apply 施工的是每个 change，服务的是 plan 画出的整张地图。plan 回答项目做到什么程度算完，change 回答这次改动怎么做才符合约定。",
    # 句5 决策表（要不要长期积累 一条判断）
    "什么情况走哪个，判断标准只有一条：要不要长期积累。新项目目标明确，走 Superpowers 铺全局计划。既有功能迭代，走 OpenSpec 定义行为、留档归档。大项目出现架构级变更，两层一起走。一次性探索，explore 聊透再动手。",
    # 句6 反模式（5 条）
    "五个反模式，对号入座：把 change 当项目计划用，四件套写成巨型需求书。把 plan 当变更规格用，plan 膨胀到没人读。apply 完不 archive，能力没攒进主规格，下次又从头再来。同一个任务两套都建，重复记账。最隐蔽的是只装不用，工具吃灰，AI 还是裸奔。",
    # 句7 结论（3D 粒子：装完 OpenSpec 再补 Superpowers）
    "两套不是抢同一个位置，管的粒度天生不同。把项目级的事交给计划层，变更级的事交给规格层，AI 的产出才从会写代码，变成有章法地交付。装完 OpenSpec 再补上 Superpowers，这另一半才是很多人缺的那一块。",
    # 句8 Outro
    "关注我，看懂 AI 研发实战。",
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
    ts_path = OUTPUT_ROOT / "remotion-videos" / "openspec-superpowers" / "narration.ts"
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
