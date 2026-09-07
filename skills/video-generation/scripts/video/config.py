"""视频生成管线配置。"""
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

# 输出规格：竖屏短视频（抖音/视频号通用）
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

# 全部视频的默认 BGM（2026-09-06 用户定规，试听页选定）：Mixkit "Raising Me Higher"，
# 免费商用免署名；已 -12dB 响度校准对齐 gen-sfx 合成轨，既有音量常数沿用。
# 台账（直链/许可）主仓 data/bgm-library/；持久副本 scripts/assets/ 同名文件。
# 换默认轨时与 remotion core/sound-points.ts::DEFAULT_BGM 等四处同名常量同步。
DEFAULT_BGM = "bgm-raising-me-higher.mp3"


def bgm_path(mood: str | None = None) -> Path | None:
    """BGM 解析（2026-09-06 定规）：全部视频默认 DEFAULT_BGM；
    mood 仅作手动覆盖入口（要情绪轨显式传 mood，自动链路一律不传）。
    兜底链 bgm-bed.wav → skill assets/bgm.mp3，都不存在返回 None（纯配音）。"""
    if mood:
        cand = NARRATION_ASSETS_DIR / BGM_MOOD_FILES.get(mood, "bgm-bed.wav")
        if cand.exists():
            return cand
    for cand in (NARRATION_ASSETS_DIR / DEFAULT_BGM, NARRATION_ASSETS_DIR / "bgm-bed.wav", ASSETS_DIR / "bgm.mp3"):
        if cand.exists():
            return cand
    return None


def sfx_paths(mood: str | None = None) -> dict[str, Path] | None:
    """courseware/graph 装配时自动点缀的音效（开场 + 稀疏转场 + 提问，存在才加）。
    narration/ 开场/转场齐才返回 dict（提问音可选），否则 None。
    mood 给了按场景矩阵选变体（openspec video-sfx-scenario-palette）；
    None 走各场景兜底默认 = 变更前的固定三件（chime/swoosh/question-up）。"""
    opening = NARRATION_ASSETS_DIR / suggest_sfx("opening", mood)
    transition = NARRATION_ASSETS_DIR / suggest_sfx("transition", mood)
    question = NARRATION_ASSETS_DIR / suggest_sfx("question", mood)
    if opening.exists() and transition.exists():
        out = {"opening": opening, "transition": transition}
        if question.exists():
            out["question"] = question
        return out
    return None


# ── SFX 场景×氛围矩阵（openspec video-sfx-scenario-palette，2026-08-26）──
# scenario → [(文件, 适用 mood 框架…), …]；查表顺序取首个命中 mood 的条目，
# 全未命中回退首项（兜底默认）。氛围轴复用 BGM 8 档 → BGM 与 SFX 同一声音人格。
# ⚠️ 与 remotion core/sound-points.ts::SFX_SCENARIOS 同源镜像，改一边必须同步另一边；
#    文档 SSOT = references/sound-design.md §五矩阵表。
SFX_SCENARIO_MATRIX: dict[str, list[tuple[str, tuple[str, ...]]]] = {
    # 开场引子:讲解系柔钟声 / 进取系缓升落地 / 张力系扫频+钟声抓注意
    "opening": [
        ("sfx-opening-chime.wav", ("calm", "walk", "focus", "lofi")),
        ("sfx-opening-riser.wav", ("bright", "epic")),
        ("sfx-opening.wav", ("tense", "chiptune")),
    ],
    # 提问:讲解系中性双音 / 进取系上行引好奇 / 张力系下行收束反思
    "question": [
        ("sfx-question.wav", ("calm", "focus")),
        ("sfx-question-up.wav", ("walk", "bright", "epic", "chiptune")),
        ("sfx-question-down.wav", ("tense", "lofi")),
    ],
    # 转场:讲解/进取系融合 swoosh / 张力系数字故障
    "transition": [
        ("sfx-transition-swoosh.wav", ("calm", "walk", "focus", "bright", "epic", "lofi")),
        ("sfx-transition-glitch.wav", ("tense", "chiptune")),
    ],
    # 重点结论:讲解系软 ping / 进取·张力系低频重击 / 轻快系极短 tick
    "emphasis": [
        ("sfx-emphasis.wav", ("calm", "focus", "lofi")),
        ("sfx-impact.wav", ("bright", "epic", "tense")),
        ("sfx-emphasis-tick.wav", ("walk", "chiptune")),
    ],
    # 揭晓/数据:讲解系软和弦 bloom / 轻快系 whoosh-open / 张力系竖琴刮奏
    "reveal": [
        ("sfx-reveal-bloom.wav", ("calm", "focus", "lofi")),
        ("sfx-reveal.wav", ("walk", "bright", "chiptune")),
        ("sfx-harp-gliss.wav", ("tense", "epic")),
    ],
    # 里程碑/成功:清亮叮兜底,进取/8-bit 用金属双音(数字落地)
    "milestone": [
        ("sfx-ding.wav", ()),
        ("sfx-coin.wav", ("bright", "chiptune")),
    ],
    # 报错/翻车:三全音下行双音(全档兜底);tapestop 悬念切断是手动备选不进自动矩阵
    "error": [("sfx-error-buzz.wav", ())],
    "typing": [("sfx-typewriter.wav", ())],      # 代码/打字,全档单一
    "countdown": [("sfx-ticktock.wav", ())],     # 倒计时/时间线
    "suspense": [("sfx-heartbeat.wav", ())],     # 悬念铺垫
    "hook": [("sfx-hook-riser.wav", ())],        # 钩子埋点(上扬悬置不落地)
    "outro": [("sfx-outro-chord.wav", ())],      # 签名句收尾,全片一次
}


def suggest_sfx(scenario: str, mood: str | None = None) -> str:
    """场景×氛围 → 推荐音效文件名（矩阵首项为兜底默认）。"""
    entries = SFX_SCENARIO_MATRIX.get(scenario)
    if not entries:
        raise ValueError(f"未知 SFX 场景: {scenario}（合法值: {sorted(SFX_SCENARIO_MATRIX)}）")
    for file, moods in entries:
        if mood in moods:
            return file
    return entries[0][0]


# ── 内容感知定点音效 cue 关键词（courseware/graph 扫口播 subtitle cue；
#    每类 error/milestone/reveal ≤2、hook ≤1、提问 ≤3，全片定点总数 ≤8，
#    超限按 error > question > hook > milestone > reveal 砍）──
ERROR_CUES = ["报错", "失败", "翻车", "错误", "异常", "崩溃", "error", "failed"]
MILESTONE_CUES = ["成功", "跑通", "搞定", "通过", "完成", "装好"]
REVEAL_CUES = ["答案", "真相", "其实是", "原因就是"]
HOOK_CUES = ["彩蛋", "下条视频", "下期", "敬请期待"]


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
