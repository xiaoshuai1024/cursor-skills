"""mp 后台数据接口健康检查（只读诊断工具）。

逐个探测 wa.collect 依赖的只读端点，改版或登录态失效时快速定位是哪一通道断了。
用法：WECHAT_PROJECT_ROOT=<root> python -m wa.probe
"""
from __future__ import annotations

import sys
import time

from . import ensure_wp_path

ensure_wp_path()

from .common import (  # noqa: E402
    URL_ARTICLE_LIST,
    URL_DETAIL_PAGE,
    URL_PUBLISH_LIST,
    URL_TENDENCY_SOURCE,
    MpSession,
)


def main() -> None:
    d2 = int(time.time()) - 86400
    d1 = d2 - 30 * 86400
    results = []
    try:
        with MpSession() as s:
            print(f"✅ 登录态 OK: token={s.mp['token'][:6]}...")

            def check(name: str, fn):
                try:
                    detail = fn()
                    results.append((name, "OK", detail))
                    print(f"  ✅ {name}: {detail}")
                except Exception as exc:
                    results.append((name, "FAIL", str(exc)[:120]))
                    print(f"  ❌ {name}: {str(exc)[:120]}")

            def _article_list():
                data = s.get_json(URL_ARTICLE_LIST.format(d1=d1, d2=d2, offset=0, count=10, token=s.mp["token"]))
                assert data.get("base_resp", {}).get("ret") == 0, str(data.get("base_resp"))
                return f"{len(data.get('article_list', []))} 篇"

            def _tendency():
                data = s.get_json(URL_TENDENCY_SOURCE.format(d1=d1, d2=d2, fp="0" * 32, token=s.mp["token"]))
                assert data.get("base_resp", {}).get("ret") == 0, str(data.get("base_resp"))
                return f"{len(data.get('all_article_stat_tendency', {}).get('list', []))} 行"

            def _publish():
                data = s.get_json(URL_PUBLISH_LIST.format(begin=0, count=10, token=s.mp["token"]))
                assert data.get("base_resp", {}).get("ret") == 0, str(data.get("base_resp"))
                page = data.get("publish_page") or "{}"
                import json

                return f"{len(json.loads(page).get('publish_list', []))} 条"

            def _detailpage():
                # 用列表第一篇真实 msgid 探测详情页
                data = s.get_json(URL_ARTICLE_LIST.format(d1=d1, d2=d2, offset=0, count=1, token=s.mp["token"]))
                rows = data.get("article_list", [])
                if not rows:
                    return "无已发表文章可探"
                a = rows[0]
                resp = s.get(URL_DETAIL_PAGE.format(msgid=f"{a['msg_id']}_{a.get('item_idx') or 1}", pub_date=str(a.get("ref_date", "")).replace("/", "-"), token=s.mp["token"]))
                assert resp.status == 200, f"status={resp.status}"
                ok = "article_data_new" in resp.text()
                return f"cgiData 内嵌 {'有' if ok else '无'}（{a['title'][:16]}）"

            time.sleep(2)
            check("get_article_list", _article_list)
            time.sleep(3)
            check("tendency_and_source", _tendency)
            time.sleep(3)
            check("appmsgpublish", _publish)
            time.sleep(3)
            check("detailpage cgiData", _detailpage)
    except RuntimeError as exc:
        print(f"❌ {exc}")
        sys.exit(2)
    failed = [r for r in results if r[1] == "FAIL"]
    print(f"\n探测完成: {len(results) - len(failed)}/{len(results)} 通道正常" + ("，存在失败通道（collect 会降级并标注缺失）" if failed else ""))


if __name__ == "__main__":
    main()
