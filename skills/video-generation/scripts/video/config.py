"""视频生成管线配置。和 scripts/xiaohongshu、scripts/douyin 的风格保持一致。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]          # blog-src 根（skill 内 scripts/video 下 5 层）
SCRIPT_DIR = Path(__file__).resolve().parent
NARRATIONS_DIR = SCRIPT_DIR / "narrations"
ASSETS_DIR = SCRIPT_DIR / "assets"

# 输出规格：竖屏短视频（抖音/视频号/小红书通用）
FPS = 30
OUT_W, OUT_H = 1080, 1920
OUT_SIZE = f"{OUT_W}x{OUT_H}"

# 横屏培训讲解（courseware 模式）：16:9，知识/教学视频标准
COURSEWARE_W, COURSEWARE_H = 1920, 1080
COURSEWARE_SIZE = f"{COURSEWARE_W}x{COURSEWARE_H}"

# 时间参数（秒）
FADE = 0.4          # 段内淡入淡出
HEAD_PAD = 0.35     # 每段配音前的画面留白（配音延迟开始）
TAIL_PAD = 0.25     # 每段配音后的画面留白

# 默认 TTS（可被 narrations/<slug>.json 覆盖）
DEFAULT_VOICE = "zh-CN-YunxiNeural"   # 云希，沉稳男声，适合知识口播
DEFAULT_RATE = "+6%"                  # 略快，短视频节奏

# 编码参数：所有段必须保持一致，concat 才能直接 copy
VIDEO_KWARGS = ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p"]
AUDIO_KWARGS = ["-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2"]

# 背景音乐（可选，放入 scripts/video/assets/bgm.mp3 即自动混入）
BGM_PATH = ASSETS_DIR / "bgm.mp3"
BGM_VOLUME = 0.12   # BGM 音量，配音为主


def deck_root(slug: str) -> Path:
    """定位卡片源目录：优先抖音高清版，回退小红书版。"""
    for cand in (ROOT / ".douyin-build" / slug, ROOT / "image-text" / slug):
        if (cand / "cards").is_dir():
            return cand
    raise FileNotFoundError(f"找不到 {slug} 的卡片目录（.douyin-build 或 image-text）")


def cards_paths(slug: str) -> list[Path]:
    return sorted((deck_root(slug) / "cards").glob("*.png"))


def build_dir(slug: str) -> Path:
    d = ROOT / ".video-build" / slug
    (d / "segments").mkdir(parents=True, exist_ok=True)
    (d / "audio").mkdir(parents=True, exist_ok=True)
    return d
