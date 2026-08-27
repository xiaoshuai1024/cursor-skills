"""时间轴对齐：edge-tts 词级时间戳 → 句级字幕 + 要点亮起时刻。

设计依据：openspec/changes/video-courseware-upgrade/design.md（D2）。
edge-tts WordBoundary 给出每个词的 [offset, duration]，本模块把它聚合成：
  1. subtitle_cues：按中文标点切句，每句一个 [start_ms, end_ms]
  2. point_timings：把句按顺序均匀分配给 N 个要点，给出每个要点的亮起时刻
"""
from __future__ import annotations

from typing import List, Tuple

# 中文断句标点。只在中标点处断句，故 ASCII 单词（Claude Code）不会被切断。
_SENTENCE_PUNCT = "，。！？、：；"

# 无字幕标记（openspec video-engagement-cta）：口播稿里给某句加 〖无字幕〗 前缀，
# 该句正常配音但不出字幕——用于抖音「动作引导只走口播、字幕停在互动问题」的露出面合规。
# 与 narrate.py 的 NOSUB_MARK 同源双份（两模块互不 import），改一处必须同步另一处。
NOSUB_MARK = "〖无字幕〗"
_SENT_END = "。！？；"


def extract_nosub(text: str) -> tuple[str, list[tuple[int, int]]]:
    """剥掉全部 〖无字幕〗 标记，返回 (剥后文本, 屏蔽字符区间列表)。

    标记作用于「标记处到本句句末（。！？；或文本结尾）」；区间坐标相对剥后文本
    （标记本身不占位）。TTS 合成与 boundary 映射都用剥后文本，音频不含标记。
    """
    ranges: list[tuple[int, int]] = []
    parts: list[str] = []
    out_pos = 0
    i = 0
    while True:
        j = text.find(NOSUB_MARK, i)
        if j == -1:
            parts.append(text[i:])
            break
        parts.append(text[i:j])
        out_pos += j - i
        k = j + len(NOSUB_MARK)
        end = len(text)
        for ch in _SENT_END:
            e = text.find(ch, k)
            if e != -1:
                end = min(end, e + 1)
        seg = text[k:end]
        parts.append(seg)
        ranges.append((out_pos, out_pos + len(seg)))
        out_pos += len(seg)
        i = end
    return "".join(parts), ranges

# 字幕显示去标点（知识视频惯例：避免画面杂乱）；口播原文标点不动，只去显示字幕
_SUBTITLE_STRIP = "，。！？、；：　“”‘’（）【】《》…—·"
_SUBTITLE_TABLE = str.maketrans("", "", _SUBTITLE_STRIP)


def strip_subtitle_punct(text: str) -> str:
    """去除字幕中的中文标点与全角空格，压缩多余空白。"""
    return " ".join(text.translate(_SUBTITLE_TABLE).split())


def split_sentences(text: str) -> List[Tuple[str, int, int]]:
    """按中文标点分句。

    返回 [(句子文本, 起始字符偏移, 结束偏移(不含)), ...]，偏移相对 text 原文。
    跳过句间空白；句末标点归属当前句；尾部无标点的余文自成一句。
    """
    sentences: List[Tuple[str, int, int]] = []
    cur_start: int | None = None
    for i, ch in enumerate(text):
        if cur_start is None and not ch.isspace():
            cur_start = i
        if ch in _SENTENCE_PUNCT:
            if cur_start is not None:
                sentences.append((text[cur_start : i + 1], cur_start, i + 1))
                cur_start = None
    if cur_start is not None:
        sentences.append((text[cur_start:], cur_start, len(text)))
    return sentences


def _map_boundaries_to_chars(
    narration_text: str, boundaries: list[dict]
) -> list[tuple[int, int, int, int]]:
    """把每个 boundary 映射回 narration_text 的字符区间。

    任务要求：用各 boundary text 的字符长度累加来定位（比 text_offset 稳）。
    本实现用「贪婪锚定」：以 boundary.text 为锚，从当前游标在 narration_text
    里找最近出现位置，命中即得 [start_char, end_char) 并推进游标；未命中则按
    len(text) 推进（兜底）。贪婪锚定天然跳过那些不在 boundary 里的空格与标点，
    比纯长度累加更不容易漂移。

    返回 [(start_char, end_char, start_ms, end_ms), ...]。
    """
    spans: list[tuple[int, int, int, int]] = []
    pos = 0
    nt = narration_text
    fallback_count = 0
    for b in boundaries:
        bt = b["text"]
        if not bt:
            continue
        idx = nt.find(bt, pos)
        if idx == -1:
            # 兜底 1：strip 后再找（边界 token 偶带空白）
            stripped = bt.strip()
            if stripped:
                idx2 = nt.find(stripped, pos)
                if idx2 != -1:
                    spans.append(
                        (idx2, idx2 + len(stripped), b["start_ms"], b["end_ms"])
                    )
                    pos = idx2 + len(stripped)
                    continue
            # 兜底 2：按 len 推进，保证不卡住
            fallback_count += 1
            spans.append((pos, pos + len(bt), b["start_ms"], b["end_ms"]))
            pos = pos + len(bt)
        else:
            spans.append((idx, idx + len(bt), b["start_ms"], b["end_ms"]))
            pos = idx + len(bt)
    if fallback_count:
        print(f"  [timeline] 边界字符定位兜底 {fallback_count} 次（贪婪未命中）")
    return spans


def build_card_timeline(
    narration_text: str, boundaries: list[dict], points_count: int
) -> dict:
    """从词级 boundaries 构建单卡时间轴。

    流程：
      1. split_sentences 切句；
      2. 每个 boundary 映射回 narration_text 字符区间；
      3. 按句聚合：句 start_ms = 落在该句字符区间内第一个 boundary 的 start_ms，
         end_ms = 最后一个 boundary 的 end_ms（用字符区间重叠判定归属）；
      4. 句按顺序均匀分配给 points_count 个要点（base = n//points，余数给前面
         几个要点），每个要点亮起时刻 = 分配给它的第一句的 start_ms。

    返回 {"subtitle_cues": [...], "point_timings": [...]}。
    cue 可能带 no_subtitle=True（源文本含 〖无字幕〗 标记的句子）——渲染层跳过
    该 cue 的字幕显示，时间轴与要点分配不受影响。
    """
    narration_text, nosub_ranges = extract_nosub(narration_text)
    sentences = split_sentences(narration_text)
    spans = _map_boundaries_to_chars(narration_text, boundaries)

    # 按句聚合字幕
    subtitle_cues: list[dict] = []
    for stext, s_start, s_end in sentences:
        # 取与该句字符区间有重叠的 boundary（overlap 判定避免端点丢词）
        in_range = [
            (bsm, bem)
            for (_bc_start, _bc_end, bsm, bem) in spans
            if _bc_start < s_end and _bc_end > s_start
        ]
        if not in_range:
            continue
        cue = {
            "text": stext,
            "start_ms": min(x[0] for x in in_range),
            "end_ms": max(x[1] for x in in_range),
        }
        # 问句标记要在去标点前判（build.py 的提问音点位依赖它；字幕文本之后会剥标点）
        if stext.rstrip().endswith(("？", "?")):
            cue["is_question"] = True
        if any(a0 < s_end and s_start < a1 for a0, a1 in nosub_ranges):
            cue["no_subtitle"] = True
        subtitle_cues.append(cue)

    # 句分配给要点：余数给前面几个
    point_timings: list[dict] = []
    n = len(subtitle_cues)
    if points_count > 0:
        if n == 0:
            for p in range(points_count):
                point_timings.append({"point_idx": p, "start_ms": 0})
        else:
            base = n // points_count
            rem = n % points_count
            idx = 0
            last_start = subtitle_cues[0]["start_ms"]
            for p in range(points_count):
                count = base + (1 if p < rem else 0)
                if count == 0:
                    # 要点多于句数：此要点无句可分，复用上一可用时刻保持单调
                    point_timings.append({"point_idx": p, "start_ms": last_start})
                    continue
                group_start = subtitle_cues[idx]["start_ms"]
                point_timings.append({"point_idx": p, "start_ms": group_start})
                last_start = subtitle_cues[idx + count - 1]["start_ms"]
                idx += count

    # 字幕去标点（口播原文不动，只去显示字幕）
    for cue in subtitle_cues:
        cue["text"] = strip_subtitle_punct(cue["text"])
    return {"subtitle_cues": subtitle_cues, "point_timings": point_timings}


if __name__ == "__main__":
    # 自测：用真实 edge-tts 合成第一卡口播，验证 boundaries / 分句 / 要点时间轴
    import json
    import os
    import sys

    # Windows 编码护栏（CLAUDE.md）
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    # 直接运行脚本时 sys.path[0] = scripts/video，可直接 import 同级模块
    from config import NARRATIONS_DIR, OUTPUT_ROOT, build_dir
    from tts import synth_with_boundaries

    SLUG = "ai-dev-claude-code-power-user"

    with open(NARRATIONS_DIR / f"{SLUG}.json", encoding="utf-8") as f:
        narr = json.load(f)
    with open(OUTPUT_ROOT / "deck" / SLUG / "deck.json", encoding="utf-8") as f:
        deck = json.load(f)

    voice = narr["voice"]
    rate = narr["rate"]
    cards = narr["cards"]

    # 第一卡（cards[0]，cover）无 points 字段；取首个有 points 的内容卡（idx=1，
    # 「核心判断」insight，3 个 points）来真正验证要点分配逻辑。
    test_idx = 1
    test_text = cards[test_idx]
    deck_card = deck["cards"][test_idx]
    points_count = len(deck_card.get("points", []))

    print(f"=== 自测卡 idx={test_idx}（{deck_card.get('title', '')}）===")
    print(f"voice={voice}  rate={rate}  points_count={points_count}")
    print(f"口播：{test_text}")
    print()

    # 1) 分句（纯文本，不依赖 TTS）
    sents = split_sentences(test_text)
    print(f"--- split_sentences：{len(sents)} 句 ---")
    for s_text, s_start, s_end in sents:
        print(f"  [{s_start:>3}:{s_end:>3}] {s_text}")
    print()

    # 2) 真实合成拿 boundaries
    out_dir = build_dir(SLUG) / "audio"
    out_path = out_dir / f"_selftest_card{test_idx:02d}.mp3"
    print(f"--- synth_with_boundaries → {out_path} ---")
    _path, boundaries = synth_with_boundaries(test_text, out_path, voice, rate)
    print(f"mp3 已写入：{_path}（{_path.stat().st_size} bytes）")
    print(f"boundaries 数量：{len(boundaries)}")
    assert boundaries, "boundaries 为空"
    print("前 6 条 boundary：")
    for b in boundaries[:6]:
        print(f"  {b['start_ms']:>6}~{b['end_ms']:<6}ms  {b['text']!r}")
    print()

    # 3) boundary start_ms 单调递增校验
    starts = [b["start_ms"] for b in boundaries]
    mono = all(starts[i] <= starts[i + 1] for i in range(len(starts) - 1))
    print(f"boundary start_ms 单调非降：{mono}")
    assert mono, "boundary start_ms 非单调"
    print()

    # 4) 构建时间轴
    timeline = build_card_timeline(test_text, boundaries, points_count)
    pt = timeline["point_timings"]
    cues = timeline["subtitle_cues"]

    print(
        f"--- point_timings：{len(pt)} 条（应 == points_count={points_count}）---"
    )
    for entry in pt:
        print(f"  point#{entry['point_idx']} 亮起 @ {entry['start_ms']}ms")
    assert len(pt) == points_count, f"要点数不符 {len(pt)} != {points_count}"
    pt_starts = [e["start_ms"] for e in pt]
    if len(pt_starts) >= 2:
        pt_mono = all(
            pt_starts[i] <= pt_starts[i + 1] for i in range(len(pt_starts) - 1)
        )
        print(f"point_timings start_ms 单调非降：{pt_mono}")
    print()

    print(f"--- subtitle_cues：共 {len(cues)} 条，前 3 条 ---")
    for cue in cues[:3]:
        print(f"  {cue['start_ms']:>6}~{cue['end_ms']:<6}ms  {cue['text']}")

    print()
    print("=== timeline 自测通过 ===")
