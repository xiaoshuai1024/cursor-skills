---
name: crawl
description: 爬虫自动化最佳实践——浏览器反检测策略、各平台已知技巧、速率限制、captcha 处理。在写/修改爬虫脚本时调用，避免重复踩坑。
---

# 爬虫自动化最佳实践

## 何时用本 skill

- 编写或修改 BOSS直聘 / 猎聘 / 智联 等平台的爬虫
- 遇到 captcha、白屏、空列表等反爬拦截
- 选择浏览器导航策略时

## 核心原则

1. **不要从零推理策略**——下面记录的是已经被验证有效的方法，直接遵循
2. **爬虫的本质是模拟真人**——越快越假，越规律越容易被封
3. **每个平台的反爬策略不同**——不要把一个平台的方法套到另一个

---

## 一、浏览器自动化通用规则

### 视窗口径（2026-08-30 定规）

- **有头（headless=False）交互工具**（发布/修封面/删卡/评论确认等用户盯屏幕的）：launch args 加 `--start-maximized` + `new_context(viewport=None)`——页面跟随系统分辨率（实测 inner=screen），禁止写死 1440×900 之类比屏幕还大的固定尺寸。
- **无头采集 / 渲染类**（截图留证、cover/frames 成片渲染）：保持固定 viewport（如 1920×1080）——确定性优先，跟随窗口反而不可复现。

### 导航策略（最重要）

| 方法 | 推荐度 | 说明 |
|------|--------|------|
| `page.goto(url)` 直接导航 | ✅ **始终优先** | 最接近真人地址栏输入，反爬特征最少 |
| `page.click()` + 等待导航 | ⚠️ 仅限必要 | 可能触发前端路由检测 |
| CDP (`CDPSession.send`) | ❌ **避免** | BOSS直聘 等平台会检测 CDP 调用特征 |

**结论：始终用 `page.goto()` 直接导航到目标 URL，不要用 click + 等待导航**

### 反检测清单

- [ ] 使用 stealth 插件（`puppeteer-extra-plugin-stealth` 或手动 patch）
- [ ] 禁用 `webdriver` 属性：`page.evaluateOnNewDocument(() => delete navigator.__proto__.webdriver)`
- [ ] 随机化 User-Agent（不同会话用不同 UA）
- [ ] 添加合理的页面操作延迟（每个操作间隔 1-3 秒，随机）
- [ ] 不要关闭用户已有的浏览器会话——复用已登录的上下文（cookie/Storage）
- [ ] 页面加载后随机滚动（模拟真人阅读行为）

### 请求间隔

```
每次搜索之间:     5-15 秒随机
每次翻页之间:     8-20 秒随机
每次完整爬取:     不超过 50 条，否则强制休息 60 秒
同一会话总次数:   不超过 3 轮，之后必须新建浏览器上下文
```

---

## 二、各平台已知策略

### BOSS直聘

- **反爬等级**：🔴 严苛
- **已验证有效的方法**：
  - 使用 `page.goto()` 直接导航，**禁止** CDP/UI click 导航
  - 必须使用 stealth 插件，否则 about:blank 拦截
  - 搜索 URL 格式：`https://www.zhipin.com/web/geek/job?city=100010000&query=技术总监`
  - 搜索结果加载后等 3-5 秒让 DOM 完全渲染
  - 如果出现验证码弹窗 → 暂停该会话，切换 IP 或等 10 分钟后重试
  - **不要**点击「搜索按钮」——直接 goto 搜索 URL
- **已知无效**：
  - CDP 导航 → 触发检测
  - 高频请求（< 3 秒间隔）→ 触发 captcha

### 猎聘

- **反爬等级**：🟡 中等
- **已验证有效的方法**：
  - 用户已登录状态下，白屏概率降低
  - 搜索 URL 格式：`https://www.liepin.com/zhaopin/?key=技术总监`
  - 翻页使用 URL 参数：`?key=...&curPage=1`
  - 关键词不要连续搜索，每次搜索之间等 10 秒以上
- **已知触发 captcha**：
  - 快速切换关键词（< 15 秒间隔）
  - 同一 IP 短时间内大量翻页

### 智联招聘

- **反爬等级**：🟢 较宽松
- **已验证有效的方法**：
  - 搜索 URL 格式：`https://www.zhaopin.com/sou/?kw=技术总监`
  - 基本可以直接抓取，注意数据通常通过 XHR 加载
  - 翻页参数：`?kw=...&p=1`

---

## 三、反爬对抗决策树

```
页面加载后白屏/空白？
  ├→ 检查是否触发 about:blank 拦截
  │    └→ 启用 stealth 插件，重试
  ├→ 检查 URL 是否被重定向到验证码页面
  │    └→ 该会话已触发 captcha → 暂停，切换 IP，等 10 分钟
  └→ 检查是否因登录态过期
       └→ 重新登录，保存 cookies

搜索结果为空？
  ├→ 检查 DOM 选择器是否过时（平台改版）
  │    └→ 更新选择器
  ├→ 检查是否触发隐性限制（返回空列表但不报错）
  │    └→ 降低频率，换关键词重试
  └→ 检查搜索条件是否过于严格
       └→ 放宽城市/关键词条件

请求被 429/403 拒绝？
  └→ 速率过快 → 停止当前会话，等 60 秒再试
     → 仍然 429 → 等待 5 分钟，切换 IP
     → 仍然 403 → 该 IP 被临时封禁，换 IP
```

---

## 四、数据字段标准化

从不同平台爬到的同一字段往往格式不同，统一用 Python 处理：

```python
import re

def parse_salary(text: str) -> tuple[int, int]:
    """解析薪资，返回 (min, max) 千元/月"""
    # "30K-50K·15薪" → (30, 50)
    # "2万-3万" → (20, 30)
    # "面议" → (0, 0)
    if '·' in text:
        text = text.split('·')[0]
    if '万' in text:
        nums = re.findall(r'[\d.]+', text)
        return tuple(int(float(n) * 10) for n in nums) if len(nums) >= 2 else (0, 0)
    nums = re.findall(r'[\d.]+', text.upper().replace('K', ''))
    return tuple(int(float(n)) for n in nums[:2]) if len(nums) >= 2 else (0, 0)
```

---

## 五、状态追踪

每次爬虫会话结束后，更新爬虫状态文件（如 `CRAWL_STATE.md`）记录：

```markdown
# Crawl State

## BOSS直聘
- 上次爬取: 2026-07-27
- 登录态: ✅ 有效 / ❌ 过期
- 上次触发 captcha: 否
- 当前有效选择器: job-card, title, company, salary, jd-link

## 猎聘
- 上次爬取: 2026-07-26
- 登录态: ❌ 需要重新登录
...
```

这样下次继续时能直接恢复，不用重新摸索。
