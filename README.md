# xiaoshuai skills

个人 Agent Skills 集合 —— 把「架构师」和「内容输出」两条线上反复用到的工作流沉淀成可复用的 skill。

每个 skill 是一个目录：`skills/<name>/SKILL.md` 是入口，必要时带 `references/` 和 `scripts/`。所有 skill 兼容 [Agent Skills 规范](https://agentskills.io)，可在 Claude Code、Cursor、Codex、Gemini CLI、opencode 等编码 Agent 里通用。

## Skill 一览

两条 track，共 5 个 skill。分组定义见 [`skills.sh.json`](./skills.sh.json)。

### 架构师 / Architect

做系统设计、写技术文档、画架构图时用。

| Skill | 作用 | 触发场景 |
|------|------|----------|
| [`code-doc-maker`](./skills/code-doc-maker) | 维护并补齐仓库 Markdown 文档：根 README 聚合目录、笔记按规范改写 | 要「补齐/完善/整理文档」、更新 README/目录、把零散要点整理成可复述笔记 |
| [`fix-mermaid`](./skills/fix-mermaid) | 修复 Mermaid 图渲染报错（如 9.4.3 的 `Syntax error in graph`），只改图源不动正文 | 文章/文档里的 Mermaid 图无法渲染或报语法错 |

### 内容输出 / Content

把架构师的思考沉淀成可发布的图文与视频。

| Skill | 作用 | 触发场景 |
|------|------|----------|
| [`excalidraw`](./skills/excalidraw) | 用真实 Excalidraw 引擎渲染手绘风格图（流程图/架构图/ER/时序/线框），导出 SVG+PNG | 要画「diagram / flowchart / 架构图」，或把系统/流程可视化，且希望手绘风、矢量、可回拖到 excalidraw.com |
| [`blog-writing`](./skills/blog-writing) | 博客写作全流程：选题自检→定类型→搭骨架→起标题→写正文→配图→润色→验证 | 写新文章或大改现有文章（扩写、去 AI 味、改标题）前调用 |
| [`video-generation`](./skills/video-generation) | 把一篇文章/主题生成为横屏 16:9 讲解视频，courseware / graph / remotion 三种程序化模式 | 把文章转成知识/培训讲解视频（B站知识区、YouTube、在线课程风格） |

## 安装

通过 [skills](https://github.com/vercel-labs/skills) CLI（`npx skills add`）安装到任意编码 Agent：

```bash
# 装全部 5 个 skill（所有 agent，跳过确认）
npx skills add xiaoshuai1024/skills --all

# 交互式选择要装哪几个、装到哪个 agent
npx skills add xiaoshuai1024/skills

# 只装某一个
npx skills add xiaoshuai1024/skills --skill excalidraw

# 装到指定 agent（如 claude-code / cursor / opencode）
npx skills add xiaoshuai1024/skills --skill blog-writing -a claude-code -y
```

CLI 会对仓库 `skills/*/SKILL.md` 做自动发现，无需手动指定路径。`skills.sh.json` 里的 `groupings` 控制在 skills.sh 上的分组展示。

<details>
<summary>不用 npx，手动安装</summary>

把对应 skill 目录拷到 Agent 的 skills 目录：

- Claude Code：`~/.claude/skills/<name>/SKILL.md`
- Cursor：`~/.cursor/skills/<name>/SKILL.md`（别用 `~/.cursor/skills-cursor/`，那是内置目录）
- 项目级：`<repo>/.claude/skills/<name>/` 或 `<repo>/.cursor/skills/<name>/`

</details>

## 使用

安装后在 Agent 里正常描述需求即可。描述命中 skill 的触发场景时，Agent 会自动按 `SKILL.md` 的规则执行；也可显式点名，例如：

- 「用 `code-doc-maker` 把这个仓库的文档补齐」
- 「按 `blog-writing`，先过选题自检再写」
- 「用 `excalidraw` 画一张微服务 CI/CD 架构图，导出 SVG」

## 目录结构

```
skills/
├── README.md            # 本文件
├── skills.sh.json       # skills.sh 注册元数据 + 分组（架构师 / 内容输出）
├── package.json         # npm 元数据
├── LICENSE              # MIT
└── skills/
    ├── code-doc-maker/      # 架构师
    │   ├── SKILL.md
    │   └── reference.md
    ├── fix-mermaid/         # 架构师
    │   └── SKILL.md
    ├── excalidraw/          # 内容输出
    │   ├── SKILL.md
    │   ├── references/
    │   └── scripts/
    ├── blog-writing/        # 内容输出
    │   ├── SKILL.md
    │   └── references/
    └── video-generation/    # 内容输出
        ├── SKILL.md
        └── scripts/
```

## 约定

- **结构**：每个 skill 一个目录 `skills/<name>/SKILL.md`，可带 `references/`（按需加载的详细规范）、`scripts/`（可执行脚本）、`examples/`。
- **frontmatter**：`SKILL.md` 顶部必须有 `name` 和 `description`。`description` 写清楚「何时触发」，Agent 靠它判断要不要加载这个 skill。
- **渐进式披露**：`SKILL.md` 只写工作流骨架，细节放 `references/` 按步骤加载，避免主文件膨胀（参考 `blog-writing`）。
- **命名**：小写 + 连字符，≤64 字符。
- **扩展规则**：新增规则优先追加到该 skill 的 append-only 段落，不破坏已有约束。

## 新增 skill

1. 在 `skills/` 下建目录，写 `SKILL.md`（含 `name`/`description` frontmatter）。
2. 在 `skills.sh.json` 的对应 `groupings` 里加上 skill 名。
3. 在本 README 的「Skill 一览」表里加一行。
4. 提交。

## 来源

本集合整合自此前几个独立仓库，统一收敛到这里维护：

- `code-doc-maker`、`fix-mermaid` —— 原 `cursor-skills`（本仓库前身）
- `excalidraw` —— 原 `excalidraw-skill`
- `blog-writing`、`video-generation` —— 沉淀自博客工作流

## License

MIT
