# -*- coding: utf-8 -*-
"""留存深度对齐：过程锚点 × 句级时间轴 → 「平均观众停在哪句、哪段」。

锚点（deep 快照）：完播率 / 平均播放时长 / 3s 退出率 / 封面点击率
时间轴：faster-whisper 本地转写（缓存 data/analytics/transcripts/<slug>.json）
诚实边界：平台 web 端无秒级留存曲线 → 输出为「锚点推断」，报告明确标注。

产出 data/analytics/retention.json
用法: python -m va.retention [--slug xxx[,yyy]] [--force-transcribe]
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from . import common, fetch_uid
from .common import DATA_DIR, setup_utf8

TECH_PROMPT = "以下是一位技术博主的中文口播视频，涉及 Claude Code、Codex、Agent、插件、源码、编程、AI 工具等术语。"
MODEL_NAME = "small"


def transcript_path(slug: str) -> Path:
    d = DATA_DIR / "transcripts"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{slug}.json"


def extract_audio(mp4: Path) -> Path:
    out = transcript_path(mp4.stem).with_suffix(".wav")
    if out.exists():
        return out
    subprocess.run(["ffmpeg", "-y", "-i", str(mp4), "-vn", "-ac", "1", "-ar", "16000",
                    str(out)], capture_output=True, timeout=300, check=True)
    return out


def transcribe(slug: str, force: bool = False) -> list[dict] | None:
    """句级时间轴 [{start, end, text}]，缓存复用。"""
    cache = transcript_path(slug)
    if cache.exists() and not force:
        return json.loads(cache.read_text(encoding="utf-8"))
    mp4 = fetch_uid._video_path(slug)
    if not mp4:
        return None
    try:
        audio = extract_audio(mp4)
        from faster_whisper import WhisperModel
        model = WhisperModel(MODEL_NAME, device="cpu", compute_type="int8")
        segs, _info = model.transcribe(str(audio), language="zh", initial_prompt=TECH_PROMPT,
                                       vad_filter=True, beam_size=1)
        out = [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()}
               for s in segs if s.text.strip()]
        cache.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
        return out
    except Exception as e:
        print(f"  [{slug}] 转写失败: {type(e).__name__}: {str(e)[:120]}")
        return None


def load_deep(platform: str) -> dict[str, dict]:
    """slug -> 最新深度快照。"""
    p = common.SNAP_DIR / "deep" / f"{platform}.jsonl"
    if not p.exists():
        return {}
    out = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        slug = r.get("slug")
        if not slug:
            continue
        if slug not in out or (r.get("fetched_at") or "") > (out[slug].get("fetched_at") or ""):
            out[slug] = r
    return out


def sentence_at(segs: list[dict], t: float) -> tuple[int, dict] | None:
    """时间 t 落在第几句（1-based）。"""
    for i, s in enumerate(segs, 1):
        if t < s["end"]:
            return i, s
    return len(segs), segs[-1] if segs else None


def build_sections(segs: list[dict], k: int = 6) -> list[dict]:
    """时间轴聚成 ≤k 段，每段 {start, end, sentences, digest}。"""
    if not segs:
        return []
    total = segs[-1]["end"]
    if total == 0:
        return []
    step = total / k
    sections = []
    cur = {"start": 0.0, "end": 0.0, "sentences": []}
    for s in segs:
        if s["start"] >= (len(sections) + 1) * step and cur["sentences"]:
            cur["end"] = s["start"]
            sections.append(cur)
            cur = {"start": s["start"], "end": 0.0, "sentences": []}
        cur["sentences"].append(s)
    if cur["sentences"]:
        cur["end"] = segs[-1]["end"]
        sections.append(cur)
    for sec in sections:
        texts = [s["text"] for s in sec["sentences"]]
        digest = "；".join(texts[:2])
        if len(texts) > 2:
            digest += f"…（共 {len(texts)} 句）"
        sec["digest"] = digest
    return sections


def mmss(sec: float) -> str:
    return f"{int(sec // 60):02d}:{int(sec % 60):02d}"


def analyze_slug(slug: str, deep: dict, duration_s: float | None) -> dict | None:
    segs = transcribe(slug)
    if not segs:
        return None
    raw = deep.get("raw") or {}
    avg_time = raw.get("play_avg_time") or raw.get("avg_play_time")
    finish = raw.get("play_finish_ratio") or raw.get("full_play_ratio")
    video_len = duration_s or segs[-1]["end"]

    result = {"slug": slug, "sentence_count": len(segs), "video_len_s": round(video_len, 1),
              "transcript_digest": segs[0]["text"][:60] if segs else "", "sections": [],
              "anchors": {"completion_rate": finish, "avg_play_time": avg_time,
                          "crash_rate_3s": raw.get("crash_rate_3s"),
                          "cover_ctr": raw.get("cover_click_ratio") or raw.get("cover_ctr"),
                          "new_fans": raw.get("new_fans_count")},
              "note": "平台 web 端无秒级留存曲线，以下为锚点推断（平均时长/完播率/3s退出 × 句级时间轴）"}

    # 平均观众停留定位
    if avg_time:
        idx, sent = sentence_at(segs, float(avg_time)) or (None, None)
        if sent:
            result["avg_stop"] = {
                "time_s": round(float(avg_time), 1), "at": mmss(float(avg_time)),
                "sentence_no": idx, "sentence": sent["text"][:80],
                "depth": round(float(avg_time) / video_len, 4) if video_len else None,
            }
    # 3s 退出（钩子判定）落点
    if raw.get("crash_rate_3s") is not None:
        _, sent3 = sentence_at(segs, 3.0) or (None, None)
        result["hook_sentence"] = sent3["text"][:80] if sent3 else None

    # 段落表 + 每段锚点覆盖标注
    sections = build_sections(segs)
    avg_t = float(avg_time) if avg_time else None
    for sec in sections:
        entry = {"range": f"{mmss(sec['start'])}-{mmss(sec['end'])}", "digest": sec["digest"]}
        if avg_t is not None:
            if avg_t < sec["start"]:
                entry["retention_hint"] = "在平均停留点之后（多数观众未到达）"
            elif avg_t <= sec["end"]:
                entry["retention_hint"] = "★ 平均观众在这里离开"
            else:
                entry["retention_hint"] = None
        result["sections"].append(entry)
    return result


def run(slugs: list[str] | None = None, force: bool = False) -> int:
    setup_utf8()
    metrics = json.loads((DATA_DIR / "metrics.json").read_text(encoding="utf-8")) \
        if (DATA_DIR / "metrics.json").exists() else {"videos": {}}
    deep_dy, deep_bili = load_deep("douyin"), load_deep("bilibili")

    targets = slugs or (set(deep_dy) | set(deep_bili))
    out = []
    for slug in sorted(targets):
        deep = deep_dy.get(slug) or deep_bili.get(slug)
        if not deep:
            continue
        plat = "douyin" if deep_dy.get(slug) else "bilibili"
        dur = None
        m = (metrics.get("videos") or {}).get(slug, {}).get(plat) or {}
        dur = m.get("duration_s")
        r = analyze_slug(slug, deep, dur)
        if r:
            r["platform"] = plat
            out.append(r)
            stop = r.get("avg_stop") or {}
            print(f"  [{slug[:38]}] {len(r['sections'])} 段 {len([s for s in r['sections'] if s.get('retention_hint')=='★ 平均观众在这里离开'])} ★"
                  + (f" | 平均停在第 {stop.get('sentence_no')}/{r['sentence_count']} 句（{stop.get('at')}，深度 {stop.get('depth'):.1%}）"
                     if stop.get("sentence_no") else ""))
    (DATA_DIR / "retention.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[retention] {len(out)} 个 slug -> retention.json")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", default="", help="逗号分隔，默认全部有深度快照的")
    ap.add_argument("--force-transcribe", action="store_true")
    args = ap.parse_args()
    return run([s.strip() for s in args.slug.split(",") if s.strip()] or None, args.force_transcribe)


if __name__ == "__main__":
    raise SystemExit(main())
