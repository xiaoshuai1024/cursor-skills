---
name: video-detail-site
description: 视频详情预览站——扫描 video-generation/build/ 全部成片，生成本地静态站点（列表页 + 每支视频独立 URL 详情页）。详情页含 HTML5 视频播放器（封面海报）、meta 信息（标题/系列/时长/体积/发布字段）、口播稿逐卡全文、分镜脚本（deck 镜头逐卡明细）。用户要「视频预览地址」「视频详情页」「预览站点」或想用浏览器看成片时调用。
---

# Video Detail Site（视频详情预览站）

给 `video-generation/build/` 里的成片生成可浏览的本地站点：一个列表页 + 每支视频一个独立 URL 的详情页。纯 stdlib 实现，零第三方依赖。

## 何时用

- 用户要「视频的 http 预览地址」「详情页」「想用浏览器看成片」
- 渲染完成后想逐集检查画面/口播/分镜对照
- 交付给用户审片时提供一个可点击的入口

## 用法

```bash
# ① 生成/刷新站点（扫描 build/ 全部 mp4，产物落 video-generation/site/）
make video-site

# ② 起本地服务（根目录 = video-generation/，端口 8767）
make video-site-serve
```

URL（服务起后）：

- 列表页：`http://localhost:8767/site/index.html`
- 详情页：`http://localhost:8767/site/<slug>/index.html`（每支视频独立 URL）
- 视频文件：`http://localhost:8767/build/<slug>/<slug>.mp4`

## 详情页内容

1. **播放器**：HTML5 video（成片 mp4 + 横版封面海报），浏览器直接播
2. **meta**：metadata.txt 全字段（标题/系列/封面hero/关键词组…）+ 时长/体积/分辨率（ffprobe 探测，缺失显示 ?）
3. **口播稿**：`narrations/<slug>.json` 逐卡全文（编号 + 正文）
4. **分镜脚本**：`deck/<slug>/deck.json` 逐卡镜头明细（卡标题/要点/每个镜头的类型徽章 + from_s + 内容全文）
5. **系列口播稿原始稿**：eng-series 系列自动关联 `build/eng-series-202609/<ep>.md`，折叠展示口播稿与分镜表原文

## 规则

- 只读管线：不修改 build/deck/narrations 任何产物；站点产物落 `video-generation/site/`（可随时删掉重生成）
- 纯 stdlib（json/re/html/pathlib/subprocess），ffprobe 缺失时不阻塞，时长显示 `?`
- 重新渲染后重跑 `make video-site` 即刷新站点；服务不用重启（静态文件即时生效）
