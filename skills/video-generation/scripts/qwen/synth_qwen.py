# -*- coding: utf-8 -*-
"""默认朗读链 Qwen3-TTS 合成驱动（skill 固化版，2026-09-07）。

取代仓库 scripts/video/synth_qwen3tts.py（同日早版），是其严格超集：
- 加载与逐句调用口径**完全复刻**已验收链（device_map="cpu" + .to("cuda") +
  language="Chinese"），音色/停顿零漂移
- 性能三增量：①克隆 prompt 每进程只构建一次并复用（旧版每句重传 ref_audio
  = 每句重付 ~25s VQ 编码）；②--jobs N 多进程有界并行（按空闲显存封顶，
  0.6B 单实例 ~2GB）；③逐句 RTF 遥测进 qwen_metrics.json
- 门禁默认关闭（2026-09-07 定规：保护用户试听认可的原始停顿）；--gate v4
  可选开启门禁选优+手术（同 IndexTTS 链口径）
- 断点续跑 / --backup 备份旧产物，与旧版一致

产物契约（与 synth_indextts25.py 同构，下游 assemble/shrink 零改动）：
    sent/<slug>/c{i}_s{j}.wav（44.1k 单声道 16bit）+ .txt（原文）+ .tts.txt（合成输入）
    + meta.json（[{card, sentences}]）+ qwen_metrics.json（进度+RTF 遥测）

用法（生产链由仓库 scripts/video/_qwen_synth.sh 包环境；WSL 用 setup_wsl.sh 环境）：
  python synth_qwen.py <slug> [--jobs 3] [--backup] [--limit N] [--gate]
  python synth_qwen.py --probe        # 两句探针：快听 + RTF
"""
import argparse
import json
import re
import subprocess
import sys
import time
import wave
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SKILL_DIR))
from qwen_audit import QWEN_ROOT, REF_WAV  # noqa: E402

REF_TXT = QWEN_ROOT / "ref_text.txt"
LANG = "Chinese"
VRAM_PER_INSTANCE = {"0.6b": 2300, "1.7b": 5200}  # MiB，含余量
PROBE_SENTS = ["今天我们用三句话讲清楚这个概念。",
               "第一步装好工具，第二步改一个配置，第三步验证生效。"]


def find_repo_root():
    for anc in Path(__file__).resolve().parents:
        if (anc / "scripts" / "video" / "pause_audit.py").is_file():
            return anc
    raise SystemExit("repo root not found（需在 blog-src 仓内运行）")


def split_sentences(text):
    parts = re.split(r"([。！？；\n])", text)
    out, buf = [], ""
    for p in parts:
        buf += p
        if p in "。！？；\n" and buf.strip():
            out.append(buf.strip())
            buf = ""
    if buf.strip():
        out.append(buf.strip())
    return out


def to_pcm44k(src, dst):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src),
                    "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", str(dst)],
                   check=True)


def wav_dur(p):
    with wave.open(str(p)) as w:
        return w.getnframes() / w.getframerate()


def free_vram_mib():
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5)
        return int(out.stdout.strip().splitlines()[0])
    except Exception:
        return 0


def load_engine(size):
    """已验收加载口径（与 synth_qwen3tts.py 逐字对齐）：device_map="cpu" 挂
    accelerate hook 自动搬输入张量（本机 device_map="cuda:0" 段错误的绕行），
    再整体上卡。"""
    import torch
    from qwen_tts import Qwen3TTSModel

    weights = QWEN_ROOT / "weights" / ("Qwen3-TTS-12Hz-0.6B-Base"
                                       if size == "0.6b" else "Qwen3-TTS-12Hz-1.7B-Base")
    t0 = time.perf_counter()
    model = Qwen3TTSModel.from_pretrained(str(weights), device_map="cpu",
                                          dtype=torch.bfloat16)
    model.model.to("cuda")
    model.device = model.model.device
    ref_text = REF_TXT.read_text(encoding="utf-8").strip()
    items = model.create_voice_clone_prompt(ref_audio=str(REF_WAV), ref_text=ref_text)
    print(f"[engine] loaded {size} + clone prompt in {time.perf_counter()-t0:.1f}s",
          flush=True)
    return model, items


def synth_one(model, items, text, out_wav):
    import soundfile as sf
    t0 = time.perf_counter()
    wavs, sr = model.generate_voice_clone(
        text=text, language=LANG, voice_clone_prompt=items)
    dt = time.perf_counter() - t0
    raw = out_wav.with_suffix(".raw.wav")
    sf.write(str(raw), wavs[0], sr)
    to_pcm44k(raw, out_wav)
    raw.unlink(missing_ok=True)
    return dt, len(wavs[0]) / float(sr)


def fmt(rec):
    sil = " ".join(f"{'C' if x['comma'] else 'x'}{x['dur']:.2f}{'!' if x['viol'] else ''}"
                   for x in rec["silences"]) or "-"
    sp = f"{rec['speed']:.1f}字/s" if rec.get("speed") else "短句"
    return f"{sp} | {sil}"


def worker_main(worker_id, jobs, tasks, sent_dir, attempts, size, gate):
    """子进程入口（spawn）：认领 idx % jobs == worker_id 的句子，写 shard 报告。"""
    repo = find_repo_root()
    pause_audit = None
    if gate:
        sys.path.insert(0, str(repo / "scripts" / "video"))
        import pause_audit as _pa
        pause_audit = _pa

    model, items = load_engine(size)
    metrics, records = [], []
    for t in tasks:
        if t["idx"] % jobs != worker_id:
            continue
        tag, s, s0 = t["tag"], t["text"], t["orig"]
        wav = sent_dir / f"{tag}.wav"
        if not gate:
            sw, adur = synth_one(model, items, s, wav)
            (sent_dir / f"{tag}.txt").write_text(s0, encoding="utf-8")
            (sent_dir / f"{tag}.tts.txt").write_text(s, encoding="utf-8")
            metrics.append({"tag": tag, "synth_s": round(sw, 1),
                            "audio_s": round(adur, 2), "rtf": round(sw / adur, 1)})
            print(f"[w{worker_id}] {tag} {len(s)}字 {adur:.2f}s音频 {sw:.0f}s "
                  f"rtf={sw/adur:.1f}", flush=True)
            continue
        # --gate：v4 门禁选优 + 手术（同 IndexTTS 链口径，可选档）
        best = None
        for att in range(attempts):
            print(f"[w{worker_id}] {tag} synth att{att + 1} ...", flush=True)
            cand = sent_dir / f".tmp_cand_w{worker_id}_{tag}.wav"
            sw, adur = synth_one(model, items, s, cand)
            metrics.append({"tag": tag, "synth_s": round(sw, 1),
                            "audio_s": round(adur, 2), "rtf": round(sw / adur, 1)})
            rec = pause_audit.audit(cand, s, align=None, profile="v4")
            rec.update({"card": t["card"], "sent": t["sent"], "text": s,
                        "attempts": att + 1})
            print(f"[w{worker_id}] {tag} att{att + 1}: "
                  f"{'PASS' if rec['pass'] else 'viol'} {fmt(rec)}", flush=True)
            if best is None or rec["score"] < best[0]["score"]:
                best = (rec, cand)
            if rec["pass"]:
                break
        rec, cand = best
        if not rec["pass"]:
            fix = sent_dir / f".tmp_fix_w{worker_id}_{tag}.wav"
            n = pause_audit.enforce(cand, s, fix, align=None, profile="v4")
            if n:
                rec2 = pause_audit.audit(fix, s, align=None, profile="v4")
                rec2.update({"card": t["card"], "sent": t["sent"], "text": s,
                             "attempts": rec["attempts"], "surgery": n})
                rec, cand = rec2, fix
            else:
                rec["surgery"] = 0
        if str(cand) != str(wav):
            cand.replace(wav)
        for p in sent_dir.glob(f".tmp_*{tag}*"):
            p.unlink(missing_ok=True)
        (sent_dir / f"{tag}.txt").write_text(s0, encoding="utf-8")
        (sent_dir / f"{tag}.tts.txt").write_text(s, encoding="utf-8")
        records.append(rec)
    shard = sent_dir / f".qwen_shard_{worker_id}.json"
    json.dump({"metrics": metrics, "records": records},
              open(shard, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"[w{worker_id}] shard done: {len(metrics)} 合成", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", nargs="?", default=None)
    ap.add_argument("--probe", action="store_true", help="两句探针：快听 + RTF，不进台账")
    ap.add_argument("--jobs", type=int, default=1, help="并行进程数（按空闲显存自动封顶）")
    ap.add_argument("--attempts", type=int, default=2, help="--gate 档每句重采上限")
    ap.add_argument("--gate", action="store_true",
                    help="开启 v4 停顿门禁+手术（默认关闭：保护试听认可的原始停顿）")
    ap.add_argument("--backup", action="store_true",
                    help="把现有 sent/audio 产物移到 .bak-indextts25 目录（首次换声必加）")
    ap.add_argument("--limit", type=int, default=0, help="只合成前 N 句（探针/demo）")
    ap.add_argument("--size", default="0.6b", choices=["0.6b", "1.7b"])
    a = ap.parse_args()

    repo = find_repo_root()
    vg = repo / "video-generation"

    # ---- 探针模式
    if a.probe or not a.slug:
        sent_dir = vg / "sent" / "_probe_qwen"
        sent_dir.mkdir(parents=True, exist_ok=True)
        model, items = load_engine(a.size)
        for i, s in enumerate(PROBE_SENTS):
            wav = sent_dir / f"probe_s{i}.wav"
            sw, adur = synth_one(model, items, s, wav)
            print(f"probe_s{i} wall {sw:.2f}s audio {adur:.2f}s RTF {sw/adur:.2f}",
                  flush=True)
        print("PROBE_DONE")
        return

    # ---- 备份旧产物（首次换声）
    if a.backup:
        for d in (vg / "sent" / a.slug, vg / "audio" / a.slug, vg / "audio" / f"{a.slug}_t"):
            if d.exists():
                bak = d.parent / f"{d.name}.bak-indextts25"
                if bak.exists():
                    sys.exit(f"备份已存在：{bak}（先处理再跑）")
                d.rename(bak)
                print(f"backup: {d} -> {bak}")

    import json as _json
    narr = _json.load(open(vg / "narrations" / f"{a.slug}.json", encoding="utf-8"))
    sent_dir = vg / "sent" / a.slug
    sent_dir.mkdir(parents=True, exist_ok=True)

    # ---- 任务展开 + 断点续跑（wav+tts.txt 匹配即跳过）
    tasks, resumed = [], 0
    reused_audio = 0.0
    meta, stop = [], False
    total = sum(len(split_sentences(c)) for c in narr["cards"])
    for i, card in enumerate(narr["cards"]):
        if stop:
            break
        keep = []
        for j, s0 in enumerate(split_sentences(card)):
            s = s0.replace("1024工程笔记", "一零二四工程笔记")
            keep.append(s)
            tag = f"c{i:02d}_s{j:02d}"
            wav, ttxt = sent_dir / f"{tag}.wav", sent_dir / f"{tag}.tts.txt"
            if wav.exists() and ttxt.exists() and ttxt.read_text(
                    encoding="utf-8").strip() == s:
                reused_audio += wav_dur(wav)
                resumed += 1
                print(f"skip {tag} (resume)", flush=True)
                continue
            tasks.append({"idx": len(tasks), "card": i, "sent": j,
                          "tag": tag, "text": s, "orig": s0})
        if keep:
            meta.append({"card": i, "sentences": keep})
        if a.limit and len(tasks) + resumed >= a.limit:
            stop = True
    if a.limit:
        tasks = tasks[:max(0, a.limit - resumed)]

    if not tasks:
        _json.dump(meta, open(sent_dir / "meta.json", "w", encoding="utf-8"),
                   ensure_ascii=False, indent=1)
        print(f"QWEN_SYNTH_DONE slug={a.slug} 全部复用 audio={reused_audio:.1f}s")
        return

    # ---- 并行封顶：按空闲显存估实例数
    vram_cap = 8
    free = free_vram_mib()
    if free:
        vram_cap = max(1, free // VRAM_PER_INSTANCE[a.size])
    import multiprocessing as mp
    jobs = max(1, min(a.jobs, vram_cap, len(tasks), 4))
    print(f"JOBS {jobs}（请求 {a.jobs}，显存上限 {vram_cap}，free {free}MiB，"
          f"任务 {len(tasks)}/{total} 句）", flush=True)

    t0 = time.perf_counter()
    if jobs == 1:
        worker_main(0, 1, tasks, sent_dir, a.attempts, a.size, a.gate)
    else:
        ctx = mp.get_context("spawn")
        procs = [ctx.Process(target=worker_main,
                             args=(w, jobs, tasks, sent_dir, a.attempts, a.size, a.gate))
                 for w in range(jobs)]
        for p in procs:
            p.start()
        for p in procs:
            p.join()
        failed = [w for w, p in enumerate(procs) if p.exitcode]
        if failed:
            print(f"WORKER_FAILED {failed}（已完成 shard 保留，重跑续接）", flush=True)
    wall = time.perf_counter() - t0

    # ---- 合并 shard：meta.json + qwen_metrics.json（+ pause_audit.json 仅 gate 档）
    _json.dump(meta, open(sent_dir / "meta.json", "w", encoding="utf-8"),
               ensure_ascii=False, indent=1)
    metrics, records = [], []
    for shard in sorted(sent_dir.glob(".qwen_shard_*.json")):
        d = _json.load(open(shard, encoding="utf-8"))
        metrics.extend(d["metrics"])
        records.extend(d["records"])
        shard.unlink()
    synth_s = sum(m["synth_s"] for m in metrics)
    audio_s = sum(m["audio_s"] for m in metrics) + reused_audio
    metrics_obj = {
        "engine": f"qwen3-tts-{a.size}-base", "slug": a.slug, "jobs": jobs,
        "gate": bool(a.gate),
        "sent_done": len(metrics) + resumed,
        "sent_total": total,
        "audio_s": round(audio_s, 1), "synth_wall_s": round(synth_s, 1),
        "wall_s": round(wall, 1),
        "rtf_per_process": round(synth_s / max(1e-9, sum(m['audio_s'] for m in metrics)), 2),
        "sentences": metrics,
    }
    (sent_dir / "qwen_metrics.json").write_text(
        _json.dumps(metrics_obj, ensure_ascii=False, indent=1), encoding="utf-8")
    if a.gate and records:
        records.sort(key=lambda r: (r["card"], r["sent"]))
        n_pass = sum(r["pass"] for r in records)
        first_try = sum(1 for r in records if r.get("attempts") == 1 and r["pass"])
        surgered = sum(1 for r in records if r.get("surgery"))
        _json.dump({"gate": {"total": len(records), "pass": n_pass,
                             "first_try": first_try, "surgered": surgered,
                             "profile": "v4",
                             "engine": f"qwen3-tts-{a.size}-base"},
                    "sentences": records},
                   open(sent_dir / "pause_audit.json", "w", encoding="utf-8"),
                   ensure_ascii=False, indent=1)
        print(f"\nGATE {n_pass}/{len(records)} PASS（首发过 {first_try}，手术 {surgered}）")
    print(f"QWEN_SYNTH_DONE slug={a.slug} jobs={jobs} sents={len(metrics)}+"
          f"{resumed}reused audio={audio_s:.1f}s synth={synth_s:.0f}s "
          f"wall={wall:.0f}s rtf/proc={metrics_obj['rtf_per_process']}", flush=True)


if __name__ == "__main__":
    main()
