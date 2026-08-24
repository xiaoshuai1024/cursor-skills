#!/usr/bin/env python3
"""账号标题 DNA 统计:从 blog-src 语料生成 references/account-dna.md(风格锚)。

数据源(--blog-root,默认 D:/codes/blog-src):
  - video-generation/archive/*/metadata.txt   视频标题(已发布)
  - content/posts/*.md front matter           文章标题
  - data/analytics/metrics.json               互动分位(标注 P75 以上视频标题共性)

统计维度:中位长度(len + CJK 当量宽)/问句率/数字率/标点习惯/高频词。
样本量 n<30 的维度输出「样本不足」标注——诚实优先,不硬造结论。
幂等:纯函数(输入 + 日期),同日重跑输出一致。

用法:
    python account_dna.py                    # 打印到 stdout
    python account_dna.py --write            # 写入 ../references/account-dna.md
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter
from datetime import date
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

DEFAULT_ROOT = Path("D:/codes/blog-src")
MIN_SAMPLE = 30          # 低于此样本的维度标「样本不足」
P75_MIN_VIDEOS = 8       # P75 共性标注至少要 8 支视频,否则整块标注样本不足


def cjk_width(text: str) -> float:
    w = 0.0
    for ch in text:
        if ch.isspace():
            w += 0.3
        elif ord(ch) > 0x2E80:
            w += 1.0
        else:
            w += 0.6
    return w


# ---- 语料读取 ----

def load_video_titles(root: Path) -> list[tuple[str, str]]:
    """(slug, title),来自 archive/*/metadata.txt 的 标题: 行。"""
    out = []
    for d in sorted((root / "video-generation" / "archive").iterdir()):
        txt = d / "metadata.txt"
        if not txt.is_file():
            continue
        for ln in txt.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^标题\s*[:：]\s*(.+)$", ln.strip())
            if m:
                out.append((d.name, m.group(1).strip()))
                break
    return out


def load_post_titles(root: Path) -> list[str]:
    out = []
    for f in sorted((root / "content" / "posts").glob("*.md")):
        fm: list[str] = []
        fence = ""  # +++ (TOML) 或 --- (YAML,极少数旧文)
        for ln in f.read_text(encoding="utf-8").splitlines():
            s = ln.strip()
            if s in ("+++", "---") and not fence:
                fence = s
                continue
            if s == fence and fm:
                break
            if fence:
                fm.append(ln)
        pats = [r"""^title\s*=\s*['"](.+)['"]$"""] if fence == "+++" \
            else [r"""^title\s*:\s*['"]?(.+?)['"]?$"""]
        for ln in fm:
            for pat in pats:
                m = re.match(pat, ln.strip())
                if m:
                    out.append(m.group(1))
                    break
    return out


def load_title_retention_pairs(root: Path) -> list[dict]:
    """反哺接口(预留,本期不实现):标题特征 × 完播/互动配对数据。

    数据成熟判据(实现前提):video-analytics 覆盖 ≥30 支已发视频且各平台互动分位稳定。
    届时实现:读 data/analytics/{metrics,retention}.json,按 7 项清单特征
    (score_title.py 的 CHECKS)逐视频打标 × 完播率/engagement 配对,
    输出「哪些标题要素在本账号真实拉动互动」,反哺:
      - account-dna.md 的 P75 共性块(从「样本不足」标注转为自动结论)
      - score_title.py 的清单权重(要素按实证排序,而非等权)
    """
    return []


def load_p75_videos(root: Path) -> tuple[list[str], float | None, str]:
    """互动 P75 以上的视频 slug 列表(取每支视频各平台 engagement_rate 最大值)。"""
    path = root / "data" / "analytics" / "metrics.json"
    if not path.is_file():
        return [], None, "metrics.json 不存在"
    data = json.loads(path.read_text(encoding="utf-8"))
    per_video: dict[str, float] = {}
    for slug, platforms in data.get("videos", {}).items():
        rates = [p.get("engagement_rate") for p in platforms.values()
                 if isinstance(p, dict) and p.get("engagement_rate") is not None]
        if rates:
            per_video[slug] = max(rates)
    if not per_video:
        return [], None, "metrics.json 无 engagement_rate 数据"
    vals = sorted(per_video.values())
    p75 = vals[max(0, int(len(vals) * 0.75) - 1)]  # 经验分位(最近秩)
    top = [slug for slug, r in per_video.items() if r >= p75]
    note = f"口径:每视频取各平台 engagement_rate 最大值,P75={p75:.4f},n={len(per_video)}"
    return top, p75, note


# ---- 统计 ----

PUNCTS = {"！": "感叹号", "？": "问号", "，": "逗号", "：": "冒号",
          "「」": "直角引号", "【】": "方头括号", "—": "破折号"}

STOP_BIGRAMS = {"的", "了", "是", "在", "我", "你", "它", "就", "都", "和", "一个",
                "什么", "怎么", "这个", "还是", "不是"}


def title_stats(titles: list[str]) -> dict:
    lens = [len(t) for t in titles]
    widths = [cjk_width(t) for t in titles]
    n = len(titles)
    stats: dict = {
        "n": n,
        "len_median": statistics.median(lens) if lens else 0,
        "width_median": statistics.median(widths) if widths else 0,
        "question_rate": sum(1 for t in titles if re.search(r"[？?]", t)) / n if n else 0,
        "number_rate": sum(1 for t in titles if re.search(r"\d", t)) / n if n else 0,
        "punct": {p: (sum(1 for t in titles if p[0] in t or (len(p) > 1 and p[1] in t)) / n if n else 0)
                  for p in PUNCTS},
    }
    # 高频词:拉丁 token + CJK bigram(滤停用词)
    latin = Counter()
    for t in titles:
        latin.update(w for w in re.findall(r"[A-Za-z][A-Za-z0-9.+#]{1,}", t))
    bigram = Counter()
    for t in titles:
        for run in re.findall(r"[\u4e00-\u9fff]{2,}", t):
            for i in range(len(run) - 1):
                bg = run[i:i + 2]
                if not any(s in bg for s in STOP_BIGRAMS):
                    bigram[bg] += 1
    stats["latin_top"] = latin.most_common(10)
    stats["bigram_top"] = [x for x in bigram.most_common(15) if x[1] >= 3][:10]
    return stats


def render(video_stats: dict, post_stats: dict, p75: list[str], p75_note: str,
           video_titles: list[tuple[str, str]]) -> str:
    today = date.today().isoformat()
    lines = [
        "# 账号标题 DNA(风格锚)",
        "",
        f"> 统计日期 {today} | 由 `scripts/account_dna.py --write` 生成,语料变化后重跑。",
        f"> 样本:视频 {video_stats['n']} 支(archive)/ 文章 {post_stats['n']} 篇(front matter)。",
        "",
    ]

    def block(name: str, s: dict) -> None:
        thin = " ⚠️ 样本不足(<30),仅供参考不作为硬约束" if s["n"] < MIN_SAMPLE else ""
        lines.append(f"## {name}(n={s['n']}){thin}")
        lines.append("")
        lines.append(f"- 中位长度 **{s['len_median']:.0f} 字**(CJK 当量宽 {s['width_median']:.0f})")
        lines.append(f"- 问句率 {s['question_rate']:.0%} / 数字率 {s['number_rate']:.0%}")
        lines.append("- 标点习惯: " + " ".join(
            f"{PUNCTS[p]} {r:.0%}" for p, r in s["punct"].items()))
        if s["latin_top"]:
            lines.append("- 高频实体: " + " ".join(f"`{w}`×{c}" for w, c in s["latin_top"][:6]))
        if s["bigram_top"]:
            lines.append("- 高频中文词: " + " ".join(f"{w}×{c}" for w, c in s["bigram_top"]))
        lines.append("")

    block("视频标题", video_stats)
    block("文章标题", post_stats)

    lines.append("## 互动 P75 以上视频的标题共性")
    lines.append("")
    if len(p75) < P75_MIN_VIDEOS:
        lines.append(f"⚠️ 样本不足:互动分位覆盖 {len(p75)} 支(<{P75_MIN_VIDEOS}),不做共性结论。"
                     f"{p75_note}")
    else:
        top_titles = [t for slug, t in video_titles if slug in p75]
        sub = title_stats(top_titles)
        lines.append(f"{p75_note};上榜 {len(top_titles)} 支:")
        lines.append("")
        lines.append(f"- 中位长度 {sub['len_median']:.0f} 字 / 问句率 {sub['question_rate']:.0%} / "
                     f"数字率 {sub['number_rate']:.0%}")
        if sub["latin_top"]:
            lines.append("- 实体: " + " ".join(f"`{w}`×{c}" for w, c in sub["latin_top"][:6]))
        for t in top_titles:
            lines.append(f"  - {t}")
    lines.append("")
    lines.append("## 使用方式")
    lines.append("")
    lines.append("候选生成时对齐:长度贴近中位±30%、问句/数字按题材选用(教程偏数字、"
                 "观点偏问句)、高频实体是本账号被记住的词。P75 共性数据成熟前,以人工判断为主。")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="账号标题 DNA 统计")
    ap.add_argument("--blog-root", default=str(DEFAULT_ROOT))
    ap.add_argument("--write", action="store_true", help="写入 references/account-dna.md")
    args = ap.parse_args()

    root = Path(args.blog_root)
    video_titles = load_video_titles(root)
    post_titles = load_post_titles(root)
    if not video_titles and not post_titles:
        print(f"❌ 语料为空,检查 --blog-root({root})")
        return 1

    video_stats = title_stats([t for _, t in video_titles])
    post_stats = title_stats(post_titles)
    p75, _, p75_note = load_p75_videos(root)
    md = render(video_stats, post_stats, p75, p75_note, video_titles)

    if args.write:
        out = Path(__file__).resolve().parent.parent / "references" / "account-dna.md"
        out.write_text(md, encoding="utf-8")
        print(f"✅ 已写入 {out}")
    else:
        sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
