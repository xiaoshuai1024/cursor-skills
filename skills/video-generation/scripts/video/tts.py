"""edge-tts 逐卡配音 + 时长探测。

edge-tts 联网调用微软接口，免费不限额，音质为 Azure 同源中文神经语音。
"""
import asyncio
import re
import subprocess
from pathlib import Path

import edge_tts

# 需要逐字母读的技术缩写白名单（极简版）。
# 设计权衡：逐字母读得准但慢（每个字母停顿 ~197ms，不自然）。
# 只保留会被读成"无法识别的中文错音"的词（如 DOM→"多姆"）。
# 其他缩写（API/GLM/GPT/CSS 等）让 TTS 当单词读，自然流畅，可识别。
#
# AI 实测（WordBoundary 探针，男声 YunxiNeural）：
#   原始 "AI" → 拆成单词 ['AI'] → 读成拼音音"爱/哀"（不自然）
#   "A I"    → 拆成 ['A', 'I'] → 逐字母读（技术圈标准读法）
# 故 AI 进白名单。旧注释"AI 自动逐字母、保持原样"被实测推翻。
# ⚠️ 不要用中文谐音替换（如 "AI"→"诶爱"）：实测反而切成两个独立词（SKILL.md 发音章节已记录）。
_LETTER_BY_LETTER_ABBREV = {
    "DOM",
    "AI",
    # TUI 实测（WordBoundary 探针，YunxiNeural）：整词 "dsh-TUI" 读成一个乱音词，
    # "T U I" 才逐字母。dsh 单独读法可接受，只拆 TUI。
    "TUI",
}


def normalize_for_tts(text: str) -> str:
    """TTS 文本预处理。

    1. 技术缩写逐字母化：DOM → "D O M"、AI → "A I"。
       中文语音会把全大写缩写读成单词音（DOM 读成"多姆"、AI 读成"爱/哀"），需手动拆字母。
       只处理白名单内的缩写，避免误伤正常英文单词。
       用前后非字母断言（不用 \\b），确保中文夹着的 DOM 也能命中。

    注意：AI 经 WordBoundary 实测须逐字母（见模块头注释与白名单 {"DOM","AI"}），
    否则男声 YunxiNeural 会读成"爱/哀"。edge-tts 不支持 SSML 音素控制，
    只能靠文本改写（AI → "A I"）来修正读音。
    """

    def _expand(match: re.Match[str]) -> str:
        word = match.group(0)
        if word in _LETTER_BY_LETTER_ABBREV:
            return " ".join(word)
        return word

    out = re.sub(r"(?<![A-Za-z])[A-Z]{2,5}(?![A-Za-z])", _expand, text)
    # TUI 大小写都要逐字母（口播常写小写 "dsh-tui"，
    # 小写 "tui" 会被读成一个整词音；实测 "T U I" 才逐字母）
    out = re.sub(r"(?<![A-Za-z])[tT][uU][iI](?![A-Za-z])", "T U I", out)
    # 品牌名读法定规（2026-08-26）：「1024工程笔记」必须逐位读"一零二四"，
    # edge-tts 默认把 1024 读成"一千零二十四"。只定向品牌短语，不碰其他
    # 1024（如 "1024 tokens" 该读一千零二十四）。字幕不受影响（走原文）。
    out = out.replace("1024工程笔记", "一零二四工程笔记")
    return out


async def _synth(text: str, out_path: Path, voice: str, rate: str) -> None:
    text = normalize_for_tts(text)
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(str(out_path))


async def _synth_with_boundaries(
    text: str, out_path: Path, voice: str, rate: str
) -> tuple[Path, list[dict]]:
    """合成并收集词级时间戳。

    关键：必须显式传 boundary="WordBoundary"。edge-tts Communicate 默认是
    SentenceBoundary（见 edge_tts/communicate.py __init__），默认情况下不会吐
    词级事件。stream() 流式 yield dict：type=="audio" 含 data(bytes)，
    type=="WordBoundary" 含 offset/duration/text。

    offset 单位是 10 微秒（见 edge_tts/submaker.py:44 timedelta(offset/10)），
    故 offset/10000 = 毫秒。
    """
    text = normalize_for_tts(text)
    communicate = edge_tts.Communicate(
        text, voice, rate=rate, boundary="WordBoundary"
    )
    boundaries: list[dict] = []
    audio_bytes = bytearray()
    async for message in communicate.stream():
        msg_type = message["type"]
        if msg_type == "audio":
            audio_bytes.extend(message["data"])
        elif msg_type == "WordBoundary":
            offset = message["offset"]
            duration = message["duration"]
            boundaries.append(
                {
                    "text": message["text"],
                    "start_ms": round(offset / 10000),
                    "end_ms": round((offset + duration) / 10000),
                }
            )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(audio_bytes)
    return out_path, boundaries


def synth_with_boundaries(
    text: str, out_path, voice: str, rate: str, max_retries: int = 7
) -> tuple[Path, list[dict]]:
    """同步合成 mp3 到 out_path，返回 (path, boundaries)。

    boundaries = [{"text": str, "start_ms": int, "end_ms": int}, ...]
    start_ms / end_ms 由 edge-tts WordBoundary 的 offset/duration 换算（毫秒）。

    edge-tts 免费服务会抛 NoAudioReceived——有两类：(1) 间歇单次失败；(2) 长失败窗口
    （某段十几秒内持续失败，已实测与文本无关，是服务端波动）。故用指数退避把重试跨度
    拉到 ~3 分钟，跨越长窗口；文本本身经诊断确认无问题。
    """
    import time

    from edge_tts.exceptions import NoAudioReceived
    from aiohttp.client_exceptions import WSServerHandshakeError

    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            return asyncio.run(
                _synth_with_boundaries(text, Path(out_path), voice, rate)
            )
        except (NoAudioReceived, WSServerHandshakeError, ConnectionError) as exc:
            last_exc = exc
            if attempt < max_retries:
                wait = min(2 ** attempt, 60)   # 指数退避 2/4/8/16/32/60，跨越长失败窗口
                print(f"  [tts] {type(exc).__name__}，{wait}s 后重试 {attempt}/{max_retries}…")
                time.sleep(wait)
    assert last_exc is not None
    raise last_exc


def synth_all(cards: list[str], out_dir: Path, voice: str, rate: str) -> list[Path]:
    """逐段生成配音 mp3，返回按卡序排列的路径列表。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    async def run() -> None:
        for i, text in enumerate(cards, 1):
            p = out_dir / f"audio_{i:02d}.mp3"
            await _synth(text, p, voice, rate)
            paths.append(p)
            print(f"  配音 {i:02d}/{len(cards)}  {p.name}  ({len(text)}字)")

    asyncio.run(run())
    return paths


def probe_duration(path: Path) -> float:
    """用 ffprobe 取音频时长（秒）。"""
    r = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True, encoding="utf-8",
    )
    if r.returncode != 0:
        raise RuntimeError(f"ffprobe 失败: {r.stderr}")
    return float(r.stdout.strip())
