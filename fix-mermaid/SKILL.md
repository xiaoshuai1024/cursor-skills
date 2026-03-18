---
name: fix-mermaid
description: Fix Mermaid diagrams that fail to render (e.g., "Syntax error in graph", Mermaid 9.4.3). Applies safe Mermaid 9.4.3-compatible rewrites inside Mermaid blocks without disturbing surrounding prose.
---

## Fix Mermaid (Mermaid 9.4.3)

## Scope / constraints
- Only edit the markdown files the user asks you to edit.
- Prefer **minimal diffs**: modify **only Mermaid diagram source** (inside Mermaid blocks) unless the rendering failure is caused by Mermaid text not being in a Mermaid block (then wrap it into a Mermaid block).
- Target Mermaid runtime: **9.4.3**.

## Quick diagnosis
1. Locate Mermaid usage:
   - Fenced blocks: <code>```mermaid</code>
   - Also check for Mermaid shortcodes (if present): `{{< mermaid >}} ... {{< /mermaid >}}`
2. Identify the failure mode:
   - If the page shows `Syntax error in graph`, the diagram source is being parsed but is invalid Mermaid.
   - If nothing renders and there is no error, the source may not be inside a Mermaid block or is being escaped by the renderer.

## Safe rewrite rules (Mermaid 9.4.3)
Apply these rewrites **inside the diagram only**.

### 1) Quote node labels (default)
When node labels contain any of: Chinese punctuation, parentheses `()`, slashes `/`, plus `+`, semicolons, colons, or line breaks, rewrite:
- From: `A[管理后台 luban]`
- To: `A["管理后台 luban"]`

In practice, when debugging, it’s usually fastest and safest to quote **all** node labels in the diagram to standardize and avoid edge-case parsing.

### 2) Avoid problematic “DB/cylinder” shapes with symbols
Prefer plain quoted nodes over special shapes when labels include symbols:
- From: `DB[(MySQL + Redis)]`
- To: `DB["(MySQL + Redis)"]`

### 3) Fix `subgraph` titles
Mermaid can be picky about `subgraph` identifiers.
- Avoid: `subgraph A[终端层]`
- Use: `subgraph TerminalGroup["终端层"]`

### 4) Replace unsupported diagram types
If the diagram type is not supported by Mermaid 9.4.3 (commonly `timeline`), replace with a supported equivalent:
- Prefer `flowchart TB` with staged nodes and arrows.

### 5) Ensure Mermaid is actually inside a Mermaid block
If the post contains raw Mermaid lines (e.g., a `flowchart TD` line not fenced), wrap it:

```text
```mermaid
flowchart TD
...
```
```

If the post uses Mermaid shortcodes, keep them **only if they work in this repo**. Otherwise convert to fenced ` ```mermaid ` blocks.

## Workflow (recommended)
1. Read the target markdown file(s) enough to isolate each Mermaid diagram.
2. For each diagram:
   - Quote node labels broadly.
   - Replace `[(...)]`-style nodes with quoted nodes if they include punctuation/symbols.
   - Fix `subgraph` headers if they use `subgraph X[Title]`.
   - Replace `timeline` with `flowchart`.
3. Verify (when applicable):
   - If it’s a Hugo site, run a build to ensure markdown still renders and no shortcodes broke.

## Output expectations
- Keep changes localized to Mermaid diagrams.
- Report which files were touched and why (briefly).
