"""主入口：图文卡片/课件/节点图 → 竖屏口播视频。

三种模式：
  --mode courseware（默认）：程序化深色科幻课件，要点/字幕按 edge-tts 词级时间戳
    逐条浮现。依赖 Playwright。
  --mode graph：节点图/知识图谱，中心辐射式布局，适合展示概念关系/知识体系。
    依赖 Playwright。需要 deck-graph.json（而非 deck.json）。
  --mode legacy：静态卡片轮播 + 底部整段 ASS 字幕（旧管线，可回退）。

用法：python -m scripts.video.build --slug <slug> [--mode courseware|graph|legacy]
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

from . import config as C
from . import frames, render, tts

# ASS 字幕字体: Windows 微软雅黑, macOS 苹方(libass 找不到雅黑会渲染豆腐块)
_ASS_FONT = "Microsoft YaHei" if sys.platform == "win32" else "PingFang SC"

_PUNCTS = "，。！？、：；"


def load_narrations(slug: str) -> dict:
    p = C.NARRATIONS_DIR / f"{slug}.json"
    if not p.exists():
        raise FileNotFoundError(
            f"找不到口播文案 {p}（在 scripts/video/narrations/ 下新建 {slug}.json）"
        )
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def wrap(text: str, width: int = 16) -> str:
    """按字符数断行。优先级：中文标点 > 空格 > 不切断 ASCII 单词。

    返回 ASS 硬换行 \\N 连接的字符串。关键：硬切时若切点落在英文单词中间
    （如 Claude Code 的 Code），要退到单词起点，避免字幕显示成 "Cod / e"。
    """
    out = []
    while text:
        if len(text) <= width:
            out.append(text.rstrip())
            break
        seg = text[:width]
        cut = max(seg.rfind(ch) for ch in _PUNCTS)          # 1) 中文标点
        if cut < width // 2:
            cut = seg.rfind(" ")                            # 2) 空格（英文词边界）
        if cut >= width // 2:
            cut += 1
        else:
            cut = width                                     # 3) 切点落在 ASCII 单词中间 → 退到词首
            while (cut > width // 2
                   and text[cut - 1].isascii() and text[cut - 1].isalnum()
                   and text[cut].isascii() and text[cut].isalnum()):
                cut -= 1
            if cut <= width // 2:
                cut = width
        out.append(text[:cut].rstrip())
        text = text[cut:]
    return "\\N".join(out)


def fmt_ts(s: float) -> str:
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = s % 60
    return f"{h}:{m:02d}:{sec:05.2f}"


def build_ass(meta: list[tuple[float, float]], cards_text: list[str], out) -> None:
    """生成 ASS 字幕文件（UTF-8 with BOM，FFmpeg ass filter 在 Windows 读中文需要 BOM）。"""
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "PlayResX: 1080\n"
        "PlayResY: 1920\n"
        "WrapStyle: 2\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, BackColour, Bold, Italic, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,{_ASS_FONT},54,&H00FFFFFF,&H00000000,-1,0,1,3,1,2,90,90,160,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    lines = [header]
    for (start, end), text in zip(meta, cards_text):
        lines.append(f"Dialogue: 0,{fmt_ts(start)},{fmt_ts(end)},Default,,0,0,0,,{wrap(text)}\n")
    out.write_text("".join(lines), encoding="utf-8-sig")


def normalize_card(raw: dict) -> dict:
    """把 deck.json 的原始卡片标准化成 courseware 的 card 格式。

    - cover：hook→标题，subtitle→副标题（series），无要点
    - cta：text→标题，hint→副标题，无要点
    - insight：label→副标题，title + points + sub_points + footer
    """
    ctype = raw.get("type", "insight")
    if ctype == "tool":
        # 屏录感工具窗口卡片：保留 tool 类型 + 窗口标题（subtitle），steps 放 points。
        # 透传全部字段（big/mats/cta/items/req/code/resp/repo/ver 等），screencast
        # 的 tool builder 按需读取——不剥字段，否则新视频 deck 的自定义内容会全落默认值。
        card = dict(raw)
        card.update({
            "type": "tool",
            "tool": raw.get("tool", ""),
            "title": raw.get("title", ""),
            "subtitle": raw.get("subtitle", raw.get("label", "")),
            "points": list(raw.get("points", [])),
            "footer": raw.get("footer", ""),
            "is_cover": False,
        })
        return card
    if ctype == "tutorial":
        # 教程模板卡（亮色全量展示 + active 高亮）：全透传，
        # tutorial.py 按 kind（intro/step/end）渲染 steps/shot/lines/hotspots。
        card = dict(raw)
        card.update({
            "type": "tutorial",
            "kind": raw.get("kind", "step"),
            "title": raw.get("title", ""),
            "subtitle": raw.get("subtitle", ""),
            "points": list(raw.get("points", [])),
            "footer": raw.get("footer", ""),
            "is_cover": False,
        })
        return card
    if ctype == "cover":
        title = (raw.get("hook", "") or raw.get("subtitle", "")).replace("\n", " ")
        return {"title": title, "subtitle": raw.get("subtitle", ""),
                "points": [], "sub_points": [], "footer": "", "is_cover": True}
    if ctype == "cta":
        title = raw.get("text", "") or raw.get("hint", "")
        return {"title": title, "subtitle": raw.get("hint", ""),
                "points": [], "sub_points": [],
                "footer": raw.get("hint", ""), "is_cover": True}
    return {
        "title": raw.get("title", ""),
        "subtitle": raw.get("label", ""),
        "points": list(raw.get("points", [])),
        "sub_points": list(raw.get("sub_points", [])),
        "flow": raw.get("flow"),   # 可选：链式流程图画布（与 sub_points 互斥，flow 优先）
        "shots": list(raw.get("shots", [])),  # 卡内镜头序列（openspec card-shots，优先于 flow/sp）
        "annotate": raw.get("annotate"),  # 手绘强调注记（openspec shot-motion-upgrade）
        "footer": raw.get("footer", ""),
        "is_cover": False,
    }



def warn_points_over_limit(slug: str, deck_cards: list[dict]) -> None:
    """可读性基准警告：要点超条数/超字数（大字号下会折行拥挤）。

    只警告不阻塞（存量 deck 普遍超限）；`make video-lint` 机检时硬卡。
    基准见 config.POINT_MAX_COUNT / POINT_MAX_CHARS（2026-08-24 定规）。
    """
    for i, card in enumerate(deck_cards):
        pts = card.get("points") or []
        if len(pts) > C.POINT_MAX_COUNT:
            print(f"  ⚠️ 卡{i:02d} 要点 {len(pts)} 条 > {C.POINT_MAX_COUNT}（精简到 3 条内）")
        for j, t in enumerate(pts):
            if len(str(t)) > C.POINT_MAX_CHARS:
                print(f"  ⚠️ 卡{i:02d} 要点{j + 1} {len(str(t))} 字 > {C.POINT_MAX_CHARS}：「{t}」")

def _sfx_asset(scenario: str, mood: str | None = None) -> Path:
    """场景矩阵推荐的音效路径（不存在时调用方自行跳过）。"""
    return C.NARRATION_ASSETS_DIR / C.suggest_sfx(scenario, mood)


def scan_cue_sfx_points(
    cards_data: list,
    sfx: dict[str, Path] | None,
    mood: str | None,
    transition_dur: float,
    max_total: int = 8,
    head_pad: float | None = None,
    tail_pad: float | None = None,
) -> tuple[list[tuple[Path, float]], list[str]]:
    """内容感知定点音效（openspec video-sfx-scenario-palette）。

    扫每卡口播 subtitle cue：问句 → 提问音、ERROR/MILESTONE/REVEAL_CUES 关键词
    → 对应场景音（按 mood 走场景矩阵选变体）。每类上限 question 3、其余各 2；
    定点总数 ≤ max_total，超限按 error > question > milestone > reveal 砍。

    时间轴：段 i 内容在输出时间轴的起点 =
    sum(dur_j + tail+head, j<i) - i*transition_dur + head（courseware 段含
    HEAD/TAIL_PAD；graph 段音频直连 acrossfade 无 pad，传 head_pad=tail_pad=0。
    courseware 旧实现按未扣转场重叠的段累计算，第 i 卡提问音漂移
    i*transition_dur，本次修正）。

    返回 (点位列表, 人类可读点位描述)。
    """
    if not sfx:
        return [], []
    hp = frames.HEAD_PAD if head_pad is None else head_pad
    tp = frames.TAIL_PAD if tail_pad is None else tail_pad
    durs = [d for *_, d in cards_data]

    def out_time(i: int, cue_start_s: float) -> float:
        return sum(durs[:i]) + i * (hp + tp) - i * transition_dur + hp + cue_start_s

    pools: list[tuple[str, int, callable, Path, int]] = []  # (场景, 上限, 命中判断, 音效, 砍除优先级)
    q_file = sfx.get("question") or _sfx_asset("question", mood)
    pools.append((
        "question", 3,
        lambda cue: cue.get("is_question") or cue["text"].rstrip().endswith(("？", "?")),
        q_file, 1,
    ))
    for scenario, cues, prio, cap in (
        ("error", C.ERROR_CUES, 0, 2),
        ("milestone", C.MILESTONE_CUES, 2, 2),
        ("reveal", C.REVEAL_CUES, 3, 2),
        ("hook", C.HOOK_CUES, 2, 1),   # 钩子埋点（彩蛋/下期预告），全片 1 次足够
    ):
        asset = _sfx_asset(scenario, mood)
        pools.append((
            scenario, cap,
            (lambda kws: lambda cue: any(kw in cue["text"].lower() for kw in kws))(cues),
            asset, prio,
        ))

    hits: list[tuple[int, Path, float, str]] = []  # (优先级, 音效, 时间, 描述)
    counts: dict[str, int] = {}
    for i, entry in enumerate(cards_data):
        tl = entry[1]  # courseware/graph 的 cards_data 第 2 位都是时间轴 dict
        for cue in tl["subtitle_cues"]:
            for j, (scenario, cap, match, asset, prio) in enumerate(pools):
                if asset.exists() and match(cue):
                    t = out_time(i, cue["start_ms"] / 1000.0)
                    hits.append((prio, asset, t, f"{scenario}@卡{i:02d} {t:6.2f}s（{cue['text'][:12]}）"))
                    counts[scenario] = counts.get(scenario, 0) + 1
                    if counts[scenario] >= cap:  # 该类达上限,移出池
                        pools.pop(j)
                    break
            if not pools:
                break
        if not pools:
            break
    hits.sort(key=lambda h: (h[0], h[2]))
    hits = hits[:max_total]
    hits.sort(key=lambda h: h[2])
    return ([(asset, t) for _, asset, t, _ in hits],
            [desc for _, _, _, desc in hits])


def outro_sfx_point(mood: str | None, total_out_dur: float) -> tuple[Path, float] | None:
    """尾卡收尾和弦：输出时间轴 total-1.5s 定点，全片一次（签名句定格）。"""
    asset = _sfx_asset("outro", mood)
    if asset.exists() and total_out_dur > 3.0:
        return asset, max(total_out_dur - 1.5, 0.0)
    return None


def build_courseware(slug: str, voice: str, rate: str) -> None:
    """课件模式：程序化深色科幻画面 + 配音驱动的逐条浮现。"""
    from playwright.sync_api import sync_playwright

    from . import frames, timeline

    narr = load_narrations(slug)
    cards_text: list[str] = narr["cards"]
    outline: list[str] = narr.get("outline", [])
    deck_path = C.OUTPUT_ROOT / "deck" / slug / "deck.json"
    if not deck_path.exists():
        raise SystemExit(f"❌ 课件模式需要 {deck_path}（标题/要点来源）")
    with open(deck_path, encoding="utf-8") as f:
        deck = json.load(f)
    deck_cards = deck["cards"]
    if len(deck_cards) != len(cards_text):
        raise SystemExit(f"❌ deck 卡片数({len(deck_cards)}) ≠ 口播数({len(cards_text)})")
    warn_points_over_limit(slug, deck_cards)

    bdir = C.build_dir(slug)
    seg_dir = bdir / "segments"
    audio_dir = bdir / "audio"

    # 换声旁路（openspec tts-prosody-pause-hierarchy）：assemble→shrink 产物在则
    # 跳过内建 edge-tts，直接用 Seed-VC 换声后的每卡音频与子句级时间轴。
    voice_dir = C.OUTPUT_ROOT / "audio" / f"{slug}_t"
    use_override = voice_dir.exists() and any(voice_dir.glob("audio_*.mp3"))
    if use_override:
        print(f"[1/3] 配音 + 时间轴（换声旁路：{voice_dir}）...")
    else:
        print(f"[1/3] 配音 + 时间轴（{voice} {rate}，edge-tts WordBoundary）...")
    cards_data = []
    for i, (raw, text) in enumerate(zip(deck_cards, cards_text)):
        card = normalize_card(raw)
        if card.get("is_cover") and outline:
            card["outline"] = outline
        audio = audio_dir / f"audio_{i:02d}.mp3"
        clean_text, _nosub = timeline.extract_nosub(text)  # 〖无字幕〗标记不进 TTS
        ov_audio = voice_dir / f"audio_{i:02d}.mp3"
        ov_bounds = voice_dir / f"boundaries_{i:02d}.json"
        if use_override and ov_audio.exists() and ov_bounds.exists():
            shutil.copy(ov_audio, audio)
            boundaries = json.load(open(ov_bounds, encoding="utf-8"))
            dur = tts.probe_duration(audio)
        else:
            _, boundaries = tts.synth_with_boundaries(clean_text, audio, voice, rate)
            dur = tts.probe_duration(audio)
        tl = timeline.build_card_timeline(text, boundaries, len(card["points"]))
        cards_data.append((card, tl, audio, dur))
        print(f"  卡 {i:02d}  {dur:5.2f}s  points={len(card['points'])}  cues={len(tl['subtitle_cues'])}")

    pad = frames.HEAD_PAD + frames.TAIL_PAD
    total_dur = sum(d for _, _, _, d in cards_data) + len(cards_data) * pad

    print(f"[2/3] 逐帧渲染课件画面（Playwright + FFmpeg，{frames.FPS}fps）...")
    segs = []
    progress_base = 0.0
    # 内容感知声音层（openspec video-sfx-scenario-palette）：mood 判定 →
    # 槽位变体（开场/转场/提问）+ cue 定点（提问/报错/里程碑/揭晓）+ 尾卡收尾和弦
    mood = C.suggest_bgm_mood(cards_text)
    sfx = C.sfx_paths(mood)
    transition_dur = 0.8  # 转场持续时间（秒）,下方装配沿用
    cue_points, cue_descs = scan_cue_sfx_points(cards_data, sfx, mood, transition_dur)
    actual_dur = total_dur - (len(cards_data) - 1) * transition_dur
    outro = outro_sfx_point(mood, actual_dur)
    extra_points = cue_points + ([outro] if outro else [])
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": C.COURSEWARE_W, "height": C.COURSEWARE_H})
        for i, (card, tl, audio, dur) in enumerate(cards_data):
            seg = seg_dir / f"seg_{i:02d}.mp4"
            frames.render_card_segment(card, tl, dur, audio, progress_base, total_dur, seg, page)
            segs.append(seg)
            progress_base += dur + pad
            print(f"  段 {i:02d} 完成  累计 {progress_base:6.2f}s")
        browser.close()

    print("[3/3] 拼接 + BGM/音效同图混入（xfade 转场，单 pass 装配）...")
    final = bdir / f"{slug}.mp4"
    # 转场会减少总时长：每个转场重叠 transition_dur 秒
    bgm = C.bgm_path(mood)
    render.concat_with_transitions(
        segs, final, transition_dur,
        bgm=bgm, sfx=sfx, transition_sfx_every=C.TRANSITION_SFX_EVERY,
        extra_sfx=extra_points,
    )

    print(f"\n✅ 完成：{final}")
    print(f"   总时长 {actual_dur:.1f}s · {len(cards_data)} 段 · 课件模式 {C.COURSEWARE_SIZE}@{frames.FPS}fps · xfade 转场 {transition_dur}s")
    print(f"   BGM {mood} {'✓ ' + bgm.name if bgm else '✗ 未找到（narration/ 素材与 assets/bgm.mp3 均缺失），纯配音版'}")
    if sfx:
        sel = " / ".join(f"{sc}={C.suggest_sfx(sc, mood)}" for sc in ("opening", "transition", "question"))
        sfx_desc = f"✓ 开场音 + 每 {C.TRANSITION_SFX_EVERY} 段转场音（矩阵[{mood}]: {sel}）"
        for d in cue_descs:
            sfx_desc += f"\n      · {d}"
        if outro:
            sfx_desc += f"\n      · outro@{outro[1]:6.2f}s（{outro[0].name}，签名句收尾）"
    else:
        sfx_desc = "✗ narration/ 音效素材缺失，跳过"
    print(f"   音效 {sfx_desc}")


def build_graph(slug: str, voice: str, rate: str, theme: str = "dark") -> None:
    """节点图模式：中心辐射式布局 + 动态连线，适合展示概念关系/知识体系。"""
    from playwright.sync_api import sync_playwright

    from . import frames, graph, timeline

    narr = load_narrations(slug)
    cards_text: list[str] = narr["cards"]
    deck_path = C.OUTPUT_ROOT / "deck" / slug / "deck-graph.json"
    if not deck_path.exists():
        raise SystemExit(f"❌ 节点图模式需要 {deck_path}")
    with open(deck_path, encoding="utf-8") as f:
        deck = json.load(f)

    graph_data = deck.get("graph")
    if not graph_data:
        raise SystemExit(f"❌ deck-graph.json 缺少 graph 字段")

    deck_cards = deck["cards"]
    if len(deck_cards) != len(cards_text):
        raise SystemExit(f"❌ deck 卡片数({len(deck_cards)}) ≠ 口播数({len(cards_text)})")
    warn_points_over_limit(slug, deck_cards)

    bdir = C.build_dir(slug)
    # theme 后缀目录，支持同 slug 生成多主题
    seg_dir = bdir / f"segments_{theme}"
    audio_dir = bdir / "audio"

    print(f"[1/3] 配音 + 时间轴（{voice} {rate}，edge-tts WordBoundary）...")
    cards_data = []
    # 节点图的 active_node_idx：第一张卡（cover）=-1，后续卡=0,1,2...
    for i, text in enumerate(cards_text):
        active_idx = i - 1 if i > 0 else -1
        audio = audio_dir / f"audio_{i:02d}.mp3"
        clean_text, _nosub = timeline.extract_nosub(text)  # 〖无字幕〗标记不进 TTS
        _, boundaries = tts.synth_with_boundaries(clean_text, audio, voice, rate)
        dur = tts.probe_duration(audio)
        tl = timeline.build_card_timeline(text, boundaries, 0)  # graph 模式不用 points
        cards_data.append((active_idx, tl, audio, dur))
        print(f"  卡 {i:02d}  {dur:5.2f}s  active_node={active_idx}  cues={len(tl['subtitle_cues'])}")

    pad = frames.HEAD_PAD + frames.TAIL_PAD
    total_dur = sum(d for _, _, _, d in cards_data) + len(cards_data) * pad

    print(f"[2/3] 逐帧渲染节点图画面（theme={theme}，Playwright + FFmpeg，{frames.FPS}fps）...")
    segs = []
    progress_base = 0.0
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": C.COURSEWARE_W, "height": C.COURSEWARE_H})
        for i, (active_idx, tl, audio, dur) in enumerate(cards_data):
            seg = seg_dir / f"seg_{i:02d}.mp4"
            _render_graph_segment(graph_data, active_idx, tl, dur, audio, progress_base, total_dur, seg, page, theme=theme)
            segs.append(seg)
            progress_base += dur + pad
            print(f"  段 {i:02d} 完成  累计 {progress_base:6.2f}s")
        browser.close()

    print("[3/3] 拼接视频 + 合并音频（xfade 视频转场 + acrossfade 音频交叉淡化，严格对齐）...")
    final = bdir / f"{slug}_{theme}.mp4"
    transition_dur = 0.8
    actual_dur = total_dur - (len(cards_data) - 1) * transition_dur

    import subprocess

    # 1. 拼接视频（xfade 只处理视频，段间重叠 transition_dur）
    video_only = seg_dir / "video_only.mp4"
    render.concat_with_transitions(segs, video_only, transition_dur)

    # 2. 合并音频 + BGM/音效同图混入：acrossfade 与视频 xfade 严格对齐，
    #    BGM 垫底 + 音效点缀在同一条 filter_complex 里完成（单 pass，非成片后混）。
    audio_inputs = []
    for _, _, audio, _ in cards_data:
        audio_inputs.extend(["-i", str(audio)])

    n = len(cards_data)
    af_parts = []
    # 每条输入先统一采样率/声道（edge-tts mp3 是 24kHz mono）
    for i in range(n):
        af_parts.append(
            f"[{i}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[a{i}f]"
        )
    # acrossfade 链：段 i 与段 i+1 交叉淡化 transition_dur
    prev_label = "[a0f]"
    for i in range(1, n):
        out_label = f"[a{i-1}o]" if i < n - 1 else "[aout]"
        af_parts.append(
            f"{prev_label}[a{i}f]acrossfade=d={transition_dur}:c1=tri:c2=tri{out_label}"
        )
        prev_label = out_label

    # 音效点位与 courseware 同语义：开场 @0.08s；段 k(k>0, k%every==0) 在其
    # 转场重叠起点响（音频时间轴段 k 起点 = sum(dur_j, j<k) - k*d，再往前 d）
    # + 内容感知 cue 定点与尾卡收尾和弦（openspec video-sfx-scenario-palette）
    mood = C.suggest_bgm_mood(cards_text)
    bgm = C.bgm_path(mood)
    sfx = C.sfx_paths(mood)
    sfx_points: list[tuple[Path, float]] = []
    cue_descs: list[str] = []
    if sfx:
        sfx_points.append((sfx["opening"], 0.08))
        every = max(1, C.TRANSITION_SFX_EVERY)
        durs = [dur for _, _, _, dur in cards_data]
        for k in range(1, n):
            if k % every == 0:
                start_k = sum(durs[:k]) - k * transition_dur
                sfx_points.append((sfx["transition"], max(start_k - transition_dur, 0.0)))
        cue_points, cue_descs = scan_cue_sfx_points(
            cards_data, sfx, mood, transition_dur, head_pad=0.0, tail_pad=0.0
        )
        sfx_points.extend(cue_points)
        outro = outro_sfx_point(mood, actual_dur)
        if outro:
            sfx_points.append(outro)
            cue_descs.append(f"outro@{outro[1]:6.2f}s（{outro[0].name}，签名句收尾）")

    extra_inputs, overlay_parts, audio_label = render.audio_overlay_chain(
        "[aout]", bgm, sfx_points, actual_dur, n
    )
    af_parts.extend(overlay_parts)
    audio_inputs.extend(extra_inputs)

    filter_complex_audio = ";".join(af_parts)
    merged_audio = seg_dir / "merged_audio.wav"
    cmd = [
        "ffmpeg", "-y",
        *audio_inputs,
        "-filter_complex", filter_complex_audio,
        "-map", audio_label,
        "-c:a", "pcm_s16le", str(merged_audio),
    ]
    r = subprocess.run(cmd, capture_output=True, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(f"音频 acrossfade 失败: {r.stderr[-2000:]}")

    # 3. 把合并音频（已含 BGM/音效）mux 进视频
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_only),
        "-i", str(merged_audio),
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-map", "0:v", "-map", "1:a",
        "-shortest",
        str(final),
    ]
    r = subprocess.run(cmd, capture_output=True, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(f"音视频合成失败: {r.stderr[-2000:]}")

    print(f"\n✅ 完成：{final}")
    print(f"   总时长 {actual_dur:.1f}s · {len(cards_data)} 段 · 节点图模式({theme}) {C.COURSEWARE_SIZE}@{frames.FPS}fps · xfade 转场 {transition_dur}s · acrossfade 音频同步")
    print(f"   BGM {mood} {'✓ ' + bgm.name if bgm else '✗ 未找到（narration/ 素材与 assets/bgm.mp3 均缺失），纯配音版'}")
    if sfx:
        sel = " / ".join(f"{sc}={C.suggest_sfx(sc, mood)}" for sc in ("opening", "transition", "question"))
        sfx_desc = f"✓ 开场音 + 每 {C.TRANSITION_SFX_EVERY} 段转场音（矩阵[{mood}]: {sel}）"
        for d in cue_descs:
            sfx_desc += f"\n      · {d}"
    else:
        sfx_desc = "✗ narration/ 音效素材缺失，跳过"
    print(f"   音效 {sfx_desc}")


def _render_graph_segment(
    graph_data: dict,
    active_node_idx: int,
    timeline_data: dict,
    duration: float,
    audio: Path,
    progress_base: float,
    total_dur: float,
    out: Path,
    page,
    theme: str = "dark",
) -> None:
    """渲染单个节点图段：从 timeline 生成帧序列 → FFmpeg 合成视频。

    动效驱动：每帧根据 t_in_segment (0~1) 计算缩放/脉冲/dashoffset，
    保证截图序列合成后是连贯动画。
    """
    import subprocess
    from . import config as C
    from . import graph

    subtitle_cues = timeline_data.get("subtitle_cues", [])
    fps = 24

    frame_dir = out.parent / f"frames_{out.stem}"
    frame_dir.mkdir(parents=True, exist_ok=True)

    total_frames = int(duration * fps)
    if total_frames == 0:
        total_frames = 1

    for frame_idx in range(total_frames):
        t = frame_idx / fps
        t_in_segment = frame_idx / max(total_frames - 1, 1)  # 0~1 用于驱动动效

        current_sub = ""
        for cue in subtitle_cues:
            if cue["start_ms"] <= t * 1000 <= cue["end_ms"]:
                if not cue.get("no_subtitle"):  # 〖无字幕〗标记句：有声明无字幕
                    current_sub = cue.get("text", "")
                break

        progress = (progress_base + t) / total_dur

        html = graph.render_frame(
            graph_data,
            active_node_idx,
            current_sub,
            progress,
            width=C.COURSEWARE_W,
            height=C.COURSEWARE_H,
            theme=theme,
            t_in_segment=t_in_segment,
        )

        frame_path = frame_dir / f"frame_{frame_idx:05d}.png"
        page.set_content(html)
        page.wait_for_timeout(5)
        page.screenshot(path=str(frame_path))

    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", str(frame_dir / "frame_%05d.png"),
        "-i", str(audio),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        str(out),
    ]
    r = subprocess.run(cmd, capture_output=True, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(f"FFmpeg 帧合成失败: {r.stderr[-2000:]}")

    import shutil
    shutil.rmtree(frame_dir, ignore_errors=True)


def build_legacy(slug: str, voice: str, rate: str) -> None:
    """legacy 模式：静态卡片轮播 + 底部整段 ASS 字幕（旧管线）。"""
    narr = load_narrations(slug)
    cards_text: list[str] = narr["cards"]
    cards = C.cards_paths(slug)
    if len(cards) != len(cards_text):
        raise SystemExit(f"❌ 卡片数({len(cards)}) ≠ 口播数({len(cards_text)})")

    bdir = C.build_dir(slug)
    seg_dir = bdir / "segments"
    audio_dir = bdir / "audio"

    print(f"[1/4] 配音生成（{voice} {rate}，{len(cards_text)} 段）...")
    audios = tts.synth_all(cards_text, audio_dir, voice, rate)

    print("[2/4] 渲染单卡动效段（Ken Burns + 淡入淡出）...")
    segs = []
    meta: list[tuple[float, float]] = []
    cursor = 0.0
    for i, (card, audio) in enumerate(zip(cards, audios), 1):
        adur = tts.probe_duration(audio)
        sdur = adur + C.HEAD_PAD + C.TAIL_PAD
        seg = seg_dir / f"seg_{i:02d}.mp4"
        render.build_segment(card, audio, sdur, seg)
        segs.append(seg)
        meta.append((cursor, cursor + sdur))
        cursor += sdur
        print(f"  段 {i:02d}  {sdur:5.2f}s  累计 {cursor:6.2f}s")

    print("[3/4] 拼接全片...")
    full = bdir / "full.mp4"
    render.concat(segs, full)

    print("[4/4] 烧录字幕 + 混入 BGM...")
    ass = bdir / "subtitle.ass"
    build_ass(meta, cards_text, ass)
    final = bdir / f"{slug}.mp4"
    bgm = C.bgm_path()
    render.finalize(full, ass, bgm, cursor, final)

    print(f"\n✅ 完成：{final}")
    print(f"   总时长 {cursor:.1f}s · {len(cards)} 段 · legacy {C.OUT_SIZE}@{C.FPS}fps")
    if bgm is None:
        print("   ⚠ 未找到 BGM（narration/bgm-bed.wav 与 assets/bgm.mp3 均缺失），纯配音版")


def main() -> None:
    ap = argparse.ArgumentParser(description="图文卡片/课件/节点图 → 竖屏口播视频")
    ap.add_argument("--slug", required=True, help="文章 slug（对应 narrations/<slug>.json）")
    ap.add_argument("--mode", default="courseware", choices=["courseware", "graph", "legacy"],
                    help="courseware=程序化课件(默认)；graph=节点图/知识图谱；legacy=静态卡片轮播")
    ap.add_argument("--theme", default="dark", choices=["dark", "light"],
                    help="dark=科幻青蓝(默认)；light=亮色中性(深蓝主色)")
    ap.add_argument("--voice", default=None, help="覆盖 TTS 声音，如 zh-CN-XiaoxiaoNeural")
    ap.add_argument("--rate", default=None, help="覆盖语速，如 +10%%")
    args = ap.parse_args()

    narr = load_narrations(args.slug)
    voice = args.voice or narr.get("voice", C.DEFAULT_VOICE)
    rate = args.rate or narr.get("rate", C.DEFAULT_RATE)

    if args.mode == "legacy":
        build_legacy(args.slug, voice, rate)
    elif args.mode == "graph":
        build_graph(args.slug, voice, rate, theme=args.theme)
    else:
        build_courseware(args.slug, voice, rate)


if __name__ == "__main__":
    main()
