#!/usr/bin/env python3
"""标题候选 7 项清单打分(qiaomu xinzhiyuan-title 方法,脚本化可确定性部分)。

7 项:可识别实体/真实数字/清晰动词/后果人群/标点转折/权威钩子/概念包装。
满足 >=4 合格。脚本只判「要素在场」;要素是否真实由 banned-words.md 事实边界
在 fact card 环节人工核(数字在场 ≠ 数字真实)。

自包含:不 import blog-src;平台上限表内嵌(与 blog-src scripts/pub/config.py
title_max 同步,改动两处一起)。长度口径:len() 对齐 crop_title 裁剪行为。

用法:
    python score_title.py "标题一" "标题二" [--platform douyin,bilibili]
    python score_title.py --file candidates.txt
    python score_title.py --selftest
"""
from __future__ import annotations

import argparse
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

# 平台上限(len 口径;同步源 blog-src scripts/pub/config.py)
TITLE_MAX = {"douyin": 30, "kuaishou": 50, "xiaohongshu": 20,
             "shipinhao": 63, "weixin": 64, "bilibili": 80}

VERBS = ("安装", "装", "配置", "部署", "上线", "写", "剪", "生成", "拆解", "读懂",
         "看懂", "看完", "上手", "学会", "搞懂", "避开", "避坑", "排坑", "实测",
         "对比", "评测", "迁移", "修复", "自动化", "省", "翻", "让", "替代",
         "接入", "打通", "重构", "调试", "定位", "排查", "弃用", "停用")

CHECKS: list[tuple[str, str, re.Pattern]] = [
    ("可识别实体", "专有名词在场(工具/人名/项目名)",
     re.compile(r"[A-Z][A-Za-z0-9.+#]{1,}")),
    ("真实数字", "含数字(fact card 核过的才算真)",
     re.compile(r"\d")),
    ("清晰动词", "有具体动作词",
     re.compile("|".join(map(re.escape, sorted(VERBS, key=len, reverse=True))))),
    ("后果人群", "第二人称/人群/损失厌恶词",
     re.compile(r"你|程序员|开发者|前端|后端|团队|新手|小白|别再|浪费|踩坑|省")),
    ("标点转折", "问句/冒号/破折号/转折字",
     re.compile(r"[？?]|：|——|却|但|才")),
    ("权威钩子", "Star/开源/官方/作者级背书",
     re.compile(r"[Ss]tar|开源|官方|作者|GitHub|教父|之父|万[行位字条]|原创", re.IGNORECASE)),
    ("概念包装", "「」/【】概念词",
     re.compile(r"「|」|【|】")),
]


def cjk_width(text: str) -> float:
    """CJK 当量宽:CJK=1 / ASCII=0.6 / 空格=0.3(与封面管线口径一致)。"""
    w = 0.0
    for ch in text:
        if ch.isspace():
            w += 0.3
        elif ord(ch) > 0x2E80:
            w += 1.0
        else:
            w += 0.6
    return w


def score_one(title: str) -> tuple[int, list[tuple[str, bool]]]:
    """返回 (满足数, [(项名, 是否命中)])。"""
    results = [(name, bool(pat.search(title))) for name, _, pat in CHECKS]
    return sum(1 for _, hit in results if hit), results


def report(title: str, platforms: list[str]) -> None:
    n, results = score_one(title)
    marks = " ".join(f"{'✓' if hit else '✗'}{name}" for name, hit in results)
    verdict = "✅ 合格" if n >= 4 else "❌ 不合格"
    print(f"「{title}」")
    print(f"  得分 {n}/7 {verdict} | {marks}")
    width = cjk_width(title)
    print(f"  len={len(title)} 当量宽={width:.0f}", end="")
    for p in platforms:
        if p in TITLE_MAX:
            flag = "🔴超限" if len(title) > TITLE_MAX[p] else "🟢"
            print(f" | {p}≤{TITLE_MAX[p]} {flag}", end="")
    print()
    if n < 4:
        missing = [d for (name, hit), (_, d, _) in zip(results, CHECKS) if not hit]
        print(f"  ↳ 缺要素: {('; '.join(missing[:3]))}——按这些方向补,别换新话题")
    print()


def selftest() -> int:
    """任务 2.3 验收标准:正例 >=4,反例 <4。"""
    good = "装完 Codex 只会写代码？6 个 skill 让它自动剪视频"
    bad = "Claude Code 使用教程"
    n_good, _ = score_one(good)
    n_bad, _ = score_one(bad)
    ok_good, ok_bad = n_good >= 4, n_bad < 4
    print(f"{'✅' if ok_good else '❌'} 正例 {n_good}/7 (期望 >=4): {good}")
    print(f"{'✅' if ok_bad else '❌'} 反例 {n_bad}/7 (期望 <4): {bad}")
    all_ok = ok_good and ok_bad
    print(f"selftest {'✅ 全过' if all_ok else '❌ 有失败'}")
    return 0 if all_ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="标题候选 7 项清单打分")
    ap.add_argument("titles", nargs="*", help="候选标题(引号包裹)")
    ap.add_argument("--file", help="从文件读,一行一个候选")
    ap.add_argument("--platform", default=None, help="逗号分隔平台 key,附长度检查")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    titles = list(args.titles)
    if args.file:
        from pathlib import Path
        titles += [ln.strip() for ln in Path(args.file).read_text(encoding="utf-8").splitlines()
                   if ln.strip() and not ln.startswith("#")]
    if not titles:
        ap.error("至少给一个候选(位置参数 / --file)")

    platforms = [p.strip() for p in args.platform.split(",")] if args.platform else []
    for t in titles:
        report(t, platforms)
    return 0


if __name__ == "__main__":
    sys.exit(main())
