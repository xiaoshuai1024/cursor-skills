"""为 ai-dev-stop-discipline 视频生成口播。复用 skill 的 video.narrate。

数据来源：文章 ai-dev-stop-discipline.md（mattpocock/skills 的 25 个 skill + 六关决策路由，不编造）。
结构（内容驱动设计，spec: video-content-driven-design）：
  句0 Cover（三种翻车钩子 + 21万 Star 亮相）
  句1 核心概念（隐性判断 → 可执行流程）
  句2 第一关·需求盘问（grill-with-docs/grill-me/grilling/codebase-design/wayfinder/research·to-questionnaire）
  句3 共享语言 CONTEXT.md（最酷的技巧 + ADR）
  句4 第二关·落盘规格（to-spec/to-tickets/测试驱动开发）
  句5 第三关·实现审查（implement/code-review/diagnosing-bugs）
  句6 第四关·冲突重构（解冲突/架构治理/domain-modeling）
  句7 第五关·试探交接传承（prototype/handoff/wizard/writing-for-agents/wait-what/teach）
  句8 主干串线（idea→ship + 三匝道 + ask-matt，ParallelPipeline）
  句9 tdd 反模式（seam 规则 + 实现耦合/同义反复/横切片，AntiPatternWall）
  句10 积分功能走全程（4 步卡片）
  句11 什么时候别用（红线 4 条 + 安全审计回退）
  句12 四个失败模式（全部条目的覆盖映射）
  句13 结论（上手建议 + 模型负责快流程负责停）
  句14 Outro
每句分句 ≤24 字，避免 split_units 硬切中文词。
用法：python scripts/narrate_ai_dev_stop_discipline.py
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
AUDIO_NAME = "ai-dev-stop-discipline-narration.mp3"
SLUG = "ai-dev-stop-discipline"

# 口播文案（真实数据，全部来自文章，不编造）
# 每句 = 一个场景段落；生成后按 units 序号映射到 config 场景
# 断句规范：只用中文标点（split_units 只认 ，。、：；），每分句 ≤24 字避免硬切；
#   分句尽量 ≥7 字（意群太碎每个单元吃 ~2s TTS 开销，成片会过长，目标 ~110 单元 ≈ 4.3 分钟）
# 读音：AI 白名单自动逐字母；tdd 口播用「测试驱动开发」；长 skill 名口播用短说法，
#   屏幕卡片显示全名（覆盖判定以屏幕文字为准）
NARRATION_SENTENCES = [
    # 句0 Cover 三种翻车钩子 + 项目亮相（7 单元）
    "让 AI 写代码，你一定见过三种翻车。作者 Matt Pocock，把这套解法开源了。21万 Star，25个 skill，把工程师自律做成了可执行流程。",
    # 句1 核心概念（5 单元）
    "它的核心是把资深工程师的隐性判断固化成流程。每个 skill，对应一个隐性判断。AI 没有肌肉记忆，但可以把肌肉记忆写成流程。",
    # 句2 第一关·需求盘问（10 单元，6 卡：research/to-questionnaire 走屏幕卡）
    "第一关，把需求盘清楚。grill-with-docs 反复盘问，grill-me 没仓库就纯访谈，每问都带推荐答案。grilling 底层画设计树，只问前提已满足的问题。codebase-design 管接口。wayfinder 管巨型模糊项目，先建决策票地图。",
    # 句3 共享语言 CONTEXT.md（8 单元）
    "盘问的产出是一份 CONTEXT.md，作者说这是最酷的技巧。同一个问题之前二十多个字，之后只剩五个词，materialization cascade。术语统一后 AI 导航代码库更快，还能省下 token。难逆的决策写进架构决策记录。",
    # 句4 第二关·落盘规格（7 单元）
    "第二关把共识落盘。to-spec 把对话综合成规格，直接发到 issue tracker。to-tickets 拆纵向切片，每张票声明阻塞边。测试驱动开发的 skill，红绿重构一次一个切片。",
    # 句5 第三关·实现审查（8 单元）
    "第三关实现和审查。implement 每张票开独立会话，每票之间清上下文。code-review 双轴并行，标准轴查仓库规范，spec 轴查需求本意。diagnosing-bugs 先建稳定复现，再最小化问题再验证假设再回归测试。",
    # 句6 第四关·冲突重构（7 单元）
    "第四关管三年后的可维护性。解 merge 冲突的 skill，逐 hunk 追溯双方意图绝不 abort。架构治理的 skill，扫描该治理的账不是救援。domain-modeling 挑战术语，一个词干三件事就是灾难。",
    # 句7 第五关·试探交接传承（10 单元，6 卡）
    "第五关试探交接传承。prototype 用一次性代码回答设计问题，试探完折叠进真代码。handoff 把会话压成交接文档。wizard 生成交互式向导，带人配密钥跑控制台。writing-for-agents，写给 agent 读的文档。wait-what 没听懂重解释。teach 跨多会话教学。",
    # 句8 主干串线（9 单元，ParallelPipeline）
    "六关不是平的官方给了一条主干。idea 进来，先盘问收敛再落盘规格，然后循环实现最后 ship。三个匝道汇入主干。外部需求堆积走 triage，东西坏了走 diagnosing-bugs，巨大模糊项目走 wayfinder。不确定用哪个 ask-matt 替你选刀。",
    # 句9 tdd 反模式（8 单元，AntiPatternWall）
    "测试驱动开发为什么值得单独拆，因为它把测试先行写成了规则。测试只写在预先约定的 seam 上。实现耦合就是 mock 内部对象测私有方法。同义反复就是断言用同款方式重算期望。横切片就是先写完所有测试再写实现。重构不属于测试驱动开发循环，它属于 review。",
    # 句10 积分功能走全程（9 单元，4 卡）
    "拿加积分功能走一遍感受这套东西的密度。第一步 grill-with-docs 五轮问答，每问带推荐答案需求变成规格。第二步 to-tickets 拆三张纵向切片，先连上积分入账到展示这条链路。第三步 implement 开独立会话，测试驱动开发写测试，review 双轴审。第四步全部票完成就 ship。",
    # 句11 什么时候别用（10 单元，5 卡：红线 4 条 + 安全审计）
    "但这套东西也写了什么时候别用。单文件小改直接裸改，杀鸡别用牛刀。目标明确无歧义直接动手。一次性脚本 prototype 都嫌重。没冲突别预防性跑解冲突 skill。标准就一句，动作复杂度小于流程开销直接做。安全审计没有专属 skill，回退 security-reviewer。",
    # 句12 四个失败模式（6 单元）
    "不用这套 skill 会怎样。四个失败模式。Agent 没做你要的事 grill 系列治。Agent 太啰嗦共享语言治。代码跑不起来测试驱动开发治。代码库变泥球架构 skill 治。",
    # 句13 结论（8 单元，ConclusionFocus）
    "好在把隐性判断落成了流程，缺在默认你有规范的工程环境。它治流程治不了人。想上手先装 grill-with-docs，再练测试驱动开发，再让 ask-matt 选刀。模型负责快，流程负责停。",
    # 句14 Outro（2 单元）
    "关注，看懂 AI 研发实战。",
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
    # 打印单元索引，供 config.ts 场景 span 映射
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
