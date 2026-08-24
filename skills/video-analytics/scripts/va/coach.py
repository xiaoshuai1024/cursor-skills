# -*- coding: utf-8 -*-
"""创作指导装配（coach）：账号真实数据 × playbook 技巧 → 优先级 directives。

输入: metrics.json / diagnosis.json / retention.json
输出: data/analytics/directives.json（机器可读，供 video-generation 自查引用）
      .video-analytics/reports/directives.md（人读，写下一支脚本前必读）
用法: python -m va.coach
"""
from __future__ import annotations

import json

from . import common
from .common import DATA_DIR, REPORT_DIR, setup_utf8

PLAYBOOK_REF = "references/playbook.md"


def _load(name):
    p = DATA_DIR / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def build() -> dict:
    setup_utf8()
    metrics = _load("metrics.json")
    diag = _load("diagnosis.json")
    retention = {r.get("slug"): r for r in _load("retention.json")} if _load("retention.json") else {}
    videos = metrics.get("videos") or {}

    # ---- 账号级证据聚合（抖音为主战场）----
    depths, stops, stop_sents = [], [], []
    for slug, entry in videos.items():
        m = entry.get("douyin") or {}
        if m.get("watch_depth") is not None and (m.get("play") or 0) >= 50:
            depths.append((slug, m["watch_depth"], m.get("avg_play_time_s")))
        r = retention.get(slug) or {}
        st = r.get("avg_stop") or {}
        if st.get("sentence_no"):
            stops.append((slug, st["sentence_no"], st.get("time_s"), st.get("sentence", "")))
    fan_rows = []
    for slug, entry in videos.items():
        m = entry.get("douyin") or {}
        if m.get("new_fans") is not None and (m.get("play") or 0) >= 50:
            fan_rows.append((slug, m["new_fans"], m.get("follow_rate") or 0, m.get("play") or 0))

    directives: list[dict] = []

    def add(tid, priority, evidence, action, target):
        directives.append({"id": tid, "priority": priority, "evidence": evidence,
                           "action": action, "target": target})

    # H5/H1: 平均停留短 + 停在过渡句（账号级最优先）
    if depths:
        n = len(depths)
        med_depth = sorted(d[1] for d in depths)[n // 2]
        med_avg = sorted(d[2] or 0 for d in depths)[n // 2]
        if med_depth < 0.15:
            stop_desc = ""
            if stops:
                parts = [f"{s[0][:24]} 第{s[1]}句({s[2]:.0f}s)" for s in sorted(stops, key=lambda x: x[2] or 0)]
                stop_desc = "；停留落点：" + "、".join(parts)
            add("H5", "P0",
                f"{n} 支有深度数据的视频平均观看深度中位数 {med_depth:.0%}（平均时长中位 {med_avg:.0f}s）{stop_desc}",
                "删除第 2-3 句过渡句（「这条视频带你…」「先看结构」类），口播第 1 句直接给最反常识结论（H1）；过渡信息改字卡承担",
                "平均停留时长 ≥30s / 停留句位后移到第 5 句后")
            add("H1", "P0",
                f"平均观看深度 {med_depth:.0%}：观众在进入正题前离开，前三句信息量不足以留人",
                "结论前置——三个反常识答案在第 1 句各给半句（先给答案的名字，细节后展开）；首帧放结果画面（H2）",
                "平均观看深度 ≥15%")
    # H2: 封面点击可用但深度差 → 进来留不住
    ctrs = [(s, m.get("cover_ctr")) for s, e in videos.items()
            if (m := e.get("douyin") or {}).get("cover_ctr") and (m.get("play") or 0) >= 50]
    if ctrs and depths and med_depth < 0.10:
        good_ctr = [c for _, c in ctrs if c and c >= 0.03]
        if good_ctr:
            add("H2", "P1",
                f"封面点击率 {min(good_ctr):.1%}-{max(good_ctr):.1%} 达标（≥3%）但深度 {med_depth:.0%}——封面拉人成功、第 0 帧留人失败",
                "视频第 0 帧直接复用封面主视觉（结果画面/对比数据），禁静态标题页",
                "3s 退出率 / 深度")
    # M 系列: 完播
    comps = [(s, m.get("completion_rate"), m.get("duration_s")) for s, e in videos.items()
             if (m := e.get("douyin") or {}).get("completion_rate") is not None and (m.get("play") or 0) >= 50]
    if comps:
        long_low = [(s, c, d) for s, c, d in comps if d and d >= 180 and c and c < 0.01]
        if long_low:
            add("M4", "P1",
                f"{len(long_low)}/{len(comps)} 支 ≥3min 长视频完播 <1%（最低 {min(c for _, c, _ in long_low):.1%}）",
                "拆系列（一集一个点）或压到 2min 内；B站保留长版",
                "完播率 ≥2%")
        add("M1", "P1",
            "行业口径：每 5-10 秒需一个新信息点/视觉变化；本账号中段数据待留存曲线（当前仅锚点）",
            "分镜按论点配额写：每论点 ≤2 句（≈10s）到点换画面；论点切换配 SFX/字卡（M2）",
            "完播率")
    # C 系列: 转粉
    if fan_rows:
        converters = [r for r in fan_rows if r[2] >= 0.004]
        if converters:
            best = max(converters, key=lambda r: r[1])
            add("C3", "P0",
                f"转粉器：{best[0]} 单支涨粉 {best[1]}（播转粉 {best[2]:.2%}，播放 {best[3]:,}）",
                f"该选题系列化复制：拆集数 + 合集 + 集间导流 + 发布节奏加密（追更是知识类第一涨粉杠杆）",
                f"该系列周涨粉 ≥ 单支 {best[1]} 的 2 倍")
        weak = [r for r in fan_rows if r[2] < 0.001]
        if weak and not converters:
            add("C1", "P1", f"{len(weak)} 支播转粉 <0.1%",
                "结尾 10s 固定下一集预告 + 关注价值承诺（C2，说订阅理由不说「关注我」）",
                "播转粉率 ≥0.2%")
    # D 系列
    add("D1", "P2",
        "账号小时级播放序列已随 fans 采集积累中",
        "峰前 1h 发布试验（当前用 12:00/20:00 双窗），30 天后按序列定窗",
        "前 2 小时播放占比")

    out = {"generated_at": common.now_iso(), "playbook_ref": PLAYBOOK_REF,
           "account_snapshot": {
               "douyin_followers": (metrics.get("account") or {}).get("douyin", {}).get("follower_total"),
               "videos_with_depth": len(depths),
               "median_watch_depth": round(med_depth, 4) if depths else None,
               "median_avg_time": round(med_avg, 1) if depths else None,
               "converters": [r[0] for r in fan_rows if r[2] >= 0.004],
           },
           "directives": sorted(directives, key=lambda d: d["priority"])}
    (DATA_DIR / "directives.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    _render_md(out)
    print(f"[coach] directives {len(directives)} 条（P0 {sum(1 for d in directives if d['priority']=='P0')}）-> directives.json + directives.md")
    return out


def _render_md(out: dict) -> None:
    lines = ["# 创作指导 directives（写下一支脚本前必读）", "",
             f"生成：{out['generated_at']} · 技巧库：`video-analytics/{PLAYBOOK_REF}` · 本文件由 `make analytics-report` 自动刷新", "",
             "账号快照：" + " · ".join(
                 f"{k}={v}" for k, v in out["account_snapshot"].items() if v is not None), ""]
    pri_name = {"P0": "🔴 P0 立即执行（当前最大杠杆）", "P1": "🟡 P1 常规执行", "P2": "⚪ P2 观察试验"}
    for pri in ("P0", "P1", "P2"):
        group = [d for d in out["directives"] if d["priority"] == pri]
        if not group:
            continue
        lines += [f"## {pri_name[pri]}", ""]
        for d in group:
            lines += [f"### {d['id']} · {d['action'][:40]}…", "",
                      f"- **证据**：{d['evidence']}",
                      f"- **动作**：{d['action']}",
                      f"- **验证**：{d['target']}（下一支发布后同口径复测）", ""]
    lines += ["## 接入方式", "",
              "- video-generation 写口播/分镜时对照本清单自查；钩子→回收映射表引用 directive ID",
              "- 新视频发布满 24h：`make analytics-deep` → `make analytics-report` 复测验证指标",
              "- 技巧详解与行业依据见 `video-analytics/references/playbook.md`"]
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "directives.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    build()
