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
ASSETS_DIR = SCRIPT_DIR / "assets"                   # skill 内可复用素材（预留）
NARRATION_ASSETS_DIR = OUTPUT_ROOT / "narration"     # BGM/SFX 素材（gen-sfx.py 产物,与 Remotion public/ 同源）

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

# 横屏可读性基准（2026-08-24 定规，openspec/changes/video-landscape-readability）
# 抖音信息流中 16:9 视频仅占 1080×607，字号按「信息流最坏情况」设计：
SAFE_RIGHT = 180        # 关键文字右缘避让带宽（抖音右侧图标列遮挡）
FONT_BODY_MIN = 48      # 正文/要点下限（画面高 4.4%，Netflix 字幕可读下限口径）
FONT_TITLE_MIN = 72     # 标题下限（紧凑模板/Remotion 内容场景允许 48）
FONT_SUB_MIN = 36       # 辅助说明下限（紧凑模板允许 34）
POINT_MAX_COUNT = 3     # 每卡要点条数上限（大字号对冲：宁可少条不缩字）
POINT_MAX_CHARS = 14    # 单条要点字数上限（渲染时超限警告，video-lint 机检硬卡）

# 编码参数：所有段必须保持一致，concat 才能直接 copy
# crf 18（自 20 调整）：文字高频边缘对压缩敏感，18 档在 200% 放大下无可见块状伪影
VIDEO_KWARGS = ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p"]
AUDIO_KWARGS = ["-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2"]

# 背景音乐（可选，缺失则该视频纯配音）
BGM_VOLUME = 0.12   # BGM 音量，配音为主（legacy 竖屏模式用）
SFX_VOLUME_DB = "-10dB"   # courseware/graph 装配时 SFX 音量（低于口播人声）
TRANSITION_SFX_EVERY = 4  # 转场音稀疏度：每 N 个段响一次（参考片拆解：不逐场堆）


def bgm_path(mood: str | None = None) -> Path | None:
    """BGM 解析：mood 给了用对应情绪轨（gen-sfx 产物），否则 bgm-bed 兜底，
    最后 skill assets/bgm.mp3。都不存在返回 None（纯配音）。"""
    if mood:
        cand = NARRATION_ASSETS_DIR / BGM_MOOD_FILES.get(mood, "bgm-bed.wav")
        if cand.exists():
            return cand
    for cand in (NARRATION_ASSETS_DIR / "bgm-bed.wav", ASSETS_DIR / "bgm.mp3"):
        if cand.exists():
            return cand
    return None


def sfx_paths() -> dict[str, Path] | None:
    """courseware/graph 装配时自动点缀的音效（开场 + 稀疏转场 + 提问，存在才加）。
    narration/ 开场/转场齐才返回 dict（提问音可选），否则 None。"""
    opening = NARRATION_ASSETS_DIR / "sfx-opening-chime.wav"
    transition = NARRATION_ASSETS_DIR / "sfx-transition-swoosh.wav"
    question = NARRATION_ASSETS_DIR / "sfx-question-up.wav"
    if opening.exists() and transition.exists():
        out = {"opening": opening, "transition": transition}
        if question.exists():
            out["question"] = question
        return out
    return None


# ── 内容 → BGM 情绪（抖音知识区口径；与 remotion core/sound-points.ts 同规则，两边同步改）──
BGM_MOOD_FILES = {
    "calm": "bgm-light-calm.wav",      # 沉稳科普(默认,任何讲解都安全)
    "walk": "bgm-light-walk.wav",      # 轻快带节奏:教程/步骤/上手
    "focus": "bgm-light-focus.wav",    # 极简专注:深度解析/长讲解
    "bright": "bgm-light-bright.wav",  # 明亮进取:新发布/技巧/效率
    "tense": "bgm-tense.wav",          # 悬疑脉冲:源码内幕/揭秘/踩坑
    "epic": "bgm-epic.wav",            # 史诗推进:对决/评测/跑分
    "chiptune": "bgm-chiptune.wav",    # 8-bit:程序员梗/终端/装机
    "lofi": "bgm-lofi.wav",            # Lo-fi:温和长教程/随笔体验
}
BGM_MOOD_RULES: list[tuple[str, list[str]]] = [
    ("tense", ["源码", "内幕", "揭秘", "真相", "为什么", "原理", "底层", "事故", "翻车", "踩坑", "坑"]),
    ("epic", ["对决", "对比", "排行", "榜单", "跑分", "评测", "性能", "倍", "吊打", "完胜"]),
    ("chiptune", ["程序员", "终端", "命令行", "npm", "git", "代码", "编译", "安装包"]),
    ("bright", ["新", "发布", "升级", "技巧", "效率", "提速", "省"]),
    ("walk", ["教程", "步骤", "入门", "上手", "怎么", "如何", "零基础"]),
    ("lofi", ["聊聊", "随笔", "体验", "一周", "记录"]),
]


def suggest_bgm_mood(texts: list[str]) -> str:
    """口播文本关键词计分选情绪；同分靠前优先（tense 最特异），无命中 calm。"""
    corpus = "\n".join(texts)
    best, best_score = "calm", 0
    for mood, kws in BGM_MOOD_RULES:
        score = sum(1 for kw in kws if kw in corpus)
        if score > best_score:
            best, best_score = mood, score
    return best


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
