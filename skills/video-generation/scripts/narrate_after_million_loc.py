"""为 after-million-loc-my-skills 视频生成口播。复用 skill 的 video.narrate。

数据来源：文章 after-million-loc-my-skills.md（真实 skill 名 + 各 skill"管什么"，不编造）。
结构（内容驱动设计，spec: video-content-driven-design）：
  句0 Cover（事故钩子）
  句1 核心概念（skill 是肌肉 / CLAUDE.md 是骨头）
  句2-7 六组核心 skill（A 方向对齐 → B 编码纪律 → C 验证审查 → D 排障诊断 → E 安全命门 → F 多 agent 并行），逐组展开
  句8 反模式（精简 2-3 条）
  句9 底层逻辑收尾
  句10 Outro
每句分句 ≤24 字，避免 split_units 硬切中文词。
用法：python scripts/narrate_after_million_loc.py
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
AUDIO_NAME = "after-million-loc-narration.mp3"

# 口播文案（真实数据，全部来自文章 + kangdou-fullstack 自定义 skill，不编造）
# 每句 = 一个场景段落；生成后按 units 序号映射到 config 场景
# 六组核心 skill 全覆盖（spec「内容覆盖完整性」强制规则），反模式 + 底层逻辑在片中
# 断句规范：只用中文标点（split_units 只认 ，。、：；），每分句 ≤24 字避免硬切
# AI 读法：白名单已把 "AI" → "诶爱"（自然读 A-I）；口播里 "AI" 只保留 4 处，
#   其余用 "agent"，降低 "AI" 出现频率（用户反馈）
NARRATION_SENTENCES = [
    # 句0 Cover 事故钩子（agent×2：钩子 + 主旨句；不用 AI，规避读音 + 降频率）
    # 口径修正（2026-08-02 二轮）：不提"一百来个 skill"，直说核心 23 个（用户要求，
    # 挂 100+ 是囤积反模式不值得立题）；全文统一"核心 23 个"。
    "百万行代码全是 agent 写的，没翻车不是模型强，是项目里沉淀了二十三个核心 Skill。它不教 agent 新知识，它把工程纪律变成 agent 逃不掉的流程。",
    # 句1 核心概念
    "先记住一句话：skill 是肌肉，CLAUDE.md 是骨头。skill 负责某种活儿怎么干，CLAUDE.md 焊死绝对不能违反的底线。",
    # 句2 A 方向对齐（4 卡 + 新增 plan-eng-review = 5 卡）
    "第一组，动手之前，把方向对齐。brainstorming 强制先聊透意图再写代码。to-prd 把结论沉淀成能力清单，暴露未决决策。ubiquitous-language 统一术语，消灭歧义。grill-me 像面试官拷问方案，把决策逼到死角。plan-eng-review 写方案后先锁架构，数据流、边界、测试覆盖过一遍。",
    # 句3 B 编码纪律（3 卡 + 新增 component-reference / ui-spec-enforcer = 5 卡）
    "第二组，写代码时，把纪律焊死。test-driven-development，红绿重构，agent 写的代码不写测试你拿什么信它。executing-plans 每步一个验证门，治 agent 一口气做完说搞定的毛病。ECC 模式组统一风格，十个 agent 写出来像一个人。component-reference，写前端先查组件库，能复用就别重造。ui-spec-enforcer 按 v1.0 规范，强制 UI 实现，风格不漂移。",
    # 句4 C 验证审查（4 卡 + 新增 e2e-archi = 5 卡）
    "第三组，验证与审查，防 agent 自欺。verification-before-completion，治最致命的毛病，没跑就说跑通了。ai-regression-testing，专抓自己写自己审的盲区。批量审查并行二十一个 subagent 逐维度扫。receiving-code-review，收到意见先判断再改。e2e-archi 方案阶段查架构分层，事务边界、测试矩阵、安全合规一起过。",
    # 句5 D 排障诊断（2 卡）
    "第四组，排障与诊断。systematic-debugging，强制结构化诊断，不是看到报错就猜。diagnose 走复现到最小化到假设到修复的循环。顺序不能反，先想清楚假设再跑复现。数据丢失事故就是这么查出来的。",
    # 句6 E 安全命门（3 卡）
    "第五组，安全与数据，项目的命门。security-review，涉及支付密钥强制启用。git-guardrails 用 hook，拦危险 git 命令。CLAUDE.md 焊死三条，DELETE 三必查，定时任务必须有 dry-run，禁止裸 jdbcTemplate 写。",
    # 句7 F 多 agent 并行（3 卡）
    "第六组，多 agent 并行，百万行的吞吐策略。dispatching-parallel-agents，把互不依赖的任务并行派出去。using-git-worktrees，保证隔离不互踩。handoff 把会话压成交接文档。底层就三件事，约束、可验证、隔离。",
    # 句8 反模式（3 条）
    "别把 skill 当收藏品。装而不用，三个月没触发就该摘掉。追新模型不攒 skill，模型每代都强，你项目里那个不带 where 的 DELETE 还在。纪律和知识，职责要分清。",
    # 句9 底层逻辑收尾（agent×1：主旨回响；不用 AI）
    "追模型是消费，攒 skill 是投资。百万行能稳，靠的是把约束、可验证、隔离，变成 agent 逃不掉的流程。别急着追更强的模型，先想清楚你的项目最怕 agent 在哪翻车，从那个点沉淀第一个 skill。",
    # 句10 Outro（口号，不用 AI）
    "关注，看懂 agent 研发实战。",
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
    ts_path = OUTPUT_ROOT / "remotion-videos" / "after-million-loc-my-skills" / "narration.ts"
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
