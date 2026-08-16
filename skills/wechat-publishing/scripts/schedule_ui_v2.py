"""端到端定时发表(UI 驱动 v2,精确复刻前端流程,每步断言+抓包取证)。

从 mass_dialog.js 反推的真实流程(isFreePublish=false 群发通知 + 定时):
1. 编辑器点「发表」→ 主弹窗(massSendDialogShow)
2. 开「定时发表」开关 → .mass-send__timer-container 出现
3. 日期下拉选目标日(dayChange 依配额自动置 isFreePublish=false)
4. 可见 time-picker 选 HH:MM(day>=2 是 curTime2),**断言回读值**
5. 主弹窗 footer「发表」→ confirmSendtype → double_check_dialog(继续发表)
6. 点「继续发表」→ submit → preCheck → check 链 → checkSafe → post → POST time_send

用法:python -m schedule_ui_v2 <appid> <日期文案> <HH:MM>
  --capture-only: 到 double_check_dialog 即停(不点继续发表,不会真发,取证用)

⚠️ **禁止定时「今天」**:前端 dayChange 对「今天」会降级为 isFreePublish=true
  免费发布——文章**静默上主页、无粉丝推送**,走即时 masssend 不走 time_send,
  脚本的 time_send 检测永远不触发 → 空响应「假失败真发布」(2026-08-05 事故)。
  本脚本只允许定时**未来配额日**(isFreePublish=false 群发通知)。真今天发需即时群发(暂不可靠)。
"""
from __future__ import annotations

import os
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

from playwright.sync_api import sync_playwright

import config
from publish_mp import get_token


def close_stray(page) -> bool:
    for kw in ("我知道了", "取消"):
        try:
            x = page.get_by_text(kw, exact=True).first
            if x.is_visible():
                x.click(timeout=1200)
                time.sleep(1)
                return True
        except Exception:
            pass
    # 兜底:education-dialog 等提示弹窗拦截点击但按钮文本带空白,文本匹配不上
    for sel in (".weui-desktop-dialog__wrp.education-dialog button",
                ".weui-desktop-dialog__wrp:visible button.weui-desktop-btn_primary"):
        try:
            btn = page.locator(sel).first
            if btn.count() and btn.is_visible():
                btn.click(timeout=1200)
                time.sleep(1)
                return True
        except Exception:
            pass
    return False


def click_primary_in_dialog(page, timeout=5000):
    """点某个可见 dialog 里的 primary 按钮(传回其文本)。"""
    try:
        btn = page.locator(
            ".weui-desktop-dialog:visible button.weui-desktop-btn_primary:visible"
        ).first
        if btn.count() and btn.is_visible():
            txt = btn.inner_text().strip()
            btn.click(timeout=timeout)
            return txt
    except Exception:
        pass
    return None


def is_today_label(date_label: str) -> bool:
    """目标日期是否是「今天」(今天/今日/当天 MM月DD日)。是 → 拒绝,避免免费发布事故。"""
    import datetime
    import re

    if "今天" in date_label or "今日" in date_label:
        return True
    m = re.match(r"(?:0?(\d{1,2}))月(\d{1,2})日", date_label)
    if m:
        now = datetime.datetime.now()
        return (int(m.group(1)), int(m.group(2))) == (now.month, now.day)
    return False


def main() -> None:
    appid = sys.argv[1] if len(sys.argv) > 1 else "100001177"
    date_label = sys.argv[2] if len(sys.argv) > 2 else "8月7日"
    hhmm = sys.argv[3] if len(sys.argv) > 3 else "06:00"
    capture_only = "--capture-only" in sys.argv
    hh, mm = hhmm.split(":")

    if is_today_label(date_label):
        sys.exit(
            f"❌ 拒绝定时「{date_label}」:今天走 isFreePublish=true 免费发布"
            "(静默上主页,无粉丝推送,假失败真发布)。"
            "本脚本只允许定时未来配额日(群发通知)。"
        )

    posts = []

    def on_response(r):
        try:
            if r.request.method != "POST" or "cgi-bin" not in r.url:
                return
            body = r.request.post_data or ""
            resp = ""
            try:
                resp = r.text()[:900]
            except Exception:
                pass
            posts.append((r.url, body[:1800], resp))
        except Exception:
            pass

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            config.WECHAT_PROFILE_DIR,
            channel=config.BROWSER_CHANNEL,
            headless=os.environ.get("DSH_UI_HEADLESS", "1") != "0",
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1600, "height": 1000},
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.on("response", on_response)
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
        print(f"✅ token={mp['token'][:6]}... 目标: {date_label} {hhmm} appid={appid}")

        url = (
            "https://mp.weixin.qq.com/cgi-bin/appmsg"
            f"?t=media/appmsg_edit_v2&action=edit&type=77&appMsgId={appid}"
            f"&token={mp['token']}&lang=zh_CN"
        )
        page.goto(url, wait_until="load", timeout=60000)
        time.sleep(8)

        # 1. 编辑器「发表」→ 主弹窗
        opened = False
        for attempt in range(30):
            clicked = False
            for i in range(25):
                try:
                    el = page.get_by_text("发表", exact=True).nth(i)
                    if el.is_visible():
                        el.click(timeout=2000)
                        clicked = True
                        break
                except Exception:
                    continue
            time.sleep(2)
            if page.locator(".mass-send__td").count():
                opened = True
                print(f">> 主弹窗已打开 (attempt {attempt})")
                break
            # 「发表」不可见多半是「我知道了」等提示弹窗挡着,先关再重试
            if close_stray(page):
                continue
            if not clicked:
                # 再给一次机会:关弹窗后按钮通常下一轮才渲染
                try:
                    el = page.get_by_text("发表", exact=True).first
                    if el.is_visible():
                        continue
                except Exception:
                    pass
                print("!! 无可见「发表」")
                break
        if not opened:
            ctx.close()
            sys.exit("!! 未打开主弹窗")

        # 2. 开「定时发表」开关(timer_setting)
        sw_done = False
        for sel in [".mass-send__td-setting.timer_setting .weui-desktop-switch",
                    ".mass-send__td-setting:nth-of-type(2) .weui-desktop-switch"]:
            try:
                page.locator(sel).first.click(timeout=4000)
                sw_done = True
                print(f">> 已开定时发表开关 ({sel})")
                break
            except Exception as exc:
                print(f"!! 定时开关失败 {sel}: {str(exc)[:80]}")
        for _ in range(20):
            if page.locator(".mass-send__timer-container").count():
                break
            time.sleep(1)
        print(">> 定时区域出现:", page.locator(".mass-send__timer-container").count() > 0)
        if not sw_done:
            ctx.close()
            sys.exit("!! 定时开关无法打开")

        # 3. 选日期(遍历所有可见 dt,别只点 .first —— day≥2 用 curTime2,首个可能是隐藏元素)
        try:
            dt = page.locator(".mass-send__timer .weui-desktop-form__dropdown__dt:visible").first
            if not dt.count():
                dt = page.locator(".mass-send__timer .weui-desktop-form__dropdown__dt").first
            dt.click(timeout=8000)
            time.sleep(2)
            # 只点可见下拉项:页面里还有隐藏的国家/性别下拉,.first 会匹配到隐藏元素导致超时
            opt = None
            for cand in page.locator(".weui-desktop-dropdown__list-ele",
                                     has_text=date_label).all():
                try:
                    if cand.is_visible():
                        opt = cand
                        break
                except Exception:
                    continue
            if opt:
                opt.click(timeout=4000)
                print(f">> 已选日期 {date_label}")
            else:
                opts = [t.strip() for t in page.locator(
                    ".weui-desktop-dropdown__list-ele").all_inner_texts() if len(t.strip()) < 12]
                print("!! 下拉无目标日,现有:", opts)
                ctx.close()
                sys.exit(1)
        except Exception as exc:
            print("!! 日期选择失败:", str(exc)[:120])
            ctx.close()
            sys.exit(1)
        time.sleep(2)

        # 4. 选时间(可见 picker;day>=2 → curTime2)
        visible_picker = page.locator("dl.weui-desktop-picker__time:visible").first
        try:
            visible_picker.locator("dt.weui-desktop-picker__dt").first.click(timeout=4000)
            print(">> 已点开时间面板")
            time.sleep(2)
        except Exception as exc:
            print("!! 时间面板打开失败:", str(exc)[:100])
        for pname, val in [("weui-desktop-picker__time__hour", hh), ("weui-desktop-picker__time__minute", mm)]:
            try:
                panel = page.locator(f"ol.{pname}:visible").first
                if panel.count():
                    ok = False
                    for k in range(panel.locator("li").count()):
                        li = panel.locator("li").nth(k)
                        cls = li.get_attribute("class") or ""
                        if li.inner_text().strip() == val and "disabled" not in cls:
                            li.click(timeout=2000)
                            ok = True
                            break
                    print(f">> 面板 {pname}: {val} 点击{'OK' if ok else '未命中/禁用'}")
            except Exception as exc:
                print(f">> {pname} 点击失败:", str(exc)[:80])
            time.sleep(1)
        time.sleep(1)
        # 收起时间面板
        try:
            page.locator(".mass-send__td .publish_container label.weui-desktop-form__label").first.click(timeout=2000)
            time.sleep(1)
        except Exception:
            pass

        # 断言日期 + 时间回读
        state = page.evaluate("""() => {
            const d=document.querySelector('.mass-send__timer .weui-desktop-form__dropdown__value');
            const pick=[...document.querySelectorAll('dl.weui-desktop-picker__time')];
            const vis=pick.filter(x=>x.getBoundingClientRect().width>0);
            return {date:d?d.innerText.trim():'', time:vis.length?vis[0].querySelector('input').value:''};
        }""")
        print(">> 回读 日期/时间:", state)
        if date_label not in (state.get("date") or "") or state.get("time") != hhmm:
            print(f"!! 断言失败: 期望 {date_label} {hhmm},实际 {state.get('date')} {state.get('time')}")
            ctx.close()
            sys.exit(1)

        # 5. 主弹窗 footer「发表」→ double_check_dialog
        pub_txt = click_primary_in_dialog(page)
        print(f">> 主弹窗 footer 点击: {pub_txt}")
        time.sleep(4)
        dlg = page.evaluate("""() => {
            const out=[];
            document.querySelectorAll('.weui-desktop-dialog').forEach(d=>{
                const r=d.getBoundingClientRect();
                if(r.width>0){
                    out.push({cls:(d.className||'').slice(0,60), btns:[...d.querySelectorAll('button')].map(b=>({t:b.innerText.trim(),p:(b.className||'').includes('primary')}))});
                }
            });
            return out;
        }""")
        print(">> 当前可见弹窗:", dlg)

        if capture_only:
            print("--capture-only: 停在 double_check_dialog,未点「继续发表」")
        else:
            # 6. 反复点掉所有弹窗里的 primary 确认按钮(继续发表/继续群发/下一步等),
            #    直到出现 time_send POST 或 30s 无变化,全程抓包。
            fired = False
            for cycle in range(8):
                before = len(posts)
                clicked_any = False
                for attempt in range(3):
                    try:
                        btns = page.locator(
                            ".weui-desktop-dialog:visible button.weui-desktop-btn_primary:visible"
                        )
                        n = btns.count()
                        if not n:
                            btns = page.locator(
                                ".weui-desktop-dialog:visible button:visible:has-text('继续')"
                            )
                            n = btns.count()
                        for k in range(n):
                            b = btns.nth(k)
                            txt = (b.inner_text() or "").strip()
                            if not txt:
                                continue
                            b.click(timeout=2500)
                            print(f">> 弹窗确认点击: 「{txt}」(cycle {cycle})")
                            clicked_any = True
                            break
                    except Exception as exc:
                        print(f">> 确认点击失败: {str(exc)[:80]}")
                        time.sleep(1)
                time.sleep(3)
                # 检测 time_send POST
                for u, b, rt in posts[before:]:
                    if "time_send" in u:
                        fired = True
                        print("!! 检测到 time_send POST 已发出")
                if fired:
                    break
                if not clicked_any:
                    print(f">> 无更多确认按钮可点(cycle {cycle})")
                    break
            if not fired:
                print("!! 未检测到 time_send POST 发出")
            # 结果分类:真定时 / 免费发布(危险)/ 即时群发 / 未知
            ts_ok = any("time_send" in u and '"ret":0' in rt for u, b, rt in posts)
            free_pub = [(u, b, rt) for u, b, rt in posts
                        if "masssend" in u and "isFreePublish=true" in b]
            immed = [(u, b, rt) for u, b, rt in posts
                     if "masssend" in u and "isFreePublish=false" in b and "send_time" not in b]
            if ts_ok:
                print("✅ 结果:真·定时群发通知(isFreePublish=false + send_time),粉丝到点推送")
            elif free_pub:
                print("!! ⚠️ 危险:检测到 isFreePublish=true 免费发布——文章已静默上主页(无推送)。"
                      "若是误发,请到 发表记录 手动删除对应条目;不是定时排期。")
            elif immed:
                print("✅ 结果:即时群发(isFreePublish=false 无 send_time),已立即推送")
            else:
                print("!! 未确认任何发布动作:需人工核对 home「近期发表」")
            time.sleep(6)
            # dump 错误 toast
            try:
                toasts = page.evaluate("""() => {
                    const out=[];
                    document.querySelectorAll('.weui-desktop-msg__title, .weui-desktop-tips, .js_tips').forEach(t=>{
                        const s=t.innerText||'';
                        if(s) out.push(s.slice(0,120));
                    });
                    return out;
                }""")
                if toasts:
                    print(">> 页面上提示文案:", toasts)
            except Exception:
                pass
            print("当前 URL:", page.url[:140])

        print("\n=== POST 请求(排期相关)===")
        seen = set()
        for u, b, rt in posts:
            if any(k in u for k in ["masssend", "operate_appmsg", "appmsgpublish", "appmsg"]):
                if u[:120] in seen:
                    continue
                seen.add(u[:120])
                print(f"  POST {u[:170]}")
                print(f"    body: {b[:1100]}")
                print(f"    resp: {rt[:260]}")
                print("  ---")
        ctx.close()


if __name__ == "__main__":
    main()
