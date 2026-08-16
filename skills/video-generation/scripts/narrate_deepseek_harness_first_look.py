"""为 deepseek-harness-first-look 视频生成口播。复用 skill 的 video.narrate。

数据来源：文章 deepseek-harness-first-look.md（DeepSeek 开源自研 Harness，一切皆插件，第一手实测）。
结构（内容驱动设计）：
  句0 Cover（发布当天 3 万星 + 一切皆插件钩子）
  句1 发布速报（1.5万→2.9万星，Everything is a Plugin）
  句2 反常设计（3 卡：没有 CLI / node 后台 + Web UI / 一行安装 3080 端口）
  句3 架构核心（3 卡：Cordis 插件树 / 没有特权核心 / 卸载自动撤销）
  句4 三层结构（3 卡：bundle / profile / patch）
  句5 实测 133 插件（4 卡：SQLite 会话/OTEL 遥测/API key 只写）
  句6 headless 实测（4 卡：第一任务 / 多 agent / 子代理独立会话 / zstd JSONL 472 事件）
  句7 与 Claude Code 对比（ComparisonTable3D：形态/扩展/模型/会话/成熟度）
  句8 插件生态（4 卡：275 仓库 / 12 秒安装 / 值得装的四个）
  句9 三个坑（AntiPatternWall：Node 22.14+ / 破坏性变更 / 生态参差）
  句10 三段演进（3 卡：单体 CLI → 协议外挂 → 插件化平台）
  句11 判断（ConclusionFocus：装好跑通看懂，别全切）
  句12 Outro（中性价值钩子，无诱导关注 CTA）
每句分句 ≤24 字、尽量 ≥7 字（目标 ~95 单元 ≈ 4.4 分钟）。
平台合规（platform-compliance）：口播全程规避广告法极限词、诱导引流词与权威冒用词（词库见
platform-compliance/references/word-list.md）；Outro 不用诱导 CTA，用中性价值钩子；发布时勾选 AI 生成声明。
用法：VIDEO_PROJECT_ROOT=<博客根> python scripts/narrate_deepseek_harness_first_look.py
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
AUDIO_NAME = "deepseek-harness-first-look-narration.mp3"
SLUG = "deepseek-harness-first-look"

NARRATION_SENTENCES = [
    # 句0 Cover：3 万星 + 一切皆插件
    "DeepSeek 开源自研 harness：模型、工具、agent loop，一切皆插件。发布当天，GitHub 趋势榜登顶，12 小时逼近 3 万星。",
    # 句1 发布速报
    "仓库创建于八月十三号，发布时一万五千星。到我实测，已经两万九千星，十二小时不到。真正让我放下手头活去装的，是仓库描述里那句话：everything is a plugin，一切皆插件。",
    # 句2 反常设计（3 卡）
    "用惯了 Claude Code，第一反应是找 dsh 命令。装完发现方向反了：没有 CLI，是个 node 后台服务，操作界面在浏览器。安装只有一行：npx 加包名加 web。启动后监听本地 3080 端口，浏览器打开就是完整界面。",
    # 句3 架构核心（3 卡）
    "核心架构基于 Cordis，一个插件化框架。运行中的 dsh，是一棵启动时组合出来的插件树，没有一块代码是特权核心。模型适配器是插件，工具注册表是插件，会话日志是插件，连 agent 主循环本身都是插件。任何一块都能替换，卸载自动撤销，不留残留。",
    # 句4 三层结构（3 卡）
    "组合方式分三层。bundle 是分发格式，官方内置三个基础包。profile 是命名组合，web 和 headless 是出厂模板。patch 是覆盖机制，按插件 id 替换配置，按顺序叠加。一条命令就能打印出实际启动的插件树，我跑出来四百九十行。",
    # 句5 实测 133 插件（4 卡）
    "设置页的插件列表，就是一切皆插件的现场：133 个插件，全部挂着挂载启用状态。会话查询走 SQLite，遥测导出走 OpenTelemetry，连这些都是插件。API key 只写，界面只显示打码后的描述符。你能想到的每一块能力，都插件化了。",
    # 句6 headless 实测（4 卡）
    "真实任务，用 headless 模式跑。第一个任务，列出目录、总结 README，整条链路是通的。第二个任务上强度：主 agent 开发表单网页，同时派子代理写测试。子代理是独立会话，有自己的事件流，继承沙箱和权限，跑完把结果送回主会话。会话是 zstd 压缩的 JSONL 事件流，一次任务四百七十二个事件，每一步都可回放。",
    # 句7 与 Claude Code 对比（ComparisonTable3D）
    "和 Claude Code 摆在一起比。形态：一个终端 CLI，一个后台服务加浏览器。扩展：一个内置功能加外挂，一个一切皆插件。模型：一个官方模型为主，一个任意 OpenAI 兼容协议都收。会话：一个本地文件，一个 JSONL 加 SQLite 查询。成熟度：一个生产可用，一个开发者预览。落点是一句话：Claude Code 是把一件事做透的产品，dsh 是让你自己组装 Agent 的平台。",
    # 句8 插件生态（4 卡）
    "生态也爆发了：发布十二小时，社区目录收录约 275 个仓库。装一个 JSON 查询工具，一条命令，十二秒挂载完成。值得装的不少：dsh-cc-tui 补上终端界面，dsh-memory 做跨会话记忆，dsh-agent-teams 一句话驱动多 agent 团队，dsh-vscode 原生接进 VS Code。官方没做的事，全有人在用插件做。",
    # 句9 三个坑（AntiPatternWall）
    "坑也实在。第一个：Node 版本硬门槛，v22.13 直接起不来，报错跟版本毫无关系，要 22.14 以上，建议直接上 24。第二个：官方明说会有破坏性变更，三天迭代六个版本。第三个：生态质量参差，装插件前过一遍源码，是基本动作。",
    # 句10 三段演进（3 卡）
    "放进时间线看，Agent 工具链的形态演进很清楚。第一阶段，单体 CLI：能力内置，改任何一块都要等官方发版。第二阶段，协议外挂。MCP 和 Skills 把能力接进来，harness 还是封闭单体。第三阶段，插件化平台：把核心两个字删掉了，模型、工具、会话、UI，全可替换。harness 从产品，变成了平台。",
    # 句11 判断（ConclusionFocus）
    "我的做法：装好它，跑通它，看懂它的插件树，插件挑着装，但不把生产工作流迁过去。等插件 API 稳定、CI 跑出真实案例，再花半天认真试一遍。",
    # 句12 Outro（中性价值钩子）
    "看懂 agent 工程，从拆插件开始。",
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
