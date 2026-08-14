"""抖音平台违规词检查器：扫文件/目录，输出命中报告（只定位，不自动改）。

词库与 douyin-compliance skill 的 references/word-list.md 保持一致（2026 时效）：
  ① 绝对化/极限词（广告法第九条）  ② 夸大宣传/虚假承诺  ③ 诱导引流/诱导消费
  ④ 权威冒用  ⑤ 金融收益承诺（一级违规封号）  ⑥ 迷信敏感
  ⑧ 语境敏感词（MEDIUM，人工判断，技术比喻可留但审核不认语境）
平台行为红线（⑦）不是词，输出为 INFO checklist，由发布前确认。

用法:
  python scripts/check_douyin_compliance.py --path file.md [--path file2.json ...]
  python scripts/check_douyin_compliance.py --dir some/dir        # 扫 .md/.txt/.json/.py
  python scripts/check_douyin_compliance.py --path x.md --json    # 机读输出

返回码：HIGH 命中 1，否则 0（配合 Makefile 门禁）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# ---------- 词库（与 references/word-list.md 同步） ----------

# HIGH：命中必改
HIGH_WORDS: dict[str, list[str]] = {
    "①极限词-最字": ["全网最低", "最高档", "最先进", "最受欢迎", "最佳", "最好", "最具", "最赚", "最优"],
    "①极限词-最单字": ["最"],  # 单字「最」命中率高，单独处理（技术语境 MEDIUM，见后）
    "①极限词-第一唯一": ["全网第一", "销量第一", "行业第一", "中国第一", "独一无二", "仅此一家", "没有之一", "唯一"],
    "①极限词-级极顶": ["国家级", "世界级", "全球级", "宇宙级", "极品", "极致", "顶尖", "尖端", "终极", "顶级"],
    "①极限词-首国": ["全球首发", "全国首家", "首选", "首款", "独家", "首家"],
    "①极限词-其他": ["王牌", "销冠", "性价比之王", "绝无仅有", "史无前例", "巅峰", "至尊", "万能", "无敌", "绝对", "封神", "yyds", "绝绝子", "绝版"],
    "②夸大宣传": ["100%有效", "零风险", "无副作用", "特效", "速效", "一次见效", "1天见效", "7天见效", "彻底解决", "根治", "治愈", "消炎", "杀菌", "排毒", "增强免疫力", "防癌", "抗癌", "减肥", "瘦身", "溶脂", "祛疤", "生发", "壮阳", "祛湿", "改善睡眠"],
    "③诱导引流": ["微信", "手机号", "二维码", "加V", "私信", "评论区扣", "扣1", "扣666", "关注我", "点赞关注", "点击获取", "恭喜获奖", "全民免单"],
    "③诱导消费": ["手慢无", "闭眼入", "无脑买", "赶紧下单", "错过今天", "最后一波", "仅此一次", "随时涨价", "限时清仓", "抢疯了", "再不抢就没了"],
    "④权威冒用": ["央视推荐", "官方指定", "专家认证", "质量免检", "无需质量检测", "国宴专用", "专供", "特供", "中国驰名商标"],
    "⑤金融承诺": ["躺赚", "稳赚", "保本", "高收益", "日入过千", "月入过万", "年入百万", "稳赚不赔", "保本保息", "零风险赚钱", "一本万利", "炒币", "数字货币"],
    "⑥迷信敏感": ["招财进宝", "旺财", "旺宅", "辟邪", "转运", "逢凶化吉", "化解小人", "增强第六感", "镇宅", "消灾"],
}

# MEDIUM：命中人工判断（技术语境比喻通常可留，审核不认语境，能换就换）
MEDIUM_WORDS: dict[str, list[str]] = {
    "⑧天花板/封神/yyds": ["天花板", "封神", "yyds", "绝绝子"],
    "⑧教父/大师/专家": ["教父", "大师"],
    "⑧永久/绝对/无敌(术语?)": ["永久", "绝对", "无敌"],
}

# 「最」字：独立判断——后面跟技术/中性词（直接、值得、优先、常用、简单、大、小）算 MEDIUM，
# 跟商业词（低、赚、优、新、高性价比）算 HIGH
_MOST_COMMERCIAL = re.compile(r"最(低|赚|优|新|实惠|高性价比|划算)")
_MOST_NEUTRAL = re.compile(r"最(直接|值得|优先|常用|简单|大|小|快|慢|常见|常用|后|早|先|合适|适合|接近|相似|接近|常用|近)")

# 平台行为红线（INFO 规则，非词）
INFO_RULES: list[str] = [
    "AI 生成声明：抖音发布时勾选 AI 生成声明（AI 占比>50% 需片头/封面/简介标注）",
    "结尾 CTA 中性化：不用「关注我/评论区扣XX」，用中性价值钩子",
    "口播与画面不出现联系方式（QQ/微信/手机号/二维码）",
    "封面文字会被 OCR：封面标题同样过一遍本检查",
    "标题 ≤ 平台字数限制，不堆砌极限词",
    "平台规则以官方规则中心为准，词库只是快检",
]

_FILE_EXTS = {".md", ".txt", ".json", ".py", ".html"}


def _scan_text(text: str, source: str, report: list[dict]) -> None:
    lines = text.splitlines()
    for lineno, line in enumerate(lines, 1):
        # HIGH 词（先多字词再单字「最」，避免「最」重复命中）
        for cat, words in HIGH_WORDS.items():
            for w in words:
                if w == "最":
                    continue  # 单字「最」单独处理
                if w in line:
                    report.append({"级别": "HIGH", "类别": cat, "词": w, "位置": f"{source}:{lineno}", "行": line.strip()[:60]})
        # 单字「最」
        if "最" in line:
            if _MOST_COMMERCIAL.search(line):
                report.append({"级别": "HIGH", "类别": "①极限词-最字", "词": "最+商业词", "位置": f"{source}:{lineno}", "行": line.strip()[:60]})
            elif _MOST_NEUTRAL.search(line):
                report.append({"级别": "MEDIUM", "类别": "⑧最+技术词(人工判)", "词": "最+中性词", "位置": f"{source}:{lineno}", "行": line.strip()[:60]})
        # MEDIUM 词
        for cat, words in MEDIUM_WORDS.items():
            for w in words:
                if w in line:
                    report.append({"级别": "MEDIUM", "类别": cat, "词": w, "位置": f"{source}:{lineno}", "行": line.strip()[:60]})


def _print_report(report: list[dict], as_json: bool) -> int:
    high = [r for r in report if r["级别"] == "HIGH"]
    medium = [r for r in report if r["级别"] == "MEDIUM"]
    if as_json:
        print(json.dumps({"HIGH": high, "MEDIUM": medium, "INFO": INFO_RULES}, ensure_ascii=False, indent=2))
        return 1 if high else 0
    print("\n===== 抖音违规词检查报告 =====")
    if not report:
        print("✅ 无命中")
    if high:
        print(f"\n🔴 HIGH（必改，{len(high)} 处）")
        for r in high:
            print(f"  [{r['类别']}] 「{r['词']}」 {r['位置']}  {r['行']}")
    if medium:
        print(f"\n🟡 MEDIUM（人工判断，{len(medium)} 处）")
        for r in medium:
            print(f"  [{r['类别']}] 「{r['词']}」 {r['位置']}  {r['行']}")
    print("\n📋 INFO 发布前确认：")
    for rule in INFO_RULES:
        print(f"  - {rule}")
    if high:
        print("\n❌ 门禁：存在 HIGH 命中，全部替换后复扫（替换建议见 references/word-list.md）")
    else:
        print("\n✅ 门禁：HIGH 归零，MEDIUM 已人工确认")
    return 1 if high else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="抖音平台违规词检查")
    ap.add_argument("--path", action="append", help="目标文件（可多次）")
    ap.add_argument("--dir", help="目标目录（扫 .md/.txt/.json/.py/.html）")
    ap.add_argument("--json", action="store_true", help="机读输出")
    args = ap.parse_args()

    targets: list[Path] = []
    for p in args.path or []:
        targets.append(Path(p))
    if args.dir:
        for f in sorted(Path(args.dir).rglob("*")):
            if f.is_file() and f.suffix in _FILE_EXTS:
                targets.append(f)
    if not targets:
        print("❌ 没有输入：--path 或 --dir 至少一个", file=sys.stderr)
        return 2

    report: list[dict] = []
    for f in targets:
        if not f.exists():
            print(f"⚠️ 跳过（不存在）: {f}", file=sys.stderr)
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = f.read_text(encoding="utf-8", errors="ignore")
        _scan_text(text, str(f), report)

    return _print_report(report, args.json)


if __name__ == "__main__":
    sys.exit(main())
