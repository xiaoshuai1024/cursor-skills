"""生成 AI 及类似技术缩写的读音 demo（对比原始读法 vs normalize 白名单修法）。

用法：python scripts/tts_demo_readings.py
输出：.video-generation/tts-demos/*.mp3
  - demo_ai.mp3       AI 读法对比（原样「爱」 / normalize 逐字母「A I」）
  - demo_dom.mp3      DOM 读法对比（原样「多姆」 / normalize 逐字母「D O M」）
  - demo_scan.mp3     其余缩写 normalize 后扫读（复现真实视频管线效果）

关键：demo 必须走 normalize_for_tts（与视频管线一致），否则听到的是未修复的原始读法。
"""
import asyncio
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))
from video.config import OUTPUT_ROOT  # noqa: E402
from video.tts import normalize_for_tts  # noqa: E402

VOICE = "zh-CN-YunxiNeural"
RATE = "+8%"
OUT = OUTPUT_ROOT / "tts-demos"
OUT.mkdir(parents=True, exist_ok=True)


async def synth(text: str, path: Path, rate: str = RATE):
    import edge_tts
    c = edge_tts.Communicate(text, VOICE, rate=rate)
    await c.save(str(path))


def synch(text: str, path: Path, raw: bool = False, rate: str = RATE, max_retries: int = 7):
    """按真实管线合成；raw=True 时不 normalize（用于对比未修正的原始读法）。"""
    import time
    from edge_tts.exceptions import NoAudioReceived
    if not raw:
        text = normalize_for_tts(text)
    for attempt in range(1, max_retries + 1):
        try:
            asyncio.run(synth(text, path, rate))
            print(f"  [{path.name}] {text}")
            return
        except NoAudioReceived:
            if attempt < max_retries:
                wait = min(2 ** attempt, 60)
                print(f"  [tts] NoAudioReceived，{wait}s 后重试 {attempt}/{max_retries}…")
                time.sleep(wait)
    raise RuntimeError(f"合成失败: {text}")


def concat(parts: list[tuple], out: Path, gap: float = 0.35):
    """parts = [(label, sentence, raw), ...]; raw=True 跳过 normalize 对比原始读法。
    rate 可选，覆盖默认 RATE（探测某缩写是否有更紧凑的读法）。"""
    files: list[Path] = []
    for i, item in enumerate(parts):
        label, sentence, raw = item[0], item[1], item[2]
        rate = item[3] if len(item) > 3 else RATE
        p = OUT / f"_grp_{i:02d}.mp3"
        synch(f"{label}，{sentence}", p, raw=raw, rate=rate)
        files.append(p)
    silence = OUT / "_silence.mp3"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
         f"anullsrc=r=24000:cl=mono", "-t", str(gap), str(silence)],
        check=True,
    )
    n = len(files)
    inputs = []
    for f in files:
        inputs += ["-i", str(f)]
    inputs += ["-i", str(silence)]
    filter_complex = "".join(
        f"[{i}:a][{n}:a]" for i in range(n)
    ) + f"concat=n={n*2}:v=0:a=1[out]"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", *inputs,
         "-filter_complex", filter_complex, "-map", "[out]", str(out)],
        check=True,
    )
    for f in files + [silence]:
        f.unlink(missing_ok=True)
    print(f"✅ {out.name}  ({len(parts)} 组)")


def main():
    # ============ Demo 1: AI 读法对比 ============
    # 原样(不 normalize) vs 白名单 normalize（A I 逐字母）——同一语音，只差 normalize
    print("== AI demo ==")
    concat([
        ("第一组，不修正", "人工智能，简称AI。", True),
        ("第二组，白名单修正", "人工智能，简称AI。", False),
        ("第三组，白名单提速", "人工智能，简称AI。", False, "+16%"),
    ], OUT / "demo_ai.mp3", gap=0.15)

    # ============ Demo 2: DOM 读法对比 ============
    print("== DOM demo ==")
    concat([
        ("第一组，不修正", "浏览器里的对象模型叫DOM。", True),
        ("第二组，白名单修正", "浏览器里的对象模型叫DOM。", False),
    ], OUT / "demo_dom.mp3", gap=0.15)

    # ============ Demo 3: 其余缩写扫读（真实管线 normalize 后） ============
    print("== scan demo ==")
    scan_words = [
        ("API", "后端接口叫API。", False),
        ("UI", "界面设计叫UI。", False),
        ("ECC", "这段代码用的是ECC。", False),
        ("SQL", "数据库查询用SQL。", False),
        ("CSS", "样式文件是CSS。", False),
        ("HTML", "网页结构是HTML。", False),
        ("JSON", "接口返回JSON。", False),
        ("GPT", "模型叫GPT。", False),
        ("CLI", "命令行工具叫CLI。", False),
        ("MVP", "最小可行版本叫MVP。", False),
        ("SDK", "开发工具包叫SDK。", False),
        ("TDD", "测试驱动开发叫TDD。", False),
        ("PRD", "产品需求文档叫PRD。", False),
        ("Vue", "前端框架用Vue。", False),
        ("URL", "网页地址是URL。", False),
        ("ID", "主键叫ID。", False),
        ("npm", "包管理器叫npm。", False),
        ("GLM", "模型叫GLM。", False),
        ("RAG", "检索增强生成叫RAG。", False),
    ]
    concat(scan_words, OUT / "demo_scan.mp3", gap=0.2)


if __name__ == "__main__":
    main()
