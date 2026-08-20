# -*- coding: utf-8 -*-
"""渲染产物验收：逐场景 frame-diff（动画有无）+ 音频 volumedetect（mix 健康）。

用法（skill 根）：
    python scripts/verify_render.py <mp4> <fps> <start:name> [<start:name> ...]

例（pipeline-arch, 场景起始帧来自 config.ts 的 span）：
    python scripts/verify_render.py \\
      ../video-generation/build/pipeline-arch/pipeline-arch.mp4 60 \\
      0:cover 528:parallelpipeline 2009:comparisontable3d 3036:conclusionfocus 3383:logosting

验收标准（SKILL.md 标准三件套 ③）：
    - 首屏(Cover)豁免动画，其余场景 max diff > 0.3% 才算「动」。
    - 音频 max_volume 接近 0dB 即削波 FAIL；mean 健康区间 ~ -20~-30dB。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PIL import Image

FPS = 60
SAMPLE_OFFSETS = [40, 90, 160, 260, 400, 560]
TMP = Path(__file__).resolve().parent.parent / ".tmp-verify"


def video_frames(video: Path) -> int:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=nb_frames", "-of", "csv=p=0", str(video)],
        capture_output=True, text=True,
    )
    return int(r.stdout.strip().splitlines()[0].strip().rstrip(","))


def extract_frame(video: Path, frame: int, out: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-ss", str(frame / FPS),
         "-i", str(video), "-frames:v", "1", str(out)],
        check=True,
    )


def diff_pct(a: Path, b: Path) -> float:
    ia = Image.open(a).convert("RGB")
    ib = Image.open(b).convert("RGB")
    assert ia.size == ib.size, (ia.size, ib.size)
    pa, pb = ia.load(), ib.load()
    W, H = ia.size
    changed = 0
    total = 0
    for y in range(0, H, 4):
        for x in range(0, W, 4):
            total += 1
            for c in range(3):
                if abs(pa[x, y][c] - pb[x, y][c]) > 10:
                    changed += 1
                    break
    return changed / total * 100


def main() -> None:
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(2)
    video = Path(sys.argv[1])
    FPS = int(sys.argv[2])
    scenes = []
    for arg in sys.argv[3:]:
        start, _, name = arg.partition(":")
        scenes.append((int(start), name))

    if not video.exists():
        print(f"❌ 视频不存在: {video}")
        sys.exit(1)
    total = video_frames(video)
    TMP.mkdir(parents=True, exist_ok=True)
    print(f"视频: {video}  ({video.stat().st_size/1024/1024:.1f} MB, {total} 帧)")

    ok = True
    for start, name in scenes:
        diffs = []
        prev = None
        for off in SAMPLE_OFFSETS:
            f = start + off
            if f >= total:
                break
            out = TMP / f"f{f}.png"
            extract_frame(video, f, out)
            if prev is not None:
                diffs.append(diff_pct(prev, out))
            prev = out
        mx = max(diffs) if diffs else 0
        exempt = "cover" in name.lower() or name.startswith("首屏")
        verdict = "OK 有动画" if (exempt or mx > 0.3) else "✗ 疑似静态"
        if not exempt and mx <= 0.3:
            ok = False
        print(f"  {name:<32} 采样{len(diffs)}对  max diff={mx:.2f}%  {verdict}")

    print("\n音频 mix (volumedetect):")
    r = subprocess.run(
        ["ffmpeg", "-i", str(video), "-map", "a", "-af", "volumedetect",
         "-f", "null", "NUL" if sys.platform == "win32" else "/dev/null"],
        capture_output=True, text=True,
    )
    for line in r.stderr.splitlines():
        if any(k in line for k in ("mean_volume", "max_volume")):
            print("   " + line.strip())

    print("\n" + ("✅ 验收通过" if ok else "❌ 存在疑似静态场景"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
