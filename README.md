# Cursor Skills

这是一个独立维护的 Cursor Skills 项目，用来集中管理你常用的工作流（Skills），并用 Git 进行版本控制。

## 安装（Install）

你可以按使用范围选择两种安装方式（二选一）：

### 方式 A：安装到个人目录（跨项目通用）

把某个 skill 目录放到 `~/.cursor/skills/` 下，例如：

- `~/.cursor/skills/code-doc-maker/SKILL.md`

### 方式 B：安装到项目目录（随仓库走）

把 skill 目录放到项目的 `.cursor/skills/` 下，例如：

- `<your-repo>/.cursor/skills/code-doc-maker/SKILL.md`

> 约束：不要放到 `~/.cursor/skills-cursor/`（这是 Cursor 内置目录）。

## 使用（How to use）

安装完成后，在 Cursor 里你只需要像平常一样描述需求即可。只要你的描述命中 skill 的触发场景，Agent 会自动按 `SKILL.md` 的规则执行。

如果你想显式触发，也可以直接说类似：

- “用 `code-doc-maker` 的规则把这个仓库的文档补齐”
- “按 `code-doc-maker`，根目录聚合目录，手写题先思路再链接”

## Skills 一览

| Skill | 作用 | 适用场景（触发） |
|------|------|------------------|
| `code-doc-maker` | 维护并补齐仓库的 Markdown 文档：根目录 `README` 聚合目录；`hand-writing` 先“思路”再“代码链接”；`basic` 把要点改写成通顺的面试表达 | 当你要“补齐/完善/整理文档”、更新 README/目录、或把零散要点整理成可复述的笔记时 |
| `fix-mermaid` | 修复 Mermaid 图表渲染报错（如 Mermaid 9.4.3 的 `Syntax error in graph`）：在 ` ```mermaid ` 块内做最小安全改写（统一加引号、修 `subgraph`、替换不支持的 `timeline` 等） | 当你的 Markdown 文章/文档里的 Mermaid 图无法渲染或报 `Syntax error in graph`，且希望只改图表源码、不动正文时 |

## 规范（Conventions）

- **结构**：每个 skill 一个目录：`<skill-name>/SKILL.md`（可选 `reference.md/examples.md/scripts/`）
- **命名**：skill 名称使用小写 + 连字符（hyphen），不超过 64 字符
- **可扩展**：当你新增规则时，优先追加到该 skill 的“append-only / extra rules”段落，避免破坏已有约束
