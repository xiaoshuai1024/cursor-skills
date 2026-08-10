# -*- coding: utf-8 -*-
"""两阶段编排（抖音选题 skill）。

  phase1  选题（不下载原片）:
    fetch_sources → filter_score → 对 Top 候选生成假设大纲（--rough）
  phase2  深挖（用户确认模仿后）:
    fetch_video → transcribe（无音频轨则从视频抽）→ analyze → outline --deep

用法:
  py -3.11 -m pipeline phase1 [--top 5] [--no-cache]
  py -3.11 -m pipeline phase2 --group-id <id> [--headful]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def _utf8_stdio() -> None:
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


SCRIPTS_DIR = Path(__file__).resolve().parent
OUTPUT_ROOT = project_root() / ".douyin-topic"


def _run(*args: str) -> int:
    """跑同目录脚本（继承 PYTHONIOENCODING）。"""
    cmd = [sys.executable, "-m"] + list(args)
    print(f"▶ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(SCRIPTS_DIR))
    return result.returncode


def phase1(top: int = 5, no_cache: bool = False) -> int:
    latest = OUTPUT_ROOT / "latest.json"
    topics_json = OUTPUT_ROOT / "topics.json"
    topics_md = OUTPUT_ROOT / "topics.md"
    rough_dir = OUTPUT_ROOT / "rough_outlines"

    code = _run("fetch_sources", "--out", str(latest), *(["--no-cache"] if no_cache else []))
    if code != 0:
        return code
    code = _run(
        "filter_score",
        "--in", str(latest),
        "--out", str(topics_json),
        "--markdown", str(topics_md),
    )
    if code != 0:
        return code

    # 对 Top 候选生成假设大纲（不下载），让用户先判断模仿哪条
    topics = json.loads(topics_json.read_text(encoding="utf-8"))
    candidates = sorted(
        topics["series"]["hot"] + topics["series"]["growth"],
        key=lambda x: x.get("score") or 0, reverse=True,
    )[:top]
    rough_dir.mkdir(parents=True, exist_ok=True)
    index_lines = ["# Phase 1 假设大纲（未下载原片）\n"]
    for item in candidates:
        item_path = rough_dir / f"{item['word'][:20]}.json"
        item_path.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
        out_path = item_path.with_name(item_path.stem + "_rough.md")
        code = _run("outline", "--rough", str(item_path), "--out", str(out_path))
        if code != 0:
            return code
        index_lines.append(f"- [{item['score']}] {item['word']} → {out_path.name}")
    (rough_dir / "INDEX.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")

    print(f"\n✅ Phase 1 完成")
    print(f"   选题清单: {topics_md}")
    print(f"   假设大纲: {rough_dir}/INDEX.md  (共 {len(candidates)} 条)")
    print("   确定模仿 → make topic-deep id=<group_id>")
    return 0


def _check_imitated(group_id: str) -> Optional[dict]:
    """查已仿写台账: 命中返回台账条目，否则 None。"""
    ledger = SCRIPTS_DIR.parent / "imitated_ledger.json"
    if not ledger.exists():
        return None
    try:
        data = json.loads(ledger.read_text(encoding="utf-8"))
        for item in data.get("imitated", []):
            if item.get("aweme_id") == group_id:
                return item
    except (json.JSONDecodeError, OSError):
        return None
    return None


def phase2(group_id: str, headful: bool = False, skip_fetch: bool = False) -> int:
    # 已仿写过的作品直接跳过深挖（避免重复仿写同一部原片）
    imitated = _check_imitated(group_id)
    if imitated:
        print(f"⏭ {group_id} 已在已仿写台账（{imitated.get('output_slug')}），跳过深挖")
        print(f"   产物: {imitated.get('imitation_artifact')}")
        return 0
    video_dir = OUTPUT_ROOT / "videos" / group_id
    transcript_json = video_dir / "transcript.json"
    analysis_json = video_dir / "analysis.json"

    if not skip_fetch:
        code = _run("fetch_video", "--group-id", group_id, *(["--headless"] if not headful else []))
        if code != 0:
            return code
    elif not video_dir.exists():
        print(f"❌ --skip-fetch 但目录不存在: {video_dir}")
        return 1

    audio = video_dir / "audio.mp4"
    video_mp4 = video_dir / "video.mp4"
    meta = json.loads((video_dir / "meta.json").read_text(encoding="utf-8")) if (video_dir / "meta.json").exists() else {}

    if transcript_json.exists():
        print(f"⏭ 已有逐字稿，跳过转写")
    elif audio.exists() and meta.get("has_audio"):
        code = _run("transcribe", "--audio", str(audio), "--out-dir", str(video_dir))
        if code != 0:
            return code
    elif video_mp4.exists() and meta.get("has_video"):
        print("⚠️ 无音频轨，从视频抽取 16k wav 转写")
        code = _run("transcribe", "--video", str(video_mp4), "--out-dir", str(video_dir))
        if code != 0:
            return code
    else:
        print("⚠️ 未取到媒体流，仅截图兜底，跳过转写/拆解")
        return 0

    if analysis_json.exists():
        print(f"⏭ 已有拆解，跳过 analyze")
    else:
        code = _run("analyze", "--dir", str(video_dir))
        if code != 0:
            return code
    code = _run("outline", "--deep", str(analysis_json))
    if code != 0:
        return code

    print(f"\n✅ Phase 2 完成")
    print(f"   拆解: {video_dir / 'analysis.md'}")
    print(f"   可抄大纲: {video_dir / 'deep_outline.json'}")
    print("   ⚠️ 原片仅分析用，仿写稿需差异化重写，禁止直接发布")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="抖音选题两阶段编排")
    sub = parser.add_subparsers(dest="phase", required=True)

    p1 = sub.add_parser("phase1", help="选题（不下载）")
    p1.add_argument("--top", type=int, default=5, help="生成假设大纲的候选数")
    p1.add_argument("--no-cache", action="store_true", help="忽略缓存强制刷新三源")

    p2 = sub.add_parser("phase2", help="下载+拆解+可抄大纲")
    p2.add_argument("--group-id", required=True, help="代表视频 group_id")
    p2.add_argument("--headful", action="store_true", help="显示浏览器窗口（默认 headless）")
    p2.add_argument("--skip-fetch", action="store_true", help="复用已下载目录（已有逐字稿/拆解自动跳过）")

    args = parser.parse_args()
    _utf8_stdio()
    if args.phase == "phase1":
        return phase1(args.top, args.no_cache)
    return phase2(args.group_id, args.headful, args.skip_fetch)


if __name__ == "__main__":
    raise SystemExit(main())
