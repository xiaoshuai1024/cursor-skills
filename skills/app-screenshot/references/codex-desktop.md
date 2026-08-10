# Codex 桌面版截图案例（2026-08-07 实测）

## App 形态

- 进程名 **ChatGPT**（Electron「owl」），WindowsApps Store 版 `OpenAI.Codex_26.730.*`
- AppX manifest 注册 **`codex://` URL 协议**（`windows.protocol`，name=`codex`）——深链可拉起 app
- `app.asar` 主进程 `main-*.js`：`Are(e)` 判 `codex://` 前缀；深链经 `navigate-to-route` 把 path 发给 renderer（Renderer 按 path 路由）
- 对话真实内容**不在** `app.asar` 里，在用户目录 `~/.codex/` 下（CLI/桌面/VS Code 共享）

## UI 自动化硬限制

1. **输入框不可达**：会话视图点 hero / 新对话 / Alt+F 均无效，键盘事件落不到任何输入框，无法新建对话 / 发任务
2. **每次启动必回 home 态**，不恢复上次线程
3. **侧栏不显示 `source='vscode'` 的线程**：改 `threads` 表 cwd 到桌面项目目录、清 `thread_source`/`model` 都没用；导航旧对话不可行
4. **屏幕锁定 / 显示器休眠时全屏截图失败**：`PIL ImageGrab.grab` 报 `OSError: screen grab failed`，PowerShell `CopyFromScreen` 报「参数无效」——此时只能用 Playwright headless

## 对话数据源（复刻取内容用）

- `~/.codex/state_5.sqlite` → `threads` 表：`id` / `title` / `first_user_message` / `preview` / `cwd`（找线程 id 与任务文本）
- `~/.codex/sessions/<年>/<月>/<日>/rollout-<时间戳>-<id>.jsonl` → 真实对话流，逐行 JSON，`type=response_item`：
  - `payload.type=message`，`payload.content[]` 里 `type=input_text`（用户任务）/ `type=output_text`（助手回复）
  - `payload.type=function_call`：`payload.arguments`（JSON 字符串）拿执行的命令（如 `shell_command.command`）
  - `payload.type=function_call_output`：`payload.output` 拿命令输出
- 脚本本体：会话工作目录下的实际 `.py` 文件，可摘核心逻辑进图

## 真实配色（浅色主题）

| 元素 | 色值 |
|------|------|
| 页面/内容底 | `#ffffff` |
| 侧栏 | `#f6f6f6` |
| 用户消息气泡 | `#f3f3f4`（右对齐，圆角 14） |
| 助手正文 | `#1f2937` |
| 命令块头 | `#f7f7f8`，边框 `#e3e3e5`，▶ 圆钮 `#4f8ff5` |
| 命令输出/代码块 | 底 `#1a1c1f`，字 `#e3e5e8` |
| accent（链接） | `#2f6fdb` |
| 次要文字 | `#6b7280` / `#9aa0aa` |
| 文件创建 chip | 底 `#f2f8f4`，边框 `#d3e9da`，字 `#166534` |

## 复刻布局要点（对照真实界面）

- 顶栏 48px：logo（黑底白字圆角方）+ Codex + 竖线 + 线程标题 + 右窗口控制
- 内容列左起 **336px**、max-width **860px**、右侧留白 ~360px —— 这是「不裁剪」的关键
- 用户消息**右对齐**浅灰气泡（max-width 76%）；助手消息**左对齐**纯文本
- 命令块 = 浅色头（▶ 命令 时长）+ **深色输出**；脚本创建用绿字 chip；代码段深底 `white-space:pre`
- 收尾 `✓ Worked for X` 灰色徽章；底部输入框占位「向 Codex 发送消息…」
- 无侧栏、无私人对话信息

## 复刻流程（一条龙）

1. 从 rollout jsonl 逐字提取内容（见上「对话数据源」）
2. 填 `templates/conv.html`：只改 `.conv` 容器内的消息块，样式类不动
3. `python scripts/shoot.py <输出.png> 1600`（Playwright msedge headless）
4. OCR 核验：任务文本、关键命令输出表、收尾徽章都应在图中
5. 替换 `static/images/<slug>/01-*.png` → `hugo --gc --minify` → `curl` 服务端 md5 一致 → 提醒 Ctrl+F5

## 遗留线索

- `codex://threads/<thread_id>` 深链实测能拉起 app（8 个 ChatGPT 进程），但**未验证能否直接打开线程**。线程路径格式待实测（Web 端为 `/threads/<id>` 或 `/c/<id>`）。屏幕解锁后值得一试：若深链能开线程，就能截真实 app 界面替代复刻。
