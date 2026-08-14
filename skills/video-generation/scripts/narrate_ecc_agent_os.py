"""为 ecc-agent-os 视频生成口播。复用 skill 的 video.narrate。

数据来源：文章 ecc-agent-os.md（ECC 仓库 README 原文 + What's Inside 组件目录，不编造）。
结构（内容驱动设计）：
  句0 Cover（24 万星钩子 + 把 agent 工程做成操作系统）
  句1 翻车与环境（agent 翻车三连 → harness 的含义，3 卡）
  句2 ECC 是什么（项目 + 五大件 6 卡）
  句3 能做什么·计划与证据（README 对照表 → TDD 证据链，3 卡）
  句4 能做什么·多 agent 与记忆（4 卡）
  句5 能做什么·安全（AgentShield，4 卡）
  句6 README 含金量（四处，4 卡）
  句7 skill 盘点（语言四件套 + 通用件，4 卡）
  句8 建议安装（7 个起步，5 卡）
  句9 三仓对比（LeaderboardChart：16.7/21/24 万星）
  句10 四个代价（AntiPatternWall）
  句11 结论（ConclusionFocus：模型负责聪明 · 环境负责刹车）
  句12 Outro（中性价值钩子，无诱导关注 CTA）
每句分句 ≤24 字、尽量 ≥7 字（目标 ~95 单元 ≈ 4.4 分钟）。
平台合规（douyin-compliance）：口播全程规避广告法极限词、诱导引流词与权威冒用词（词库见
douyin-compliance/references/word-list.md）；Outro 不用诱导 CTA，用中性价值钩子；发布时勾选 AI 生成声明。
用法：VIDEO_PROJECT_ROOT=<博客根> python scripts/narrate_ecc_agent_os.py
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
AUDIO_NAME = "ecc-agent-os-narration.mp3"
SLUG = "ecc-agent-os"

NARRATION_SENTENCES = [
    # 句0 Cover 24 万星钩子
    "一个仓库八个月拿到 24 万星，超过 Linux 内核，里面没有一行算法，全是 markdown 和 shell 脚本。它叫 ECC，把 agent 工程做成了操作系统。",
    # 句1 翻车与环境（3 卡）
    "让 agent 干活的都见过三种翻车。改个配置，它顺手动了测试文件。加个功能，它把三个模块的重构一起做了。问题不在模型，在环境。agent 干活的每一步，没人立规矩。给 agent 搭环境，就是 harness 的含义。",
    # 句2 ECC 是什么（6 卡）
    "这个仓库叫 ECC，作者是黑客松冠军。仓库简介一句话，给 agent 搭运行环境，让它每一步都有人管。五块组成：284 个 skill，68 个 agent，instincts 从会话里攒经验，memory 跨会话记状态，AgentShield 专扫安全。同一套定义挂在十几个工具上。",
    # 句3 能做什么·计划与证据（3 卡）
    "它能做什么，README 里一张对照表讲完。没有系统，计划消失在聊天记录里；有它，计划先落成文档再动手。写测试靠嘱咐，有它 TDD 变成红绿门禁，每一步带证据。",
    # 句4 能做什么·多 agent 与记忆（4 卡）
    "还有多 agent 分工。planner 出计划，tdd-guide 写测试，code-reviewer 用全新上下文审查，写的人不审自己。Memory Vault 让工具之间共享记忆，一个工具干一半，另一个接着干。",
    # 句5 能做什么·安全（4 卡）
    "安全也不靠自觉。AgentShield 一百零二条静态规则，一千二百八十二个测试，扫硬编码密钥、越权配置、hook 注入。加一条命令，就能把整个仓库当攻击面扫。",
    # 句6 README 含金量（4 卡）
    "它的 README 也值得读。安装三条路，每条都标了坑，还贴了安全警告。一张速查表把你想做的事映射到入口，另一张表告诉你每个命令背后是哪个 agent。五层分工讲得清，说明作者想明白了自己造的是什么。",
    # 句7 skill 盘点（4 卡）
    "284 个 skill 有规律。一门语言一套四件套，约定安全测试验证。Spring Boot 一套，Django 一套，骨架一模一样。api-design 管接口约定，tdd-workflow 管红绿门禁，article-writing 管去 AI 味的写作。",
    # 句8 建议安装（5 卡）
    "要装，别装全家桶。先装记忆 hooks，会话开始读进度，结束写回去。code-reviewer 带防御基线，白赚一层安全防线。api-design 拷进项目改改就能用。tdd-workflow 治说做完了的毛病。再加你技术栈的那套四件套。七个起步，跑一个小任务看看哪块真的被触发。",
    # 句9 三仓对比（LeaderboardChart）
    "放进坐标系看更清楚。官方仓库 16.7 万星，管格式。mattpocock 21 万星，管流程。ECC 24 万星，什么都给你。正确顺序：先学官方格式，再用 mattpocock 立流程，把 ECC 当零件库拆。",
    # 句10 四个代价（AntiPatternWall）
    "它的缺点和规模一样大。上下文税，元数据吃掉 2 到 4 万 token。概率触发，规则有一半时间不生效。安装陷阱，两条路叠加出重复 hooks。星数泡沫，围观的多，真用的少。",
    # 句11 结论（ConclusionFocus）
    "模型负责聪明，环境负责刹车。把工程师的护栏做成 agent 绕不过的环境，AI 写代码的质量就能追平资深工程师。不是模型变聪明了，是环境变严了。",
    # 句12 Outro（中性价值钩子）
    "看懂 agent 工程，从拆零件开始。下期接着拆。",
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
