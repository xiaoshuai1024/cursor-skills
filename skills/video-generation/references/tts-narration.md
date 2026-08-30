# TTS 与口播细则（tts-narration）

> 拆分自 SKILL.md「规则约束 → 发音/断句/音频同步」与「音色选择」（2026-08-30，openspec video-generation-skill-split），内容逐字保留；默认口播配置（IndexTTS-2 全节）仍在 SKILL.md。

### 发音（重要决策，多次试听迭代确认）

> ### ⚠️ 默认口播 = IndexTTS-2 用户声克隆，不是 edge-tts（2026-08-25 定规，违者返工）
>
> **每条正式视频的口播必须走克隆链**（用户声音，AGENTS.md「视频声音管线」为权威）：WSL `scripts/video/synth_indextts.py <slug> --attempts 4 --emo dyn`（2026-08-28 定档 D，openspec tts-emotion-dynamics：逐句角色情绪向量值已烙入 `emotion_map.py`，`--emo-scale` 仅作 ±0.1 微调；参考音 `~/refaudio/my_voice_seg.wav`，逐句 best-of-N 门禁选优）→ `tts_pipeline/assemble.py`（发布五步链：120ms 垫 / RMS -18dB / treble g=2 / deesser / alimiter）→ `tts_speed_shrink.py --tempo 1.06` → 产物落 `video-generation/audio/<slug>_t/` → `make video` 换声旁路自动接管（`audio/<slug>_t/audio_*.mp3 + boundaries_*.json` 在则跳过 edge-tts）。本节及「音色选择」的 edge-tts 内容**仅是克隆链不可用时的 fallback**，fallback 必须先向用户说明并获准，不得默认使用。`narrations/<slug>.json` 的 `voice/rate` 字段只在 fallback 生效——渲染前 checklist 必查一项：**口播是否为用户克隆声**。

- edge-tts 中文语音**不支持 SSML 音素控制**（标签会被当文本读出）
- **缩写逐字母 vs 单词音的权衡**（核心经验）：
  - 逐字母（DOM→`D O M`）读得准，但每个字母停顿 ~197ms，**慢且不自然**
  - 单词音（API→/æpi/、GLM→/gælm/）**自然流畅**，虽不完全符合中文技术圈逐字母习惯，但可识别
  - ✅ **结论**：`normalize_for_tts` 白名单**只留会被读成"无法识别中文错音"的词**，其他缩写当单词读。当前白名单 = `{DOM, AI}`。
  - ⚠️ **AI 必须逐字母**（claude-plugins 视频踩坑，两次复发）：男声 `YunxiNeural` 实测原始 "AI" 被当单词读成拼音音"爱/哀"（不自然），"A I" 才是技术圈标准读法。故 AI 进白名单 → normalize 展开成 "A I"。**旧的"AI 自动逐字母、保持原样"结论是错的**，WordBoundary 探针已推翻。验证方法：合成后看 WordBoundary 是否把 AI 拆成 A、I 两个独立词。
  - ⚠️ **TUI 大小写通吃 + 探针必须用口播原文（2026-08-17 踩坑）**：dsh-TUI 读音错误两轮才修好——第一轮只把 `TUI` 加进白名单，但白名单正则 `[A-Z]{2,5}` 只匹配大写，而口播写的是小写 `dsh-tui`，normalize 根本没命中，用户复听仍错。**修法：normalize 里追加大小写不敏感规则（`[tT][uU][iI]` → "T U I"）**；且**探针测试必须用口播文件里的原文（含小写）**，不能只测大写形式——探针通过 ≠ 口播通过。
  - ⚠️ **多音字「行」作量词被读成 xíng（2026-08-28 用户实听定规，勿再犯）**：口播里「日志多少**行** / 那**行**报错 / 代码一**行**没丢 / 通知**行**」的「行」（háng）克隆声一律误读成 xíng，index-tts 无拼音标注通道、参数修不动。**写稿期规避**：量词场合一律改「条」（那行→那条）或删量词（代码一行没丢→代码没丢）；「行」只允许出现在 xíng 语义（行不行/行动）或固定词（行业/银行）里。口播稿定稿前 grep `那行|一行|通知行|多少行` 自查（humor-pilot-exitcode 实翻车三处）。
  - ❌ 不要靠整体提速（rate +20%）补偿字母停顿——会让中文语调变机械。英文慢的根因是加空格，不是语速。
- **rate 用 `+8%`**（自然区间，验证过）。男声 `zh-CN-YunxiNeural`（科普/技术默认），女声 `zh-CN-XiaoxiaoNeural`（培训）。
- ❌ 不要用中文谐音替换（如 "AI"→"诶爱"）：实测反而切成两个独立词
### 断句（`narrate.split_units`，避免误切）
- 先按中文标点（`，。、：；`）拆意群——这步永远对
- 超长才字数硬切，阈值 **24**（接近字幕单行容量）。❌ 不要用 18，会把 "DeepSeek发布V4 Flash正式版"(20字) 切成两半
- 英文词块**整体切**（`computed style` 不可断成 `computed`+`style`）
- **尾部短词(<6字)回并上一句**——避免 "正式版" 这类尾巴单独成句、断句不自然
- ⚠️ **超 24 字分句会硬切中文词**（claude-plugins 踩坑）：某分句 >24 字时按字符硬切，切点不看词边界，实测 "12 个按 GitHub Star 排行的必装开源插件"(28字)→"必装开|源插件"、"…结构化的无障碍快照…"(29字)→"结构|化"。**修法：写口播句子时保证每个标点分句 ≤24 字**，从源头避免触发硬切。计数注意：英文词块含空格算（"Playwright MCP"=14 字）。
### 音频同步（架构约束，违反即错）
- **narrate 管线**：逐意群单元合成 mp3 → **ffmpeg `concat` filter**（样本级精确）拼接。时间戳基于 probe 累加，与音频严格同源。
  - ❌ 不用 concat **demuxer `-c copy`**：mp3 帧间 encoder padding 会累计，时间戳和音频漂移几十~几百 ms（音画不同步的根因）
  - ❌ 不用"逐句合成拿时间戳 + 整段重合成 mp3"：两次合成，时间戳和音频来自不同合成，漂移
  - ✅ 验收标准：最后单元 end_frame/60 与音频 total_seconds 偏差 < 0.01s
- **courseware/graph 管线**：视频段用 **xfade** 转场（段间重叠 `transition_dur=0.8s`），音频**必须**用 **acrossfade** 与视频一一对应，总时长 = `sum(dur) - (n-1)*0.8`
### 音色选择（2026-08-18 实测标定）

对标过抖音口播标杆（低沉男声解说型，F0 中位 ≈148Hz、频谱质心 ≈1kHz，偏暗），用同一句文案对 edge-tts 4 个中文男声测基频/质心对比，结论：

| 场景 | 音色 | 说明 |
|------|------|------|
| ⚠️ **正式视频一律不用** | （克隆链） | 见「发音」节顶部的克隆默认定规；下表仅克隆链不可用且用户已批准 fallback 时查用 |
| **解说/深度/悬疑叙事（fallback 默认）** | `zh-CN-YunjianNeural` | 低沉磁性男声（F0med 132Hz、质心 1205Hz，4 者中最接近对标），rate `0%`~`+8%` |
| 轻快教程/产品演示 | `zh-CN-YunxiNeural` | 阳光青年男声（F0med 186Hz），节奏快时配 `+10%`~`+15%` |
| 新闻播报式/权威口径 | `zh-CN-YunyangNeural` | 播音腔男声，音色偏亮（质心 1543Hz），科普引用数据时可切 |
| 培训/温和女声 | `zh-CN-XiaoxiaoNeural` | 女声兜底 |

- 判据可复现：`ffmpeg` 抽 wav → 30ms 帧自相关估 F0 + rFFT 质心，对比样本落点（脚本思路见 `/tmp` 一次性分析，不必沉淀）。
- 抖音头部「AI 解说」类多为剪映系音色（如解说小帅），edge-tts 无同款；**YunjianNeural 是可白嫖的最接近替代**。若对标的明显是真人配音，不做音色克隆，按上表选最近替代。

---

## 附录：二批搬运（2026-08-30 拆分 pass2）——断句根源实证 / 已知坑

### 断句根源定论（实证存档，防止再走调参弯路）

IndexTTS-2 整句推理时，句内停顿由 **AR 随机采样**决定：tokenizer 实跑证明逗号只是段内普通 token（`interval_silence` 对单段句子不生效）；`infer_v2.py:590` `do_sample=True` 硬编码；同机同配置同句重采，停顿位置每次不同；上游 [issue #572](https://github.com/index-tts/index-tts/issues/572) 同病未修。**参数修不动，只能管线强制（门禁选优 + 手术）。**
### 已知坑

- **`use_cuda_kernel=False` 必须显式传**：默认 True 触发 BigVGAN kernel JIT 编译，8GB 卡 >13min 无产出（2026-08-25 实测）
- fp16 = webui 8GB 卡默认档（发布系列口径）；fp32 扩散极慢勿轻试
- GPU 被 Seed-VC 等任务并行占用时只影响速度不影响停顿位置（停顿与算力无关——这本身是根源证据）
- whisper 词级对齐失败自动退化字数比例映射（审计表 `align` 字段可查：whisper/prop）
- 续跑会用现行门禁复核旧产物，不过自动重合成（改档位后重跑即全量生效）
