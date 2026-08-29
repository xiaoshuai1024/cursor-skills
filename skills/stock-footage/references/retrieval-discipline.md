# 检索纪律

> 方法论重写自 OpenMontage documentary-montage 资产导演（AGPL-3.0），术语体系改为本仓直接检索快路径（corpus+CLIP 向量检索路径暂不搬，要点见文末备查）。

## 槽位制：先列槽位再搜素材

把视频的素材需求想成一张**槽位表**（slot）：每个槽位 = 一句画面描述（`slot_01 雨滴落在柏油路慢动作`）。搜索、下载、择片、去重全部围绕槽位进行，产出 `asset_manifest`（每槽恰一条素材 + 溯源三件套）。

## Query 改写纪律

- **具体名词 + 视觉特征**是好查询：`raindrop on asphalt slow motion`、`satellite dish night sky`、`1990s computer room CRT monitors`
- **抽象概念词是坏查询**：`the passage of time`、`loneliness`——素材 API 只认画面词
- 弱结果改写次序：**换更具体的名词 → 加视觉限定词（颜色/光线/天气/年代）→ 换同义词**（`car headlights rain` → `taillights wet street night neon`）
- **每槽最多两轮改写**；仍无匹配 → 标记该槽 `unfilled` 并上报，**禁止拿不相关素材硬凑**。三处都凑不上的画面说明开放素材库里不存在，改槽位内容或让用户供素材

## 规模配比

- `--per-source` 经验值 **4-8**/源/查询；推到 20+ 大多只加噪声
- 候选总量 ≈ **槽位数 × 8-12 倍**（15 槽 ≈ 150 条候选），给择片留真实选择空间
- 每槽下载 2-3 条足够对比；快路径（搜索+立即下载前 N 条）适合 ≤30 槽的单幕制作

## 慢源隔离与批次

- **Prelinger（archive_org 深翻）与 NASA 单独成批**，禁与现代源（pexels/mixkit）混在同一次 fan-out
- vintage 简报：sources 收敛 `archive_org,wikimedia,loc,nara`，用年代限定词，archive_org 占比目标 ≥60%
- 搜索可在后台跑，同时并行做 TTS/字幕/BGM（OpenMontage 生产实证：并行省一半以上时长）

## 择片四判断（人看缩略图定，不唯参数论）

1. **年代匹配**：2022 年 4K 阳光素材放进怀旧调片子就是错——分数高也弃
2. **运动匹配**：槽位要 hold 4 秒，候选却是 2 秒快甩镜头 → 拉不动，弃
3. **相邻构图去重**：槽 2 是天台雨夜全景，槽 3 的第一名也是天台雨夜全景 → 取第 2 名
4. **情绪档位**：检索 API 会把「深夜空荡人行道」匹配成「拉斯维加斯霓虹」——语义近似但情绪相反，弃

## 溯源与去重（硬规则）

- 每槽恰一条主素材；`clip_id` 全局唯一归属（同一条「开门」镜头不许赢两个槽）
- 相邻槽位产出后跑一遍视觉去重：两条高度相似留一条，被挤掉的槽用已下载候选补或降级 unfilled
- **溯源三件套（provider/source_url/license）缺一即弃**——这是发布侧可查证的底线
- 保留 `rejected_picks`（弃选记录：哪条、为何弃），下游觉得不对劲时直接翻第 2 名，不用重搜

## 素材上片的接法（与 video-generation 的衔接）

- 素材进成片走 video-generation 现有渲染链（Remotion `<Video>`/`<Img>` + config 声明）；卡点侧见 `video-generation/references/beat-cut.md`（beat_cut/ken_burns/bg_under_text 三式）
- 视频素材一律**静音入片**，BGM/口播是唯一音轨（素材自带音轨需入片时另行显式设计）
- 素材下载后归一化（转横屏/缩放/转码）走现有 FFmpeg 链；进片素材的溯源三件套随项目 archive 登记

## 备查：CLIP 向量检索路径（本次未搬）

OpenMontage 另有 corpus_builder + clip_search 标准路径：把候选库做 CLIP embedding 索引，按槽位描述文本做相似度排序（描述比查询词更适合做排序文本），余弦 ≥0.30 强匹配 / 0.22-0.30 需人工判断 / <0.22 说明库里没有，扩库别硬选；`diversify` 操作做相邻去重。待实拍混剪选题真起来、槽位规模上来（50+）再考虑引入。
