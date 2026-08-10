# xiaoshuai skills

个人 Agent Skills 集合 —— 把技术博客全链路（选题→写作→配图→发布→视频）沉淀成可复用的 skill。

每个 skill 是一个目录：`skills/<name>/SKILL.md` 是入口，必要时带 `references/` 和 `scripts/`。所有 skill 兼容 [Agent Skills 规范](https://agentskills.io)，可在 Claude Code、Cursor、Codex、Gemini CLI 等编码 Agent 里通用。

## 安装

```bash
npx skills add xiaoshuai1024/skills
```

或手动克隆后，把 `skills/` 目录链接/复制到你的项目的 `.claude/skills/` 下。

## Skill 一览（12 个）

| 分类 | Skill | 做什么 | 依赖 |
|------|-------|--------|------|
| **选题** | [tech-topic](skills/tech-topic/) | 掘金+CSDN/InfoQ/知乎 多源选题，按方向过滤+热度排序 | Python 3（stdlib） |
| | [douyin-topic](skills/douyin-topic/) | 抖音选题+对标拆解（三源→双系列→下载→转写→大纲） | Python 3 + playwright + faster-whisper + yxer CLI |
| **写作** | [blog-writing](skills/blog-writing/) | 博客写作全流程（选题→定类型→骨架→标题→正文→配图→润色→验证） | 无（纯文档 skill） |
| | [de-ai-smell](skills/de-ai-smell/) | 去 AI 味扫描（L1 禁词 + L2 慎用词 + 风格检查） | Python 3（stdlib） |
| | [image-text-cards](skills/image-text-cards/) | 小红书/抖音/视频号图文笔记卡片+正文设计 | 无（纯文档 skill） |
| **发布** | [wechat-publishing](skills/wechat-publishing/) | 公众号 mp 后台 API 直推（草稿+定时群发+封面+代码高亮） | Python 3 + playwright + bs4 + PIL；配置 `.env.local`（见 `.env.local.example`） |
| **视频** | [video-generation](skills/video-generation/) | 博客文章→横屏视频（remotion 数据可视化/课件/知识图谱） | Python 3 + edge-tts + FFmpeg；Node + pnpm（remotion） |
| **配图** | [drawio](skills/drawio/) | draw.io 架构图（mxGraph XML，禁止 mermaid） | draw.io CLI（`--export --format svg`） |
| | [excalidraw](skills/excalidraw/) | 手绘风概念图/对比图/心智模型 | Node + npm（excalidraw export） |
| | [app-screenshot](skills/app-screenshot/) | 桌面应用窗口截图 + OCR（跨平台） | Python 3 + playwright + pyobjc（macOS）/ WinRT（Windows） |
| **工具** | [crawl](skills/crawl/) | 爬虫反检测策略 + 各平台已知技巧 | 无（纯文档 skill） |
| | [code-doc-maker](skills/code-doc-maker/) | 仓库 Markdown 文档治理 | 无（纯文档 skill） |

分组定义见 [`skills.sh.json`](./skills.sh.json)。

## 初始化（按需）

### wechat-publishing
```bash
# 1. 安装依赖
pip install playwright beautifulsoup4 Pillow
playwright install chromium

# 2. 配置环境变量（复制模板填你的值）
cp skills/wechat-publishing/.env.local.example .env.local
# 编辑 .env.local 填 SITE_BASE_URL / WECHAT_AUTHOR / WECHAT_ALBUMS / WECHAT_FINGERPRINT

# 3. 首次运行需扫码登录公众号后台
```

### video-generation
```bash
pip install edge-tts  # 配音
# FFmpeg 需系统安装

# remotion 渲染（可选，数据可视化模式）
cd skills/video-generation/remotion && pnpm install
```

### douyin-topic
```bash
pip install playwright faster-whisper
npm install -g @yixiaoermail/cli  # 蚁小二（多平台数据）
```

### tech-topic / de-ai-smell
```bash
# 纯 stdlib，无需额外安装
```

## 配置约定

- **`.env.local`**（gitignore）：wechat-publishing 的账号配置（URL/作者/合集/指纹）。
- **`topic_keywords.json`**：tech-topic / douyin-topic 的方向关键词表（示例配置，按你的内容方向修改）。
- **`category_map.json`**：tech-topic 的掘金 category_id → 方向映射。

## 原则

- **skill 自包含**：脚本在 skill 目录内、不引用外部路径。
- **项目信息脱敏**：账号/域名/指纹等通过环境变量配置，不硬编码。
- **差异化原创**：所有涉及原文/原片的 skill 均遵守「仅分析素材、产出差异化原创、禁止照搬」。

## License

MIT
