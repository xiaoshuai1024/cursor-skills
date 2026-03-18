---
name: code-doc-maker
description: Maintains and expands Markdown documentation for this interview/practice repository. Use when the user asks to补齐/完善/整理 Markdown 文档、更新 README/目录、或新增面试笔记结构。Enforces: root README aggregates all content; hand-writing docs are "思路 → 代码链接"; basic notes are rewritten into fluent sentences without losing technical accuracy.
---

# Code Doc Maker

## Goal

Keep this repository’s documentation **complete, navigable, and interview-friendly**, following the project’s conventions.

## Non‑negotiable rules (must follow)

1. **Root has everything**: The root `README.MD` must include links to every major content area and entry docs.
2. **Hand-writing structure**: For `hand-writing/` topics, write **思路 first**, then provide **code links** (implementation + tests when present).
3. **Basic notes rewrite**: For `basic/` topics, transform terse bullet points into **smooth, readable sentences** (still concise, still technically correct).

## Workflow (do this every time)

### 1) Inventory and gaps

- List all Markdown files under repo (including `basic/`, `hand-writing/`, `algorithm/`).
- Identify:
  - Missing index docs (e.g. a directory has content but no README/index).
  - Stale links (files moved/renamed).
  - Sections that are still “草稿/要点” and need rewriting.

### 2) Update root aggregation (`README.MD`)

- Ensure `README.MD` contains:
  - Short purpose statement
  - Links to `basic/` docs
  - Link to `hand-writing/README.MD`
  - Link to `algorithm/` (and `algorithm/README` if it exists)
  - Minimal “how to run tests” section when relevant

### 3) Hand-writing docs (`hand-writing/README.MD` and topic docs)

For each hand-writing problem:

- **思路** must include:
  - Problem restatement (1–2 lines)
  - Key edge cases
  - Time/space complexity (if meaningful)
  - Common pitfalls
- **代码链接** must include:
  - Implementation file link
  - Test file link (if present)

If a problem is listed but no code exists yet:

- Keep it as “思路 + 题面”，and mark code link as **TODO** (do not invent file paths).

### 4) Basic notes rewrite (`basic/*.md`)

- Preserve the original technical points, but rewrite into interview-speak:
  - “是什么 → 为什么 → 怎么做/有什么影响”
  - Prefer short paragraphs + small lists
- Fix obvious formatting issues:
  - Wrong fenced block tags (e.g. `mermaind` → `mermaid`)
  - Broken list numbering / headings
- Do **not** add long tutorials; keep it as a compact interview note.

### 5) Consistency checks

- All links are relative and valid.
- Heading hierarchy is consistent (top-level title + `##/###` sections).
- No duplicated or contradictory statements across docs.

### 6) Validation (when possible)

- If the repo has tests (e.g. Jest), run them after doc refactors only when edits might affect code links or structure (optional, but preferred).

## Output expectations

When finishing a doc update request, report:

- Which files changed
- What gaps were filled (indexes/links/rewrites)
- Any remaining TODOs (missing implementations, empty directories)

## Extensibility: add new requirements safely

When the user provides new doc rules, append them to the following list **without removing existing rules**.

### Project-specific extra rules (append-only)

- (none yet)

