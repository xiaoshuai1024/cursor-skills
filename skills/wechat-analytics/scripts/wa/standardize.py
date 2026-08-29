"""标准化：快照 → data/wechat-analytics/metrics.json（统一指标名，缺失置 null）。

口径要点：
- 打开率双口径：open_rate_total = 阅读/送达（含推荐流量，可 >100%，传统口径）；
  session_open_rate = 会话场景阅读/送达（对标行业 1.9%/4% 基准的可比口径）。
- scene → 标签映射见 common.SCENE_LABELS；scene 9999 为日合计行。
- 诚实原则：平台没给的指标一律 null，报告标注「本次缺失」。
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Optional

from .common import (
    ACCOUNT_SNAPSHOT,
    ARTICLES_SNAPSHOT,
    BASELINE_OPEN,
    METRICS_PATH,
    MIN_PUBLISHED_SAMPLES,
    PROJECT_ROOT,
    SCENE_LABELS,
    read_jsonl,
)

SESSION_SCENES = (1,)  # 仅公众号消息列表（inbox）——打开率对送达的分母口径；scene 2 聊天转发属裂变流量


def _latest_by(rows: list[dict], key_fields: tuple[str, ...], kind: str) -> dict[tuple, dict]:
    out: dict[tuple, dict] = {}
    for row in rows:
        if row.get("kind") != kind:
            continue
        k = tuple(row.get(f) for f in key_fields)
        cur = out.get(k)
        if cur is None or str(row.get("fetched_at")) > str(cur.get("fetched_at")):
            out[k] = row
    return out


def parse_tendency(tendency_list: str) -> dict[str, int]:
    """'20260828_0,0,25,21' → {'2026-07-30': 0, ..., '2026-08-28': 156}（30 天逐日阅读）。"""
    if not tendency_list or "_" not in str(tendency_list):
        return {}
    head, _, seq = str(tendency_list).partition("_")
    try:
        end = time.strptime(head, "%Y%m%d")
    except ValueError:
        return {}
    import datetime

    end_date = datetime.date(*end[:3])
    vals = [int(x) for x in seq.split(",") if x.strip() != ""]
    out = {}
    for i, v in enumerate(vals):
        d = end_date - datetime.timedelta(days=len(vals) - 1 - i)
        out[d.isoformat()] = v
    return out


def source_mix_from_summary(summary_list: Optional[list[dict]]) -> dict[str, int]:
    """单篇 summary_list（逐日×场景 read_user）→ 来源构成 {标签: 阅读合计}。"""
    mix: dict[str, int] = {}
    if not summary_list:
        return mix
    for row in summary_list:
        scene = row.get("scene")
        label = SCENE_LABELS.get(scene, f"scene_{scene}")
        if label == "合计":
            continue
        mix[label] = mix.get(label, 0) + int(row.get("read_user") or 0)
    return mix


def daily_from_summary(summary_list: Optional[list[dict]]) -> dict[str, dict]:
    """单篇逐日合计（scene 9999 行）→ {date: {read, share}}。"""
    out: dict[str, dict] = {}
    for row in summary_list or []:
        if row.get("scene") != 9999:
            continue
        d = str(row.get("ref_date", ""))[:10]
        cur = out.setdefault(d, {"read": 0, "share": 0})
        cur["read"] += int(row.get("read_user") or 0)
        cur["share"] += int(row.get("share_user") or 0)
    return out


def account_daily(rows: list[dict]) -> list[dict]:
    """账号快照 → 逐日指标（同日多跑取最新 fetched_at）。"""
    best: dict[str, dict] = {}
    for snap in rows:
        for item in snap.get("tendency_list", []):
            d = time.strftime("%Y-%m-%d", time.localtime(int(item.get("date"))))
            cur = best.get(d)
            if cur is None or str(snap.get("fetched_at")) > str(cur.get("fetched_at")):
                cur = {"fetched_at": snap.get("fetched_at")}
                best[d] = cur
            scene = item.get("scene")
            label = SCENE_LABELS.get(scene, f"scene_{scene}")
            slot = cur.setdefault("scenes", {})
            slot[label] = slot.get(label, 0) + int(item.get("read_uv") or 0)
            if label == "合计":
                cur.update(
                    {
                        "read_uv": int(item.get("read_uv") or 0),
                        "share_uv": int(item.get("share_uv") or 0),
                        "collection_uv": int(item.get("collection_uv") or 0),
                        "source_uv": int(item.get("source_uv") or 0),
                        "mass_pv": int(item.get("mass_pv") or 0),
                    }
                )
    out = []
    for d in sorted(best):
        row = {"date": d, **best[d]}
        out.append(row)
    return out


def slug_word_count(slug: str) -> Optional[int]:
    """博客源稿正文字数（长度决策三档分桶的代理口径：以博客版为代理，报告注明）。"""
    path = os.path.join(PROJECT_ROOT, "content", "posts", f"{slug}.md")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = re.search(r"^\+\+\+.*?^\+\+\+", text, re.S | re.M)
    body = text[m.end():] if m else text
    return len(re.sub(r"\s", "", body))


def sent_by_msgid(acc_rows: list[dict]) -> dict[int, dict]:
    """发表记录快照 → appmsgid(msg_id 同域) → {sent_total, sent_hour}。"""
    best: dict[int, dict] = {}
    for snap in acc_rows:
        if snap.get("kind") != "publish_records":
            continue
        for rec in snap.get("records", []):
            if not rec.get("sent_time"):
                continue
            lt = time.localtime(rec["sent_time"])
            for am in rec.get("appmsgs", []):
                cur = best.get(am["appmsgid"])
                if cur is None or str(snap.get("fetched_at")) > str(cur.get("fetched_at")):
                    best[am["appmsgid"]] = {
                        "fetched_at": snap.get("fetched_at"),
                        "sent_total": rec.get("sent_total"),
                        "sent_hour": lt.tm_hour,
                        "sent_date": time.strftime("%Y-%m-%d", lt),
                    }
    return {k: {kk: vv for kk, vv in v.items() if kk != "fetched_at"} for k, v in best.items()}


def build_metrics() -> dict:
    from .map_ids import load_identity

    art_rows = read_jsonl(ARTICLES_SNAPSHOT)
    acc_rows = read_jsonl(ACCOUNT_SNAPSHOT)
    ident = load_identity().get("mapping", {})
    sent_map = sent_by_msgid(acc_rows)

    lists = _latest_by(art_rows, ("msg_id", "item_idx"), "list")
    details = _latest_by(art_rows, ("msg_id", "item_idx"), "detail")

    articles = []
    for (msg_id, item_idx), lst in sorted(lists.items(), key=lambda kv: str(kv[1].get("ref_date"))):
        det = details.get((msg_id, item_idx), {})
        adv = ((det.get("detail") or {}).get("article_data_new")) or {}
        summary = (det.get("detail") or {}).get("summary_list")
        info = ident.get(str(msg_id), {})
        slug = info.get("slug")

        sent = sent_map.get(msg_id) or {}
        read_uv = adv.get("read_uv")
        if read_uv is None:
            read_uv = lst.get("total_read_uv")
        sent_total = lst.get("sent_total") or sent.get("sent_total")
        sent_hour = lst.get("sent_hour") or sent.get("sent_hour")
        mix = source_mix_from_summary(summary)
        session_reads = sum(v for k, v in mix.items() if k == "公众号消息")
        session_shares = sum(v for k, v in mix.items() if k in ("公众号消息", "聊天会话"))

        open_total = round(read_uv / sent_total, 4) if read_uv is not None and sent_total else None
        session_open = round(session_reads / sent_total, 4) if sent_total and (summary is not None) else None
        share_rate = round(adv.get("share_uv", 0) / read_uv, 4) if adv.get("share_uv") is not None and read_uv else None
        fav_rate = round(adv.get("collection_uv", 0) / read_uv, 4) if adv.get("collection_uv") is not None and read_uv else None
        zaikan_rate = round(adv.get("zaikan_cnt", 0) / read_uv, 4) if adv.get("zaikan_cnt") is not None and read_uv else None
        follow_rate = round(adv.get("follow_after_read_uv", 0) / read_uv, 4) if adv.get("follow_after_read_uv") is not None and read_uv else None

        retention = det.get("retention")
        articles.append(
            {
                "msg_id": msg_id,
                "item_idx": item_idx,
                "slug": slug,
                "title": lst.get("title"),
                "ref_date": lst.get("ref_date"),
                "sent_total": sent_total,
                "sent_hour": sent_hour,
                "read_uv": read_uv,
                "open_rate_total": open_total,
                "session_open_rate": session_open,
                "read_done_rate": adv.get("finished_read_pv_ratio"),
                "avg_read_sec": adv.get("avg_article_read_time"),
                "share_rate": share_rate,
                "fav_rate": fav_rate,
                "zaikan_rate": zaikan_rate,
                "follow_conv": adv.get("follow_after_read_uv"),
                "follow_rate": follow_rate,
                "comment_cnt": adv.get("comment_cnt"),
                "like_cnt": adv.get("like_cnt"),
                "listen_uv": adv.get("listen_uv"),
                "source_mix": mix,
                "daily": daily_from_summary(summary),
                "tendency": parse_tendency(lst.get("tendency_list")),
                "jumps": (det.get("detail") or {}).get("article_jump_stat"),
                "profile": (det.get("detail") or {}).get("profile"),
                "retention": retention,
                "has_detail": bool(adv),
                "word_count": slug_word_count(slug) if slug else None,
            }
        )

    published = [a for a in articles if a.get("read_uv") is not None]
    metrics = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "published_samples": len(published),
        "baseline_note": (
            f"已发表样本 {len(published)} 篇"
            + ("，基线积累期：仅行业基准对照，不给自身分位数" if len(published) < MIN_PUBLISHED_SAMPLES else "")
        ),
        "articles": articles,
        "account": {"daily": account_daily(acc_rows)},
        "baselines": {
            "read_done": {"terminate": 0.30, "pool": 0.50, "push": 0.65},
            "session_open": BASELINE_OPEN,
            "share": {"low": 0.01, "high": 0.03},
        },
    }
    os.makedirs(os.path.dirname(METRICS_PATH), exist_ok=True)
    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=1)
    return metrics


def main() -> None:
    m = build_metrics()
    print(f"✅ metrics.json: {m['published_samples']} 篇已发表样本 / 账号日序列 {len(m['account']['daily'])} 天 / {m['baseline_note']}")


if __name__ == "__main__":
    main()
