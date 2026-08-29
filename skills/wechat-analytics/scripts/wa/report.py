"""报告层：diagnosis.json → .wechat-analytics/reports/。

- per-article/<slug>.md  单篇诊断卡（漏斗评级 + 流失章节 + 证据→诊断→动作）
- overview-<date>.md     账号总览（日序列 / Top-Bottom / 因子分桶 / 基线声明）
- feedback-topics.md     选题反哺（<5 篇降级观察清单）
- report.json            机器可读全量诊断（link-map 48h 回看备注可直接引用）
"""
from __future__ import annotations

import json
import os
import time

from .common import DIAGNOSIS_PATH, REPORT_DIR


def _pct(v) -> str:
    return f"{v * 100:.1f}%" if isinstance(v, (int, float)) else "—"


def _load() -> dict:
    with open(DIAGNOSIS_PATH, encoding="utf-8") as f:
        return json.load(f)


def article_card(d: dict) -> str:
    f = d.get("funnel", {})
    lines = [
        f"# 诊断卡：{d.get('title') or d.get('slug')}",
        "",
        f"- slug：{d.get('slug') or '未映射'}｜群发日：{d.get('ref_date')}｜长度档：{d.get('length_tier') or '—'}",
        f"- msg_id：{d.get('msg_id')}_{d.get('item_idx')}｜详情数据：{'有' if d.get('has_detail') else '缺失'}",
        "",
        "## 转化漏斗",
        "",
        "| 级 | 指标 | 值 |",
        "|---|------|-----|",
        f"| 1 送达 | sent | {f.get('送达') or '—'} |",
        f"| 2 打开 | 阅读 | {f.get('打开(阅读)') or '—'}（含推荐 {_pct(f.get('打开率(含推荐)'))} / 消息 {_pct(f.get('消息打开率'))}） |",
        f"| 3 读完 | 完读率 | {_pct(f.get('读完率'))}（{d.get('read_done_class')}） |",
        f"| 4 互动 | 分享+在看+收藏 | {_pct(f.get('互动率(分享+在看+收藏)'))} |",
        f"| 5 转化 | 新增关注 | {f.get('关注转化(人)') if f.get('关注转化(人)') is not None else '—'} 人（{_pct(f.get('关注转化率'))}） |",
        "",
        "> 口径注：消息打开率与来源构成按「逐日去重累加」的人日近似口径（detailpage 只给日粒度），跨日重复阅读会使该值偏高；>100% 即属此情况，看趋势不看绝对值。",
        "",
    ]
    ret = d.get("retention") or {}
    if ret.get("drop_node"):
        lines += [
            "## 留存曲线流失定位",
            "",
            f"- 最大跌落节点：{ret['drop_node']}（{ret['drop_from_to'][0]} → {ret['drop_from_to'][1]}）",
            f"- {ret.get('note')}",
            "",
        ]
    elif d.get("has_detail"):
        lines += ["## 留存曲线", "", "- 本次缺失（服务端数据延迟，日频重采自然收敛）", ""]
    lines += ["## 证据", ""] + [f"- {e}" for e in d.get("evidence", [])]
    lines += ["", "## 诊断 → 动作", ""]
    if d.get("actions"):
        lines += [f"- {a}" for a in d["actions"]]
    else:
        lines += ["- 各层均在基准内或数据缺失，暂无动作项"]
    return "\n".join(lines) + "\n"


def overview(d: dict, account_daily: list[dict]) -> str:
    arts = d.get("articles", [])
    lines = [
        f"# 公众号数据总览 {time.strftime('%Y-%m-%d')}",
        "",
        f"> {d.get('baseline_note')}",
        "",
    ]
    if account_daily:
        recent = account_daily[-7:]
        lines += [
            "## 近 7 天账号级（推荐引擎为主的结构验证）",
            "",
            "| 日期 | 阅读 | 分享 | 收藏 | 推荐 | 搜一搜 | 会话(消息+聊天) |",
            "|------|------|------|------|------|--------|----------------|",
        ]
        for row in recent:
            sc = row.get("scenes", {})
            lines.append(
                f"| {row['date']} | {row.get('read_uv', 0)} | {row.get('share_uv', 0)} | {row.get('collection_uv', 0)} "
                f"| {sc.get('推荐', 0)} | {sc.get('搜一搜', 0)} | {sc.get('公众号消息', 0) + sc.get('聊天会话', 0)} |"
            )
        lines.append("")
    if arts:
        lines += ["## 单篇排行（完读率口径）", "", "| slug | 群发日 | 阅读 | 完读率 | 消息打开 | 新增关注 |", "|------|--------|------|--------|----------|----------|"]
        for a in sorted(arts, key=lambda x: -(x.get("funnel", {}).get("读完率") or 0)):
            f = a.get("funnel", {})
            lines.append(
                f"| {a.get('slug') or a.get('msg_id')} | {a.get('ref_date')} | {f.get('打开(阅读)') or '—'} "
                f"| {_pct(f.get('读完率'))} | {_pct(f.get('消息打开率'))} | {f.get('关注转化(人)') if f.get('关注转化(人)') is not None else '—'} |"
            )
        lines.append("")
    fac = d.get("factors", {})
    lines += ["## 因子分桶（桶内 <3 篇只列数据，禁结论）", ""]
    for fname, buckets in fac.items():
        for bname, b in buckets.items():
            mark = "✅可结论" if b.get("conclusive") else "⚠️样本不足"
            lines.append(
                f"- **{fname}={bname}** n={b['n']} 完读中位={_pct(b.get('read_done_median'))} 消息打开中位={_pct(b.get('session_open_median'))} [{mark}]"
            )
    lines.append("")
    return "\n".join(lines) + "\n"


def feedback_md(d: dict) -> str:
    fb = d.get("feedback", {})
    lines = [
        f"# 选题反哺 {time.strftime('%Y-%m-%d')}",
        "",
        f"> 模式：{fb.get('mode')}｜{fb.get('note')}",
        "",
        "## Top（完读率）",
        "",
    ]
    for t in fb.get("top", []):
        lines.append(f"- {t.get('slug')}：完读 {_pct(t.get('read_done'))}，关注 +{t.get('follow') if t.get('follow') is not None else '—'}")
    lines += ["", "## Bottom（完读率）", ""]
    for t in fb.get("bottom", []):
        lines.append(f"- {t.get('slug')}：完读 {_pct(t.get('read_done'))}，关注 +{t.get('follow') if t.get('follow') is not None else '—'}")
    if fb.get("diff"):
        lines += ["", "## 加权 diff（人工确认后才写回 blog-writing 选题清单）", ""]
        for df in fb["diff"]:
            lines.append(f"- {df['direction']} {df['action']}")
    return "\n".join(lines) + "\n"


def main() -> None:
    d = _load()
    from .standardize import account_daily, read_jsonl
    from .common import ACCOUNT_SNAPSHOT

    daily = account_daily(read_jsonl(ACCOUNT_SNAPSHOT))
    os.makedirs(REPORT_DIR, exist_ok=True)
    date_tag = time.strftime("%Y-%m-%d")

    per_dir = os.path.join(REPORT_DIR, f"{date_tag}-per-article")
    os.makedirs(per_dir, exist_ok=True)
    for a in d.get("articles", []):
        name = a.get("slug") or f"msgid-{a.get('msg_id')}"
        with open(os.path.join(per_dir, f"{name}.md"), "w", encoding="utf-8") as f:
            f.write(article_card(a))

    with open(os.path.join(REPORT_DIR, f"overview-{date_tag}.md"), "w", encoding="utf-8") as f:
        f.write(overview(d, daily))
    with open(os.path.join(REPORT_DIR, "feedback-topics.md"), "w", encoding="utf-8") as f:
        f.write(feedback_md(d))
    with open(os.path.join(REPORT_DIR, "report.json"), "w", encoding="utf-8") as f:
        json.dump({"date": date_tag, **d}, f, ensure_ascii=False, indent=1)

    print(f"✅ 报告落盘 {REPORT_DIR}（单篇卡 {len(d.get('articles', []))} 张 + overview + feedback + report.json）")


if __name__ == "__main__":
    main()
