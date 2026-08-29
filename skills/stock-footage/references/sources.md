# 16 源特性表

> 检索方法论参考 OpenMontage documentary-montage 资产导演（AGPL-3.0）。可用状态以 `python stock_search.py sources` 实时输出为准。

## 免 key · 纯 stdlib（零安装直用）

| 源 | 强项 | 短板/注意 | 查询技巧 |
|----|------|-----------|----------|
| **nasa** | 太空/航天/地球观测/科学装置，公有领域，元数据完整（center/日期/创作者） | 本机直连可达但慢、结果 niche；大文件原始 mp4 很大 | 用具体对象词（`artemis rollout`），别用泛词（`space`）；单独小批量跑 |
| **wikimedia** | 历史/科普图为主，CC/PD 逐文件标注；视频存 webm/ogv | 本机直连被墙（走代理）；视频持有量稀疏 | 内置「精确→宽泛」级联（AND 语义吞多词，自动剥停用词）；单 token 命中率最高 |
| **archive_org** | Prelinger 档案等年代影像宝库，vintage 主力 | 本机直连被墙；深翻极慢——单独成批，禁与现代源混跑 | 加 `prelinger`/年代词；内置源提示词剥离 |
| **loc** | 美国国会图书馆历史照片/影像，PD | 直连 403（需浏览器 UA，走适配器或代理）；偏静态 | 具体历史事件/地名 |
| **nara** | 美国国家档案馆，政府影像 PD | 直连一般；`NARA_API_KEY` 可选提额 | 政府项目/战争/年代事件词 |
| **pond5_pd** | Pond5 公有领域专区的整理版历史影像 | 覆盖面小，作补充 | 年代 + 主题词 |
| **coverr** | 现代 HD 空镜/城市/自然，免 key 50 次/时 | 仅视频；`COVERR_API_KEY` 提额 | 具体名词 + 视觉特征 |

## 免 key · 需 `pip install requests beautifulsoup4`（页面解析源）

| 源 | 强项 | 短板/注意 | 查询技巧 |
|----|------|-----------|----------|
| **mixkit** | 现代 HD 空镜/氛围/转场素材，质量高，自由许可 | 仅视频；页面解析对改版敏感 | 短名词短语（`city night`） |
| **esa** | 欧空局太空/地球影像 | 需 bs4；偏静态图 | 任务名/仪器名（`mars express`） |
| **jaxa** | 日本宇宙航空研究机构影像 | 需 bs4；量少 | 项目词（`hayabusa`） |
| **noaa** | 海洋/气象/灾害影像 | 需 bs4 | 天气现象具体词（`hurricane eyewall`） |
| **dareful** | 4K/360° 极限运动/游戏资产，CC4 | 需 bs4；下载大 | 运动具体词（`skydiving`） |

## 免费注册 key（环境变量启用，未配置自动跳过）

| 源 | 强项 | key 环境变量 | 查询技巧 |
|----|------|--------------|----------|
| **pexels** | 现代 HD 实拍主力，视频+图，质量与覆盖最优 | `PEXELS_API_KEY` | 具体名词+视觉特征；URL 自带标签可作检索通道 |
| **pixabay_video** | **儿童/童话向 AI fantasy 集中地**（见下），通用素材也全 | `PIXABAY_API_KEY` | fantasy 向加 `fairy tale/enchanted/glowing` 前缀 |
| **unsplash** | 高质量**图片**（无视频） | `UNSPLASH_ACCESS_KEY` | 文章配图/背景板；作辅助源不作主力 |
| **videvo** | 免费 video clips 补充 | `VIDEOVO_API_KEY` | 通用名词 |

## 特殊经验（来自 OpenMontage 生产实证）

- **Pixabay 儿童内容源锁定**：Pixabay 社区有数千条 Midjourney/SD 视频工作流产出的 fantasy 动画（发光森林/魔法生物），儿童向内容表现碾压真实 footage。规则：儿童向 `sources` 锁 `pixabay_video` 单源、查询前置 fantasy 关键词、下载后核验全部候选共享 AI fantasy 美学（混入一条真实 footage 即破坏沉浸感）、两轮改写仍空则上报而不是拿真实素材顶替。
- **NASA/Prelinger 慢源隔离**：两者都慢且 niche，与其他源的 fan-out 分开跑；vintage 简报下 archive_org 占比目标 ≥60%。
- **unsplash 仅图**：视频为主的项目里只作图板辅助，不做运动画面主力。
