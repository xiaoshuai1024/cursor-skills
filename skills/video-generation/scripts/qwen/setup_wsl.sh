#!/usr/bin/env bash
# Qwen3-TTS WSL2 部署 + 复测（openspec windows-native-tts-research「留待 WSL 复测」兑现）。
#
# 动机（2026-09-07 审计实锤）：Windows 栈两病——① accelerate device_map 段错误被迫
# device_map="cpu"+.to('cuda') 绕行；② 无 flash-attn 轮子，包内走 manual PyTorch
# attention（包自打印警告）。Linux 两者皆有解。
#
# 用法（Windows 侧，注意包在 bash -c 里防 Git Bash 路径改写）：
#   wsl -d Ubuntu -- bash -c "bash /mnt/d/codes/blog-src/.skills/skills/video-generation/scripts/qwen/setup_wsl.sh [--skip-audit]"
# 幂等：重复执行只补缺失步骤。产物 venv=~/qwen-tts/.venv（WSL 内 fs → D 盘 vhdx，C 盘安全）。
# 网络：PyPI 走清华镜像（astral.sh/GitHub 在本机网络不稳，uv 用已装好的 ~/.local/bin/uv）。
set -uo pipefail

REPO=/mnt/d/codes/blog-src
SKILL_QWEN=$REPO/.skills/skills/video-generation/scripts/qwen
WIN_SITE=/mnt/d/models/Qwen3TTS/.venv/Lib/site-packages
HOME_DIR=~/qwen-tts
VENV=$HOME_DIR/.venv
MIRROR=https://pypi.tuna.tsinghua.edu.cn/simple
LOG_TAG="[setup_wsl]"
SKIP_AUDIT=0
[ "${1:-}" = "--skip-audit" ] && SKIP_AUDIT=1

echo "$LOG_TAG start $(date)"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null \
  || { echo "$LOG_TAG WSL 内无 nvidia-smi（CUDA 直通异常），中止"; exit 1; }

# ---- uv：优先用已装的（勿从 astral.sh 重装——本机网络对它会挂死）
UV=$HOME/.local/bin/uv
if [ ! -x "$UV" ]; then
  python3 -m pip install --user uv -i "$MIRROR" 2>/dev/null \
    && UV=$(python3 -m site --user-base)/bin/uv \
    || { echo "$LOG_TAG 无可用 uv 且 pip3 兜底失败"; exit 1; }
fi
echo "$LOG_TAG uv: $($UV --version)"

# ---- venv + 依赖（清华镜像；PyPI linux torch 2.8.0 = cu128 构建，与 Windows 档同代）
export UV_HTTP_TIMEOUT=180
mkdir -p "$HOME_DIR"
[ -d "$VENV" ] || "$UV" venv --python 3.12 "$VENV"
source "$VENV/bin/activate"
if ! python -c "import torch" 2>/dev/null; then
  echo "$LOG_TAG installing torch (mirror, ~3GB, 静默下载请耐心)..."
  "$UV" pip install torch==2.8.0 --index-url "$MIRROR" \
    || "$UV" pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cu128
fi
python -c "import qwen_tts" 2>/dev/null \
  || "$UV" pip install qwen-tts==0.1.1 torchaudio==2.8.0 soundfile librosa \
        --index-url "$MIRROR"
python - <<'EOF' && echo "$LOG_TAG deps ok"
import torch, qwen_tts, soundfile, librosa
print("torch", torch.__version__, "cuda", torch.cuda.is_available())
EOF

# ---- sox 补丁对齐：直接拷 Windows venv 已打补丁的 speech_vq.py（numpy 峰值归一等价，
#      双平台产物一致）。幂等。定位用 sysconfig（勿 import qwen_tts——依赖装坏时它自己
#      会崩，且 import 会把 flash-attn 警告打到 stdout 污染路径，2026-09-07 双坑实录）。
LNX_SITE=$(python -c "import sysconfig; print(sysconfig.get_paths()['purelib'])")
SRC_PATCH="$WIN_SITE/qwen_tts/core/tokenizer_25hz/vq/speech_vq.py"
DST_PATCH="$LNX_SITE/qwen_tts/core/tokenizer_25hz/vq/speech_vq.py"
if [ -f "$DST_PATCH" ] && ! cmp -s "$SRC_PATCH" "$DST_PATCH"; then
  cp "$SRC_PATCH" "$DST_PATCH" && echo "$LOG_TAG speech_vq.py 补丁已同步"
elif [ -f "$DST_PATCH" ]; then
  echo "$LOG_TAG speech_vq.py 补丁已就位"
else
  echo "$LOG_TAG 异常：未找到 $DST_PATCH"
fi

# ---- flash-attn 预编译轮子（torch2.8+cu12+py312；github 网络不稳则跳过，sdpa 档照跑）
if ! python -c "import flash_attn" 2>/dev/null; then
  PYV=$(python -c "import sys; print(f'cp{sys.version_info.major}{sys.version_info.minor}')")
  ABI=$(python -c "import torch; print(str(torch._C._GLIBCXX_USE_CXX11_ABI).upper())")
  FA_VER=2.8.3
  BASE="https://github.com/Dao-AILab/flash-attention/releases/download"
  ok=""
  for abi in "$ABI" TRUE FALSE; do
    WHL="flash_attn-${FA_VER}+cu12torch2.8cxx11abi${abi}-${PYV}-${PYV}-linux_x86_64.whl"
    echo "$LOG_TAG try $WHL"
    if curl -sfL --max-time 300 -o /tmp/fa.whl "$BASE/v${FA_VER}/$WHL"; then
      if "$UV" pip install /tmp/fa.whl --index-url "$MIRROR"; then ok="$WHL"; break; fi
    fi
  done
  if [ -n "$ok" ]; then echo "$LOG_TAG flash-attn 装好：$ok"; else echo "$LOG_TAG flash-attn 轮子拉取/安装失败（github 网络），跳过——sdpa 档照跑"; fi
else
  echo "$LOG_TAG flash-attn 已装：$(python -c 'import flash_attn; print(flash_attn.__version__)')"
fi

# ---- 审计（默认 attn + flash 档；--skip-audit 用于先装环境后补测，避免抢卡污染数据）
if [ "$SKIP_AUDIT" = "1" ]; then
  echo "$LOG_TAG --skip-audit：环境就绪，审计未跑（之后手动：python $SKILL_QWEN/qwen_audit.py）"
else
  AUDIT="$SKILL_QWEN/qwen_audit.py"
  echo "$LOG_TAG ---- audit: default attn ----"
  python "$AUDIT" --tokens 36 || echo "$LOG_TAG default attn audit 失败"
  if python -c "import flash_attn" 2>/dev/null; then
    echo "$LOG_TAG ---- audit: flash_attention_2 ----"
    python "$AUDIT" --tokens 36 --attn flash_attention_2 || echo "$LOG_TAG flash audit 失败"
  fi
fi

echo "$LOG_TAG done $(date)"
