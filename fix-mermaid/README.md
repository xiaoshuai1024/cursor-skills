# fix-mermaid

This folder contains a Cursor Skill: `fix-mermaid`.

## What it does
- Fixes Mermaid diagrams that fail to render with errors like **`Syntax error in graph`** (commonly on Mermaid **9.4.3**).
- Applies **safe, minimal rewrites** inside Mermaid blocks (quote labels, fix `subgraph`, replace unsupported `timeline`, etc.).

## How to use in Cursor
1. Make sure this repo/folder is available to your Cursor environment (you’re already using `~/codes/cursor-skills`).
2. When you want Mermaid fixes, tell the agent explicitly, for example:
   - “调用 skill `fix-mermaid`，修复 `content/posts/xxx.md` 里的所有 Mermaid 图（Mermaid 9.4.3 报错 Syntax error in graph）”
3. Constrain scope if you want (recommended):
   - “只修改 `content/posts/**/*.md`，不要改主题/模板”

## What the skill changes (rules of thumb)
- Quote node labels: `A[中文/()/:+...]` → `A["..."]`
- Avoid cylinder/shape nodes when labels include symbols: `DB[(MySQL + Redis)]` → `DB["(MySQL + Redis)"]`
- Fix subgraph titles: `subgraph A[终端层]` → `subgraph TerminalGroup["终端层"]`
- Replace unsupported diagram types (e.g. `timeline`) with `flowchart TB`
- Ensure Mermaid source is fenced in <code>```mermaid</code> blocks

## Notes
- This skill is intentionally conservative: it aims to fix rendering while keeping post prose unchanged.
