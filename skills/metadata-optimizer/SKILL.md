---
name: metadata-optimizer
description: 视频与文章的标题/简介/话题（发布元信息）生成与优化。fact card 事实提取 → 分档位候选（数字/问句/反差/后果/克制）→ 7 项清单脚本打分 → 人选定稿 → 平台标题变体写入 metadata.txt → metadata-lint 收口。写标题、起标题、改标题、标题候选、metadata 元信息、简介 digest、话题标签时调用。
---

# metadata-optimizer 标题/简介/话题优化

把「每次手写一条直接发」的发布元信息，变成有方法论支撑的候选→打分→定稿流程。方法论来自 2688 篇标题统计驱动的 qiaomu skill + 平台实证研究（完整来源：blog-src `openspec/changes/metadata-optimization/research.md`）。

**两条铁律（先于一切技巧）：**

1. **事实边界**（`references/banned-words.md`）：素材里没有的事实（刚刚/首个/全球第一/榜单/规模数字）候选不得出现，命中即判废；素材干瘪只出克制档。宁可标题平，不可事实假。
2. **人选定稿**：本 skill 只生成、打分、给依据，**定稿永远是人**。人没选之前不写 metadata.txt。

## 工作流（六步）

### ① 读素材，提 fact card

输入：文章 slug（`content/posts/<slug>.md`）或视频 slug（`video-generation/build/<slug>/`，含脚本/metadata.txt）。提取五要素，**缺失就标缺失，不编造**：

| 要素 | 问自己 | 例 |
|------|--------|-----|
| 核心实体 | 提到什么工具/项目/人？ | Codex、DeepSeek Harness |
| 动作 | 观众看完能做什么？ | 自动剪视频、配权限 |
| 硬数字 | 素材里核过的数字 | 21 万 Star、6 个 skill、307MB |
| 权威 | 谁背书（开源作者/官方/榜单）？ | TypeScript 教父 |
| 利害关系 | 不看会损失什么/对号入座谁 | 白白手动剪片 |

### ② 对齐账号 DNA

读 `references/account-dna.md`（生成方式见文末）：长度贴近中位 ±30%，高频实体优先复用（本账号被记住的词），问句/数字按题材选。

### ③ 出 5-7 个候选，分档位

按 `references/formulas.md` 五档位（数字型/问句型/反差型/后果型/克制型），同档位不重复。每个候选标注：所用档位+技巧、适用平台、素材依据（哪个 fact card 要素）。强度三档（克制 L1/默认 L2/爆炸 L3），L3 仅当素材真有 breaking 级事实。

### ④ 脚本打分

```bash
python <skill目录>/scripts/score_title.py "候选1" "候选2" --platform douyin,bilibili
```

7 项清单（可识别实体/真实数字/清晰动词/后果人群/标点转折/权威钩子/概念包装）**满足 ≥4 合格**。同时过一遍 "Now you can" 测试（formulas.md 末节）：<4 的候选按脚本提示的缺项补要素，不换话题。

### ⑤ 人选定稿 → 平台变体写入 metadata.txt

人挑出主标题后，产出平台变体（规则见 `references/platform-limits.md`）：

- `标题_抖音:` ≤30 字，钩子前 10 字
- `标题_小红书:` 18-20 字，核心词前 10 字，不用感叹号
- `标题_B站:` 20-40 字，含可搜索关键词，可带【】标签

连同主标题写进 `video-generation/build/<slug>/metadata.txt`（中文键，续行规则见 blog-src `scripts/pub/meta.py`）。文章侧对应写 front matter `description`（54-120 字三段式：痛点+给什么+数字背书——正文前 54 字会被默认抓去当摘要，不能不管）。

### ⑥ lint 收口

```bash
make metadata-lint slug=<slug>
```

FAIL（硬截断/词中断/结构红线）必须修到绿；WARN（最优长度/话题配比/断句丢钩子）看建议酌情改。正式发布 `make pub-video` 会自动再跑同一门禁。

## 简介与话题

- **简介首句**用三拍：当前不适 → 更好愿景 → 行动路径（formulas.md「简介首句」）；结尾互动问题 + 原文链接（video-generation SKILL.md 已定规）。

### 话题推荐（第 ⑤½ 步，写 `话题:` 字段前跑）

```bash
python <skill目录>/scripts/topic_suggest.py --slug <slug>   # 读 build/<slug>/metadata.txt
python <skill目录>/scripts/topic_suggest.py --theme "Codex 自动剪辑"
```

输出按 **大词 / 长尾** 两组、总数 3-5（1 大词 + 2 长尾核心 + 最多 2 长尾补位），每组标来源依据（方向词表命中 / 实体×场景组合），完全本地计算、无外部查询。人确认后写入 `话题:` 字段；注意抖音/快手话题上限 4 个。长尾后缀词表与 blog-src lint 的 LONGTAIL_MARKERS 同步——推荐器产出的长尾必被 lint 识别。

## 维护

- `references/account-dna.md` 过时重生成：`python scripts/account_dna.py --write --blog-root <blog-src 路径>`
- 打分口径/词表改动：`python scripts/score_title.py --selftest` 必须过
- **反哺接口（预留未实现）**：`account_dna.py::load_title_retention_pairs()` 是标题特征×完播/互动的配对入口，video-analytics 覆盖 ≥30 支已发视频后填实现，届时 P75 共性块从「样本不足」转自动结论、score 清单按实证加权
- 产物（候选清单/fact card）存本 skill `.tmp/`，不进 blog-src

## 事实边界自查清单（候选产出后逐条过）

- [ ] 每个数字都能在素材里指到出处
- [ ] 无「刚刚/首个/全球第一/榜单名」类凭空声明
- [ ] 无结构红线词（凭什么/打赢/吊打/杀疯了/官方口吻）
- [ ] 素材干瘪时只出了克制档
- [ ] 人做了定稿选择，skill 没有替人选
