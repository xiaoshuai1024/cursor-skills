## Templates

### Hand-writing topic template

Use this structure when adding a new hand-writing topic page (or expanding the index entry):

```markdown
## 题目名

### 思路

- **目标**：
- **关键点**：
- **边界情况**：
- **复杂度**：
- **常见坑**：

### 代码链接

- **实现**：`./xxx.js`
- **测试**：`./__tests__/xxx.test.js`（如有）
```

### Basic note rewrite pattern

When converting terse notes to fluent text:

1. Keep the original bullet’s meaning.
2. Add a short “why it matters” sentence.
3. Add the interview-ready contrast (what it fixes / trade-offs).

## Quality bar (quick checklist)

- Root `README.MD` links to all sections.
- `hand-writing/` entries are “思路 → 链接”.
- `basic/` reads smoothly and remains concise.
- Mermaid fences are correct (` ```mermaid `).
- No invented code links.

