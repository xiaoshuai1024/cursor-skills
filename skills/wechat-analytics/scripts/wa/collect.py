"""mp 后台只读采集 → data/wechat-analytics/snapshots/{articles,account}.jsonl。

四通道（2026-08-29 spike 实证）：
1. get_article_list      单篇列表（msg_id/title/ref_date/total_read_uv/tendency_list）
2. appmsgpublish         发表记录（群发时间 + 送达数 = 打开率分母）
3. detailpage cgiData    单篇指标内嵌 JSON（完读率/新增关注/在看/收藏/逐日×场景/画像）
4. datacubequery tmpl=28 深度数据（留存曲线，delay:true 当日缺失诚实落 null）

风控纪律：只读；请求间随机 sleep；同日详情去重；单接口失败降级不阻塞。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import date, timedelta
from typing import Optional

from .common import (
    ARTICLES_SNAPSHOT,
    ACCOUNT_SNAPSHOT,
    DETAIL_PAGE_WINDOW_DAYS,
    URL_ARTICLE_LIST,
    URL_DATACUBE_QUERY,
    URL_USER_ANALYSIS,
    URL_DETAIL_PAGE,
    URL_PUBLISH_LIST,
    URL_TENDENCY_SOURCE,
    MpSession,
    append_jsonl,
    now_iso,
    polite_sleep,
    read_jsonl,
    record_error,
)

LIST_PAGE_SIZE = 10


def _ts(days_ago_end: int = 1, window_days: int = 62) -> tuple[int, int]:
    d2 = int(time.time()) - days_ago_end * 86400
    d1 = d2 - window_days * 86400
    return d1, d2


def fetch_article_list(s: MpSession, max_pages: int = 6) -> list[dict]:
    """单篇图文列表（offset 翻页直到空页/无 next_offset，最多 max_pages 页）。"""
    d1, d2 = _ts()
    rows: list[dict] = []
    offset = 0
    for _ in range(max_pages):
        data = s.get_json(URL_ARTICLE_LIST.format(d1=d1, d2=d2, offset=offset, count=LIST_PAGE_SIZE, token=s.mp["token"]))
        if data.get("base_resp", {}).get("ret") != 0:
            raise RuntimeError(f"get_article_list ret={data.get('base_resp')}")
        batch = data.get("article_list", [])
        rows.extend(batch)
        nxt = data.get("next_offset")
        if not batch or nxt is None or nxt <= offset:
            break
        offset = nxt
        polite_sleep()
    return rows


def fetch_publish_records(s: MpSession, max_pages: int = 8) -> list[dict]:
    """发表记录（begin 翻页，服务端每页固定 20 条）：msgid/群发时间/送达/appmsg_info。

    appmsg_info[].appmsgid 与统计接口 msg_id 同域（spike 实证），是送达 join 的主键。
    """
    out: list[dict] = []
    seen = set()
    for page_idx in range(max_pages):
        data = s.get_json(URL_PUBLISH_LIST.format(begin=page_idx * 20, count=20, token=s.mp["token"]))
        if data.get("base_resp", {}).get("ret") != 0:
            raise RuntimeError(f"appmsgpublish ret={data.get('base_resp')}")
        page = json.loads(data.get("publish_page") or "{}")
        recs = page.get("publish_list", [])
        if not recs:
            break
        for rec in recs:
            try:
                info = json.loads(rec.get("publish_info") or "{}")
            except json.JSONDecodeError:
                continue
            key = info.get("msgid")
            if key in seen:
                continue
            seen.add(key)
            sent = info.get("sent_info", {}) or {}
            status = info.get("sent_status", {}) or {}
            out.append(
                {
                    "publish_msgid": key,
                    "publish_type": rec.get("publish_type"),
                    "sent_time": sent.get("time"),
                    "sent_total": status.get("total"),
                    "sent_succ": status.get("succ"),
                    "appmsgs": [
                        {"appmsgid": a.get("appmsgid"), "title": a.get("title")}
                        for a in (info.get("appmsg_info") or [])
                        if a.get("appmsgid")
                    ],
                }
            )
        if len(recs) < 20:
            break
        polite_sleep()
    return out


_CGI_KEY_RE = {
    "articleData": "articleData",
    "articleSummaryData": "articleSummaryData",
    "detailData": "detailData",
}


def _extract_json_value(html: str, key: str) -> Optional[dict]:
    """从 cgiData 赋值块里按括号配对提取某 key 的 JSON 值（值本身是合法 JSON）。"""
    m = re.search(rf"\n\s+{key}\s*:\s*", html)
    if not m:
        return None
    i = html.find("{", m.end())
    if i < 0:
        return None
    depth = 0
    in_str = False
    esc = False
    for j in range(i, min(len(html), i + 2_000_000)):
        c = html[j]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(html[i : j + 1])
                except json.JSONDecodeError:
                    return None
    return None


def fetch_detail(s: MpSession, msg_id: int, item_idx: int, ref_date: str) -> dict:
    """单篇详情：GET detailpage HTML 解析内嵌 cgiData（服务端渲染，无需轮询）。

    ref_date 格式 'YYYY/MM/DD'（列表接口原样）→ URL 用 'YYYY-MM-DD'。
    """
    pub_date = ref_date.replace("/", "-")
    url = URL_DETAIL_PAGE.format(msgid=f"{msg_id}_{item_idx}", pub_date=pub_date, token=s.mp["token"])
    resp = s.get(url)
    html = resp.text()
    if resp.status != 200 or "cgiData" not in html:
        raise RuntimeError(f"detailpage status={resp.status}")
    out = {"article_data_new": None, "subs_transform": None, "article_jump_stat": None, "summary_list": None, "profile": None}
    ad = _extract_json_value(html, "articleData")
    if ad:
        out["article_data_new"] = ad.get("article_data_new")
        out["subs_transform"] = ad.get("subs_transform")
        out["article_jump_stat"] = ad.get("article_jump_stat")
    sm = _extract_json_value(html, "articleSummaryData")
    if sm:
        out["summary_list"] = sm.get("list")
    dd = _extract_json_value(html, "detailData")
    if dd:
        out["profile"] = dd
    return out


def fetch_retention(s: MpSession, msg_id: int, item_idx: int, ref_date: str) -> Optional[dict]:
    """tmpl=28 深度数据（留存曲线等）：一次查询，delay:true 即当日缺失。

    fingerprint 为前端生成的账号级稳定值，实测直连不带也能提交，但服务端异步
    计算未就绪时返回 delay:true——诚实落 null，靠日频重试自然收敛。
    """
    try:
        refcompact = ref_date.replace("/", "").replace("-", "")
        j = s.datacube_query(
            tmpl="28",
            args={
                "refdate": refcompact,
                "offset": 0,
                "size": 10,
                "mp_article_appmsgid": str(msg_id),
                "mp_article_item_idx": item_idx,
            },
        )
        if j.get("base_resp", {}).get("ret") != 0:
            return {"delay": True, "error": str(j.get("base_resp"))}
        data = j.get("data") or []
        if j.get("delay") and not data:
            return {"delay": True}
        return {"delay": False, "rows": data}
    except Exception as exc:
        record_error("fetch_retention", exc, {"msg_id": msg_id})
        return {"delay": True, "error": str(exc)[:200]}


def fetch_tendency_source(s: MpSession) -> dict:
    """账号级日趋势×场景 + 流量来源。"""
    fingerprint = ""
    env_fp = __import__("os").environ.get("WECHAT_FINGERPRINT", "")
    fingerprint = env_fp or "0" * 32
    d1, d2 = _ts()
    data = s.get_json(URL_TENDENCY_SOURCE.format(d1=d1, d2=d2, fp=fingerprint, token=s.mp["token"]))
    if data.get("base_resp", {}).get("ret") != 0:
        raise RuntimeError(f"tendency_and_source ret={data.get('base_resp')}")
    return data


def fetch_user_growth(s: MpSession, window_days: int = 62) -> list[dict]:
    """用户分析：日粒度 new/cancel/netgain/cumulate_user 序列（openspec wechat-fans-growth-channel）。

    user_source=99999999 为全部场景；fingerprint 传 0 直连可用（2026-08-30 实证）。
    """
    fingerprint = __import__("os").environ.get("WECHAT_FINGERPRINT", "") or "0" * 32
    end = time.time() - 86400  # 数据 T+1
    d2 = time.strftime("%Y-%m-%d", time.localtime(end))
    d1 = time.strftime("%Y-%m-%d", time.localtime(end - window_days * 86400))
    data = s.get_json(URL_USER_ANALYSIS.format(d1=d1, d2=d2, fp=fingerprint, token=s.mp["token"]))
    if data.get("base_resp", {}).get("ret") != 0:
        raise RuntimeError(f"user_analysis ret={data.get('base_resp')}")
    for c in data.get("category_list") or []:
        if c.get("user_source") == 99999999:
            return c.get("list") or []
    return []


def detail_fetched_today(msg_id: int, item_idx: int) -> bool:
    """同日详情去重：当天已有 detail 快照即跳过（列表快照仍刷新）。"""
    today = time.strftime("%Y-%m-%d")
    for row in read_jsonl(ARTICLES_SNAPSHOT):
        if (
            row.get("kind") == "detail"
            and row.get("msg_id") == msg_id
            and row.get("item_idx") == item_idx
            and str(row.get("fetched_at", "")).startswith(today)
        ):
            return True
    return False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-detail", action="store_true", help="只刷列表/账号级，不拉单篇详情")
    ap.add_argument("--force-detail", action="store_true", help="忽略同日去重强制拉详情")
    args = ap.parse_args()

    try:
        with MpSession() as s:
            print(f"✅ 登录态 OK: token={s.mp['token'][:6]}...")

            # 1) 发表记录（送达分母 + 群发时间 + appmsgid 主键）
            try:
                publishes = fetch_publish_records(s)
                append_jsonl(
                    ACCOUNT_SNAPSHOT,
                    {"fetched_at": now_iso(), "kind": "publish_records", "records": publishes},
                )
                print(f"  发表记录: {len(publishes)} 条")
            except Exception as exc:
                publishes = []
                record_error("publish_list", exc)
                print(f"  ⚠️ 发表记录失败: {exc}")
            polite_sleep()

            # 2) 单篇列表
            try:
                articles = fetch_article_list(s)
                print(f"  单篇列表: {len(articles)} 篇")
            except Exception as exc:
                record_error("article_list", exc)
                print(f"  ❌ 单篇列表失败: {exc}")
                sys.exit(1)

            sent_by_date = {}
            sent_by_msgid = {}
            for p in publishes:
                if p.get("sent_time"):
                    lt = time.localtime(p["sent_time"])
                    p["sent_hour"] = lt.tm_hour
                    sent_by_date.setdefault(time.strftime("%Y-%m-%d", lt), p)
                for am in p.get("appmsgs", []):
                    sent_by_msgid.setdefault(am["appmsgid"], p)

            fetched = now_iso()
            for a in articles:
                ref_date = str(a.get("ref_date", ""))
                ref_iso = ref_date.replace("/", "-")
                sent = sent_by_msgid.get(a.get("msg_id")) or sent_by_date.get(ref_iso, {})
                append_jsonl(
                    ARTICLES_SNAPSHOT,
                    {
                        "kind": "list",
                        "msg_id": a.get("msg_id"),
                        "item_idx": a.get("item_idx"),
                        "title": a.get("title"),
                        "ref_date": ref_iso,
                        "publish_msgid": sent.get("publish_msgid"),
                        "sent_total": sent.get("sent_total"),
                        "sent_succ": sent.get("sent_succ"),
                        "sent_hour": sent.get("sent_hour"),
                        "total_read_uv": a.get("total_read_uv"),
                        "read_uv_ratio": a.get("read_uv_ratio"),
                        "tendency_list": a.get("tendency_list"),
                        "fetched_at": fetched,
                        "raw": a,
                    },
                )
            print(f"  列表快照落盘 {len(articles)} 行")
            if publishes:
                sent_ids = {am["appmsgid"] for p in publishes for am in p.get("appmsgs", [])}
                missing = sent_ids - {a.get("msg_id") for a in articles}
                if missing:
                    print(f"  ℹ️ {len(missing)} 篇已发送文章的统计行缺失（mp 侧数据延迟，日频重采自然收敛）")

            # 3) 单篇详情（同日去重）
            if not args.no_detail:
                done = 0
                for a in articles:
                    msg_id, item_idx = a.get("msg_id"), a.get("item_idx") or 1
                    if not msg_id or (not args.force_detail and detail_fetched_today(msg_id, item_idx)):
                        continue
                    ref_date = str(a.get("ref_date", ""))
                    age_days = (date.today() - date(*[int(x) for x in ref_date.split("/")])).days if "/" in ref_date else 999
                    if age_days > DETAIL_PAGE_WINDOW_DAYS:
                        continue  # detailpage 明示仅统计发表后 30 天内
                    try:
                        polite_sleep()
                        detail = fetch_detail(s, msg_id, item_idx, ref_date)
                        retention = fetch_retention(s, msg_id, item_idx, ref_date)
                        append_jsonl(
                            ARTICLES_SNAPSHOT,
                            {
                                "kind": "detail",
                                "msg_id": msg_id,
                                "item_idx": item_idx,
                                "title": a.get("title"),
                                "ref_date": ref_date.replace("/", "-"),
                                "fetched_at": now_iso(),
                                "detail": detail,
                                "retention": retention,
                            },
                        )
                        done += 1
                        print(f"  详情 {msg_id}_{item_idx} [{a.get('title', '')[:18]}] 完读率={(detail.get('article_data_new') or {}).get('finished_read_pv_ratio')}")
                    except Exception as exc:
                        record_error("detail", exc, {"msg_id": msg_id, "title": a.get("title")})
                        print(f"  ⚠️ 详情失败 {msg_id}: {str(exc)[:80]}")
                print(f"  详情快照落盘 {done} 行")

            # 4) 账号级日趋势×场景
            try:
                polite_sleep()
                ts_data = fetch_tendency_source(s)
                append_jsonl(
                    ACCOUNT_SNAPSHOT,
                    {
                        "fetched_at": now_iso(),
                        "tendency_list": ts_data.get("all_article_stat_tendency", {}).get("list", []),
                        "raw_keys": [k for k in ts_data.keys() if k not in ("base_resp",)],
                        "raw": {k: v for k, v in ts_data.items() if k not in ("base_resp", "all_article_stat_tendency")},
                    },
                )
                print("  账号级快照落盘")
            except Exception as exc:
                record_error("tendency_source", exc)
                print(f"  ⚠️ 账号级失败: {exc}")

            # 5) 用户增长（涨粉序列，openspec wechat-fans-growth-channel；流量主门槛追踪用）
            try:
                polite_sleep()
                rows = fetch_user_growth(s)
                if rows:
                    append_jsonl(
                        ACCOUNT_SNAPSHOT,
                        {
                            "fetched_at": now_iso(),
                            "kind": "user_growth",
                            "user_source": 99999999,
                            "latest": rows[-1],
                            "list": rows,
                        },
                    )
                    print(f"  用户增长快照落盘（cumulate_user={rows[-1].get('cumulate_user')}）")
                else:
                    print("  ⚠️ 用户增长：无数据行")
            except Exception as exc:
                record_error("user_growth", exc)
                print(f"  ⚠️ 用户增长失败: {exc}")
    except RuntimeError as exc:
        print(f"❌ {exc}")
        sys.exit(2)


if __name__ == "__main__":
    main()
