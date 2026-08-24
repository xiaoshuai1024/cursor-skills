# -*- coding: utf-8 -*-
"""诊断引擎：双基准评级 + 漏斗诊断树 + 流量池落位 + 因子分桶 + 跨平台矩阵。

基准双轨（design.md §3.1）：
- 自身历史分位数（样本 ≥5 才启用，第一基准）
- 行业阈值（references/metrics-benchmark.md，兜底）
- n<5 的桶/维度强制标注「样本不足仅供参考」

产出 data/analytics/diagnosis.json
"""
from __future__ import annotations

import json
from datetime import datetime

from . import common, fetch_uid
from .common import DATA_DIR, setup_utf8

# 行业水位线（research.md §2.2，抖音口径为主）
INDUSTRY = {
    "like_rate": {"low": 0.03, "high": 0.05},
    "comment_rate": {"low": 0.005, "high": 0.01},
    "share_rate": {"low": 0.01, "high": 0.02},
    "fav_rate": {"low": 0.01, "high": 0.02},
    "engagement_rate": {"low": 0.05, "high": 0.08},  # >8% 算法明显加量
    "follow_rate": {"low": 0.001, "high": 0.004},    # 播转粉率：0.1% 及格 / 0.4% 优秀（涨粉核心指标）
}
# 抖音流量池梯度（72h 播放落位）
DY_LADDER = [300, 3000, 20000, 100000, 500000]
SELF_SAMPLE_MIN = 5
PLAY_MATURE = 50  # 播放低于此值不算率（噪声）


def _pct(sorted_vals, p):
    if not sorted_vals:
        return None
    k = min(len(sorted_vals) - 1, max(0, int(round(p * (len(sorted_vals) - 1)))))
    return sorted_vals[k]


def percentiles(values: list[float]) -> dict | None:
    vs = sorted(v for v in values if v is not None)
    if len(vs) < SELF_SAMPLE_MIN:
        return None
    return {"p25": _pct(vs, 0.25), "p50": _pct(vs, 0.5), "p75": _pct(vs, 0.75), "n": len(vs)}


def grade(value, self_pct: dict | None, ind: dict | None) -> str:
    """low/mid/high/na。自身基准优先，无则行业阈值。"""
    if value is None:
        return "na"
    if self_pct:
        if value < self_pct["p25"]:
            return "low"
        if value > self_pct["p75"]:
            return "high"
        return "mid"
    if ind:
        if value < ind["low"]:
            return "low"
        if value > ind["high"]:
            return "high"
        return "mid"
    return "na"


def duration_bucket(sec):
    if sec is None:
        return None
    if sec < 60:
        return "<60s"
    if sec <= 90:
        return "60-90s"
    if sec <= 240:
        return "2-4min"
    return "5min+"


def title_shape(title: str) -> list[str]:
    out = []
    if not title:
        return out
    if any(c.isdigit() for c in title):
        out.append("含数字")
    if any(q in title for q in "?？"):
        out.append("疑问句")
    out.append(f"{'长' if len(title) > 20 else '短'}标题")
    return out


def dy_pool_level(play) -> tuple[int | None, str]:
    if play is None:
        return None, ""
    for i, cap in enumerate(DY_LADDER):
        if play < cap:
            nxt = f"距下一级差 {cap - play} 播放"
            return i + 1, f"第 {i + 1} 级（<{cap:,}）{nxt}"
    return len(DY_LADDER) + 1, f"第 {len(DY_LADDER) + 1} 级（≥{DY_LADDER[-1]:,}）"


def diagnose_video(slug: str, plat: str, m: dict, self_pcts: dict, hours_since_pub: float | None) -> dict:
    """单视频单平台诊断：证据→诊断→动作。"""
    findings = []
    play = m.get("play")

    # 1) 冷启动 / 流量层
    if plat == "douyin" and play is not None:
        lvl, desc = dy_pool_level(play)
        if lvl == 1 and (hours_since_pub is None or hours_since_pub > 24):
            findings.append({
                "symptom": f"72h+ 播放 {play}，卡在第 1 级流量池（冷启动未过）",
                "diagnosis": "冷启动未过：封面/标题/发布时间/账号标签问题（完播率数据 P2 接入后可细化）",
                "action": "换封面版式或标题形态重发同结构内容；核对发布时间窗（工作日 12:00/20:00 前后）",
            })
        findings.append({"pool_level": lvl, "pool_desc": desc})

    # 2) 互动漏斗
    for rate_key, label, action in [
        ("like_rate", "点赞率", "标题/口播结尾加明确观点，引导点赞"),
        ("comment_rate", "评论率", "结尾抛一个可争论的问题，置顶评论引导"),
        ("share_rate", "转发率", "内容加「发给你同事」场景句；视频号侧转发权重最高"),
        ("engagement_rate", "综合互动率", "观点更锐利 + 结尾 CTA；互动率 >8% 算法明显加量"),
    ]:
        v = m.get(rate_key)
        if v is None or (play or 0) < PLAY_MATURE:
            continue
        g = grade(v, self_pcts.get(rate_key), INDUSTRY.get(rate_key))
        if g == "low":
            basis = "自身 P25" if self_pcts.get(rate_key) else "行业阈值"
            findings.append({
                "symptom": f"{label} {v:.2%} 低于{basis}",
                "diagnosis": {"like_rate": "缺观点/情绪价值", "comment_rate": "缺可讨论点",
                              "share_rate": "缺转发场景", "engagement_rate": "整体互动偏弱"}[rate_key],
                "action": action,
            })

    # 3) 高播放低互动（流量给了但接不住）
    er = m.get("engagement_rate")
    if play is not None and play >= 1000 and er is not None and er < INDUSTRY["engagement_rate"]["low"]:
        findings.append({
            "symptom": f"播放 {play} 过千但互动率仅 {er:.2%}",
            "diagnosis": "流量承接弱：进得来留不住/不想互动，中段内容或节奏问题",
            "action": "压时长一档（当前 " + str(duration_bucket(m.get('duration_s'))) + "→ 下一档），提高信息密度",
        })

    # 4) 过程锚点（deep 快照）：观看深度 / 完播 / 3s 退出 / 封面点击 / 转粉
    depth = m.get("watch_depth")
    avg_t = m.get("avg_play_time_s")
    dur = m.get("duration_s")
    if depth is not None and depth < 0.10 and (play or 0) >= 50:
        findings.append({
            "symptom": f"平均观看深度 {depth:.1%}（平均 {avg_t:.0f}s / 全长 {dur:.0f}s）",
            "diagnosis": "开头 30 秒流失主导：观众在进入正题前离开（对照过程分析·停留句定位）",
            "action": "前 5 秒钩子重写 + 30 秒内给第一个干货点；首句直接抛结论式问题",
        })
    comp = m.get("completion_rate")
    if comp is not None and (play or 0) >= 50:
        if dur and dur >= 180 and comp < 0.01:
            findings.append({
                "symptom": f"完播率 {comp:.2%}（3 分钟以上长视频）",
                "diagnosis": "长视频结构问题：单支承载过多，完播成本高",
                "action": "拆系列（一集一个点）或压到 2 分钟内；B站侧保留长版（完播权重低）",
            })
    crash = m.get("crash_3s_rate")
    if crash is not None and crash >= 0.40:
        findings.append({
            "symptom": f"3 秒退出率 {crash:.0%}（B站）",
            "diagnosis": "钩子/封面承诺不匹配：点进来 3 秒即走",
            "action": "首帧与标题承诺对齐；前 3 秒口播直接回应标题问题",
        })
    ctr = m.get("cover_ctr")
    if ctr is not None and ctr < 0.03 and (play or 0) >= 50:
        findings.append({
            "symptom": f"封面点击率 {ctr:.1%}",
            "diagnosis": "封面/标题吸引力弱（进流量池的入口指标）",
            "action": "换封面版式（大字数字/截图 hero），标题改疑问句或数字型",
        })
    fr = m.get("follow_rate")
    if fr is not None and (play or 0) >= 500 and fr < INDUSTRY["follow_rate"]["low"]:
        findings.append({
            "symptom": f"播转粉率 {fr:.2%}",
            "diagnosis": "看完不关注：无系列感或单支无后续钩子",
            "action": "结尾预告下一集 + 合集入口；简介写系列更新节奏",
        })
    if fr is not None and (play or 0) >= 500 and fr >= INDUSTRY["follow_rate"]["high"]:
        findings.append({
            "symptom": f"播转粉率 {fr:.2%} 高于优秀线 {INDUSTRY['follow_rate']['high']:.1%}",
            "diagnosis": "转粉器内容：该选题/结构对涨粉有超额转化（涨粉是核心目标，优先复制）",
            "action": "系列化复制：同选题拆集数 + 合集置顶 + 结尾互相导流；发布节奏加密",
        })
    return findings


def analyze() -> dict:
    setup_utf8()
    metrics = json.loads((DATA_DIR / "metrics.json").read_text(encoding="utf-8"))
    videos: dict = metrics["videos"]

    # 自身分位数（按平台池）
    self_pcts: dict[str, dict] = {}
    for plat in ("douyin", "bilibili", "kuaishou"):
        pool = {"like_rate": [], "comment_rate": [], "share_rate": [], "fav_rate": [], "engagement_rate": []}
        for slug, entry in videos.items():
            m = entry.get(plat)
            if not m or (m.get("play") or 0) < PLAY_MATURE:
                continue
            for k in pool:
                if m.get(k) is not None:
                    pool[k].append(m[k])
        self_pcts[plat] = {k: percentiles(v) for k, v in pool.items()}

    now = datetime.now(common.CST)
    per_video, factors = {}, {"duration": {}, "hour": {}, "title_shape": {}, "series": {}}
    for slug, entry in videos.items():
        meta = fetch_uid.load_meta_for(slug) or {}
        pv = {}
        counted = False  # 因子桶同 slug 多平台只计一次
        for plat, m in entry.items():
            h = None
            if m.get("published_at"):
                try:
                    pub = datetime.strptime(m["published_at"], "%Y-%m-%d %H:%M").replace(tzinfo=common.CST)
                    h = (now - pub).total_seconds() / 3600
                except ValueError:
                    pass
            mature = h is None or h >= 24  # 发布未满 24h 数据未熟
            pv[plat] = {
                "metrics": m,
                "data_mature": mature,
                "findings": diagnose_video(slug, plat, m, self_pcts.get(plat) or {}, h),
            }
            # 因子桶（只统计成熟数据）
            if mature and not counted and (m.get("play") or 0) >= PLAY_MATURE:
                counted = True
                db = duration_bucket(m.get("duration_s"))
                if db:
                    factors["duration"].setdefault(db, []).append(slug)
                if m.get("published_at"):
                    hour = int(m["published_at"][11:13]) // 6 * 6
                    factors["hour"].setdefault(f"{hour:02d}点档", []).append(slug)
                for s in title_shape(m.get("title") or ""):
                    factors["title_shape"].setdefault(s, []).append(slug)
                series = meta.get("series")
                if series:
                    factors["series"].setdefault(series, []).append(slug)
        per_video[slug] = {"meta_title": meta.get("title"), "platforms": pv}

    # 跨平台矩阵：只比「已发布且有播放」的平台，至少 2 个有效平台才成行
    matrix = []
    for slug, entry in videos.items():
        plays = {p: m.get("play") for p, m in entry.items() if (m.get("play") or 0) > 0}
        if len(plays) < 2:
            continue
        best = max(plays, key=lambda p: plays[p])
        matrix.append({
            "slug": slug,
            "best": best,
            "play": plays,
            "spread": round(max(plays.values()) / max(1, min(plays.values())), 1),
        })

    out = {
        "generated_at": common.now_iso(),
        "self_percentiles": self_pcts,
        "per_video": per_video,
        "factors": factors,
        "cross_platform": matrix,
        "benchmark_source": "references/metrics-benchmark.md（行业阈值）+ 自身分位数（n≥5）",
    }
    (DATA_DIR / "diagnosis.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    n = sum(len(v) for v in videos.values())
    print(f"[diagnose] 诊断 {len(videos)} slug / {n} 平台记录 -> diagnosis.json")
    return out


if __name__ == "__main__":
    analyze()
