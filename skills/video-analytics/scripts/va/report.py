# -*- coding: utf-8 -*-
"""报告生成：单视频诊断卡 + 总览周报 + 选题反哺 diff + 机器可读 json。

产出 .agents/skills/video-analytics/.video-analytics/reports/
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from . import common
from .common import DATA_DIR, REPORT_DIR, setup_utf8

PLAT_NAME = {"douyin": "抖音", "bilibili": "B站", "kuaishou": "快手", "shipinhao": "视频号"}
RATE_KEYS = [("like_rate", "点赞率"), ("comment_rate", "评论率"),
             ("share_rate", "转发率"), ("fav_rate", "收藏率"), ("engagement_rate", "互动率")]


def _fmt(v, pct=False):
    if v is None:
        return "—"
    return f"{v:.2%}" if pct else f"{v:,}"


def _pct1(v):
    return "—" if v is None else f"{v:.1%}"


def process_section(plat: str, m: dict, ret: dict | None) -> list[str]:
    """诊断卡「过程分析」节：锚点 + 停留句 + 段落表 + 冷启动。"""
    has_anchor = any(m.get(k) is not None for k in
                     ("completion_rate", "avg_play_time_s", "crash_3s_rate", "cover_ctr"))
    if not has_anchor:
        return []
    lines = ["### 过程分析", ""]
    lines += [
        f"- 完播率 {_pct1(m.get('completion_rate'))} · 平均观看 "
        + ("—" if m.get("avg_play_time_s") is None else f"{m['avg_play_time_s']:.0f}s")
        + f" · 深度 {_pct1(m.get('watch_depth'))}"
        f" · 3s退出 {_pct1(m.get('crash_3s_rate'))} · 封面点击 {_pct1(m.get('cover_ctr'))}"
        f" · 涨粉 {_fmt(m.get('new_fans'))}（播转粉 {_pct1(m.get('follow_rate'))}）",
    ]
    if m.get("first_hour_share") is not None:
        lines.append(f"- 冷启动：前 2 小时播放占比 {_pct1(m.get('first_hour_share'))}（决定流量池晋级速度）")
    if ret:
        stop = ret.get("avg_stop") or {}
        if stop.get("sentence"):
            lines += [
                "",
                f"**平均观众停在第 {stop.get('sentence_no')}/{ret.get('sentence_count')} 句**"
                f"（{stop.get('at')}，深度 {stop.get('depth'):.1%}）：",
                "",
                f"> {stop.get('sentence')}",
                "",
                "| 时间段 | 内容 | 留存提示 |",
                "|---|---|---|",
            ]
            for sec in ret.get("sections") or []:
                hint = sec.get("retention_hint") or ""
                lines.append(f"| {sec['range']} | {sec['digest'][:48]} | {hint} |")
        lines += ["", "ℹ️ 平台 web 端无秒级留存曲线，段落留存为锚点推断（平均时长 × 转写时间轴）。"]
    return lines + [""]


def _rate_row(label, m, self_pct, industry):
    v = m.get(label if label.endswith("rate") else label)
    key = label
    g = _grade_text(v, self_pct, industry.get(key))
    return f"| {RATE_KEYS_DICT.get(key, key)} | {_fmt(v, True)} | {_fmt((self_pct or {}).get('p50'), True)} | {_fmt((industry or {}).get('low'), True)}–{_fmt((industry or {}).get('high'), True)} | {g} |"


RATE_KEYS_DICT = dict(RATE_KEYS)


def _grade_text(v, self_pct, ind):
    from .diagnose import grade
    g = grade(v, self_pct, ind)
    return {"low": "🔴 低", "mid": "🟡 中", "high": "🟢 高", "na": "—"}[g]


def per_video_card(slug: str, diag: dict, retentions: dict | None = None) -> str:
    retentions = retentions or {}
    lines = [f"# 诊断卡：{slug}", ""]
    if diag.get("meta_title"):
        lines += [f"**标题**：{diag['meta_title']}", ""]
    for plat, pv in diag["platforms"].items():
        m = pv["metrics"]
        lines += [f"## {PLAT_NAME.get(plat, plat)}", ""]
        if not pv["data_mature"]:
            lines += ["⚠️ 发布未满 24h，数据未熟，以下为当前快照", ""]
        lines += [
            f"- 播放 {_fmt(m.get('play'))} · 赞 {_fmt(m.get('like'))} · 评 {_fmt(m.get('comment'))} "
            f"· 转 {_fmt(m.get('share'))} · 藏 {_fmt(m.get('fav'))}"
            + (f" · 币 {_fmt(m.get('coin'))}" if m.get("coin") is not None else ""),
            f"- 时长 {_fmt(m.get('duration_s'))}s · 发布 {m.get('published_at') or '—'} · 采集 {m.get('fetched_at') or '—'}",
            "",
        ]
        ret = retentions.get(slug)
        lines += process_section(plat, m, ret if ret and ret.get("platform") == plat else None)
        pool = [f for f in pv["findings"] if "pool_desc" in f]
        if pool:
            lines += [f"- 流量池：{pool[0]['pool_desc']}", ""]
        findings = [f for f in pv["findings"] if "symptom" in f]
        if (m.get("play") or 0) == 0:
            lines += ["未发布或无播放数据（定时稿件后台 stat 为空），跳过诊断。", ""]
        elif findings:
            lines += ["### 诊断", ""]
            for f in findings:
                lines += [f"**症状**：{f['symptom']}", f"- 诊断：{f['diagnosis']}", f"- 动作：{f['action']}", ""]
        else:
            lines += ["各率值均在基准区间内，无异常信号。", ""]
    return "\n".join(lines)


def overview(diag: dict, metrics: dict) -> str:
    videos = metrics["videos"]
    today = datetime.now(common.CST).strftime("%Y-%m-%d")
    lines = [f"# 运营总览 · {today}", "",
             f"- 生成：{diag['generated_at']} · slug {len(videos)} 个 · 平台记录 {sum(len(v) for v in videos.values())} 条",
             f"- 平台覆盖：抖音/B站/快手（视频号登录态失效，本次缺失——`python -m scripts.pub.login shipinhao` 重新扫码后恢复）",
             f"- 数据口径：完播率/5s 留存走「导出 Excel」通道（P2），当前为列表级互动+播放漏斗",
             ""]

    lines += ["## 涨粉看板（核心目标）", ""]
    account = metrics.get("account") or {}
    for plat, acc in account.items():
        total = acc.get("follower_total")
        daily = acc.get("daily") or []
        if daily:
            lines.append(f"**{PLAT_NAME.get(plat, plat)}**：粉丝 {total:,}（user/info 口径，最新）"
                         f"，日序列（总数/涨/掉/净增）：")
            lines.append("")
            lines.append("| 日期 | 总数 | 涨粉 | 掉粉 | 净增 |")
            lines.append("|---|---|---|---|---|")
            for d in daily:
                net = d.get("net")
                lines.append(f"| {d.get('date')} | {d.get('total')} | {d.get('new_fans')} "
                             f"| {d.get('cancel_fans')} | {net if net is not None else '—'} |")
            sn = acc.get("series_net")
            if sn is not None:
                lines += ["", f"区间净增（总数差分）**{sn:+d}**"]
        elif acc.get("net_since_last") is not None:
            lines.append(f"**{PLAT_NAME.get(plat, plat)}**：粉丝 {total:,}，较上次采集 {acc['net_since_last']:+d}（B站公开接口无日序列/掉粉明细节，快照差分）")
        else:
            lines.append(f"**{PLAT_NAME.get(plat, plat)}**：粉丝 {_fmt(total)}（首日基线，明日起有差分）")
        lines.append("")

    # 涨粉效率 Top（单视频涨粉数 + 播转粉率双口径）
    fan_rows = []
    for slug, entry in videos.items():
        for plat, m in entry.items():
            if m.get("new_fans") is not None and (m.get("play") or 0) >= 50:
                fan_rows.append((slug, plat, m))
    if fan_rows:
        by_cnt = sorted(fan_rows, key=lambda x: -(x[2].get("new_fans") or 0))
        by_rate = sorted(fan_rows, key=lambda x: -(x[2].get("follow_rate") or 0))
        lines += ["**涨粉效率 Top**（左：按涨粉数；右：按播转粉率）", "",
                  "| 涨粉数 Top | 涨粉 | 播转粉 | 播转粉率 Top | 涨粉 | 播转粉 |",
                  "|---|---|---|---|---|---|"]
        for i in range(min(3, len(by_cnt))):
            a, b = by_cnt[i], by_rate[i]
            lines.append(f"| {a[0]} | {a[2].get('new_fans')} | {_pct1(a[2].get('follow_rate'))} "
                         f"| {b[0]} | {b[2].get('new_fans')} | {_pct1(b[2].get('follow_rate'))} |")
        lines.append("")

    # 发布日拉动（抖音日序列 × 发布日历）
    dy_acc = account.get("douyin") or {}
    daily = dy_acc.get("daily") or []
    if daily:
        pub_days = {str(m.get("published_at"))[:10]
                    for slug, entry in videos.items()
                    for p, m in entry.items() if p == "douyin" and m.get("published_at")}
        d_map = {d["date"]: d.get("net") for d in daily if d.get("net") is not None}
        pub_vals = [v for k, v in d_map.items() if k in pub_days]
        base_vals = [v for k, v in d_map.items() if k not in pub_days]
        if pub_vals and len(base_vals) >= 3:
            base_vals_sorted = sorted(base_vals)
            base_med = base_vals_sorted[len(base_vals_sorted) // 2]
            pub_avg = sum(pub_vals) / len(pub_vals)
            uplift = (pub_avg / base_med) if base_med else None
            lines += ["**发布日拉动**（抖音）：",
                      "",
                      f"- 发布日（{len(pub_vals)} 天）日均净增 {pub_avg:+.0f}，非发布日（{len(base_vals)} 天）中位数 {base_med:+d}"
                      + (f"，拉动约 **{uplift:.1f}x**" if uplift and uplift > 0 and base_med > 0 else ""),
                      f"- 样本窗口 {len(d_map)} 天（样本不足仅供参考）；涨粉常滞后发布 1 天，长尾效应记入次日"]
        else:
            lines += [f"**发布日拉动**：非发布日仅 {len(base_vals)} 天（需 ≥3 天基线），暂不计算；"
                      f"涨粉常滞后发布 1 天，发布次日的净增也计入发布效果。", ""]
    lines.append("")

    lines += ["## Top / Bottom（按抖音播放，数据已熟）", ""]
    dy = []
    for slug, pv in diag["per_video"].items():
        p = pv["platforms"].get("douyin")
        if p and p["data_mature"] and (p["metrics"].get("play") or 0) > 0:
            dy.append((slug, p["metrics"]))
    dy.sort(key=lambda x: -(x[1].get("play") or 0))
    for tag, seg in [("Top 3", dy[:3]), ("Bottom 3", dy[-3:][::-1] if len(dy) > 3 else [])]:
        if not seg:
            continue
        lines += [f"**{tag}**", ""]
        for slug, m in seg:
            er = m.get("engagement_rate")
            lines.append(f"- {slug}：播放 {m.get('play'):,} · 互动率 {_fmt(er, True)} · {(m.get('published_at') or '')[:10]}")
    lines.append("")

    lines += ["## 跨平台矩阵（同一内容）", ""]
    if diag["cross_platform"]:
        lines += ["| slug | 各平台播放 | 最优 | 倍差 |", "|---|---|---|---|"]
        for row in diag["cross_platform"]:
            plays = " / ".join(f"{PLAT_NAME.get(p, p)} {v:,}" for p, v in (row.get("play") or {}).items())
            lines.append(f"| {row['slug']} | {plays} | {PLAT_NAME.get(row.get('best'), '—')} | {row.get('spread', '—')}x |")
    else:
        lines += ["（暂无 ≥2 平台的数据成熟记录）"]
    lines += [""]

    lines += ["## 留存深度排行（平均播放时长 / 全长）", ""]
    rows = []
    for slug, entry in videos.items():
        for plat, m in entry.items():
            if m.get("watch_depth") is not None and (m.get("play") or 0) >= 50:
                rows.append((slug, plat, m))
    rows.sort(key=lambda x: -(x[2].get("watch_depth") or 0))
    if rows:
        lines += ["| slug | 平台 | 平均观看 | 全长 | 深度 | 完播率 |", "|---|---|---|---|---|---|"]
        for slug, plat, m in rows:
            lines.append(f"| {slug} | {PLAT_NAME.get(plat, plat)} | {m.get('avg_play_time_s'):.0f}s "
                         f"| {m.get('duration_s'):.0f}s | {_pct1(m.get('watch_depth'))} | {_pct1(m.get('completion_rate'))} |")
        lines += ["", "深度 <10% = 开头 30 秒流失主导（对照各卡「过程分析·停留句」）；样本随深度采集覆盖逐步补全。", ""]
    else:
        lines += ["（暂无深度数据——跑 `make analytics-deep`）", ""]

    lines += ["## 因子分桶（样本不足的桶仅供参考）", ""]
    for dim, buckets in diag["factors"].items():
        if not buckets:
            continue
        lines.append(f"**{ {'duration': '时长', 'hour': '发布时段', 'title_shape': '标题形态', 'series': '系列'}.get(dim, dim) }**")
        for b, slugs in sorted(buckets.items(), key=lambda x: -len(x[1])):
            note = "" if len(slugs) >= 5 else "（样本不足仅供参考）"
            lines.append(f"- {b}：{len(slugs)} 条{note} —— {', '.join(s[:30] for s in slugs[:4])}")
        lines.append("")

    lines += ["## 建议动作清单", ""]
    n = 0
    for slug, pv in diag["per_video"].items():
        for plat, p in pv["platforms"].items():
            for f in p["findings"]:
                if "action" in f:
                    n += 1
                    lines.append(f"{n}. **{slug}**（{PLAT_NAME.get(plat, plat)}）：{f['action']}")
    if not n:
        lines.append("本期无异常信号。")
    return "\n".join(lines)


def feedback_keywords(diag: dict, metrics: dict) -> str:
    """选题反哺：涨粉口径（用户核心目标）——Top/Bottom 按单视频涨粉数排序，播转粉率 tiebreak。
    涨粉数据不足（<3 支有涨粉锚点）时回退播放口径并标注。

    topic_keywords.json 现为词表结构；建议在文件级新增可选 "weights" 块（系列名 → 权重），
    douyin-topic 的 filter_score 侧接入消费属其迁移任务（见 openspec 变更 Modified Capabilities）。
    """
    from . import fetch_uid
    tk_path = common.ROOT / ".agents" / "skills" / "douyin-topic" / "topic_keywords.json"
    tk = json.loads(tk_path.read_text(encoding="utf-8")) if tk_path.exists() else {}
    weights = tk.get("weights") or {}

    fan_rows, play_rows = [], []
    for slug, pv in diag["per_video"].items():
        p = pv["platforms"].get("douyin")
        if not (p and p["data_mature"]):
            continue
        m = p["metrics"]
        if (m.get("play") or 0) > 0:
            play_rows.append((slug, m.get("play")))
        if m.get("new_fans") is not None and (m.get("play") or 0) >= 50:
            fan_rows.append((slug, m.get("new_fans"), m.get("follow_rate") or 0))

    use_fans = len(fan_rows) >= 3
    if use_fans:
        fan_rows.sort(key=lambda x: (-x[1], -x[2]))
        top, bottom = fan_rows[:3], fan_rows[-3:]
        metric_name, fmt = "涨粉数", lambda v: f"+{v}"
    else:
        play_rows.sort(key=lambda x: -x[1])
        if len(play_rows) < 3:
            return "# 选题反哺\n\n数据成熟样本 <3，暂不建议调整权重。\n"
        top, bottom = play_rows[:3], play_rows[-3:]
        metric_name, fmt = "播放量", lambda v: f"{v:,}"

    lines = ["# 选题反哺建议（人工确认后写入 topic_keywords.json，不自动应用）", ""]
    if not use_fans:
        lines += ["⚠️ 涨粉锚点不足 3 支，本次回退播放量口径——跑 `make analytics-deep` 可切涨粉口径。", ""]

    def series_of(rows):
        out = {}
        for r in rows:
            meta = fetch_uid.load_meta_for(r[0]) or {}
            ser = meta.get("series")
            if ser:
                out.setdefault(ser, []).append(r[0])
        return out

    def _display(rows):
        return ", ".join(f"{r[0]}（{fmt(r[1])}）" for r in rows)

    lines += [f"## 表现 Top 3（按{metric_name}）", _display(top), ""]
    lines += [f"## 表现 Bottom 3（按{metric_name}）", _display(bottom), ""]

    top_s, bot_s = series_of(top), series_of(bottom)
    ups = {k: v for k, v in top_s.items() if k not in bot_s}
    downs = {k: v for k, v in bot_s.items() if k not in top_s}
    lines += ["## 建议 weights 块调整", ""]
    if set(top) & set(bottom):
        lines += [f"⚠️ 涨粉锚点样本仅 {len(fan_rows)} 支，Top/Bottom 重叠——扩大 `make analytics-deep` 覆盖后再看系列信号。", ""]
    if ups or downs:
        lines += ['在 `topic_keywords.json` 新增/合并：', "", "```json",
                  '"weights": {']
        for ser, slugs in sorted(ups.items()):
            cur = weights.get(ser, 1.0)
            lines.append(f'  "{ser}": {max(0.5, round(cur + 0.5, 1))},  // Top 系列（{", ".join(s[:24] for s in slugs[:2])}）')
        for ser, slugs in sorted(downs.items()):
            cur = weights.get(ser, 1.0)
            lines.append(f'  "{ser}": {max(0.5, round(cur - 0.5, 1))},  // Bottom 系列（{", ".join(s[:24] for s in slugs[:2])}）')
        lines += ["}", "```", ""]
        lines += ["⚠️ douyin-topic 的 filter_score 目前不读 weights 块——应用后需在其侧接入（对应 openspec 变更的 Modified Capabilities）。"]
    else:
        lines += ["（Top 与 Bottom 系列无差异化信号，本期不调整）"]
    return "\n".join(lines)


def run() -> int:
    setup_utf8()
    metrics = json.loads((DATA_DIR / "metrics.json").read_text(encoding="utf-8"))
    diag = json.loads((DATA_DIR / "diagnosis.json").read_text(encoding="utf-8"))
    from .diagnose import INDUSTRY

    stamp = datetime.now(common.CST).strftime("%Y-%m-%d")
    pv_dir = REPORT_DIR / f"{stamp}-per-video"
    pv_dir.mkdir(parents=True, exist_ok=True)
    retentions = {}
    ret_file = DATA_DIR / "retention.json"
    if ret_file.exists():
        for r in json.loads(ret_file.read_text(encoding="utf-8")):
            if r.get("slug"):
                retentions[r["slug"]] = r
    n = 0
    for slug, d in diag["per_video"].items():
        (pv_dir / f"{slug}.md").write_text(per_video_card(slug, d, retentions), encoding="utf-8")
        n += 1
    (REPORT_DIR / f"overview-{stamp}.md").write_text(overview(diag, metrics), encoding="utf-8")
    (REPORT_DIR / "feedback-keywords.md").write_text(feedback_keywords(diag, metrics), encoding="utf-8")
    (REPORT_DIR / "report.json").write_text(json.dumps(diag, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[report] 诊断卡 {n} 张 + 总览 + 反哺建议 -> {REPORT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
