# -*- coding: utf-8 -*-
"""手机端信息流预览：把渲染帧模拟成抖音竖屏信息流里的实际观感。

管线（PIL 绘制，无外部素材依赖）：
  1. 帧缩到 1080 宽（横屏 16:9 → 1080×607）
  2. 贴进 1080×1920 黑边画布（居中，y≈656——抖音横屏视频的真实位置）
  3. 叠加抖音 UI mock：右侧头像/点赞/评论/分享图标列 + 底部账号名/标题/BGM
     文案区 + 进度条（半透明，遮挡带与真实比例一致）
  4. 整体缩到 390px 宽（手机逻辑宽度等效）
  5. 与原始帧（同宽缩放）并排出对比长图

用法：
  cd .agents/skills/video-generation/scripts
  python -m video.mobile_preview --frames <png目录或单帧> [--out <目录>] [--count 6]
  python -m video.mobile_preview --slug xxx          # 从 build/<slug>/ 成片抽帧
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import config as C

PHONE_W = 390          # 手机逻辑宽度等效
CANVAS_W, CANVAS_H = 1080, 1920
FRAME_W, FRAME_H = 1080, 607

_FONT_CANDIDATES = [
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/msyhbd.ttc",
    "/System/Library/Fonts/PingFang.ttc",
]


def _font(size: int) -> ImageFont.FreeTypeFont:
    for p in _FONT_CANDIDATES:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def extract_frames(src: Path, count: int, out_dir: Path) -> list[Path]:
    """mp4 → 均匀抽 count 帧；png 直接收集。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        pngs = sorted(src.glob("*.png"))
        if not pngs:
            raise SystemExit(f"❌ {src} 下没有 png 帧")
        step = max(1, len(pngs) // count)
        return pngs[::step][:count]
    if src.suffix.lower() == ".png":
        return [src]
    # mp4：ffmpeg 均匀抽帧
    dur = float(
        subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(src)],
            capture_output=True, text=True,
        ).stdout.strip()
    )
    frames = []
    for i in range(count):
        t = dur * (i + 0.5) / count
        fp = out_dir / f"frame_{i:02d}.png"
        subprocess.run(
            ["ffmpeg", "-y", "-ss", f"{t:.2f}", "-i", str(src),
             "-frames:v", "1", str(fp)],
            capture_output=True,
        )
        if fp.exists():
            frames.append(fp)
    return frames


def simulate_feed(frame: Image.Image, caption: str = "示例标题：一行讲清这条视频讲什么 #AI编程") -> Image.Image:
    """单帧 → 信息流模拟图（1080×1920 带UI mock）。"""
    f = frame.resize((FRAME_W, FRAME_H), Image.LANCZOS)
    canvas = Image.new("RGB", (CANVAS_W, CANVAS_H), (8, 10, 14))
    y0 = (CANVAS_H - FRAME_H) // 2
    canvas.paste(f, (0, y0))
    ov = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    # 右侧图标列（头像 + 点赞/评论/分享/收藏），遮挡带 ≈ 右缘 130px
    rail_cx = CANVAS_W - 74
    rail_y = y0 + 210
    d.ellipse([rail_cx - 46, rail_y - 46, rail_cx + 46, rail_y + 46],
              fill=(255, 255, 255, 210))                       # 头像
    d.text((rail_cx, rail_y), "UP", font=_font(36), fill=(20, 20, 30, 255), anchor="mm")
    icons = [("♥", "1.2万"), ("💬", "356"), ("↗", "89"), ("⭐", "")]
    for ic, num in icons:
        rail_y += 128
        d.text((rail_cx, rail_y), ic, font=_font(52), fill=(255, 255, 255, 235), anchor="mm")
        if num:
            d.text((rail_cx, rail_y + 44), num, font=_font(26),
                   fill=(255, 255, 255, 220), anchor="mm")

    # 底部文案区（落在黑边区，抖音行为）：账号名 + 标题 + 话题 + BGM
    ty = y0 + FRAME_H + 52
    d.text((36, ty), "@xiaoshuai1024", font=_font(44), fill=(255, 255, 255, 240))
    d.text((36, ty + 64), caption, font=_font(40), fill=(255, 255, 255, 225))
    d.text((36, ty + 124), "♫ BGM - light-calm", font=_font(34), fill=(255, 255, 255, 190))
    # 进度条
    d.rectangle([0, CANVAS_H - 8, CANVAS_W, CANVAS_H], fill=(255, 255, 255, 70))
    d.rectangle([0, CANVAS_H - 8, int(CANVAS_W * 0.4), CANVAS_H], fill=(255, 255, 255, 230))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), ov).convert("RGB")
    return canvas


def make_pair(frame_path: Path, out_path: Path) -> None:
    """原图（缩放）+ 信息流模拟 并排对比。"""
    frame = Image.open(frame_path).convert("RGB")
    sim = simulate_feed(frame)
    sim_small = sim.resize((PHONE_W, int(CANVAS_H * PHONE_W / CANVAS_W)), Image.LANCZOS)
    orig_small = frame.resize((PHONE_W, int(frame.height * PHONE_W / frame.width)), Image.LANCZOS)
    gap = 16
    board = Image.new(
        "RGB",
        (PHONE_W * 2 + gap * 3, max(sim_small.height, orig_small.height) + gap * 2),
        (24, 26, 32),
    )
    board.paste(orig_small, (gap, gap))
    board.paste(sim_small, (PHONE_W + gap * 2, gap))
    d = ImageDraw.Draw(board)
    d.text((gap + 4, 6), "原尺寸(390px宽)", font=_font(18), fill=(160, 170, 190))
    d.text((PHONE_W + gap * 2 + 4, 6), "抖音信息流模拟", font=_font(18), fill=(160, 170, 190))
    board.save(out_path, quality=88)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", help="从 build/<slug>/ 找成片抽帧")
    ap.add_argument("--frames", help="帧目录 / 单帧 png / mp4 路径")
    ap.add_argument("--out", help="输出目录（默认 build/<slug>/mobile_preview 或 /mobile_preview）")
    ap.add_argument("--count", type=int, default=6)
    args = ap.parse_args()

    if not args.slug and not args.frames:
        ap.error("需要 --slug 或 --frames")

    if args.slug:
        bdir = C.build_dir(args.slug)
        mp4 = bdir / f"{args.slug}.mp4"
        src = mp4 if mp4.exists() else bdir
        out_dir = Path(args.out) if args.out else bdir / "mobile_preview"
    else:
        src = Path(args.frames)
        if not src.exists():  # 相对路径兜底：以项目根（Makefile cd 到 skill 目录）
            cand = C.PROJECT_ROOT / args.frames
            if cand.exists():
                src = cand
        out_dir = Path(args.out) if args.out else C.OUTPUT_ROOT / "build" / "mobile_preview"

    with tempfile.TemporaryDirectory() as td:
        frames = extract_frames(src, args.count, Path(td))
        if not frames:
            raise SystemExit("❌ 没有可用帧")
        out_dir.mkdir(parents=True, exist_ok=True)
        for fp in frames:
            out = out_dir / f"preview_{fp.stem}.jpg"
            make_pair(fp, out)
            print("saved", out)


if __name__ == "__main__":
    main()
