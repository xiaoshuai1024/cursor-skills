"""为 pi-agent-beats-claude-code 视频生成口播。复用 skill 的 video.narrate。

数据来源：文章 pi-agent-beats-claude-code.md（Databricks 测试数字 / Pi 官方能力清单，
不编造：90% 通过率、前沿 7 席占 4 席、便宜 1.2-2 倍、GLM $1.28 vs Opus $1.94、
你好 20000 vs 1500 token、4 核心工具、四种运行模式、15+ Provider、会话树、Skills）。

结构（内容驱动设计）：
  句0 Cover（数据钩子）
  句1 跑分速报（前沿 4 席 + 90% + 便宜一半）
  句2 模型层（旗舰同层 + GLM 价格 + 单价不等于总账）
  句3 上下文起点（你好 2 万 vs 1500 + 前缀缓存）
  句4 输出清洗（git log 裁剪 + 钩子改不了结果）
  句5 内核哲学（4 工具 + 我们没有做什么）
  句6 能力全景（四模式 / Provider / 会话树 / Skills / 上下文工程 / Packages）
  句7 二次开发（SDK + 扩展自己写 + OpenClaw）
  句8 边界（提示词粗时重型更稳 + 二八分工）
  句9 结论（模型租的 / 算总账 / Harness 是你的）
  句10 Outro
每句分句 ≤24 字，避免 split_units 硬切中文词。
用法：python scripts/narrate_pi_agent.py
"""
import json
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))

from video.config import OUTPUT_ROOT                          # noqa: E402
from video.narrate import generate_narration_from_sentences  # noqa: E402

VOICE = "zh-CN-YunxiNeural"
RATE = "+8%"
FPS = 60
AUDIO_NAME = "pi-agent-narration.mp3"

NARRATION_SENTENCES = [
    # 句0 Cover 数据钩子
    "一个个人维护的开源项目，在 Databricks 的真实代码库跑分里，把 Claude Code 和 Codex 挤到了旁边。便宜一半，分数打平。这次把 Pi 拆开讲清楚。",
    # 句1 跑分速报
    "Databricks 拿自家工程师合并过的 PR 当考题，几百万行代码，模型没见过，评分跑测试说话。性价比前沿线上七个点，Pi 占了四个。最高分九十，是 Pi 接 Opus 跑出来的。同一个模型换个壳，账单差一倍。",
    # 句2 模型层
    "模型这层别纠结。Opus、GPT、GLM 挤在同一层，分数差三个点以内。开源的 GLM，一块二毛八，贴着一块九毛四的 Opus。还有个坑：单价便宜不等于总账便宜。话多的模型，单价减半，总 token 翻倍，分数还低六个点。",
    # 句3 上下文起点
    "Pi 省钱的第一刀，在起点。在 Claude Code 里发一句你好，系统提示词带下来两万 token。Pi 做同样的事，不到一千五。这份前缀每一轮都跟着，它就是你这次对话的起步成本。",
    # 句4 输出清洗
    "第二刀在过程。模型跑 git log，原生输出一大串哈希、作者、日期、diff。Pi 的扩展先裁一刀，只留关键字段，工具输出砍掉八到九成。Claude Code 的钩子只能追加信息，改不了调用结果。Pi 的扩展可以。",
    # 句5 内核哲学
    "Pi 的设计主张一句话：框架适应人，不是人适应框架。默认内核只有四个工具，运行命令、读、写、编辑。没有子智能体，没有 MCP，连 UI 都是插件。官方文档有一节，叫我们没有做什么。每一项，都留了扩展的位置。",
    # 句6 能力全景
    "内核小，外围给的反而多。四种运行模式，从终端到 JSON RPC 到 SDK，会话和扩展不变。十五家模型起步，会话中途一键切换。会话是树不是线，跑歪了跳回任意节点重来。Skills 按需加载，装二十个不膨胀提示词。AGENTS.md 管约定，压缩策略都能换成你的。扩展打成包，一条命令装。",
    # 句7 二次开发
    "我在 Pi 上做过二次开发。SDK 拿来就用，会话存储换成数据库，工具落到沙盒里执行，接口本来就是开给你换的。过瘾的一点：扩展可以让 Pi 自己写。说一句需求，它读自己的文档，写出扩展，重载就生效。增长最快的 OpenClaw，底下跑的就是 Pi。",
    # 句8 边界
    "Pi 不是全赢。提示词只丢一句话的时候，Claude Code 那两万 token 会替你把意图补全，产出更完整。提示词写得越细，Pi 的优势越大。我的分工：日常八成给 Pi 加国产模型，剩下两成重活留给 Claude Code。",
    # 句9 结论
    "三句话带走。模型是租来的，旗舰挤在一层。算账算总账，token 效率比单价狠。Harness 是你能控制的变量，框架适应人，不是人适应框架。",
    # 句10 Outro
    "关注，看懂 AI 研发实战。",
]


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
    return "\n".join(L) + "\n"


def main() -> None:
    out_dir = OUTPUT_ROOT / "remotion-videos" / "pi-agent-beats-claude-code"
    out_dir.mkdir(parents=True, exist_ok=True)
    mp3, json_path = generate_narration_from_sentences(
        sentences=NARRATION_SENTENCES,
        out_dir=out_dir,
        voice=VOICE,
        rate=RATE,
        fps=FPS,
        audio_name=AUDIO_NAME,
    )
    import json
    data = json.loads(json_path.read_text(encoding="utf-8"))
    ts_path = out_dir / "narration.ts"
    ts_path.write_text(_to_ts(data), encoding="utf-8")
    print(f"mp3: {mp3}")
    print(f"json: {json_path}")
    print(f"ts: {ts_path}")
    print(f"[narrate] 共 {len(data['segments'])} 个意群单元，总时长 {data['total_seconds']:.2f}s")


if __name__ == "__main__":
    main()
