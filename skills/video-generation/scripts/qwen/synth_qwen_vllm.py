# -*- coding: utf-8 -*-
"""Qwen3-TTS vLLM-Omni 逐句合成驱动（WSL，2026-09-07）：结构性提速档生产入口。

与 synth_qwen.py（transformers 档）产物契约完全同构：
sent/<slug>/c{i}_s{j}.wav（44.1k PCM16）+ .txt + .tts.txt + qwen_metrics.json。
断点续跑（wav+tts.txt 匹配即跳过）。

背景：transformers 栈解码循环纯 CPU 瓶颈（嵌套 HF generate + 全历史重 prefill，
RTF≈200）；vLLM-Omni 重写解码循环（持续批量 + CUDA graph）。探针实测见
qwen_vllm_probe.py 与 README 数据表。

用法（WSL，vllm venv）：
  source ~/qwen-tts/.venv-vllm/bin/activate
  python /mnt/d/codes/blog-src/.skills/skills/video-generation/scripts/qwen/synth_qwen_vllm.py <slug> \
    [--gpu-mem 0.35] [--limit N]
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import wave
from pathlib import Path

os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")
SKILL_DIR = Path(__file__).resolve().parent

QWEN_ROOT = Path("/mnt/d/models/Qwen3TTS")
WEIGHTS = QWEN_ROOT / "weights" / "Qwen3-TTS-12Hz-0.6B-Base"
REF_WAV = Path("/mnt/d/models/IndexTTS25/refaudio/my_voice_seg.wav")
REF_TEXT = (QWEN_ROOT / "ref_text.txt").read_text(encoding="utf-8").strip()
LANG = "Chinese"


def find_repo_root():
    for anc in Path(__file__).resolve().parents:
        if (anc / "scripts" / "video" / "pause_audit.py").is_file():
            return anc
    raise SystemExit("repo root not found（需经 /mnt/d 路径在 blog-src 仓内运行）")


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--gpu-mem", type=float, default=0.35)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    repo = find_repo_root()
    vg = repo / "video-generation"
    sys.path.insert(0, os.path.expanduser(
        "~/vllm-omni/examples/offline_inference/text_to_speech/qwen3_tts"))
    import end2end  # 官方示例：_estimate_prompt_len / _save_wav
    import soundfile as sf
    import torch
    from vllm_omni import Omni

    narr = json.load(open(vg / "narrations" / f"{a.slug}.json", encoding="utf-8"))
    sent_dir = vg / "sent" / a.slug
    sent_dir.mkdir(parents=True, exist_ok=True)

    tasks, resumed = [], 0
    meta = []
    for i, card in enumerate(narr["cards"]):
        keep = []
        for j, s0 in enumerate(split_sentences(card)):
            s = s0.replace("1024工程笔记", "一零二四工程笔记")
            keep.append(s)
            tag = f"c{i:02d}_s{j:02d}"
            wav = sent_dir / f"{tag}.wav"
            ttxt = sent_dir / f"{tag}.tts.txt"
            if wav.exists() and ttxt.exists() and ttxt.read_text(
                    encoding="utf-8").strip() == s:
                resumed += 1
                print(f"skip {tag} (resume)", flush=True)
                continue
            tasks.append({"card": i, "sent": j, "tag": tag, "text": s, "orig": s0})
        if keep:
            meta.append({"card": i, "sentences": keep})
    if a.limit:
        tasks = tasks[:a.limit]
    if not tasks:
        json.dump(meta, open(sent_dir / "meta.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"QWEN_VLLM_SYNTH_DONE slug={a.slug} 全部复用")
        return

    est = lambda info: end2end._estimate_prompt_len(info, str(WEIGHTS))
    print(f"[engine] Omni init（gpu_mem={a.gpu_mem}，{len(tasks)} 句待合成）...", flush=True)
    t0 = time.perf_counter()
    omni = Omni(model=str(WEIGHTS), gpu_memory_utilization=a.gpu_mem,
                allowed_local_media_path="/")
    print(f"[engine] up in {time.perf_counter()-t0:.1f}s", flush=True)

    metrics = []
    t_all = time.perf_counter()
    for t in tasks:
        info = {"task_type": ["Base"], "ref_audio": [str(REF_WAV)],
                "ref_text": [REF_TEXT], "text": [t["text"]],
                "language": [LANG], "x_vector_only_mode": [False],
                "max_new_tokens": [2048]}
        inputs = {"prompt_token_ids": [0] * est(info),
                  "additional_information": info}
        tag = t["tag"]
        t1 = time.perf_counter()
        audio_s = 0.0
        for stage_outputs in omni.generate([inputs]):
            mm = stage_outputs.outputs[0].multimodal_output
            end2end._save_wav(str(sent_dir / f".raw_{tag}"), "x", mm)
            audio = mm["audio"]
            at = audio if not isinstance(audio, list) else torch.cat(audio, dim=-1)
            sr = mm["sr"]
            sr = sr[-1] if isinstance(sr, list) and sr else sr
            sr = sr.item() if hasattr(sr, "item") else int(sr)
            sf.write(str(sent_dir / f".raw_{tag}.wav"), at.float().cpu().numpy().flatten(),
                     samplerate=sr)
            audio_s = len(at.flatten()) / float(sr)
        sw = time.perf_counter() - t1
        wav = sent_dir / f"{tag}.wav"
        to_pcm44k(sent_dir / f".raw_{tag}.wav", wav)
        (sent_dir / f".raw_{tag}.wav").unlink(missing_ok=True)
        for junk in sent_dir.glob(f".raw_{tag}*"):
            junk.unlink(missing_ok=True)
        (sent_dir / f"{tag}.txt").write_text(t["orig"], encoding="utf-8")
        (sent_dir / f"{tag}.tts.txt").write_text(t["text"], encoding="utf-8")
        metrics.append({"tag": tag, "synth_s": round(sw, 2),
                        "audio_s": round(audio_s, 2),
                        "rtf": round(sw / max(1e-9, audio_s), 2)})
        print(f"{tag} {len(t['text'])}字 {audio_s:.2f}s音频 {sw:.1f}s "
              f"rtf={sw/max(1e-9, audio_s):.2f}", flush=True)

    json.dump(meta, open(sent_dir / "meta.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    synth_s = sum(m["synth_s"] for m in metrics)
    audio_s = sum(m["audio_s"] for m in metrics)
    (sent_dir / "qwen_metrics.json").write_text(json.dumps({
        "engine": "qwen3-tts-0.6b-base+vllo-omni", "slug": a.slug,
        "sent_done": len(metrics) + resumed,
        "sent_total": len(metrics) + resumed,
        "synth_wall_s": round(synth_s, 1), "audio_s": round(audio_s, 1),
        "rtf_agg": round(synth_s / max(1e-9, audio_s), 2),
        "wall_s": round(time.perf_counter() - t_all, 1),
        "sentences": metrics}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"QWEN_VLLM_SYNTH_DONE slug={a.slug} sents={len(metrics)}+{resumed}reused "
          f"audio={audio_s:.1f}s synth={synth_s:.0f}s rtf={synth_s/max(1e-9, audio_s):.2f}",
          flush=True)


if __name__ == "__main__":
    main()
