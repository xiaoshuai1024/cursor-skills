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
import sys
from pathlib import Path

from . import config as C
from . import render, tts

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

    print(f"[1/3] 配音 + 时间轴（{voice} {rate}，edge-tts WordBoundary）...")
    cards_data = []
    for i, (raw, text) in enumerate(zip(deck_cards, cards_text)):
        card = normalize_card(raw)
        if card.get("is_cover") and outline:
            card["outline"] = outline
        audio = audio_dir / f"audio_{i:02d}.mp3"
        _, boundaries = tts.synth_with_boundaries(text, audio, voice, rate)
        dur = tts.probe_duration(audio)
        tl = timeline.build_card_timeline(text, boundaries, len(card["points"]))
        cards_data.append((card, tl, audio, dur))
        print(f"  卡 {i:02d}  {dur:5.2f}s  points={len(card['points'])}  cues={len(tl['subtitle_cues'])}")

    pad = frames.HEAD_PAD + frames.TAIL_PAD
    total_dur = sum(d for _, _, _, d in cards_data) + len(cards_data) * pad

    print(f"[2/3] 逐帧渲染课件画面（Playwright + FFmpeg，{frames.FPS}fps）...")
    segs = []
    progress_base = 0.0
    # 内容感知音效点位：问句 cue 的提问音（每卡最多 1 个，全片最多 3 个）
    sfx_probe = C.sfx_paths() or {}
    question_sfx = sfx_probe.get("question")
    question_points: list[tuple[Path, float]] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": C.COURSEWARE_W, "height": C.COURSEWARE_H})
        for i, (card, tl, audio, dur) in enumerate(cards_data):
            if question_sfx and len(question_points) < 3:
                for cue in tl["subtitle_cues"]:
                    if cue["text"].rstrip().endswith(("？", "?")):
                        t = progress_base + frames.HEAD_PAD + cue["start_ms"] / 1000.0
                        question_points.append((question_sfx, t))
                        break
            seg = seg_dir / f"seg_{i:02d}.mp4"
            frames.render_card_segment(card, tl, dur, audio, progress_base, total_dur, seg, page)
            segs.append(seg)
            progress_base += dur + pad
            print(f"  段 {i:02d} 完成  累计 {progress_base:6.2f}s")
        browser.close()

    print("[3/3] 拼接 + BGM/音效同图混入（xfade 转场，单 pass 装配）...")
    final = bdir / f"{slug}.mp4"
    transition_dur = 0.8  # 转场持续时间（秒）
    # 转场会减少总时长：每个转场重叠 transition_dur 秒
    actual_dur = total_dur - (len(cards_data) - 1) * transition_dur

    # 内容感知选曲：口播关键词 → 情绪档（tense/epic/chiptune/...，未命中 calm）
    mood = C.suggest_bgm_mood(cards_text)
    bgm = C.bgm_path(mood)
    sfx = C.sfx_paths()
    render.concat_with_transitions(
        segs, final, transition_dur,
        bgm=bgm, sfx=sfx, transition_sfx_every=C.TRANSITION_SFX_EVERY,
        extra_sfx=question_points,
    )

    print(f"\n✅ 完成：{final}")
    print(f"   总时长 {actual_dur:.1f}s · {len(cards_data)} 段 · 课件模式 {C.COURSEWARE_SIZE}@{frames.FPS}fps · xfade 转场 {transition_dur}s")
    print(f"   BGM {mood} {'✓ ' + bgm.name if bgm else '✗ 未找到（narration/ 素材与 assets/bgm.mp3 均缺失），纯配音版'}")
    sfx_desc = f"✓ 开场音 + 每 {C.TRANSITION_SFX_EVERY} 段转场音" if sfx else "✗ narration/ 音效素材缺失，跳过"
    if question_points:
        sfx_desc += f" + {len(question_points)} 处提问音"
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
        _, boundaries = tts.synth_with_boundaries(text, audio, voice, rate)
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
    mood = C.suggest_bgm_mood(cards_text)
    bgm = C.bgm_path(mood)
    sfx = C.sfx_paths()
    sfx_points: list[tuple[Path, float]] = []
    if sfx:
        sfx_points.append((sfx["opening"], 0.08))
        every = max(1, C.TRANSITION_SFX_EVERY)
        durs = [dur for _, _, _, dur in cards_data]
        for k in range(1, n):
            if k % every == 0:
                start_k = sum(durs[:k]) - k * transition_dur
                sfx_points.append((sfx["transition"], max(start_k - transition_dur, 0.0)))

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
    print(f"   音效 {'✓ 开场音 + 每 ' + str(C.TRANSITION_SFX_EVERY) + ' 段转场音' if sfx else '✗ narration/ 音效素材缺失，跳过'}")


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
