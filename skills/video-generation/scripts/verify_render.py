# -*- coding: utf-8 -*-
"""渲染产物验收：逐场景 frame-diff（动画有无）+ 音频 volumedetect（mix 健康）。

用法（skill 根）：
    python scripts/verify_render.py <mp4> <fps> <start:name> [<start:name> ...]

例（pipeline-arch, 场景起始帧来自 config.ts 的 span）：
    python scripts/verify_render.py \\
      ../video-generation/build/pipeline-arch/pipeline-arch.mp4 60 \\
      0:cover 528:parallelpipeline 2009:comparisontable3d 3036:conclusionfocus 3383:logosting

形象伴随层验收（video-mascot-narration）：
    python scripts/verify_render.py <mp4> <fps> --mascot-check <说话帧> <静默帧> [--mood <帧A> <帧B>]
    - 讲话/静默两帧裁右下形象区求差 ≥ 0.5%（波形条面板 + 待机浮动都应造成差异）
    - --mood 两帧（分属两表情）裁头顶符号带求差 ≥ 0.3%（表情切换可检出）
    - 全零帧差 FAIL（形象层死了或没渲染）

验收标准（SKILL.md 标准三件套 ③）：
    - 首屏(Cover)豁免动画，其余场景 max diff > 0.3% 才算「动」。
    - 音频 max_volume 接近 0dB 即削波 FAIL；mean 健康区间 ~ -20~-30dB。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PIL import Image

# Windows GBK 控制台打 emoji 会 UnicodeEncodeError,统一重配 UTF-8(CLAUDE.md 编码规)
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")

FPS = 60
SAMPLE_OFFSETS = [40, 90, 160, 260, 400, 560]
TMP = Path(__file__).resolve().parent.parent / ".tmp-verify"

# 形象伴随层默认包围盒（右下角 240px 高形象 + 头顶符号 + bob/反应余量），
# 覆盖 bottom 24-420 / right 0-320 区域；position/height 非默认时用 --box 覆盖
MASCOT_BOX = (0, 620)      # (x0, y0)，x1/y1 由帧尺寸推导（左下角锚定，openspec video-mascot-placement；宽 0..320 盖 left48+形象带）


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


def region_diff(a: Path, b: Path, box: tuple[int, int, int, int]) -> float:
    """裁 box 区域求差异像素占比（box = x0, y0, x1, y1，逐像素阈值 10）。"""
    ia = Image.open(a).convert("RGB").crop(box)
    ib = Image.open(b).convert("RGB").crop(box)
    assert ia.size == ib.size, (ia.size, ib.size)
    pa, pb = ia.load(), ib.load()
    W, H = ia.size
    changed = 0
    for y in range(H):
        for x in range(W):
            for c in range(3):
                if abs(pa[x, y][c] - pb[x, y][c]) > 10:
                    changed += 1
                    break
    return changed / (W * H) * 100


def mascot_check(video: Path, fps: int, args: list[str]) -> None:
    """形象伴随层验收：讲话态帧差 + 可选表情带帧差。"""
    global FPS  # extract_frame 按模块级 FPS 换算时间戳
    FPS = fps
    if len(args) < 2:
        print(__doc__)
        sys.exit(2)
    f_talk, f_silent = int(args[0]), int(args[1])
    mood_pair = None
    if "--mood" in args:
        i = args.index("--mood")
        mood_pair = (int(args[i + 1]), int(args[i + 2]))
    TMP.mkdir(parents=True, exist_ok=True)
    total = video_frames(video)

    def frame_path(f: int) -> Path:
        out = TMP / f"mascot_f{f}.png"
        extract_frame(video, f, out)
        return out

    fa = frame_path(f_talk)
    fb = frame_path(f_silent)
    W, H = Image.open(fa).size
    box = (MASCOT_BOX[0], MASCOT_BOX[1], W, H)
    d = region_diff(fa, fb, box)
    verdict = "OK 讲话态可检出" if d >= 0.5 else "✗ FAIL（形象区无差异：讲话面板没翻或形象未渲染）"
    print(f"  讲话帧 {f_talk} vs 静默帧 {f_silent}  形象区 diff={d:.2f}%  {verdict}")

    ok = d >= 0.5
    if mood_pair is not None:
        ma, mb = frame_path(mood_pair[0]), frame_path(mood_pair[1])
        # 头顶符号带：形象区上半部（符号 + 眼睛都随表情变，足够检出）
        sym_box = (MASCOT_BOX[0], MASCOT_BOX[1], W, MASCOT_BOX[1] + (H - MASCOT_BOX[1]) // 2)
        dm = region_diff(ma, mb, sym_box)
        v = "OK 表情切换可检出" if dm >= 0.3 else "✗ FAIL（表情带无差异）"
        print(f"  表情帧 {mood_pair[0]} vs {mood_pair[1]}  符号带 diff={dm:.2f}%  {v}")
        ok = ok and dm >= 0.3
    print("\n" + ("✅ 形象层验收通过" if ok else "❌ 形象层验收未过"))
    sys.exit(0 if ok else 1)


def caption_check(video: Path, fps: int, args: list[str]) -> None:
    """字幕区动态验收（openspec openmontage-knowledge-port 第二批，参考 OpenMontage visual_qa）：

    python scripts/verify_render.py <mp4> <fps> --caption-check <帧A> <帧B> [--zone x0,y0,x1,y1]
      ① 活性：两帧字幕区差 ≥ 0.5%（意群字幕在翻，不是冻住的一张图）
      ② 对比（主题无关双峰判据）：区内亮(≥235)或暗(≤50)像素至少一项 ≥5%——
       文字/背景亮度分离才算可读；全区中间调 = 对比度塌了（WARN 级）
       默认区 = 底部中央字幕 pill 带，布局不同用 --zone x0,y0,x1,y1 覆盖
    """
    global FPS
    FPS = fps
    zone = None
    if "--zone" in args:
        i = args.index("--zone")
        zone = tuple(int(v) for v in args[i + 1].split(","))
        args = args[:i] + args[i + 2:]
    if len(args) < 2:
        print(__doc__)
        sys.exit(2)
    fa_f, fb_f = int(args[0]), int(args[1])
    TMP.mkdir(parents=True, exist_ok=True)

    fa = TMP / "cap_a.png"
    fb = TMP / "cap_b.png"
    extract_frame(video, fa_f, fa)
    extract_frame(video, fb_f, fb)
    W, H = Image.open(fa).size
    box = zone or (W // 4, H - 190, W * 3 // 4, H - 50)

    d = region_diff(fa, fb, box)
    ok1 = d >= 0.5
    v1 = "OK 字幕在翻" if ok1 else "✗ FAIL（字幕区无差异：字幕层没渲染或两帧同字幕）"
    print(f"  活性  帧 {fa_f} vs {fb_f}  字幕区 diff={d:.2f}%  {v1}")

    # 对比度双峰判据（主题无关）：可读字幕 = 区内文字与其背景亮度分离
    #（暗底白字→近白像素多；浅底黑字→近黑像素多）。全区都挤在中间调 = 字幕
    # 文字和背景糊在一起（对比度塌了）。绝对亮/暗占比只作主题信息打印。
    img = Image.open(fa).convert("L").crop(box)
    px = img.load()
    bw, bh = img.size
    n = bw * bh
    bright = sum(1 for y in range(bh) for x in range(bw) if px[x, y] >= 235)
    dark = sum(1 for y in range(bh) for x in range(bw) if px[x, y] <= 50)
    sb, sd = bright / n * 100, dark / n * 100
    ok2 = (sb >= 5.0) or (sd >= 5.0)
    theme = "浅底" if sb >= sd else "深底"
    v2 = (f"OK 文字/背景亮度分离（{theme}，亮 {sb:.1f}% / 暗 {sd:.1f}%）" if ok2
          else f"⚠ WARN（亮 {sb:.1f}% / 暗 {sd:.1f}%，全区中间调：字幕与背景对比度塌了或字幕未渲染）")
    print(f"  对比  {v2}")

    print("\n" + ("✅ 字幕区验收通过" if (ok1 and ok2) else "❌ 字幕区验收未过"))
    sys.exit(0 if (ok1 and ok2) else 1)


def transition_check(video: Path, fps: int, args: list[str]) -> None:
    """转场/切点验收（openspec openmontage-knowledge-port 第二批，参考 OpenMontage visual_qa）：

    python scripts/verify_render.py <mp4> <fps> --transition-check <切点帧C> [...]
      每个切点取 C-3（切前，退 3 帧容忍 ±1 帧取整漂移）/ C+8（转场中或切后）/ C+18 三帧：
      d1=diff(切前,中) < 1.0% → FAIL（切点未生效：两侧同画面连播/转场帧没渲染）
      d2=diff(中,后) < 0.3% → WARN（切点生效但切后素材近静止：低动态素材/死帧）
    """
    global FPS
    FPS = fps
    if not args:
        print(__doc__)
        sys.exit(2)
    cuts = [int(a) for a in args]
    TMP.mkdir(parents=True, exist_ok=True)

    def fp(f: int) -> Path:
        out = TMP / f"trans_f{f}.png"
        extract_frame(video, f, out)
        return out

    ok = True
    for c in cuts:
        # pre 退 C-3：分段锁帧有 ±1 帧取整漂移，C-2 可能已越过切点造成 d1 采样失真
        d1 = diff_pct(fp(c - 3), fp(c + 8))
        d2 = diff_pct(fp(c + 8), fp(c + 18))
        # d1 = 「切点是否生效」的判据；d2 低不是切点问题，是切后镜头素材低动态/死帧 → WARN
        if d1 < 1.0:
            ok = False
            v = "✗ FAIL（切点未生效：两侧同画面连播）"
        elif d2 < 0.3:
            v = "⚠ WARN（切点生效，但切后素材近静止：低动态素材/死帧，卡点片观感受损）"
        else:
            v = "OK"
        print(f"  切点 {c}: 切前→中 diff={d1:.2f}%  中→后 diff={d2:.2f}%  {v}")
    print("\n" + ("✅ 转场验收通过" if ok else "❌ 转场验收未过"))
    sys.exit(0 if ok else 1)


def main() -> None:
    global FPS
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(2)
    video = Path(sys.argv[1])
    FPS = int(sys.argv[2])
    if sys.argv[3] == "--mascot-check":
        mascot_check(video, FPS, sys.argv[4:])
        return
    if sys.argv[3] == "--caption-check":
        caption_check(video, FPS, sys.argv[4:])
        return
    if sys.argv[3] == "--transition-check":
        transition_check(video, FPS, sys.argv[4:])
        return
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
