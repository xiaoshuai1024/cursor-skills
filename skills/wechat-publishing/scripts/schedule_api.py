"""直连 time_send API 定时发表(前端 bundle 反推出的完整 payload)。

机制(从 masssend-send-new-dialog 前端源码反推):
- 定时发表 = POST `/cgi-bin/masssend?action=time_send&t=ajax-response`
- payload 字段: appmsgid / isMulti / send_time / groupid / sex / country /
  province / city / type=10 / share_page=1 / synctxweibo=0 / operation_seq /
  scene_replace / req_id / req_time / sync_version / isFreePublish
- operation_seq 从 `masssendpage?f=json&preview_appmsgid=<id>` 拿(每次会话变)
- 只有所选日期有群发通知配额(quota_detail_list)时,isFreePublish=false 才走 time_send;
  无配额会走 freePublish(免费发布,不推送) —— 故必须先查配额再决定日期。

用法: python -m schedule_api <appmsgid> <日期文案> <HH:MM> [--dry-run]
  日期文案: 今天 / 明天 / 8月7日 ...
  --dry-run: 只打印 payload,不真正 POST
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from datetime import datetime, timedelta

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

from playwright.sync_api import sync_playwright

import config
from publish_mp import get_token

BASE = "https://mp.weixin.qq.com/cgi-bin"


def parse_date_label(label: str, today: datetime) -> tuple[datetime, int]:
    """把日期文案解析为 (目标 datetime, day_index)。day_index 1=今天,2=明天..."""
    label = label.strip()
    if label == "今天":
        return today.replace(hour=0, minute=0, second=0, microsecond=0), 1
    if label == "明天":
        return (today + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0), 2
    m = re.fullmatch(r"(\d{1,2})月(\d{1,2})日", label)
    if not m:
        raise ValueError(f"无法解析日期文案: {label!r}")
    month, day = int(m.group(1)), int(m.group(2))
    target = today.replace(month=month, day=day, hour=0, minute=0, second=0, microsecond=0)
    day_idx = (target.date() - today.date()).days + 1
    if day_idx < 1 or day_idx > 7:
        raise ValueError(f"日期超出可选范围(5分钟后~7天): {label}")
    return target, day_idx


def fetch_cgi(request, mp: dict, appmsgid: str) -> dict:
    """从 masssendpage?f=json 拿 operation_seq 与 quota_detail_list。"""
    resp = request.get(
        f"{BASE}/masssendpage",
        params={
            "f": "json", "preview_appmsgid": appmsgid,
            "token": mp["token"], "lang": "zh_CN",
        },
    )
    return resp.json()


def find_quota(cgi: dict, day_idx: int) -> int:
    """返回第 day_idx 天(1=今天)的普通群发通知配额。"""
    for q in cgi.get("quota_detail_list", []):
        if q.get("quota_type") == "kQuotaTypeMassSendNormal":
            items = q.get("quota_item_list", [])
            if 1 <= day_idx <= len(items):
                return items[day_idx - 1].get("quota", 0)
    return 0


def build_payload(cgi: dict, appmsgid: str, send_time: int,
                  fingerprint: str = config.MASS_SEND_FINGERPRINT) -> dict:
    """构造 time_send 完整 payload(逐字段复刻 UI 成功请求,见 .wechat-build/ui_run_100001177_0807.log:152)。

    2026-08-03 修复(此前 API 直发 67011/-1 的根因):
    - 缺 fingerprint + random → 服务端拒绝(masssend 系接口必带,账号级稳定值,见 config)
    - 必须全字符串表单编码(前端 FormData 序列化),布尔/数字混用会被拒
    成功 payload 关键点:
    - direct_send=1 —— 缺失直接 67011(前期反复 67011 的根因)
    - isFreePublish 必须是小写字符串 "false"(布尔 False 被序列化成 "False" 服务端不认)
    - scene_replace / isNeedCode / userType / face_verified 不在成功 payload 里,不加
    """
    now_ms = int(time.time() * 1000)
    diff_ms = int(cgi.get("client_time_diff") or 0) * 1000
    # req_id: 32 位随机字母数字(对齐前端 x(32),非小写 hex)
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    import random
    req_id = "".join(random.choice(alphabet) for _ in range(32))
    return {
        "token": cgi.get("token", ""),
        "lang": "zh_CN",
        "f": "json",
        "ajax": "1",
        "fingerprint": fingerprint,
        "random": str(random.random()),
        "ack": "",
        "code": "",
        "reprint_info": "",
        "reprint_confirm": "0",
        "list": "",
        "groupid": "",
        "sex": "0",
        "country": "",
        "province": "",
        "city": "",
        "send_time": str(send_time),
        "type": "10",
        "share_page": "1",
        "synctxweibo": "0",
        "operation_seq": cgi.get("operation_seq", ""),
        "req_id": req_id,
        "req_time": str(now_ms + diff_ms),
        "sync_version": "1",
        "isFreePublish": "false",
        "appmsgid": appmsgid,
        "isMulti": "0",
        "direct_send": "1",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("appmsgid", type=int)
    parser.add_argument("date_label", help="今天 / 明天 / 8月7日 ...")
    parser.add_argument("hhmm", help="HH:MM(北京时区)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    hh, mm = args.hhmm.split(":")
    today = datetime.now()
    target, day_idx = parse_date_label(args.date_label, today)
    send_time = int(target.replace(hour=int(hh), minute=int(mm)).timestamp())
    print(f"目标: {args.date_label} {args.hhmm} → send_time={send_time} "
          f"({datetime.fromtimestamp(send_time)}) day_idx={day_idx}")

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
        print(f"✅ token={mp['token'][:6]}...")

        cgi = fetch_cgi(ctx.request, mp, str(args.appmsgid))
        cgi["token"] = mp["token"]  # build_payload 需要 token 进表单
        quota = find_quota(cgi, day_idx)
        print(f"📊 {args.date_label}(第{day_idx}天) 群发通知配额 = {quota}")
        if quota <= 0:
            print(f"❌ 该日无配额,time_send 会被服务端拒绝。不提交。")
            ctx.close()
            sys.exit(1)

        payload = build_payload(cgi, str(args.appmsgid), send_time)
        if args.dry_run:
            print("DRY-RUN payload:")
            for k, v in payload.items():
                print(f"  {k} = {v}")
            ctx.close()
            return

        print(f"📨 POST time_send appmsgid={args.appmsgid} ...")
        resp = ctx.request.post(
            f"{BASE}/masssend?action=time_send&t=ajax-response&token={mp['token']}&lang=zh_CN&f=json",
            headers={
                "Origin": "https://mp.weixin.qq.com",
                "Referer": "https://mp.weixin.qq.com/cgi-bin/appmsg"
                          f"?t=media/appmsg_edit_v2&action=edit&type=77&appMsgId={args.appmsgid}"
                          f"&token={mp['token']}&lang=zh_CN",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            form=payload,  # 表单编码,对齐前端 FormData(此前 data= 发 JSON 导致 67011/-1)
        )
        body = resp.text()[:2000]
        print(">> 响应:", body)
        ctx.close()

    try:
        import json
        res = json.loads(body)
    except Exception:
        sys.exit("!! 响应非 JSON")
    ret = res.get("ret", res.get("base_resp", {}).get("ret"))
    if ret in (0, "0"):
        print(f"✅ 定时发表成功!send_time={send_time}")
    else:
        from publish_mp import ERROR_MAP
        detail = ERROR_MAP.get(int(ret) if ret else -1, f"未知错误码 {ret}")
        print(f"❌ 失败: {detail} | 响应: {body[:800]}")


if __name__ == "__main__":
    main()
