# -*- coding: utf-8 -*-
"""大纲生成（抖音选题 skill，两阶段）。

--rough（Phase 1，不下载）: 给定选题条目（热榜/涨粉话题 + 代表视频 id），
    生成「假设大纲」——先猜这条视频大概怎么拍、观众期待什么，用于在选题阶段
    就判断「值不值得模仿 / 模仿哪条」。映射到本站存量文章作为内容素材。

--deep（Phase 2，用户确认下载后）: 读拆解结果（analysis.json），
    生成「可抄大纲」+「仿写脚本」——同结构换内容，逐行可投产（可喂 video-generation）。

合规: 仿写脚本是对标结构的差异化重写，绝不直接搬运原片文案/画面。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def _utf8_stdio() -> None:
    """运行时把 stdout/stderr 绑成 utf-8（PYTHONIOENCODING 需在启动前设才生效）。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass


def project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "hugo.toml").exists() or (parent / ".git").exists():
            return parent
    return current.parents[-1]


def list_blog_assets() -> list[str]:
    """本站存量文章标题（content/posts/*.md 的 title）。用于选题→素材映射。"""
    posts_dir = project_root() / "content" / "posts"
    if not posts_dir.exists():
        return []
    titles: list[str] = []
    for md in sorted(posts_dir.glob("*.md")):
        text = md.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("title"):
                title = line.split("=", 1)[-1].strip().strip('"').strip("'")
                if title:
                    titles.append(title)
                break
    return titles


def match_blog_assets(topic_word: str) -> list[str]:
    """找标题里含话题关键词/方向词的存量文章。"""
    titles = list_blog_assets()
    tokens = [t for t in topic_word.replace("/", " ").split() if len(t) >= 2]
    hits: list[str] = []
    for title in titles:
        lowered = title.lower()
        if any(token.lower() in lowered for token in tokens):
            hits.append(title)
        elif any(kw in lowered for kw in ("ai", "claude", "cursor", "大模型", "agent", "提示词")):
            # 方向兜底: AI 相关文章都算可复用素材
            hits.append(title)
    return hits[:6]


def rough_outline(topic: dict) -> dict[str, Any]:
    """Phase 1 假设大纲：不下载，从话题元信息 + 方向经验推断。"""
    word = topic.get("word") or topic.get("title") or "未知话题"
    matched = topic.get("matched_keywords") or [topic.get("match_keyword") or ""]
    assets = match_blog_assets(word)
    is_hot = topic.get("source") != "c"
    series = "🔥热度系列" if is_hot else "📈涨粉系列"

    # 热门话题的常见拍摄结构（假设，待 Phase 2 用真实拆解校验）
    if is_hot:
        hypothesis_sections = [
            ("钩子", f"「最近『{word}』刷屏了，但你看到的 90% 都说错了」→ 点破认知差"),
            ("讲现象", f"这个『{word}』到底在火什么，3 句话讲清来龙去脉"),
            ("拆本质", "给受众一个能带走的技术判断（不是情绪）"),
            ("给方案", "普通开发者该做什么 / 用什么工具 / 避什么坑"),
            ("互动收尾", "抛一个问题引导评论区讨论，借热度涨互动"),
        ]
    else:
        hypothesis_sections = [
            ("钩子", f"「为什么都在聊『{word}』，却没人讲清楚怎么上手」→ 定位稀缺"),
            ("建信任", "用自己的真实实践讲『怎么开始的、当时卡在哪』"),
            ("给步骤", "一步步可跟做的路径（贴具体工具/命令/提示词）"),
            ("给判断", "哪些做法对、哪些是坑，给出专家判断"),
            ("求关注", "「关注我，后面继续更这个方向」→ 涨粉转化"),
        ]

    return {
        "phase": "rough",
        "mode": "假设大纲（Phase 1，未下载原片，结构与内容为推断）",
        "topic": word,
        "series": series,
        "matched_keywords": matched,
        "group_id": topic.get("group_id") or "",
        "video_url": f"https://www.douyin.com/video/{topic['group_id']}" if topic.get("group_id") else "待 Phase 2 定位",
        "hypothesis_sections": [
            {"role": role, "desc": desc} for role, desc in hypothesis_sections
        ],
        "blog_assets": assets,
        "decision_hints": [
            "判断 1: 话题是否 = 你的真实经历？没有亲身实践不追热度，改跟涨粉系列。",
            "判断 2: 假设结构与你的文章素材是否对得上？对不上则换一条。",
            "判断 3: 确认模仿 → make topic-deep id=<group_id> 下载并做真实拆解。",
        ],
    }


def render_rough_markdown(outline: dict) -> str:
    lines: list[str] = []
    lines.append("━━━ 抖音选题 · Phase 1 假设大纲 ━━━")
    lines.append(f"📌 话题: {outline['topic']}  [{outline['series']}]")
    lines.append(f"📼 代表视频: {outline['video_url']}")
    if outline.get("matched_keywords"):
        lines.append(f"🎯 命中关键词: {', '.join(outline['matched_keywords'])}")
    lines.append(f"\n⚠️ 未下载原片，以下为「假设结构」，用于决定模仿哪条。")
    for idx, sec in enumerate(outline["hypothesis_sections"], 1):
        lines.append(f"  {idx}. [{sec['role']}] {sec['desc']}")
    if outline.get("blog_assets"):
        lines.append("\n📚 可复用本站素材:")
        for title in outline["blog_assets"]:
            lines.append(f"  - {title}")
    lines.append("\n🔎 决策清单:")
    for hint in outline["decision_hints"]:
        lines.append(f"  - {hint}")
    lines.append("\n确认模仿 → make topic-deep id=<group_id>")
    return "\n".join(lines)


def _infer_work_type(title: str) -> tuple[str, str, list[tuple[str, str]]]:
    """按标题语义推断作品类型与假设结构（作品级 Phase 1）。"""
    t = title.lower()
    if any(k in t for k in ("教程", "安装", "上手", "从零", "攻略", "指南", "教学", "保姆级", "无痛")):
        return ("教程型", "📈 涨粉系列（教程建信任）", [
            ("钩子", f"「{_main_clause(title)}」→ 用标题痛点开头，承诺『照着做就会』"),
            ("痛点", "『为什么你装了用不起来/学不会』——点破新手卡点"),
            ("给步骤", "逐步可跟做：安装 → 配置 → 跑通第一个用例（贴具体命令/参数）"),
            ("给判断", "哪些设置是关键、哪些坑别踩，给出专家级取舍"),
            ("求关注", "「关注我，下期讲怎么接你的业务」→ 垂直涨粉"),
        ])
    if any(k in t for k in ("区别", "选哪个", "到底", "为什么", "别碰", "要不要", "测评")):
        return ("观点对比型", "🔥 热度系列（观点引战）", [
            ("钩子", f"「{_main_clause(title)}」→ 用对比冲突做钩子，制造站队"),
            ("摆事实", "两个对象各 3 句话讲清定位/适用场景"),
            ("给判断", "给出明确结论：『我的做法是 X』（不留模糊地带）"),
            ("给反例", "戳破常见误用/被神化的点，制造差异化观点"),
            ("互动收尾", "抛问题『你站哪边』引导评论区站队讨论"),
        ])
    if any(k in t for k in ("本地部署", "生成", "方法", "隐藏", "免费", "自动", "搭")):
        return ("案例演示型", "🔥 热度系列（演示吸睛）", [
            ("钩子", f"「{_main_clause(title)}」→ 先放结果画面（生成物/效果）再讲过程"),
            ("演示", "完整走一遍：输入 → 工具 → 输出（用真实项目/素材）"),
            ("讲原理", "这背后的机制/限制 3 句话讲清，别只给『魔法』"),
            ("给方案", "你也能复现：步骤 + 需要的工具/成本"),
            ("互动收尾", "「想要完整配置评论区扣 1」引导互动"),
        ])
    return ("蹭热点型", "🔥 热度系列（热点放大）", [
        ("钩子", f"「{_main_clause(title)}」→ 借热点争议/悬念开头，点破认知差"),
        ("讲现象", "这个热点到底在讲什么，3 句话讲清来龙去脉"),
        ("拆本质", "给受众一个能带走的技术判断（不是情绪宣泄）"),
        ("给方案", "普通开发者该怎么看/怎么做"),
        ("互动收尾", "抛开放问题引导评论，借热点涨互动"),
    ])


def _main_clause(title: str) -> str:
    """标题主句: 去 hashtag、去重复、截前 30 字。"""
    head = re.split(r"[#＃]", title)[0].strip()
    return head[:30] if head else title[:30]


def rough_work_outline(work: dict) -> dict[str, Any]:
    """Phase 1 作品级假设大纲：按标题推断类型/结构，不下载。"""
    title = work.get("title") or work.get("word") or "未知作品"
    wtype, series, sections = _infer_work_type(title)
    assets = match_blog_assets(title)
    aweme = work.get("aweme_id") or work.get("group_id") or ""

    return {
        "phase": "rough",
        "mode": "作品级假设大纲（Phase 1，未下载原片，结构按标题推断）",
        "work_title": title,
        "author": work.get("author") or "",
        "likes": work.get("likes_raw") or "",
        "duration": work.get("duration") or "",
        "type": wtype,
        "series": series,
        "aweme_id": aweme,
        "video_url": f"https://www.douyin.com/video/{aweme}" if aweme else "待定位",
        "hypothesis_sections": [
            {"role": role, "desc": desc} for role, desc in sections
        ],
        "blog_assets": assets,
        "decision_hints": [
            "判断 1: 这条作品的类型/结构，和你擅长的内容对得上吗？",
            "判断 2: 素材能否从本站存量文章取（避免编造经历）？",
            "判断 3: 确认模仿 → make topic-deep id=<aweme_id> 下载并做真实拆解。",
        ],
    }


def render_rough_work_markdown(outline: dict) -> str:
    lines: list[str] = []
    lines.append("━━━ 抖音选题 · Phase 1 作品假设大纲 ━━━")
    lines.append(f"🎬 作品: {outline['work_title']}")
    if outline.get("author"):
        lines.append(f"👤 作者: @{outline['author']}  {outline.get('likes') or ''}赞  时长{outline.get('duration') or '-'}")
    lines.append(f"🏷 类型: {outline['type']}  [{outline['series']}]")
    lines.append(f"📼 作品链接: {outline['video_url']}")
    lines.append(f"\n⚠️ 未下载原片，以下为按标题推断的「假设结构」：")
    for idx, sec in enumerate(outline["hypothesis_sections"], 1):
        lines.append(f"  {idx}. [{sec['role']}] {sec['desc']}")
    if outline.get("blog_assets"):
        lines.append("\n📚 可复用本站素材:")
        for title in outline["blog_assets"]:
            lines.append(f"  - {title}")
    lines.append("\n🔎 决策清单:")
    for hint in outline["decision_hints"]:
        lines.append(f"  - {hint}")
    lines.append("\n确认模仿 → make topic-deep id=<aweme_id>")
    return "\n".join(lines)


def deep_outline(analysis: dict) -> dict[str, Any]:
    """Phase 2 可抄大纲：从真实拆解（钩子/段落/热评/关键帧）生成仿写稿。"""
    full_text = analysis.get("full_text") or ""
    sections = analysis.get("sections") or []
    comments = analysis.get("comments") or []
    keywords = analysis.get("keywords") or []
    hook = analysis.get("hook") or ""
    group_id = analysis.get("group_id") or ""

    # 从真实段落提取「结构骨架」（角色推断 + 原片片段摘要）
    # 角色按短视频叙事 archetype 循环，长视频多段时重复循环而非落到「段落N」
    structure: list[dict] = []
    role_archetypes = ["钩子", "铺垫/引入", "展开", "转折/对比", "干货", "干货", "情绪/冲突", "收尾/互动"]
    for idx, sec in enumerate(sections[:12]):
        role = role_archetypes[idx % len(role_archetypes)]
        structure.append({
            "role": role,
            "time": f"{sec['start']}s-{sec['end']}s",
            "original_gist": sec["text"][:60],
            # 仿写方向：换同角色内容，不搬原文
            "rewrite_hint": "",
        })

    # 钩子差异化: 保留「制造认知差」结构，换成本号语境
    hook_rw = (
        f"原钩子主题: 「{hook[:50]}」。"
        "仿写: 用你站内的真实项目/经验替换，保持『点破认知差 + 立即给判断』的句式。"
    )

    # 评论区情绪点 → 仿写脚本的互动收尾
    if comments:
        top_comment = comments[0][:40]
        interaction = f"评论区提到「{top_comment}」——收尾抛出同一个疑问但给反向观点，引导站队讨论。"
    else:
        interaction = "收尾抛开放问题「你觉得这事未来一年会怎么变」，引导评论。"

    keyword_list = [k for k, _ in keywords[:6]]

    # 逐行可抄脚本: 口播骨架 + 画面提示（差异化重写，非搬运）
    script_lines: list[str] = []
    script_lines.append("── 仿写口播稿（同结构换内容）──")
    script_lines.append("")
    for idx, sec in enumerate(structure):
        script_lines.append(f"【{sec['role']}】({sec['time']})")
        script_lines.append(f"  🎙 口播: <把你的 {sec['role']} 内容写在这里，替代原片「{sec['original_gist'][:24]}」>")
        script_lines.append(f"  🎬 画面: <关键帧参考 {analysis.get('keyframes', [])}>")
        script_lines.append("")
    script_lines.append(f"【收尾】\n  🎙 {interaction}\n  🎬 引导评论/关注")

    return {
        "phase": "deep",
        "mode": "可抄大纲（Phase 2，已下载并真实拆解原片）",
        "group_id": group_id,
        "original_url": f"https://www.douyin.com/video/{group_id}" if group_id else "",
        "duration": analysis.get("duration"),
        "hook_rw": hook_rw,
        "structure": structure,
        "keywords": keyword_list,
        "interaction": interaction,
        "compliance": "仿写稿与原片同结构、不同内容；原片仅作结构参考，禁止直接搬运/直接发布。",
        "script": "\n".join(script_lines),
    }


def render_deep_markdown(outline: dict) -> str:
    lines: list[str] = []
    lines.append("━━━ 抖音选题 · Phase 2 可抄大纲 ━━━")
    lines.append(f"📼 对标原片: {outline['original_url']} | 时长 {outline.get('duration')}s")
    lines.append(f"\n{outline['hook_rw']}")
    lines.append("\n▸ 结构骨架（原片实测 → 仿写方向）:")
    for idx, sec in enumerate(outline["structure"], 1):
        lines.append(f"  {idx}. [{sec['role']}] ({sec['time']})")
        lines.append(f"     原片: {sec['original_gist'][:40]}")
        lines.append(f"     仿写: {sec['rewrite_hint'] or '<替换为你的内容>'}")
    if outline.get("keywords"):
        lines.append("\n▸ 关键词(评论区/文案高频): " + "、".join(outline["keywords"]))
    lines.append(f"\n▸ 互动收尾: {outline['interaction']}")
    lines.append("\n" + outline["script"])
    lines.append(f"\n⚠️ {outline['compliance']}")
    return "\n".join(lines)


def main() -> int:
    _utf8_stdio()
    parser = argparse.ArgumentParser(description="大纲生成（--rough 选题假设 / --deep 可抄大纲）")
    parser.add_argument("--rough", default=None, help="Phase 1: 选题条目 JSON（含 word/group_id/source）")
    parser.add_argument("--deep", default=None, help="Phase 2: analysis.json 路径")
    parser.add_argument("--out", default=None, help="输出 JSON 路径")
    args = parser.parse_args()

    if args.rough and args.deep:
        sys.exit("❌ --rough 与 --deep 互斥")
    if not args.rough and not args.deep:
        sys.exit("❌ 需提供 --rough 或 --deep")

    if args.rough:
        topic = json.loads(Path(args.rough).read_text(encoding="utf-8"))
        if topic.get("aweme_id") or topic.get("title"):
            outline = rough_work_outline(topic)
            md = render_rough_work_markdown(outline)
        else:
            outline = rough_outline(topic)
            md = render_rough_markdown(outline)
    else:
        analysis = json.loads(Path(args.deep).read_text(encoding="utf-8"))
        outline = deep_outline(analysis)
        md = render_deep_markdown(outline)

    out_json = Path(args.out) if args.out else (
        Path(args.rough).with_name("rough_outline.json") if args.rough
        else Path(args.deep).with_name("deep_outline.json")
    )
    out_json.write_text(json.dumps(outline, ensure_ascii=False, indent=2), encoding="utf-8")
    print(md)
    print(f"\n✅ 大纲已写入 {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
