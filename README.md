# xiaoshuai skills

技术内容创作 Agent Skills 集合 —— 把「选题 → 写作 → 配图 → 发布 → 视频」全链路沉淀成可复用的 skill。

所有 skill 兼容 [Agent Skills 规范](https://agentskills.io)，可在 Claude Code、Cursor、Codex、Gemini CLI 等编码 Agent 里通用。

## 安装

```bash
npx skills add xiaoshuai1024/skills
```

安装后，在你的项目 `.claude/skills/` 目录下即可发现所有 skill。按需使用，不需要的全部忽略即可。

## 按场景选用（渐进叠加）

这些 skill 设计为**配合使用**，按你的内容输出需求分层叠加：

```
                    博客    +选题    +公众号    +视频    +抖音
                    ────    ─────    ────────    ─────    ─────
blog-writing         ✅      ✅        ✅        ✅       ✅
drawio               ✅      ✅        ✅        ✅       ✅
excalidraw           ✅      ✅        ✅        ✅       ✅
de-ai-smell          ✅      ✅        ✅        ✅       ✅
app-screenshot       ✅      ✅        ✅        ✅       ✅
tech-topic                   ✅        ✅        ✅       ✅
wechat-publishing                       ✅        ✅       ✅
image-text-cards                        ✅        ✅       ✅
video-generation                                 ✅       ✅
douyin-topic                                              ✅
```

### Level 1 — 博客写作（基础）

**你能做什么**：写技术博客文章（选题自检→定类型→搭骨架→写正文→配图→润色→验证），画架构图和手绘概念图，去 AI 味，截应用窗口图。

| Skill | 作用 |
|-------|------|
| [blog-writing](skills/blog-writing/) | 写作全流程 9 步 + 去 AI 味手册 + 标题/SEO/分类型规范 |
| [drawio](skills/drawio/) | draw.io 架构图（禁止 mermaid），mxGraph XML + SVG 导出 |
| [excalidraw](skills/excalidraw/) | 手绘风概念图/流程图/心智模型，Excalidraw 风格 |
| [de-ai-smell](skills/de-ai-smell/) | 去 AI 味扫描（L1 禁词 + L2 慎用词 + 风格检查脚本） |
| [app-screenshot](skills/app-screenshot/) | 桌面应用窗口截图 + OCR（跨平台 macOS/Windows） |

**依赖**：Python 3（de-ai-smell、app-screenshot）；draw.io CLI（drawio）；Node（excalidraw）。

---

### Level 2 — + 技术选题

**新增能力**：不知道写什么时，自动从掘金/CSDN/InfoQ/知乎拉取近期高互动技术文章，按方向过滤 + 热度排序，每平台 Top 10 表格选题。选中后一键深挖（保存原文 + 结构分析）。

| 新增 Skill | 作用 |
|------------|------|
| [tech-topic](skills/tech-topic/) | 四源技术选题（掘金推荐流+热榜 / CSDN 热榜 / InfoQ RSS / 知乎关键词过滤）→ 方向过滤 → 分源归一 → 每平台 Top 10 表格 → 假设大纲 → 深挖原文保存+结构分析 |

**依赖**：Python 3（stdlib 零依赖，全部匿名 API）。掘金搜索（B 源）需登录态（可选，Playwright 弹窗一次）。

---

### Level 3 — + 公众号同步

**新增能力**：写完文章后，一键同步到微信公众号（mp 后台 API 直推，跳过风控），含封面自动化、代码高亮（chroma→Monokai）、原文链接注入、定时群发。

| 新增 Skill | 作用 |
|------------|------|
| [wechat-publishing](skills/wechat-publishing/) | 公众号 mp 后台 API 直推（Playwright 登录态）→ 草稿+定时群发+封面+代码高亮+内链替换 |
| [image-text-cards](skills/image-text-cards/) | 公众号/小红书图文笔记卡片设计（卡片秒抓眼球 + 正文深度展开） |

**依赖**：Python 3 + playwright + bs4 + Pillow。配置 `.env.local`（见 [`.env.local.example`](skills/wechat-publishing/.env.local.example)）：站点 URL、作者名、合集 ID、masssend 指纹。

**初始化**：
```bash
pip install playwright beautifulsoup4 Pillow
playwright install chromium
cp skills/wechat-publishing/.env.local.example .env.local  # 编辑填你的值
```

---

### Level 4 — + 视频生成

**新增能力**：把博客文章生成为横屏 16:9 视频（remotion 数据可视化 / 课件 / 知识图谱三种模式），edge-tts 配音 + FFmpeg 合成，全本地零收费。

| 新增 Skill | 作用 |
|------------|------|
| [video-generation](skills/video-generation/) | 文章→视频三种模式：remotion（数据可视化+真实素材）/ courseware（课件屏录感）/ graph（知识图谱）；edge-tts 中文配音 + Playwright/Remotion 渲染 + FFmpeg 合成 |

**依赖**：Python 3 + edge-tts + FFmpeg（系统安装）；Node + pnpm（remotion 渲染）。

**初始化**：
```bash
pip install edge-tts          # 配音
# FFmpeg 需系统安装（brew install ffmpeg / apt install ffmpeg）
cd skills/video-generation/remotion && pnpm install  # remotion 渲染（可选）
```

---

### Level 5 — + 抖音选题

**新增能力**：从抖音热榜发现选题（三源真实数据 → 双系列 → 下载原片 → faster-whisper 转写 → 拆钩子/结构/热评 → 可抄大纲），做差异化原创短视频。

| 新增 Skill | 作用 |
|------------|------|
| [douyin-topic](skills/douyin-topic/) | 抖音选题+对标拆解：三源热榜（🔥热度/📈涨粉双系列）→ 下载原片 → faster-whisper 转写 → 拆钩子/段落结构/热评词频 → 可抄大纲+仿写脚本 |

**依赖**：Python 3 + playwright + faster-whisper（本地 ASR）；yxer CLI（蚁小二，热榜数据源）。

**初始化**：
```bash
pip install playwright faster-whisper
npm install -g @yixiaoermail/cli  # 蚁小二（可选，B/C 数据源）
```

---

### 独立工具（按需，不属于上述管线）

| Skill | 作用 | 何时用 |
|-------|------|--------|
| [crawl](skills/crawl/) | 爬虫反检测最佳实践（浏览器策略/平台技巧/速率/captcha） | 写/改爬虫脚本时 |
| [code-doc-maker](skills/code-doc-maker/) | 仓库 Markdown 文档治理（README 结构/面试笔记整理） | 补齐/整理仓库文档时 |

## 配置约定

| 配置 | 说明 | 适用 skill |
|------|------|-----------|
| `.env.local`（gitignore） | 站点 URL / 作者名 / 合集 ID / masssend 指纹 | wechat-publishing |
| `topic_keywords.json` | 方向关键词表（**示例配置，按你的内容方向修改**） | tech-topic / douyin-topic |
| `category_map.json` | 掘金 category_id → 方向映射 | tech-topic |

## 设计原则

- **skill 自包含**：脚本在 skill 目录内，不引用外部路径。
- **项目信息脱敏**：账号/域名/指纹等通过环境变量配置，不硬编码。
- **差异化原创**：所有涉及原文/原片的 skill 遵守「仅分析素材、产出差异化原创、禁止照搬」。

## License

MIT
