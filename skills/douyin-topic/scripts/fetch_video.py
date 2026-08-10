# -*- coding: utf-8 -*-
"""拉取代表视频原片（Playwright+msedge 拦截 mp4）或截图兜底（抖音选题 skill）。

链路（spike 0.1 实证）:
  打开 douyin.com/video/<group_id> → 拦截媒体响应:
    - media-video-avc1   视频轨 URL（ffmpeg 可抽关键帧）
    - media-audio-und-mp4a  音频轨 URL（faster-whisper 转写用）
  带 Referer: douyin.com + UA 即可下载完整轨。
  下载失败 → 截图兜底: 视频页截图 + 页面标题(描述)。

⚠️ 合规: 下载的原片仅作分析素材（转写/截图/拆结构），禁止直接发布。
"""
from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Optional

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# 同目录共享 UA 池（防指纹一致性被风控识别）
from fetch_sources import UA_POOL

# 浏览器 channel: Windows 本机 Chrome 损坏用 msedge; macOS/Linux 用系统 Chrome(真实浏览器,避抖音反爬)
CHANNEL = "msedge" if sys.platform == "win32" else "chrome"

MEDIA_VIDEO_MARK = "media-video-avc1"
MEDIA_AUDIO_MARK = "media-audio-und-mp4a"
PAGE_WAIT_MS = 10000  # 等播放器初始化/媒体请求（基准值，实际使用随机抖动）


def project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "hugo.toml").exists() or (parent / ".git").exists():
            return parent
    return current.parents[-1]


OUTPUT_ROOT = project_root() / ".douyin-topic"
PROFILE_DIR = OUTPUT_ROOT / "profile-douyin"


def _download(url: str, dest: Path) -> bool:
    """带 Referer + 随机 UA 下载 CDN 资源。成功返回 True。"""
    req = urllib.request.Request(url, headers={
        "User-Agent": random.choice(UA_POOL),
        "Referer": "https://www.douyin.com/",
        "Accept": "*/*",
    })
    try:
        with urllib.request.urlopen(req, timeout=120) as resp, open(dest, "wb") as fh:
            while True:
                chunk = resp.read(1 << 16)
                if not chunk:
                    break
                fh.write(chunk)
        return dest.stat().st_size > 1024  # 非空文件才认为成功
    except Exception:
        return False


def _ffprobe_duration(path: Path) -> float:
    """读取媒体时长（秒）。失败返回 0。"""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, encoding="utf-8",
    )
    try:
        return float(result.stdout.strip())
    except (ValueError, AttributeError):
        return 0.0


def extract_keyframes(video_path: Path, out_dir: Path, count: int = 5) -> list[str]:
    """从视频轨抽 count 张关键帧（均匀分布）。返回帧文件路径列表。"""
    duration = _ffprobe_duration(video_path)
    if duration <= 0:
        return []
    frames: list[str] = []
    for idx in range(count):
        position = duration * (0.1 + 0.8 * idx / max(count - 1, 1))
        frame_path = out_dir / f"frame_{idx + 1}.png"
        result = subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-ss", f"{position:.1f}",
             "-i", str(video_path), "-frames:v", "1", str(frame_path)],
            capture_output=True,
        )
        if result.returncode == 0 and frame_path.exists():
            frames.append(frame_path.name)
    return frames


def _humanize(page, min_scrolls: int = 2, max_scrolls: int = 6) -> None:
    """模拟真人阅读行为: 随机次数/步长/间隔的滚动 + 概率回滚 + 随机鼠标移动。

    固定节奏(等步长等间隔)是自动化最明显的指纹, 这里的每个参数都带随机性。
    """
    try:
        # 页面加载完成后的"阅读"停顿
        page.wait_for_timeout(random.randint(1200, 3000))
        for _ in range(random.randint(min_scrolls, max_scrolls)):
            page.mouse.wheel(0, random.choice([400, 600, 800, 1000, 1200, 1500]))
            page.wait_for_timeout(random.randint(900, 2600))
            # ~25% 概率向上回滚一点: 真人会回头扫一眼
            if random.random() < 0.25:
                page.mouse.wheel(0, -random.randint(200, 500))
                page.wait_for_timeout(random.randint(500, 1200))
        # 随机移动鼠标 1-2 次（播放器区域外散点）
        for _ in range(random.randint(1, 2)):
            page.mouse.move(random.randint(100, 1200), random.randint(200, 700))
            page.wait_for_timeout(random.randint(300, 900))
    except Exception:
        pass


def fetch_video(group_id: str, out_dir: Path, headless: bool = True) -> dict:
    """主流程：打开视频页 → 拦截媒体 → 下载 / 截图兜底。"""
    from playwright.sync_api import sync_playwright

    out_dir.mkdir(parents=True, exist_ok=True)
    video_url: Optional[str] = None
    audio_url: Optional[str] = None
    page_title = ""
    page_text = ""
    comments_text = ""

    with sync_playwright() as p:
        # 每次会话随机视口尺寸（固定 1440x900 也是指纹）
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            channel=CHANNEL,
            headless=headless,
            args=["--disable-blink-features=AutomationControlled", "--lang=zh-CN"],
            viewport={"width": random.randint(1410, 1536), "height": random.randint(860, 940)},
            user_agent=random.choice(UA_POOL),
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        def on_response(resp):
            nonlocal video_url, audio_url
            content_type = resp.headers.get("content-type", "") or ""
            url = resp.url
            if "video/mp4" not in content_type:
                return
            if MEDIA_VIDEO_MARK in url and video_url is None:
                video_url = url
            elif MEDIA_AUDIO_MARK in url and audio_url is None:
                audio_url = url

        page.on("response", on_response)
        url = f"https://www.douyin.com/video/{group_id}"
        # 打开页面前的随机停顿
        page.wait_for_timeout(random.randint(1000, 3000))
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=40000)
        except Exception:
            pass
        # 播放器初始化等待: 基准 10s ± 随机抖动 3s
        page.wait_for_timeout(PAGE_WAIT_MS + random.randint(-3000, 3000))
        try:
            page_title = page.title()
        except Exception:
            pass
        try:
            page_text = page.evaluate("() => document.body.innerText.slice(0, 800)")
        except Exception:
            pass
        # 人性化滚动到评论区（评论懒加载，需滚动触发）
        _humanize(page)
        try:
            comments_text = page.evaluate("() => document.body.innerText.slice(0, 4000)")
        except Exception:
            comments_text = ""
        # 兜底素材: 视频页截图（封面+标题+评论区顶部）
        page.screenshot(path=str(out_dir / "page.png"), full_page=False)
        ctx.close()

    result: dict = {
        "group_id": group_id,
        "page_title": page_title,
        "page_text": page_text,
        "comments_text": comments_text,
        "video_url": video_url,
        "audio_url": audio_url,
        "has_video": False, "has_audio": False,
        "keyframes": [],
        "download_note": "",
        "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    # 下载视频轨 + 音频轨（带 Referer）
    if video_url:
        result["has_video"] = _download(video_url, out_dir / "video.mp4")
        if result["has_video"]:
            result["keyframes"] = extract_keyframes(out_dir / "video.mp4", out_dir)
    if audio_url:
        result["has_audio"] = _download(audio_url, out_dir / "audio.mp4")
    if not result["has_video"] and not result["has_audio"]:
        result["download_note"] = "未取到媒体流（可能触发验证），已用页面截图兜底"

    (out_dir / "meta.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="拉取代表视频原片或截图兜底")
    parser.add_argument("--group-id", required=True, help="代表视频 group_id (aweme id)")
    parser.add_argument("--out", default=None, help="输出目录（默认 .douyin-topic/videos/<group_id>）")
    parser.add_argument("--headless", action="store_true", help="强制 headless（默认同 spike 参数）")
    args = parser.parse_args()

    out_dir = Path(args.out) if args.out else OUTPUT_ROOT / "videos" / args.group_id
    result = fetch_video(args.group_id, out_dir, headless=args.headless)

    print(f"✅ group_id={args.group_id}")
    print(f"   page_title: {(result['page_title'] or '')[:80]}")
    print(f"   has_video: {result['has_video']} | has_audio: {result['has_audio']} | keyframes: {len(result['keyframes'])}")
    print(f"   dir: {out_dir}")
    if result["download_note"]:
        print(f"   ⚠️ {result['download_note']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
