"""枚举公众号草稿箱全部草稿(appmsgid + 标题),滚动触发分页/加载全部。

反例:ctx.request 直调 `appmsg?action=list_card` / `operate_appmsg?sub=get` 会被风控
静默返回空列表(缺前端指纹),只能走草稿箱列表页的**页面 DOM 枚举**。

草稿箱 URL(首页左侧「草稿箱」菜单项):`cgi-bin/appmsg?action=list_card&type=77&begin=0&count=10`
列表是 masonry 无限滚动,滚到底自动加载下一页,全部加载完出现「已加载全部内容」。
每张卡片:`.weui-desktop-card[data-appid]`,标题 `.weui-desktop-publish__cover__title`。

用法:python -m list_drafts
输出:打印 N 条,写入 .wechat-build/draft-inventory.json
"""
from __future__ import annotations

import json
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

from playwright.sync_api import sync_playwright

import config
from publish_mp import get_token

LIST_URL = (
    "https://mp.weixin.qq.com/cgi-bin/appmsg"
    "?begin=0&count=10&type=77&action=list_card&token={token}&lang=zh_CN"
)

EXTRACT_JS = """
() => {
  const out = [];
  document.querySelectorAll('.weui-desktop-card[data-appid]').forEach(card => {
    const id = card.getAttribute('data-appid');
    if (!id) return;
    const titleEl = card.querySelector('.weui-desktop-publish__cover__title');
    out.push({ id: id, title: (titleEl ? titleEl.innerText : '').trim().slice(0, 80) });
  });
  return out;
}
"""

DONE_JS = """() => {
  const nomore = document.querySelector('.weui-desktop-masonry-list__nomore');
  return !!(nomore && nomore.offsetParent !== null);
}
"""


def main() -> None:
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            config.WECHAT_PROFILE_DIR,
            channel=config.BROWSER_CHANNEL,
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1600, "height": 1000},
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(config.WECHAT_MP_URL, wait_until="domcontentloaded")
        mp = None
        deadline = time.time() + config.HEADLESS_LOGIN_WAIT
        while time.time() < deadline:
            mp = get_token(ctx.request)
            if mp:
                break
            time.sleep(2)
        if not mp:
            ctx.close()
            sys.exit("❌ 无有效登录态")
        print(f"✅ token={mp['token'][:6]}...")

        page.goto(LIST_URL.format(token=mp["token"]), wait_until="load", timeout=60000)
        time.sleep(6)

        all_items: list[dict] = []
        seen: set[str] = set()
        stable = 0
        for rnd in range(60):
            items = page.evaluate(EXTRACT_JS)
            added = 0
            for it in items:
                if it["id"] not in seen:
                    seen.add(it["id"])
                    all_items.append(it)
                    added += 1
            done = page.evaluate(DONE_JS)
            print(f"  round {rnd}: {len(items)} cards, +{added}, done={done}")
            if done:
                break
            page.mouse.wheel(0, 6000)
            time.sleep(1.2)
            if added == 0:
                stable += 1
                if stable >= 3:
                    break
            else:
                stable = 0
        ctx.close()

    all_items.sort(key=lambda x: int(x["id"]))
    print(f"\n共 {len(all_items)} 条:")
    for it in all_items:
        print(f"  {it['id']}  {it['title']}")

    out_path = config.PROJECT_ROOT + "/.wechat-build/draft-inventory.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)
    print(f"写入 {out_path}")


if __name__ == "__main__":
    main()
