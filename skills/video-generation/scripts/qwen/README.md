# Qwen3-TTS 朗读链（性能优化 + 固化，2026-09-07）

默认朗读引擎 Qwen3-TTS-0.6B-Base（2026-09-07 用户定规）的合成脚本区。本目录是
**唯一事实源**；仓库侧只留入口 `scripts/video/_qwen_synth.sh`。

## 文件

| 文件 | 作用 |
|------|------|
| `synth_qwen.py` | 生产驱动：narrations → sent 契约。断点续跑、`--jobs N` 多进程、`--gate` 可选 v4 门禁、`--probe` 探针、RTF 遥测 |
| `qwen_audit.py` | 性能审计：阶段计时（VQ encode / generate / talker AR / decode）+ device 普查 + ORT provider + GPU 采样，A/B 修复档 |
| `setup_wsl.sh` | WSL2 部署 + 复测（uv venv + torch cu128 + flash-attn 预编译轮子 + sox 补丁同步 + 自动跑审计） |

## 部署布局

| 组件 | Windows（现役） | WSL（复测/提速档） |
|------|----------------|-------------------|
| venv | `D:/models/Qwen3TTS/.venv` | `~/qwen-tts/.venv`（setup_wsl.sh 建） |
| 权重 | `D:/models/Qwen3TTS/weights/`（0.6B/1.7B，两栈共用） | `/mnt/d/models/Qwen3TTS/weights/` |
| 参考音对 | `D:/models/IndexTTS25/refaudio/my_voice_seg.wav` + `D:/models/Qwen3TTS/ref_text.txt`（fw-small 转写逐字核对） | 同路径（/mnt/d） |
| sox 补丁 | venv 内已打（numpy 峰值归一等价） | setup_wsl.sh 从 Windows venv 同步同文件，保证双栈产物一致 |

## 根因档案（2026-09-07 审计实锤，勿再走弯路）

1. **本机 `device_map="cuda:0"` 段错误**（干净卡也是）→ 生产口径 =
   `device_map="cpu"` 加载 + `.to("cuda")`：accelerate hook 自动搬输入张量，
   能跑但绕。
2. **裸 `.to("cuda")` 不带 hook 会崩**：wrapper `_tokenize_texts` 的 input_ids
   留 CPU，embedding 直接 device mismatch（qwen_audit.py 的 A 档可复现）。
   `patch_tokenize_device()` 运行时补丁可治——不动安装包，随脚本走。
3. **真凶 = 解码循环纯 CPU 瓶颈（平台无关）**：源码实证每个 talker token 嵌套
   一次完整 HF `code_predictor.generate()`，且子解码器每次 `torch.cat((past_hidden,
   ...))` 全历史重 prefill（无持久 KV cache）；实测生成期 GPU 利用率 0%、单核
   CPU 109% 打满。Windows 与 WSL(sdpa) 同病 → **flash-attn 非主角**（GPU 本就
   没吃满）；对症药 = vLLM-Omni（重写解码循环）。
4. **旧驱动每句重传 `ref_audio`** = 每句重付 ~25s 参考音 VQ 编码；
   `synth_qwen.py` 改为每进程构建一次 `voice_clone_prompt` 复用（该 25s 在
   RTF≈200 的循环瓶颈面前占比小，但在 vLLM 档/短句批量下是净赚）。
5. sdpa / non_streaming_mode / 批量模式调参无效（openspec 已实证 + 09-07 复核）。

## 性能数据（实测回填 2026-09-07）

| 配置 | RTF | 40 句全片估算 | 来源 |
|------|-----|--------------|------|
| Windows 旧驱动（每句重建 prompt，串行） | ≈199-300（生产实况 722s/3.52s 句=205） | ≈7-10h | synth_qwen3tts.py 时代 |
| Windows skill 驱动（prompt 复用，串行） | ≈205（争抢期实测，瓶颈在解码循环） | ≈7h | 生产续跑实测 |
| Windows skill 驱动 `--jobs 2` | 单句 RTF 不变（延迟型瓶颈），**吞吐 ×2** | **≈3.5h** | 生产续跑实测（2026-09-07） |
| WSL transformers sdpa | 3s 探针 >8min 未完成（GPU 0%/单核 109%） | 不可用 | qwen_audit.py WSL 档 |
| WSL flash_attention_2 | 未测——GPU 0% 已证注意力非瓶颈，降级 | — | — |
| WSL vLLM-Omni | **待测**（WSL 服务故障恢复后跑 probe；预期重写解码循环后 RTF<1） | 分钟级（若达标） | setup_wsl_vllm.sh + qwen_vllm_probe.py |

⚠️ 并行注意：worker 实测 CPU 占空仅 ~30%（大量时间等 GPU 同步/上下文切换），
吞吐近似线性于进程数直到显存上限；VRAM 预估 2300MiB/实例偏保守（实测峰值
1.76GB），模拟器等桌面占卡时按 `--jobs` 输出的显存上限为准。

## 用法

```bash
# 生产（仓库根，入口见 scripts/video/_qwen_synth.sh）
bash scripts/video/_qwen_synth.sh <slug> --jobs 3        # 并行 3 进程（显存自动封顶）
bash scripts/video/_qwen_synth.sh <slug> --backup        # 首次换声：备份旧产物
bash scripts/video/_qwen_synth.sh <slug> --gate          # 可选：v4 停顿门禁+手术
bash scripts/video/_qwen_synth.sh --probe                # 两句探针快听 + RTF

# 审计（诊断/复测，只读不写台账）
PYTHONIOENCODING=utf-8 D:/models/Qwen3TTS/.venv/Scripts/python.exe qwen_audit.py

# WSL 部署 + 复测（Windows 侧发起）
wsl -d Ubuntu -- bash -c "bash /mnt/d/codes/blog-src/.skills/skills/video-generation/scripts/qwen/setup_wsl.sh"
```

## 定规（默认值即定规，改默认先过用户）

- **门禁默认关**：保护用户试听认可的原始停顿（2026-09-07 定规）；`--gate` 才开 v4 选优。
- **加载与调用口径冻结**：`device_map="cpu"` + `.to("cuda")` + `language="Chinese"`
  + prompt 复用——这是已验收音色的复现路径，改动即音色回归风险。
- 换声/换引擎参考音走 `ref_text.txt` 配对校验（fw-small 转写核对，勿手写）。
- 产物契约 = synth_indextts25.py 同构（meta.json 供 assemble.py；qwen_metrics.json
  为 Qwen 增量遥测）。
