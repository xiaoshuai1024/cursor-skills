# -*- coding: utf-8 -*-
"""Qwen3-TTS 性能审计（openspec windows-native-tts-research §3.5 后续，2026-09-07）。

定位「病态慢 RTF≈164-304」根因并 A/B 修复档。已实锤证据链：
- 参数 100% 可上卡（914.6M 全 cuda），慢不在参数落卡
- 真凶①：wrapper `_tokenize_texts` 产物 input_ids 留 CPU——device_map 路径
  accelerate hook 会自动搬运，本机 device_map 段错误 → 手动 .to('cuda') →
  embedding 直接 device mismatch 崩溃（本脚本运行时补丁修复，不动安装包）
- 真凶②：无 flash-attn 时包内走 manual PyTorch attention（包自打印警告），
  Linux 轮子可治，见同目录 setup_wsl.sh

逐阶段计时（VQ encode / ForConditionalGeneration.generate 总 / talker AR 生成 /
speech_tokenizer VQ 解码）+ 全模块 device 普查 + ORT provider 普查 + 采样期
GPU 利用率，双探针（warmup + steady）。

用法：
  Windows: PYTHONIOENCODING=utf-8 D:/models/Qwen3TTS/.venv/Scripts/python.exe \
             qwen_audit.py [--size 0.6b|1.7b] [--tokens N]
  WSL:     同脚本，环境由 setup_wsl.sh 建（~/qwen-tts/.venv）
"""
import argparse
import json
import subprocess
import threading
import time
from pathlib import Path

import platform

if platform.system() == "Windows":
    QWEN_ROOT = Path("D:/models/Qwen3TTS")
    REF_WAV = Path("D:/models/IndexTTS25/refaudio/my_voice_seg.wav")
else:  # WSL：同机双栈复用 D 盘权重
    QWEN_ROOT = Path("/mnt/d/models/Qwen3TTS")
    REF_WAV = Path("/mnt/d/models/IndexTTS25/refaudio/my_voice_seg.wav")
REF_TXT = QWEN_ROOT / "ref_text.txt"

# ---------------------------------------------------------------- GPU 采样
_gpu_samples = []  # (t, util%, mem_mib)
_stop = threading.Event()


def _gpu_sampler():
    while not _stop.is_set():
        try:
            out = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=3)
            util, mem = out.stdout.strip().split(",")
            _gpu_samples.append((time.perf_counter(), int(util), int(mem)))
        except Exception:
            pass
        _stop.wait(1.0)


def gpu_window(t0, t1):
    w = [s for s in _gpu_samples if t0 <= s[0] <= t1]
    if not w:
        return "n/a"
    utils = [s[1] for s in w]
    return (f"util avg {sum(utils)/len(utils):.0f}% max {max(utils)}% "
            f"mem {max(s[2] for s in w)}MiB")


# ---------------------------------------------------------------- 计时包装
stage_stats = {}


def wrap_timer(obj, name):
    orig = getattr(obj, name)
    key = f"{type(obj).__name__}.{name}"

    def timed(*a, **k):
        t0 = time.perf_counter()
        try:
            return orig(*a, **k)
        finally:
            stage_stats[key] = stage_stats.get(key, 0.0) + time.perf_counter() - t0
    setattr(obj, name, timed)


# ---------------------------------------------------------------- 普查
def device_census(model, label):
    counts = {}
    for n, p in model.named_parameters():
        dev = str(p.device)
        counts[dev] = counts.get(dev, 0) + p.numel()
    total = sum(counts.values())
    print(f"  [{label}] params: " + ", ".join(
        f"{k}={v/1e6:.1f}M({v/total*100:.1f}%)" for k, v in sorted(counts.items())),
        flush=True)
    cpu_buf = [n for n, b in model.named_buffers() if not str(b.device).startswith("cuda")]
    if cpu_buf:
        print(f"  [{label}] CPU buffers: {len(cpu_buf)} e.g. {cpu_buf[:3]}", flush=True)


def ort_census(model, label):
    """递归找 ONNX Runtime InferenceSession，报 provider（CPU EP = 掉 CPU 铁证）"""
    import onnxruntime
    found = []

    def walk(obj, path, depth=0):
        if depth > 6 or len(found) > 8:
            return
        for attr in vars(obj):
            if attr.startswith("_"):
                continue
            try:
                v = getattr(obj, attr)
            except Exception:
                continue
            if isinstance(v, onnxruntime.InferenceSession):
                found.append((f"{path}.{attr}", v.get_providers()))
            elif hasattr(v, "__dict__") and depth < 5:
                walk(v, f"{path}.{attr}", depth + 1)
    walk(model, "model")
    for path, provs in found:
        print(f"  [{label}] ORT {path}: providers={provs}", flush=True)
    if not found:
        print(f"  [{label}] 未发现 ORT session", flush=True)


# ---------------------------------------------------------------- 运行时补丁
def patch_tokenize_device(qwen):
    """修复①：input_ids 留 CPU（device_map 段错误机的手动 .to('cuda') 路径必崩）。

    只 patch 实例，不动安装包；补丁随本脚本/synth_qwen.py 走。
    """
    orig = qwen._tokenize_texts

    def to_device(texts):
        return [t.to(qwen.model.device) for t in orig(texts)]
    qwen._tokenize_texts = to_device


# ---------------------------------------------------------------- 主流程
def main():
    import torch
    from qwen_tts import Qwen3TTSModel

    ap = argparse.ArgumentParser()
    ap.add_argument("--size", default="0.6b", choices=["0.6b", "1.7b"])
    ap.add_argument("--tokens", type=int, default=36,
                    help="探针句 max_new_tokens（12Hz → 36 tok ≈ 3s 音频）")
    ap.add_argument("--attn", default=None,
                    help="attn_implementation（sdpa/flash_attention_2/eager；"
                         "默认 None=包内默认。WSL+flash-attn 装好后 A/B 用）")
    a = ap.parse_args()

    weights = QWEN_ROOT / "weights" / ("Qwen3-TTS-12Hz-0.6B-Base"
                                       if a.size == "0.6b" else "Qwen3-TTS-12Hz-1.7B-Base")
    probe_text = "今天我们用三句话讲清楚这个概念。"

    print(f"platform={platform.system()} torch {torch.__version__} "
          f"cuda_ok={torch.cuda.is_available()} threads={torch.get_num_threads()} "
          f"attn={a.attn or 'default'}", flush=True)
    th = threading.Thread(target=_gpu_sampler, daemon=True)
    th.start()

    load_kwargs = {"dtype": torch.bfloat16}
    if a.attn:
        load_kwargs["attn_implementation"] = a.attn
    t0 = time.perf_counter()
    qwen = Qwen3TTSModel.from_pretrained(str(weights), **load_kwargs)
    t_load = time.perf_counter() - t0
    t0 = time.perf_counter()
    qwen.model.to("cuda")
    t_move = time.perf_counter() - t0
    print(f"load {t_load:.1f}s + move {t_move:.1f}s", flush=True)
    device_census(qwen.model, "after .to('cuda')")
    ort_census(qwen.model.speech_tokenizer, "speech_tokenizer")

    wrap_timer(qwen.model, "generate")
    wrap_timer(qwen.model.talker, "generate")
    wrap_timer(qwen.model.speech_tokenizer, "decode")
    wrap_timer(qwen.model.speech_tokenizer, "encode")

    ref_text = REF_TXT.read_text(encoding="utf-8").strip()
    t0 = time.perf_counter()
    items = qwen.create_voice_clone_prompt(ref_audio=str(REF_WAV), ref_text=ref_text)
    print(f"create_voice_clone_prompt(cold) {time.perf_counter()-t0:.2f}s "
          f"stages={ {k: round(v, 2) for k, v in stage_stats.items()} }", flush=True)
    t0 = time.perf_counter()
    items = qwen.create_voice_clone_prompt(ref_audio=str(REF_WAV), ref_text=ref_text)
    print(f"create_voice_clone_prompt(warm) {time.perf_counter()-t0:.2f}s", flush=True)

    def probe(tag):
        stage_stats.clear()
        print(f"\n== probe[{tag}] max_new_tokens={a.tokens} ==", flush=True)
        t0 = time.perf_counter()
        wavs, sr = qwen.generate_voice_clone(
            text=probe_text, voice_clone_prompt=items,
            non_streaming_mode=True, max_new_tokens=a.tokens)
        dt = time.perf_counter() - t0
        dur = len(wavs[0]) / float(sr)
        print(f"[{tag}] wall {dt:.2f}s | audio {dur:.2f}s | RTF {dt/dur:.2f} "
              f"| {gpu_window(t0, t0+dt)}", flush=True)
        print(f"[{tag}] stages: " + json.dumps(
            {k: round(v, 2) for k, v in sorted(stage_stats.items())}), flush=True)
        return dt, dur, wavs, sr

    # A 档：试点原样（预期：device mismatch 崩溃 → 证明试点路径在本机不可用）
    try:
        probe("A-pilot-asis")
    except RuntimeError as e:
        print(f"[A-pilot-asis] 崩溃（预期内）：{str(e)[:120]}", flush=True)

    # B 档：tokenize 补丁（input_ids 上卡）——Windows 单进程修复档
    patch_tokenize_device(qwen)
    probe("B-fix-warmup")
    dt, dur, wavs, sr = probe("B-fix-steady")

    out = QWEN_ROOT / f"audit_out_{platform.system().lower()}.wav"
    import soundfile as sf
    sf.write(str(out), wavs[0], sr)
    print(f"\nsaved {out} ({dur:.2f}s, sr={sr})", flush=True)
    _stop.set()
    print("AUDIT_DONE", flush=True)


if __name__ == "__main__":
    main()
