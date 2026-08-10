# -*- coding: utf-8 -*-
"""爆款拆解（抖音选题 skill Phase 2）。

输入: 视频目录（transcript.json + meta.json + frame_*.png）
输出: analysis.json + analysis.md
  拆解项:
    - 钩子（前 5 秒口播）
    - 段落结构（按 >2s 停顿分节，带时间轴）
    - 热评（从页面评论区文本提取高赞评论行）
    - 关键帧（frame_*.png 清单）
    - 文案（完整逐字稿）
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
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


NAV_CHROME = {
    "精选", "推荐", "AI抖音", "关注", "朋友", "我的", "直播", "放映厅", "短剧",
    "小游戏", "手机随时看更方便", "下载", "APP", "登录", "注册", "搜索", "首页",
    "热点", "消息", "我", "分享", "收藏", "转发", "评论", "点赞", "关注ta",
}


def extract_hook(segments: list[dict]) -> str:
    """钩子 = 前 5 秒开始的口播段；无则取首段。"""
    for seg in segments:
        if seg["start"] <= 5.0:
            return seg["text"]
    return segments[0]["text"] if segments else ""


def group_structure(segments: list[dict], gap: float = 2.0, max_dur: float = 60.0) -> list[dict]:
    """分段落：>gap 秒停顿断段；段内超过 max_dur 秒也强制断（长视频颗粒度兜底）。"""
    sections: list[dict] = []
    current: list[dict] = []
    prev_end: float | None = None
    for seg in segments:
        cur_start = current[0]["start"] if current else seg["start"]
        over_length = seg["end"] - cur_start > max_dur
        if prev_end is not None and (
            (seg["start"] - prev_end > gap and current) or over_length
        ) and current:
            sections.append(_section(current))
            current = []
        current.append(seg)
        prev_end = seg["end"]
    if current:
        sections.append(_section(current))
    return sections


def _section(segs: list[dict]) -> dict:
    return {
        "start": round(segs[0]["start"], 1),
        "end": round(segs[-1]["end"], 1),
        "text": "".join(s["text"] for s in segs),
    }


def extract_comments(comments_text: str, limit: int = 10) -> list[str]:
    """从页面评论区文本过滤出评论行（去导航/页脚噪声，去重保序）。"""
    lines = [line.strip() for line in (comments_text or "").split("\n") if line.strip()]
    filtered: list[str] = []
    for line in lines:
        if any(chunk in line for chunk in NAV_CHROME):
            continue
        if len(line) < 2:
            continue
        if line not in filtered:
            filtered.append(line)
    return filtered[:limit]


def keyword_freq(text: str, top_n: int = 10) -> list[tuple[str, int]]:
    """简单关键词频率：取评论/文案里出现≥2 次的 2-4 字中文词块。"""
    if not text:
        return []
    # 中文词块粗切: 连续的 CJK 字符
    blocks = re.findall(r"[一-鿿]{2,6}", text)
    # 过滤常见虚词/导航
    stop = NAV_CHROME | {"一个", "什么", "这个", "那个", "我们", "你们", "就是",
                         "真的", "知道", "可以", "没有", "是不是", "都是"}
    counter = Counter(
        block for block in blocks
        if block not in stop and len(set(block)) > 1
    )
    return counter.most_common(top_n)


def analyze_dir(video_dir: Path) -> dict[str, Any]:
    """从视频目录产出拆解结果。"""
    transcript_path = video_dir / "transcript.json"
    meta_path = video_dir / "meta.json"
    if not transcript_path.exists():
        return {"error": "缺少 transcript.json，先跑 transcribe.py"}

    transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    segments = transcript.get("segments") or []

    sections = group_structure(segments)
    comments = extract_comments(meta.get("comments_text", ""))
    frames = sorted(
        p.name for p in video_dir.glob("frame_*.png")
    )
    comment_blob = "".join(comments) + (transcript.get("full_text") or "")
    keywords = keyword_freq(comment_blob)

    return {
        "group_id": meta.get("group_id", ""),
        "duration": transcript.get("duration"),
        "hook": extract_hook(segments),
        "sections": sections,
        "comments": comments,
        "keywords": keywords,
        "keyframes": frames,
        "full_text": transcript.get("full_text", ""),
        "page_title": meta.get("page_title", ""),
    }


def render_markdown(analysis: dict) -> str:
    """可读拆解报告。"""
    lines: list[str] = []
    lines.append("━━━ 对标拆解 ━━━")
    if analysis.get("group_id"):
        lines.append(f"📼 原片: https://www.douyin.com/video/{analysis['group_id']} | 时长 {analysis.get('duration', '?')}s")
    lines.append(f"\n▸ 钩子(前5s): {analysis.get('hook', '')[:120]}")
    lines.append("\n▸ 段落结构:")
    for idx, sec in enumerate(analysis.get("sections", [])[:8], 1):
        lines.append(f"  [{sec['start']:>6}s-{sec['end']:<6}s] {sec['text'][:60]}")
    if analysis.get("comments"):
        lines.append("\n▸ 热评(页面抓取):")
        for comment in analysis["comments"][:5]:
            lines.append(f"  💬 {comment[:60]}")
    if analysis.get("keywords"):
        lines.append("\n▸ 关键词: " + "、".join(f"{k}({v})" for k, v in analysis["keywords"][:8]))
    if analysis.get("keyframes"):
        lines.append(f"\n▸ 关键帧: {len(analysis['keyframes'])} 张（{' '.join(analysis['keyframes'])}）")
    lines.append(f"\n▸ 完整文案({len(analysis.get('full_text', ''))}字):")
    lines.append(analysis.get("full_text", "")[:800])
    return "\n".join(lines)


def main() -> int:
    _utf8_stdio()
    parser = argparse.ArgumentParser(description="爆款拆解（钩子/结构/热评/关键帧）")
    parser.add_argument("--dir", required=True, help="视频目录（含 transcript.json + meta.json）")
    parser.add_argument("--out", default=None, help="analysis.json 输出路径")
    args = parser.parse_args()

    video_dir = Path(args.dir)
    analysis = analyze_dir(video_dir)
    if "error" in analysis:
        print(f"❌ {analysis['error']}")
        return 1

    out_json = Path(args.out) if args.out else video_dir / "analysis.json"
    out_json.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
    (video_dir / "analysis.md").write_text(render_markdown(analysis), encoding="utf-8")

    print(f"✅ 拆解完成 → {out_json}")
    print(render_markdown(analysis)[:900])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
