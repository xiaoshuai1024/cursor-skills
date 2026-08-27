# -*- coding: utf-8 -*-
"""生成式素材统一入口（openspec video-gen-assets，Windows 侧编排）。

两条 provider 通道：
- comfyui/diffusers 本地链：经 WSL comfyui env 跑 video.local_t2i（当前 demo 主路）
- zhipu 云端链：CogView-3-Flash / CogVideoX-Flash 免费档 REST 直连，
  需环境变量 ZHIPU_API_KEY；未配置时报错并提示（绝不静默降级到付费档）

产物落 项目根/video-generation/assets/<slug>/：PNG/MP4 + manifest.json
（prompt/model/license/seed/qc 溯源字段，shots 素材真实性纪律的对齐件）。

用法：
    python -m video.gen_assets --slug <slug> --prompts prompts.json [--provider local]
prompts.json: [{"id": "mcp_usb", "subject": "MCP 协议像 USB 接口", ...}]
subject 会拼进风格模板（palette 同调：深蓝黑底 + 单主青强调）。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from video.config import OUTPUT_ROOT  # noqa: E402

WSL_DISTRO = "Ubuntu"
WSL_ENV_PY = "/home/john/miniconda3/envs/comfyui/bin/python"
MODEL_DIR = "/mnt/d/models/z-image-turbo"

# 风格模板（去 AI 味 + palette 同调）：深蓝黑 #0a0e1a 底、单主青 #22d3ee 强调
STYLE_SUFFIX = (
    "dark navy tech illustration style, deep dark blue-black background "
    "color #0a0e1a, single cyan accent color #22d3ee, subtle glow lines, "
    "clean isometric composition, flat geometric shapes, professional "
    "tech explainer art, no text, no words, no letters"
)
NEGATIVE = ("rainbow colors, gradient explosion, cluttered, photo realistic face, "
            "human portrait, watermark, signature, text artifacts")

LICENSES = {
    "z-image-turbo": "Tongyi-MAI/Z-Image-Turbo 权重——许可待核（Phase0 任务1.6），限内部验证使用",
    "cogview-3-flash": "智谱免费 API——产物商用条款待核（Phase0 任务1.6），限内部验证使用",
}


def _win_to_wsl(p: Path) -> str:
    s = p.resolve().as_posix()
    drive, rest = s[0].lower(), s[2:]
    return f"/mnt/{drive}{rest}"


def _run_local(prompts_file: Path, out_dir: Path, quant: str,
               steps: int = 8, guidance: float = 4.0) -> int:
    wsl_prompts = _win_to_wsl(prompts_file)
    wsl_out = _win_to_wsl(out_dir)
    cmd = [
        "wsl", "-d", WSL_DISTRO,
        "--", "bash", "-lc",
        f"cd /mnt/d/codes/blog-src/.agents/skills/video-generation/scripts && "
        f"export CC=/home/john/miniconda3/envs/comfyui/bin/x86_64-conda-linux-gnu-cc "
        f"CXX=/home/john/miniconda3/envs/comfyui/bin/x86_64-conda-linux-gnu-c++ && "
        f"PYTHONIOENCODING=utf-8 {WSL_ENV_PY} -m video.local_t2i "
        f"--model-dir {MODEL_DIR} --prompts {wsl_prompts} --out-dir {wsl_out} "
        f"--quant {quant} --steps {steps} --guidance {guidance}",
    ]
    print("[gen-assets]", " ".join(cmd[:6]), "...")
    return subprocess.call(cmd)


def _run_zhipu(jobs: list, out_dir: Path, kind: str) -> int:
    key = os.environ.get("ZHIPU_API_KEY")
    if not key:
        print("✗ ZHIPU_API_KEY 未配置——云端免费通道不可用；本工具绝不静默走付费档。")
        return 3
    if kind != "illustration":
        print("✗ zhipu 视频通道（CogVideoX-Flash I2V）在本 change 属 Phase1 任务，先实现后放开")
        return 3
    import urllib.request
    results = []
    for job in jobs:
        payload = json.dumps({
            "model": "cogview-3-flash", "prompt": job["prompt"],
            "size": "1344x768",
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://open.bigmodel.cn/api/paas/v4/images/generations",
            data=payload,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {key}"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            url = json.loads(resp.read())["data"][0]["url"]
        dst = out_dir / f"{job['id']}.png"
        urllib.request.urlretrieve(url, dst)
        results.append({"id": job["id"], "provider": "cogview-3-flash"})
        print(f"[gen-assets] zhipu {job['id']} -> {dst.name}")
    (out_dir / "zhipu_report.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--prompts", required=True, help="JSON：[{id, subject}] 或 [{id, prompt}]")
    ap.add_argument("--provider", choices=["local", "zhipu"], default="local")
    ap.add_argument("--kind", choices=["illustration"], default="illustration")
    ap.add_argument("--quant", choices=["int8", "bf16", "nf4"], default="int8")
    args = ap.parse_args()

    assets_root = Path(OUTPUT_ROOT) / "assets" / args.slug
    assets_root.mkdir(parents=True, exist_ok=True)
    raw = json.loads(Path(args.prompts).read_text(encoding="utf-8"))
    jobs = []
    for item in raw:
        prompt = item.get("prompt") or f'{item.get("subject", "")}, {STYLE_SUFFIX}'
        jobs.append({"id": item["id"],
                     "prompt": f'{item.get("subject", item.get("prompt", ""))} | {STYLE_SUFFIX}'
                     if item.get("subject") else prompt})

    prompts_file = assets_root / "prompts.json"
    prompts_file.write_text(json.dumps(jobs, ensure_ascii=False, indent=2),
                            encoding="utf-8")

    if args.provider == "local":
        rc = _run_local(prompts_file, assets_root, args.quant)
    else:
        rc = _run_zhipu(jobs, assets_root, args.kind)
    if rc != 0:
        return rc

    report_p = assets_root / "t2i_report.json"
    gen_report = json.loads(report_p.read_text(encoding="utf-8")) if report_p.exists() else {}
    manifest = {
        "slug": args.slug,
        "provider": args.provider,
        "model": MODEL_DIR.split("/")[-1] if args.provider == "local" else "cogview-3-flash",
        "license_note": LICENSES["z-image-turbo" if args.provider == "local" else "cogview-3-flash"],
        "seed": gen_report.get("seed"),
        "mode": gen_report.get("mode"),
        "qc": "skipped_no_key（GLM-4V 门禁待 ZHIPU_API_KEY 配置后启用，任务2.4）",
        "images": [{"id": it["id"], "seconds": it.get("seconds"),
                    "wh": [it.get("width"), it.get("height")]}
                   for it in gen_report.get("images", [])],
        "comfyui_runtime": False,  # demo spike 用 diffusers 直连；ComfyUI 迁移为 Phase1 任务
    }
    (assets_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[gen-assets] manifest -> {assets_root / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
