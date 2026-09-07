# -*- coding: utf-8 -*-
"""Qwen3-TTS vLLM-Omni 探针（WSL，2026-09-07）：结构性提速档的快听 + RTF 实测。

动机：transformers 栈解码循环病根 = 每 talker token 嵌套一次 HF generate 且子解码器
全历史重 prefill（无持久 KV），单核 CPU 打满、GPU 0%。vLLM-Omni 官方 day-0 支持且
重写了解码循环。本脚本对齐官方 end2end.py 的 Base-icl 输入结构，用本仓参考音对出
探针句，量 RTF 并存 wav 供盲听。

用法（WSL，vllm venv）：
  source ~/qwen-tts/.venv-vllm/bin/activate
  python /mnt/d/codes/blog-src/.skills/skills/video-generation/scripts/qwen/qwen_vllm_probe.py \
    [--batch]  # --batch = 两句一批（Code2Wav CUDA graph 要求 batch 为 2 的幂）
"""
import argparse
import os
import sys
import time

os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")

EX_DIR = os.path.expanduser("~/vllm-omni/examples/offline_inference/text_to_speech/qwen3_tts")
sys.path.insert(0, EX_DIR)

MODEL = "/mnt/d/models/Qwen3TTS/weights/Qwen3-TTS-12Hz-0.6B-Base"
REF_AUDIO = "/mnt/d/models/IndexTTS25/refaudio/my_voice_seg.wav"
REF_TEXT = open("/mnt/d/models/Qwen3TTS/ref_text.txt", encoding="utf-8").read().strip()
PROBE = ["今天我们用三句话讲清楚这个概念。",
         "第一步装好工具，第二步改一个配置，第三步验证生效。"]

OUT_DIR = "/mnt/d/models/Qwen3TTS/vllm_probe_out"


def build_input(text, estimate_len):
    info = {"task_type": ["Base"], "ref_audio": [REF_AUDIO], "ref_text": [REF_TEXT],
            "text": [text], "language": ["Chinese"], "x_vector_only_mode": [False],
            "max_new_tokens": [2048]}
    return {"prompt_token_ids": [0] * estimate_len(info),
            "additional_information": info}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", action="store_true", help="两句一批跑（吞吐档）")
    ap.add_argument("--gpu-mem", type=float, default=0.3,
                    help="gpu_memory_utilization（默认 0.3，给同卡生产任务留量）")
    a = ap.parse_args()

    import end2end  # 官方示例模块：复用 _estimate_prompt_len / _save_wav
    import soundfile as sf
    import torch
    from vllm_omni import Omni

    os.makedirs(OUT_DIR, exist_ok=True)
    est = lambda info: end2end._estimate_prompt_len(info, MODEL)

    print(f"[probe] engine init（model={MODEL} gpu_mem={a.gpu_mem}）...", flush=True)
    t0 = time.perf_counter()
    omni = Omni(model=MODEL, gpu_memory_utilization=a.gpu_mem,
                allowed_local_media_path="/")
    print(f"[probe] engine up in {time.perf_counter()-t0:.1f}s", flush=True)

    def run(batch, tag):
        t0 = time.perf_counter()
        n_audio = 0.0
        req = 0
        for stage_outputs in omni.generate(batch):
            mm = stage_outputs.outputs[0].multimodal_output
            end2end._save_wav(OUT_DIR, f"{tag}_{req}", mm)
            audio = mm["audio"]
            t = audio if not isinstance(audio, list) else torch.cat(audio, dim=-1)
            n_audio = len(t.flatten()) / float(mm["sr"] if not isinstance(mm["sr"], list) else mm["sr"][0])
            req += 1
        wall = time.perf_counter() - t0
        print(f"[{tag}] wall {wall:.2f}s | audio {n_audio:.2f}s/句 x{req} | "
              f"RTF {wall/max(1e-9, n_audio):.2f}", flush=True)

    if a.batch:
        run([build_input(t, est) for t in PROBE], "batch2")
    else:
        for i, t in enumerate(PROBE):
            run([build_input(t, est)], f"single{i}")
    print("[probe] wavs ->", OUT_DIR, flush=True)


if __name__ == "__main__":
    main()
