"""为 ai-buzzwords-one-line 视频生成口播。复用 skill 的 video.narrate。

数据来源：文章 ai-buzzwords-one-line.md（六层主线 + 进阶七词 + 四个坑，不编造）。
结构（内容驱动设计）：
  句0 Cover（黑话看不懂钩子 + 一条主线）
  句1 主线地图（六层叠加：底座/沟通/动手/流程/工具/环境，6 卡）
  句2 大模型（4 卡：智商底座/上下文窗口/推理能力/换模型）
  句3 提示词（4 卡：是什么/角色背景/要求边界/输出格式）
  句4 Agent（4 卡：是什么/循环/多 Agent/误解）
  句5 Skill（4 卡：是什么/blog-writing/wechat-publishing/误解）
  句6 MCP（4 卡：是什么/Tool/Resource/Prompt）
  句7 Harness（4 卡：是什么/CLAUDE.md/钩子/误解）
  句8 进阶三件套（Token/上下文窗口/记忆，3 卡）
  句9 进阶其余（RAG/多模态/微调/A2A，4 卡）
  句10 四个坑（AntiPatternWall：概念通胀/定义漂移/跳级速成/伪需求）
  句11 结论（ConclusionFocus：黑话是地图 · 不是门槛）
  句12 Outro
每句分句 ≤24 字、尽量 ≥7 字（意群太碎每个单元吃 ~2s TTS 开销，目标 ~100 单元 ≈ 4.5 分钟）。
读音：AI 白名单自动逐字母；缩写按单词读（Token/RAG/A2A/MCP 可识别）。
用法：VIDEO_PROJECT_ROOT=<博客根> python scripts/narrate_ai_buzzwords_one_line.py
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
AUDIO_NAME = "ai-buzzwords-one-line-narration.mp3"
SLUG = "ai-buzzwords-one-line"

NARRATION_SENTENCES = [
    # 句0 Cover 黑话看不懂钩子 + 一条主线
    "有个前端朋友发我篇 AI 教程，说满屏黑话看不懂。我刚碰 AI 开发时，也是这个表情。现在这些词用进了我的每天，回头看其实就一条线。AI 从只会回答，到越来越能自己干活。",
    # 句1 主线地图（6 卡）
    "先把主线看清楚。六个词是六个站，一个比一个更能自己干活。大模型决定聪不聪明，提示词决定听不听得懂。Agent 让它自己动手，Skill 让它按流程干活。MCP 让它够得着工具，Harness 让它进得了大项目。这六层是叠加的，不是六个选项。",
    # 句2 大模型（4 卡）
    "第一层大模型，AI 的智商底座。GPT DeepSeek Claude，这些名字都是大模型，干的活就是预测下一个词。它决定干活的天花板，模型不行提示词再好也白搭。换模型就是换大脑，便宜但变笨贵但真能干活。它不是高级搜索引擎是现场推理。",
    # 句3 提示词（4 卡）
    "第二层提示词，把需求说成人话。同一个模型会不会问结果天差地别。它解决的是需求翻译问题，模型定下限提示词定上限。我有三个固定动作，角色背景要求边界输出格式三样给全。提示词不是越长越好是信息密度。",
    # 句4 Agent（4 卡）
    "第三层 Agent，会自己干活的下属。普通大模型你说一步它做一步，Agent 给个目标它自己走完。它内部是个循环，接目标拆计划调工具看结果不满意就重来。它不是高级聊天框是能自己把活干完的下属。",
    # 句5 Skill（4 卡）
    "第四层 Skill，把工作流封装成技能。同一个活干多了，就把步骤话术检查点写进包，AI 每次按同一套标准干。我的博客写作不是靠灵感，是靠一条九步流水线。发公众号也一样，封面高亮内链一次跑完。它不是提示词模板，是带脚本和文档的完整包。",
    # 句6 MCP（4 卡）
    "第五层 MCP，接上外部世界的手。以前每家插件一个接口，AI 学一个要学一套。MCP 把协议统一了，装一个数据库 MCP，AI 就能查你的表。它有三件套工具资源提示。它不是插件换个名字是公开标准。",
    # 句7 Harness（4 卡）
    "第六层 Harness，让 AI 进得了大项目。小项目是一张桌子一眼看到全貌，大项目是一栋楼推门就迷路。Harness 是这栋楼的导览，哪层是核心哪些房间不能乱进。基础四样，说明文档行为准则常用技能自动检查。它不是给 AI 写个 README 是运行环境。",
    # 句8 进阶三件套（3 卡）
    "主线六层讲完了，还有一批散词。先讲三个跟日常最相关的。Token 是 AI 的货币计费按它算。上下文窗口是临时记忆，窗口小聊长就忘。记忆是长期存储，写进文件下次再读。",
    # 句9 进阶其余（4 卡）
    "剩下四个知道干什么的就够。RAG 是回答前先翻你的资料，治 AI 编答案。多模态是看得见图听得见声音。微调是把知识刻进模型，个人基本用不上。A2A 是 Agent 之间互相派活，单兵作战进团队协作。",
    # 句10 四个坑（AntiPatternWall）
    "黑话还藏着四个坑。概念通胀厂商把 Agent 往产品名里塞。定义漂移同一个词各家说法不一样。跳级速成三分钟教程跳过底座。伪需求补个提示词的事硬上全套体系。",
    # 句11 结论（ConclusionFocus）
    "以后再看到新词，拿主线对一下，它让 AI 多干了一步什么，就知道值不值得学。黑话的门槛不在名词在没有地图。工具会换代模型会升级主线不会变。",
    # 句12 Outro
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
