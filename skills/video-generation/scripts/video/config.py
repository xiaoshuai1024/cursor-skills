"""视频生成管线配置。和 scripts/xiaohongshu、scripts/douyin 的风格保持一致。"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # skill 根（scripts/video 下 2 层）
SCRIPT_DIR = Path(__file__).resolve().parent


def _find_project_root() -> Path:
    """定位项目根（有 hugo.toml 的目录）。

    优先读 VIDEO_PROJECT_ROOT 环境变量（Makefile 传入），其次 cwd。不能
    用 .git 判断（skills 仓库本身是 git 仓库），也不能只依赖 __file__——
    .agents/skills 是指向外部 skills 仓库的 symlink，__file__ 解析后的真实
    路径向上走不到项目根。
    """
    env_root = os.environ.get("VIDEO_PROJECT_ROOT")
    if env_root and (Path(env_root) / "hugo.toml").exists():
        return Path(env_root)
    cwd = Path.cwd()
    if (cwd / "hugo.toml").exists():
        return cwd
    for p in [ROOT, *ROOT.parents]:
        if (p / "hugo.toml").exists():
            return p
    return cwd  # fallback: 让后续步骤报可读的错误


PROJECT_ROOT = _find_project_root()
OUTPUT_ROOT = PROJECT_ROOT / "video-generation"        # 全部产物/配置/内容落这里（不带 .，macOS Finder 可直接查看）
NARRATIONS_DIR = OUTPUT_ROOT / "narrations"          # 口播文案 json
ASSETS_DIR = SCRIPT_DIR / "assets"                   # bgm.mp3 等可复用素材（留在 skill 内）

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
    """定位卡片源目录（legacy 静态卡片模式）：.video-generation/deck/<slug>/cards/。"""
    for cand in (OUTPUT_ROOT / "deck" / slug,):
        if (cand / "cards").is_dir():
            return cand
    raise FileNotFoundError(f"找不到 {slug} 的卡片目录（.video-generation/deck）")


def cards_paths(slug: str) -> list[Path]:
    return sorted((deck_root(slug) / "cards").glob("*.png"))


def build_dir(slug: str) -> Path:
    """构建中间产物 + 成片：.video-generation/build/<slug>/"""
    d = OUTPUT_ROOT / "build" / slug
    (d / "segments").mkdir(parents=True, exist_ok=True)
    (d / "audio").mkdir(parents=True, exist_ok=True)
    return d
