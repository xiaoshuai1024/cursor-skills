#!/usr/bin/env bash
# vLLM-Omni 部署（WSL，2026-09-07）：Qwen3-TTS 结构性提速档。
#
# 为什么是 vLLM：审计实锤断层推理栈的病根在解码循环——每个 talker token 嵌套一次
# HF generate() 且子解码器全历史重 prefill（无持久 KV），单核 CPU 打满、GPU 0%
# 利用率，Windows/WSL 同病，flash-attn 治不了。vLLM-Omni 是官方 day-0 支持，
# 重写了解码循环（持续批量 + CUDA graph）。
#
# 用法：wsl -d Ubuntu -- bash -c "bash /mnt/d/codes/blog-src/.skills/skills/video-generation/scripts/qwen/setup_wsl_vllm.sh"
# 产物：~/qwen-tts/.venv-vllm（独立 venv，与 transformers 栈隔离；uv 走 ~/uvtool/bin/uv）
set -uo pipefail
MIRROR=https://pypi.tuna.tsinghua.edu.cn/simple
U="$HOME/uvtool/bin/uv"
PYV="$HOME/qwen-tts/.venv-vllm/bin/python"

# uv 新版（--torch-backend 需要）；无则从 PyPI 镜像装进 ~/uvtool
if [ ! -x "$U" ]; then
  "$HOME/.local/bin/uv" venv "$HOME/uvtool" --python 3.12
  "$HOME/.local/bin/uv" pip install -p "$HOME/uvtool/bin/python" uv --index-url "$MIRROR"
fi

export UV_HTTP_TIMEOUT=300
[ -d "$HOME/qwen-tts/.venv-vllm" ] || "$U" venv "$HOME/qwen-tts/.venv-vllm" --python 3.12
if ! "$PYV" -c "import vllm" 2>/dev/null; then
  echo "[vllm-setup] installing vllm 0.28.0（~4GB，静默期请耐心）..."
  "$U" pip install -p "$PYV" vllm==0.28.0 --torch-backend=auto --index-url "$MIRROR"
fi
"$PYV" -c "import vllm_omni" 2>/dev/null \
  || "$U" pip install -p "$PYV" vllm-omni --index-url "$MIRROR"
"$PYV" -c "import vllm, vllm_omni; print('VLLM_OMNI_OK', vllm.__version__)"

# 示例仓（Base-icl 端到端参考）
[ -d "$HOME/vllm-omni" ] || git clone --depth 1 https://github.com/vllm-project/vllm-omni.git "$HOME/vllm-omni"
ls "$HOME/vllm-omni/examples/offline_inference/qwen3_tts/" 2>/dev/null \
  && echo "[vllm-setup] examples ready"
echo "[vllm-setup] done"
