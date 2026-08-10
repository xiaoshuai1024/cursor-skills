"""批量删除公众号草稿箱里的测试/废弃草稿。

安全策略:保留集 = link-map.json 里所有 weixin.draft_appmsgid + scheduled_appmsgid
(即正式文章/已排期稿件)。草稿箱里其余一律视为测试副本,删除。
删前必须先用 `list_drafts.py` 盘点生成 .wechat-build/draft-inventory.json。

用法:
    python -m list_drafts            # 先盘点(写入 draft-inventory.json)
    python -m cleanup_drafts         # dry-run,打印将删除清单
    python -m cleanup_drafts --delete  # 真正删除
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

from playwright.sync_api import sync_playwright

import config
from publish_mp import get_token


def load_link_map_keep_ids() -> set[str]:
    """保留集:link-map.json 里 weixin 节点下所有文章/草稿 ID。"""
    keep: set[str] = set()
    path = config.LINK_MAP_PATH
    if not __import__("os").path.exists(path):
        return keep
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    for _slug, info in data.items():
        if not isinstance(info, dict):
            continue
        wx = info.get("weixin") or {}
        for key in ("draft_appmsgid", "scheduled_appmsgid"):
            val = wx.get(key)
            if val:
                keep.add(str(val))
    return keep


def load_inventory() -> list[dict]:
    path = config.PROJECT_ROOT + "/.wechat-build/draft-inventory.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def delete_draft(request, mp: dict, appmsgid: str) -> tuple[bool, str]:
    """调 operate_appmsg?sub=del 删除草稿,返回 (成功?, 响应摘要)。"""
    url = (
        "https://mp.weixin.qq.com/cgi-bin/operate_appmsg"
        f"?t=ajax-response&sub=del&type=77&token={mp['token']}&lang=zh_CN"
    )
    form = {
        "token": mp["token"],
        "lang": "zh_CN",
        "f": "json",
        "ajax": "1",
        "random": str(random.random()),
        "AppMsgId": appmsgid,
        "count": "1",
    }
    resp = request.post(
        url,
        headers={
            "Origin": "https://mp.weixin.qq.com",
            "Referer": "https://mp.weixin.qq.com/",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        form=form,
    )
    body = resp.text()
    try:
        res = json.loads(body)
    except Exception:
        return False, body[:200]
    ret = res.get("ret", res.get("base_resp", {}).get("ret"))
    return (str(ret) == "0"), f"ret={ret}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--delete", action="store_true", help="真正删除(默认 dry-run)")
    args = parser.parse_args()

    inventory = load_inventory()
    keep = load_link_map_keep_ids()
    # 在草稿箱范围内但 link-map 未覆盖的受保护项(排期原稿等),显式补齐
    keep.update({"100001177", "100001182", "100001191", "100001199"})

    to_delete = [it for it in inventory if it["id"] not in keep]
    kept = [it for it in inventory if it["id"] in keep]

    print(f"草稿箱共 {len(inventory)} 条 | 保留 {len(kept)} 条 | 待删 {len(to_delete)} 条")
    print("保留:", ", ".join(it["id"] for it in sorted(kept, key=lambda x: int(x["id"]))))
    for it in sorted(to_delete, key=lambda x: int(x["id"])):
        print(f"  [删] {it['id']}  {it['title']}")

    if not args.delete:
        print("\n(dry-run,未删除。加 --delete 真正执行)")
        return
    if not to_delete:
        print("无可删项。")
        return

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            config.WECHAT_PROFILE_DIR,
            channel=config.BROWSER_CHANNEL,
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
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

        ok = fail = 0
        for it in sorted(to_delete, key=lambda x: int(x["id"])):
            success, detail = delete_draft(ctx.request, mp, it["id"])
            if success:
                ok += 1
                print(f"  ✅ {it['id']} 已删")
            else:
                fail += 1
                print(f"  ❌ {it['id']} 删除失败: {detail}")
            time.sleep(0.4)
        ctx.close()

    print(f"\n完成:成功 {ok} 条,失败 {fail} 条")
    # 回写已删记录,便于对账
    with open(config.PROJECT_ROOT + "/.wechat-build/cleanup-result.json", "w", encoding="utf-8") as f:
        json.dump(
            {"deleted_ok": ok, "deleted_fail": fail,
             "deleted_ids": [it["id"] for it in sorted(to_delete, key=lambda x: int(x["id"]))]},
            f, ensure_ascii=False, indent=2,
        )


if __name__ == "__main__":
    main()
