"""诊断：metrics.json → diagnosis.json。

- 转化五级漏斗（送达→打开→读完→互动→关注与原文导流）逐级评级，定位最大流失环节
- 打开/完读/转化三层分开归因（wechat-retention 既有归因框架的数据化）
- 5% 节点留存曲线流失定位（tmpl=28 数据 delay 期间诚实标注缺失）
- 因子分桶（长度三档/发布窗口/标题可搜词代理），桶样本 <3 只列数据禁结论
- 证据 → 诊断 → 动作 三段式建议
"""
from __future__ import annotations

import json
import os
import statistics
import time
from typing import Optional

from .common import BASELINE_OPEN, BASELINE_READ_DONE, BASELINE_SHARE, DIAGNOSIS_PATH, MIN_FEEDBACK_SAMPLES, MIN_PUBLISHED_SAMPLES

# 可搜关键词代理：公众号搜索按标题关键词抓取，英文技术专名是最强可搜词（校准口）
SEARCHABLE_TOKENS = ("claude", "codex", "deepseek", "glm", "cursor", "openspec", "rag", "mcp", "api", "agent", "transformer", "rag")


def _fmt_pct(v) -> str:
    return f"{v * 100:.1f}%" if isinstance(v, (int, float)) else "—"


def rate_read_done(v: Optional[float]) -> str:
    if v is None:
        return "缺失"
    if v < BASELINE_READ_DONE["terminate"]:
        return "低于 30% 终止线（推荐衰减风险）"
    if v < BASELINE_READ_DONE["pool"]:
        return "过终止线未进池（30-50%）"
    if v < BASELINE_READ_DONE["push"]:
        return "进中级池（50-65%）"
    return "持续加推（>65%）"


def rate_open(v: Optional[float]) -> str:
    if v is None:
        return "缺失"
    if v < BASELINE_OPEN["avg"]:
        return "低于大盘（<1.9%）"
    if v < BASELINE_OPEN["good"]:
        return "大盘以上（1.9-4%）"
    return "优秀（>4%）"


def length_tier(word_count: Optional[int]) -> Optional[str]:
    if not word_count:
        return None
    if word_count <= 2500:
        return "≤2500 直发"
    if word_count <= 4000:
        return "2500-4000 压缩变体"
    return ">4000 拆系列/结构补偿"


def funnel(article: dict) -> dict:
    """五级漏斗 + 每级转化率。"""
    read = article.get("read_uv")
    sent = article.get("sent_total")
    share = article.get("share_rate")
    fav = article.get("fav_rate")
    zaikan = article.get("zaikan_rate")
    follow = article.get("follow_conv")
    interactive = round((share or 0) + (zaikan or 0) + (fav or 0), 4) if None not in (share, zaikan, fav) else None
    return {
        "送达": sent,
        "打开(阅读)": read,
        "打开率(含推荐)": article.get("open_rate_total"),
        "消息打开率": article.get("session_open_rate"),
        "读完率": article.get("read_done_rate"),
        "互动率(分享+在看+收藏)": interactive,
        "关注转化(人)": follow,
        "关注转化率": article.get("follow_rate"),
    }


def retention_drop(retention: Optional[dict]) -> Optional[dict]:
    """5% 节点留存曲线 → 最大跌落节点。tmpl=28 delay 期间返回 None（缺失）。"""
    if not retention or retention.get("delay") or not retention.get("rows"):
        return None
    rows = retention["rows"]
    series = []
    for r in rows if isinstance(rows, list) else []:
        if not isinstance(r, dict):
            continue
        pct = r.get("percent", r.get("pos"))
        uv = r.get("read_uv", r.get("uv"))
        if pct is not None and uv is not None:
            series.append((float(pct), int(uv)))
    if len(series) < 4:
        return {"note": "留存数据形态待解读", "raw": rows}
    series.sort()
    worst = max(range(1, len(series)), key=lambda i: series[i - 1][1] - series[i][1])
    return {
        "drop_node": f"{series[worst][0]:.0f}%",
        "drop_from_to": [series[worst - 1][1], series[worst][1]],
        "series": series,
        "note": "节点 × 正文字数 ≈ 流失章节位置；对照源稿小节定位",
    }


def diagnose_article(a: dict, history: list[dict]) -> dict:
    fun = funnel(a)
    med_follow = None
    follows = [h.get("follow_rate") for h in history if h.get("follow_rate") is not None]
    if len(follows) >= MIN_PUBLISHED_SAMPLES:
        med_follow = statistics.median(follows)

    evidence, actions = [], []
    # 打开层
    so = a.get("session_open_rate")
    ot = a.get("open_rate_total")
    if so is not None:
        evidence.append(f"消息打开率 {_fmt_pct(so)}（{rate_open(so)}），送达 {a.get('sent_total')}")
        if so < BASELINE_OPEN["avg"]:
            actions.append("打开层：下一篇 wechat_title 钩子前移 13 字 + 补 1 个可搜关键词；wechat_digest 前 40 字改「痛点/结论+数字」")
    elif ot is not None:
        evidence.append(f"打开率(含推荐) {_fmt_pct(ot)}，送达 {a.get('sent_total')}（会话口径缺失）")

    # 读完层
    rd = a.get("read_done_rate")
    if rd is not None:
        evidence.append(f"读完率 {_fmt_pct(rd)}（{rate_read_done(rd)}），平均阅读 {a.get('avg_read_sec') or '—'} 秒")
        if rd < BASELINE_READ_DONE["terminate"]:
            actions.append("读完层：优先修首屏与节奏（前 150 字问题+钩子、二级标题间隔 ≤1200 字），而非调标题")
    drop = retention_drop(a.get("retention"))
    if drop and drop.get("drop_node"):
        evidence.append(f"留存曲线最大跌落节点 {drop['drop_node']}（{drop['drop_from_to'][0]}→{drop['drop_from_to'][1]}）")
        actions.append(f"读完层：流失节点 {drop['drop_node']} ≈ 正文对应小节，优先拆分该节/补图")

    # 转化层
    fr = a.get("follow_rate")
    if fr is not None and med_follow is not None and fr < med_follow:
        evidence.append(f"关注转化率 {_fmt_pct(fr)} 低于自身中位 {_fmt_pct(med_follow)}")
        actions.append("转化层：补可收藏资产（速查/对比表/决策树）+ 文末往期关联 2-3 篇")
    elif a.get("follow_conv") is not None:
        evidence.append(f"新增关注 {a.get('follow_conv')} 人（转化率 {_fmt_pct(fr)}）")

    src = a.get("source_mix") or {}
    if src:
        top = sorted(src.items(), key=lambda kv: -kv[1])[:3]
        evidence.append("流量来源 Top3：" + "、".join(f"{k} {v}" for k, v in top))

    return {
        "msg_id": a.get("msg_id"),
        "item_idx": a.get("item_idx"),
        "slug": a.get("slug"),
        "title": a.get("title"),
        "ref_date": a.get("ref_date"),
        "length_tier": length_tier(a.get("word_count")),
        "funnel": fun,
        "read_done_class": rate_read_done(rd),
        "retention": drop,
        "evidence": evidence,
        "actions": actions,
        "has_detail": a.get("has_detail"),
    }


def factor_buckets(articles: list[dict]) -> dict:
    """因子分桶：桶内样本 <3 只列原始数据不写结论。"""
    def bucket_by(key_fn) -> dict:
        buckets: dict[str, list] = {}
        for a in articles:
            k = key_fn(a)
            if k is None:
                continue
            buckets.setdefault(k, []).append(a)
        out = {}
        for k, items in sorted(buckets.items()):
            rds = [i.get("read_done_rate") for i in items if i.get("read_done_rate") is not None]
            opens = [i.get("session_open_rate") for i in items if i.get("session_open_rate") is not None]
            follows = [i.get("follow_conv") for i in items if i.get("follow_conv") is not None]
            out[k] = {
                "n": len(items),
                "read_done_median": round(statistics.median(rds), 4) if len(rds) >= 2 else (rds[0] if rds else None),
                "session_open_median": round(statistics.median(opens), 4) if len(opens) >= 2 else (opens[0] if opens else None),
                "follow_sum": sum(follows) if follows else None,
                # 可结论需桶内有指标的样本 ≥3，光有文章数不算
                "conclusive": len(rds) >= MIN_PUBLISHED_SAMPLES,
                "slugs": [i.get("slug") for i in items],
            }
        return out

    def window_bucket(a):
        h = a.get("sent_hour")
        if h is None:
            return None
        return "20:00-21:00 档" if 20 <= h < 21 else f"{h:02d}:00 档"

    def keyword_bucket(a):
        t = (a.get("title") or "").lower()
        return "含可搜词" if any(tok in t for tok in SEARCHABLE_TOKENS) else "无可搜词"

    return {
        "length_tier": bucket_by(lambda a: length_tier(a.get("word_count"))),
        "publish_window": bucket_by(window_bucket),
        "searchable_keyword": bucket_by(keyword_bucket),
    }


def feedback(articles: list[dict]) -> dict:
    """选题反哺：≥MIN_FEEDBACK_SAMPLES 出加权 diff 建议，否则观察清单。"""
    rated = [a for a in articles if a.get("read_done_rate") is not None]
    rated.sort(key=lambda a: -a["read_done_rate"])
    top = [{"slug": a.get("slug"), "title": a.get("title"), "read_done": a.get("read_done_rate"), "follow": a.get("follow_conv")} for a in rated[:3]]
    bottom = [{"slug": a.get("slug"), "title": a.get("title"), "read_done": a.get("read_done_rate"), "follow": a.get("follow_conv")} for a in rated[-3:]]
    if len(rated) < MIN_FEEDBACK_SAMPLES:
        return {"mode": "observation", "top": top, "bottom": bottom, "note": f"样本 {len(rated)} <{MIN_FEEDBACK_SAMPLES}，只列观察不给加权建议"}
    return {
        "mode": "suggestion",
        "top": top,
        "bottom": bottom,
        "note": "加权 diff 供人工确认（写回 blog-writing 选题清单前必须人工复核）",
        "diff": _topic_diff(rated),
    }


def _topic_diff(rated: list[dict]) -> list[dict]:
    """按 slug 词面粗提选题方向（claude/codex/deepseek 系），Top 加权 Bottom 降权。"""
    directions: dict[str, list[float]] = {}
    for a in rated:
        t = (a.get("slug") or "") + " " + (a.get("title") or "")
        for key in ("claude", "codex", "deepseek", "openspec", "视频", "测试", "架构"):
            if key in t.lower():
                directions.setdefault(key, []).append(a["read_done_rate"])
    out = []
    for key, vals in directions.items():
        if len(vals) < 2:
            continue
        med = statistics.median(vals)
        if med > BASELINE_READ_DONE["pool"]:
            out.append({"direction": key, "action": f"+1（完读中位 {_fmt_pct(med)}）"})
        elif med < BASELINE_READ_DONE["terminate"]:
            out.append({"direction": key, "action": f"-1（完读中位 {_fmt_pct(med)}）"})
    return out


def diagnose(metrics: dict) -> dict:
    articles = [a for a in metrics.get("articles", []) if a.get("read_uv") is not None]
    diagnoses = [diagnose_article(a, articles) for a in articles]
    out = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "baseline_note": metrics.get("baseline_note"),
        "articles": diagnoses,
        "factors": factor_buckets(articles),
        "feedback": feedback(articles),
    }
    os.makedirs(os.path.dirname(DIAGNOSIS_PATH), exist_ok=True)
    with open(DIAGNOSIS_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    return out


def main() -> None:
    from .standardize import build_metrics

    d = diagnose(build_metrics())
    print(f"✅ diagnosis.json: {len(d['articles'])} 篇诊断 / 反哺模式={d['feedback']['mode']}")


if __name__ == "__main__":
    main()
