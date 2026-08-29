---
name: mstodo-topic
description: 微软待办选题。浏览器登录态打开 Microsoft To Do 网页版，拉指定清单最新待办 → 三维分析（仿写价值/潜力/方向匹配度）出报告（合适给文章大纲或口播稿+分镜）→ 备注追加+标记完成写回 → 编排 blog-writing/wechat-publishing/video-generation 走文章(用户确认)→发布→视频→发布。用户说「分析待办/MS Todo/微软待办/清单里的选题/待办转文章视频」时调用。
---

# MSTodo Topic Skill — 待办收件箱 → 选题 → 生产编排

Microsoft To Do 指定清单当**私人选题收件箱**：浏览器登录态拉最新待办 → 分析能否转化成文章/视频（三维评估 + 档位 + 大纲或口播分镜）→ 结论写回待办（备注 + 完成）→ 用户决定做之后，编排既有 skill 走「文章（**必须用户确认**）→ 发布 → 视频 → 发布」。

## 何时用

- 「看看我待办清单里有什么能写的」→ 跑本 skill 的拉取 + 分析段
- 待办里存了想仿写的文章/视频/点子，要判断值不值得做 → 分析段
- 报告看完决定做哪个 → 生产编排段（调既有 skill，本 skill 不写正文）

## 通道（浏览器登录态，对齐仓库惯例）

**To Do 网页版 + patchright/msedge 持久化 profile**（tech-topic B 源 / wechat-publishing / scripts.pub 同款基建），全部实测结论（2026-08-26）：

- 消费者账户应用域 = **to-do.live.com**（直达 `/tasks/` 即凭 localStorage 自动恢复会话；经 microsoft/office.com 进会在 `/tasks/?app` 空白页卡死，勿走）。
- 每次拉取/写回开一扇**可见窗口**（免交互）：静默 SSO（落地页「开始使用」→ MSAL 帐户瓦片代点）→ 应用进入 → 从应用自身 substrate 请求**偷 Authorization Bearer**（裸 fetch 401，cookie 不够；MSAL localStorage 加密不可直读）→ in-browser fetch 完成读写 → 关窗。`MSTODO_HEADLESS=1` 可藏窗（不稳，空闲启动可能不发同步请求偷不到 Bearer）。
- 会话彻底过期（瓦片也没了）→ 脚本提示 `make todo-login` 弹窗重新登录。
- 接口 = `substrate.office.com/todob2/api/v1`（应用内部 OData，PascalCase：`Value/Id/Name/Subject/Status/Body.Content`；`ChangeKey` 为版本号，整对象 PATCH 回写）。固化在 `endpoints.json`，失效重抓自愈。

### 首次安装（一次）

```bash
make todo-login              # 弹窗登录微软账号（之后静默 SSO 免交互）
# 建议顺手: make todo-login capture=1  抓包观察窗内点开清单/编辑一条测试待办，校准 endpoints.json
```

### 接口固化（endpoints.json）

To Do 网页版接口属应用内部（可能随版本变），**不硬编码**——`.mstodo-topic/endpoints.json`（已按 2026-08-26 抓包+实测定稿）：

```json
{
  "origin": "https://to-do.live.com/tasks/",
  "paths": {
    "lists": "https://substrate.office.com/todob2/api/v1/taskfolders?…&maxpagesize=200",
    "tasks": "…/taskfolders/{listId}/tasks?…&maxpagesize=50",
    "task": "…/taskfolders/{listId}/tasks/{taskId}",
    "task_update": "…/taskfolders/{listId}/tasks/{taskId}"
  },
  "headers": {},
  "notes": "Bearer 由 browser_login 每次会话自动偷取，无需配置"
}
```

- 路径模板支持 `{listId}` / `{taskId}`；接口失效症状：拉取报「非 JSON / 疑似接口变更」→ `make todo-login capture=1` 重抓 → 按新摘要更新 paths。

## 工作流（四段）

### A 拉取（脚本）

```bash
make todo-lists                    # 先看清单名
make todo-topic list="写作素材"     # 拉最新 10 条（top=N 可调）
```

产物：`.mstodo-topic/snapshots/<时间戳>-<清单>.json`（含完整正文，分析只读它，勿重复拉取）。

### B 分析（模型判断，读 `references/analysis-rubric.md`）

读快照 JSON，对每条待办做三维评估（仿写价值/潜力/方向匹配度，各 ✅/⚠️/❌）+ 档位
（✅文章+视频 / ✍️仅文章 / 🎬仅视频 / ❌不适合），写报告 `.mstodo-topic/reports/YYYY-MM-DD-<清单>.md`：

- 每条：原文摘录 → 三维评估 → 档位 → 理由 → 建议动作
- ✍️ 项附**文章大纲**（标题候选 + 骨架 + 每节要点）；🎬 项附**口播稿 + 分镜脚本**（视频三要素齐全）
- ❌ 项逐条给**具体理由**，不含糊不硬凑；空清单如实写空
- 结尾：汇总表 + 优先级排序

报告给用户看，**等用户表态**再进 C/D。

### C 写回（脚本，分析定档后统一执行）

采用与不采用**都**备注 + 标记完成（清单保持收件箱语义，分析过的清出去）：

```bash
# 备注写进临时文件（多行 + 产物路径），再 resolve：
py -m writeback resolve --list-id <快照 list.id> --task-id <taskId> --note-file note.txt
# 采用项想等生产完再完成 → 加 --keep-open，生产后补一次（此时可附文章/视频链接）
```

备注内容：不采用 = 档位 + 一句话理由；采用 = 档位 + 报告/大纲路径 + 「转生产」。

### D 生产编排（调既有 skill，两道用户门禁）

用户对采用项说「做」之后按序执行，**本 skill 不自己写正文**：

1. `/blog-writing` 按源内容结构仿写文章（**差异化原创，禁逐字搬运**；先读该 skill 全规范）
   - **2026-08-28 用户定规 A｜完全独立仿写**：成稿**不得提及任何源文章、源作者、源平台及其内容**，不出现「看到一篇《xx》」「原文说」「某团队 / 某大厂做了 xx」类引用与暗示；只借鉴钩子 / 骨架 / 呈现手法，内容、数据、案例全部换成本站源码与实操证据，文章必须完全独立成立。
   - **2026-08-28 用户定规 B｜字数下限 5000**：仿写文章正文中文字符 ≥5000，从多角度扩充素材（实操数据、事故复盘、对照表、反模式、使用方式），不许单薄交稿。
2. 【门禁 1】文章草稿给用户确认，**不确认不发布**
3. 确认后发布：`./deploy.sh`（Hugo/Pages）+ `/wechat-publishing`（公众号草稿）
4. 文章发布后 `/video-generation` 出视频并发布（口播稿基于成文，三要素/CTA 规范在该 skill 内）
5. 可选：发布链接回填待办备注（配合 `--keep-open` 项此时 resolve）

## ⚠️ 合规与边界（强制）

- 个人待办为**私有数据**：登录态 profile / 快照 / 报告全在 `.mstodo-topic/`（git 已忽略，不进版本库）。
- 通道**全自建**：playwright + 自有登录态调 To Do 网页应用自身接口（对齐 wechat-publishing / scripts/pub 惯例），不引入第三方 SaaS 及其 CLI。
- 对源内容只做「**同结构换内容**」差异化仿写（借鉴钩子/骨架/呈现），产出必须换成本站源码与实操证据，禁止逐字搬运。**2026-08-28 定规：成稿不得提及源文章/源作者/源平台（完全独立仿写），且正文中文字符 ≥5000。**
- 权限最小化：只读待办 + 备注追加 + 完成标记，不做待办增删管理。

## 依赖与产物

| 依赖 | 说明 |
|------|------|
| Python 3 + **patchright**（或 playwright 兜底） | **用 `PYTHON_PW` 解释器**（Python311，playwright/patchright 都在那）；本机原生 playwright 启动 msedge 实测崩，patchright 正常（scripts/pub 同款）；浏览器 Windows msedge / macOS chrome |
| To Do 网页版登录态 | `make todo-login` 一次，profile 持久化复用 |
| endpoints.json | 抓包固化（见「接口固化」），接口变更重抓更新 |

```
.mstodo-topic/                  （skills 仓根，git 忽略）
├── endpoints.json              接口配置（抓包后固化/维护）
├── capture.jsonl               抓包原始记录（capture 模式重开一份）
├── msedge-profile/             浏览器登录态（勿提交勿删除）
├── snapshots/<ts>-<清单>.json   待办快照（含完整正文）
└── reports/YYYY-MM-DD-<清单>.md 分析报告（含大纲/口播分镜与写回记录）
```

## 工程约束

- 文件 I/O 显式 utf-8，子进程 `PYTHONIOENCODING=utf-8`；变量名避开内置构造器。
- 未登录 / endpoints 未固化：脚本打印指引退出码 2，**不**在拉取流程里自动弹浏览器登录。
- 清单名未唯一命中：列出候选清单名退出，交用户指定，不猜。
- 字段映射多候选兼容（**substrate 为 PascalCase**：`Value/Id/Name/Subject/Status/Body.Content/ContentType`，小写 Graph 风格留兜底），接口固化后对不上就改 `fetch_todo.py` 的候选键。

## 实战坑（2026-08-27 三轮全链路沉淀，改代码前先读）

- **写回（writeback）**：① todob2 单任务 GET **不被支持**（返回 JSON error 体）——取任务走清单拉取按 Id 过滤；② `fetch_json` 对 200+JSON error 体不报错，需显式判 `error` 键；③ 整对象 PATCH 遇 `Reminder.LastSnoozedAt` 类 null 字段**两头堵**（null 拒收、省略嵌套对象也报「必填属性缺失」）——`_strip_nulls` 深清洗 + 含 null 的顶层嵌套对象**整键省略**；④ 写回用快照里的精确 taskId，**勿手工拼**（后缀段重复拼错过一轮）。
- **会话恢复时序**：登录窗（login_gate）刚退出的 profile 有锁，紧接的 headless 会话可能判「未登录」——失败先等几秒重试一次再诊断；headless 下 live.com 直达 + 静默 SSO（落地页 CTA → MSAL 帐户瓦片代点）实测 3-12s 恢复。
- **fetch_json 顺序铁律**：必须先 `_shared_page()`（建会话顺带偷 Bearer）再组装 headers——反了首次 fetch 必 401（踩过）。
- **合成/环境瞬断**：WSL 冷启动首跑可能秒退（exit 1 无有效日志）——直接重跑即过，别先怀疑代码。
- **视频链路配合**：deck 的 shots `from_s` / code `hl_steps` 必须在**合成后**按 `audio/<slug>_t/boundaries_*.json` 的真实句边界重对齐再渲染（预写值只作占位）——这是「口播画面对齐」的既定流程。
