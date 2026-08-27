# -*- coding: utf-8 -*-
"""本地文生图执行器（openspec video-gen-assets，在 WSL comfyui env 内运行）。

用法（Windows 侧 gen_assets.py 通过 wsl 子进程调用）：
    conda activate comfyui && PYTHONIOENCODING=utf-8 python -m video.local_t2i \
        --prompts /path/prompts.json --out-dir /path/out

prompts.json 格式：[{"id": "mcp_usb", "prompt": "..."}, ...]
输出：out-dir/<id>.png + stdout 逐张打印耗时与显存峰值。

显存策略（宿主 16G RAM / 8G VRAM 约束）：
- 默认 bf16 全量加载；--quant nf4 时对 transformer/text_encoder 走 bitsandbytes
  NF4 量化（DiT 6B ≈ 3.5G，整机可全进显存）。
- 加载或首图 CUDA OOM 时自动降级：NF4 失败→ bf16 + sequential offload（慢但稳）。

许可溯源（manifest 由 Windows 侧 gen_assets.py 写）：模型 Tongyi-MAI/Z-Image-Turbo，
权重协议见 model-dir/LICENSE 文件，禁止用于未核许可用途。
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
import time
from pathlib import Path


def _free_vram_mib() -> int:
    import torch
    free, _total = torch.cuda.mem_get_info()
    return int(free / (1024 * 1024))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", default="/mnt/d/models/z-image-turbo")
    ap.add_argument("--prompts", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--steps", type=int, default=0, help="0 = 管线默认（Turbo 蒸馏少步）")
    ap.add_argument("--guidance", type=float, default=0.0, help="0 = 管线默认")
    ap.add_argument("--seed", type=int, default=20260827)
    ap.add_argument("--quant", choices=["int8", "nf4", "bf16"], default="int8")
    args = ap.parse_args()

    import torch
    if not torch.cuda.is_available():
        print("CUDA unavailable inside WSL", file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    jobs = json.loads(Path(args.prompts).read_text(encoding="utf-8"))

    from diffusers import DiffusionPipeline

    dtype = torch.bfloat16

    def _pqc_int8():
        """Quanto int8：纯 torch 内核（无 bnb/triton 编译坑）。int8 后
        DiT≈6G、TE≈2G，全部可进 8G 显存；model_cpu_offload 再留出激活余量。"""
        from diffusers.quantizers.quantization_config import QuantoConfig
        from diffusers.quantizers import PipelineQuantizationConfig
        qc = QuantoConfig(weights_dtype="int8")
        return PipelineQuantizationConfig(
            quant_mapping={"transformer": qc, "text_encoder": qc})

    t0 = time.time()
    pipe = None
    mode = None
    attempts = []
    if args.quant == "int8":
        attempts.append(("int8-vram", {"torch_dtype": dtype,
                                       "quantization_config": _pqc_int8()}))
    if args.quant == "nf4":
        from diffusers import BitsAndBytesConfig
        from transformers import BitsAndBytesConfig as Tbnb
        from diffusers.quantizers import PipelineQuantizationConfig
        attempts.append(("nf4-vram-resident", {
            "torch_dtype": dtype,
            "quantization_config": PipelineQuantizationConfig(quant_mapping={
                "transformer": BitsAndBytesConfig(load_in_4bit=True),
                "text_encoder": Tbnb(load_in_4bit=True)})}))
    attempts.append(("bf16-seq-offload", {"torch_dtype": dtype}))
    last_exc = None
    for tag, kwargs in attempts:
        try:
            pipe = DiffusionPipeline.from_pretrained(args.model_dir, **kwargs)
            if tag == "bf16-seq-offload":
                pipe.enable_sequential_cpu_offload()
            else:
                pipe.enable_model_cpu_offload()
            mode = tag
            break
        except Exception as exc:  # noqa: BLE001 —— 换下一档降级
            print(f"[t2i] load mode {tag} failed: {type(exc).__name__}: {exc}",
                  flush=True)
            pipe = None
            last_exc = exc
    if pipe is None:
        raise last_exc
    print(f"[t2i] loaded in {time.time() - t0:.1f}s mode={mode} "
          f"free_vram={_free_vram_mib()}MiB", flush=True)

    gen_kwargs: dict = {}
    if args.steps > 0:
        gen_kwargs["num_inference_steps"] = args.steps
    if args.guidance > 0:
        gen_kwargs["guidance_scale"] = args.guidance

    report = []
    for i, job in enumerate(jobs):
        pid, prompt = job["id"], job["prompt"]
        t1 = time.time()
        g = torch.Generator("cuda").manual_seed(args.seed + i)
        try:
            img = pipe(prompt=prompt, width=args.width, height=args.height,
                       generator=g, **gen_kwargs).images[0]
        except torch.cuda.OutOfMemoryError:
            print(f"[t2i] OOM on {pid}; retrying smaller ...", flush=True)
            torch.cuda.empty_cache()
            img = pipe(prompt=prompt,
                       width=1024, height=576,   # 16 的倍数（Z-Image 硬约束）
                       generator=g, **gen_kwargs).images[0]
        dst = out_dir / f"{pid}.png"
        img.save(dst)
        cost = time.time() - t1
        print(f"[t2i] {i + 1}/{len(jobs)} {pid} -> {dst.name} "
              f"{cost:.1f}s free_vram={_free_vram_mib()}MiB", flush=True)
        report.append({"id": pid, "seconds": round(cost, 1),
                       "width": img.width, "height": img.height})

    (out_dir / "t2i_report.json").write_text(
        json.dumps({"mode": mode, "model": Path(args.model_dir).name,
                    "seed": args.seed, "images": report},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
