---
name: app-screenshot
description: 桌面应用界面截图配图——本地应用窗口截图（跨平台 macOS Quartz / Windows WinRT）+ OCR 识别 + Playwright 复刻兜底。教程/踩坑型文章需要应用界面截图时调用。
---

# 桌面应用界面截图配图（app-screenshot）

## 何时用

博客配图需要**桌面/本地应用**（Codex 桌面版、Cursor、IDE 等）的真实界面截图，但以下情况导致拿不到可用的真实截图：

- UI 自动化不可行：输入框不可达、导航受限、线程/对话拉不出来
- 屏幕会话锁定 / 显示器休眠，`PIL ImageGrab` 与 PowerShell `CopyFromScreen` 全屏截图失败
- 需要特定历史对话或视图，无法现场重现
- 真实窗口内容贴边缘，截出来被判「被裁剪 / 不完整」

## 核心原则（先读，再动手）

1. **真实截图优先，复刻兜底**：能截到真实界面就最大化窗口截真实图（确认内容四边留白，右侧不得贴滚动条/窗口边）。
2. **复刻 = 忠实渲染**：对话内容**逐字取自真实数据源**（会话 rollout jsonl / 脚本文件 / 命令输出），不编造文字、不改数字。配色采样真实截图，布局对照真实界面。
3. **隐私红线**：侧栏、项目名、账号、真实业务名一律不进图。
4. **完整性是硬指标**：内容列留足右/下边距，四边干净，避免用户判「被裁剪」。
5. **headless 不依赖屏幕**：复刻用 Playwright(msedge) headless 渲染，屏幕锁定也能出图。

## 工作流

1. **判断能否真实截图**：能 → 最大化窗口 + 滚动条复位顶部 + 截真实图；不能 → 走复刻。
2. **定位真实数据源**：会话记录（`~/.codex/sessions/<年>/<月>/<日>/rollout-*.jsonl`）、脚本文件、命令输出。
3. **逐字提取内容**：从数据源拿用户任务、助手回复、执行的命令、命令输出（含时间/去重数字，勿美化）。
4. **采样真实配色**：从已接受的截图上取色（Codex 配色表见 `references/codex-desktop.md`）。
5. **填复刻模板**：`templates/conv.html` 保留全部样式类，内容区按真实对话替换。
6. **Playwright 截图**：`scripts/shoot.py <输出.png> [宽度=1600]`（msedge headless，不依赖屏幕会话）。
7. **OCR 核验完整性**：确认任务、关键输出、收尾徽章都在图内（WinRT OcrEngine，PowerShell 脚本）。
8. **替换文章图 + 重建**：替换 `static/images/<slug>/xx.png` → `hugo --gc --minify` → `curl` 服务端 md5 核验 → 提醒用户 Ctrl+F5 强刷防缓存。

## Codex 桌面版案例

UI 自动化硬限制、`codex://` 深链、对话数据源结构、真实配色表、布局要点、完整复刻步骤 → **`references/codex-desktop.md`**。
