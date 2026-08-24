"""多平台违禁词检查器：扫文件/目录，输出命中报告（只定位，不自动改）。

词库与 platform-compliance skill 的 references/word-list.md + platform-rules.md 同步（2026 时效）：
  通用层（四平台都查，广告法红线）：极限词/夸大宣传/引流硬词/权威冒用/金融承诺/迷信/医疗功效/时限促销
  平台层：douyin（诱导互动/欺骗文案）kuaishou（违规导流/刺激消费）
          xiaohongshu（超严引流/医疗功效扩展/焦虑营销/平台名导流）wechat（站外导流/金融严词）
  MEDIUM：语境敏感词（人工判断，技术比喻可留但审核不认语境）
  INFO：平台行为红线规则（AI 声明/主题黑名单/三品一械等），发布前确认

用法:
  python scripts/check_compliance.py --path file.md [--path file2.json ...] [--platform all|douyin|kuaishou|xiaohongshu|wechat]
  python scripts/check_compliance.py --dir some/dir
  python scripts/check_compliance.py --path x.md --json

返回码：目标平台的 HIGH 命中 1，否则 0（配合 Makefile 门禁）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PLATFORMS = ["douyin", "kuaishou", "xiaohongshu", "wechat"]
PLATFORM_NAMES = {"douyin": "抖音", "kuaishou": "快手", "xiaohongshu": "小红书", "wechat": "视频号"}

# ---------- 通用词库（四平台都查，HIGH） ----------

COMMON_HIGH: dict[str, list[str]] = {
    "①极限词-最字": ["全网最低", "最高档", "最先进", "最受欢迎", "最佳", "最好", "最具", "最赚", "最优"],
    "①极限词-第一唯一": ["全网第一", "销量第一", "行业第一", "中国第一", "独一无二", "仅此一家", "没有之一", "唯一", "无可替代"],
    "①极限词-级极顶": ["国家级", "世界级", "全球级", "宇宙级", "极品", "极致", "顶尖", "尖端", "终极", "顶级"],
    "①极限词-首国": ["全球首发", "全国首家", "首选", "首款", "独家", "首家"],
    "①极限词-其他": ["王牌", "销冠", "性价比之王", "绝无仅有", "史无前例", "巅峰", "至尊", "万能", "无敌", "绝对", "封神", "yyds", "绝绝子", "绝版", "断层领先", "遥遥领先"],
    "②夸大宣传": ["100%有效", "零风险", "无副作用", "特效", "速效", "强效", "一次见效", "1天见效", "7天见效", "彻底解决", "保证有效", "无效退款", "假一赔十"],
    "③引流硬词": ["微信", "手机号", "二维码", "扫码", "加V", "私信", "私我", "联系方式"],
    "④权威冒用": ["央视推荐", "官方指定", "专家认证", "质量免检", "无需质量检测", "国宴专用", "专供", "特供", "中国驰名商标"],
    "⑤金融承诺": ["躺赚", "稳赚", "保本", "高收益", "日入过千", "月入过万", "年入百万", "稳赚不赔", "保本保息", "零风险赚钱", "一本万利", "炒币", "数字货币"],
    "⑥迷信敏感": ["招财进宝", "旺财", "旺宅", "辟邪", "转运", "逢凶化吉", "化解小人", "增强第六感", "镇宅", "消灾", "提升运气"],
    "⑦医疗功效": ["治疗", "治愈", "根治", "消炎", "杀菌", "排毒", "增强免疫力", "防癌", "抗癌", "减肥", "瘦身", "溶脂", "祛疤", "生发", "壮阳", "祛湿", "改善睡眠"],
    "⑧时限促销": ["限时", "秒杀", "抢购", "抢爆", "万人疯抢", "手慢无", "闭眼入", "无脑买", "赶紧下单", "错过今天", "最后一波", "仅此一次", "仅限今日", "随时涨价", "随时结束", "再不抢就没了", "最后1天"],
}

# ---------- 平台层词库（HIGH） ----------

PLATFORM_HIGH: dict[str, dict[str, list[str]]] = {
    "douyin": {
        "③诱导互动": ["评论区扣", "扣1", "扣666", "关注我", "点赞关注"],
        "③欺骗文案": ["点击获取", "恭喜获奖", "全民免单", "领取奖品"],
    },
    "kuaishou": {
        "③违规导流": ["加V领福利", "私信要链接", "境外导流"],
        "③刺激消费": ["抢爆", "万人疯抢", "再不抢就没了"],
    },
    "xiaohongshu": {
        "③引流词(严)": ["VX", "V信", "扣扣", "抠抠", "加我", "私我", "微信小号", "跳转", "外链", "看主页", "完整版在", "更多内容请看其他平台"],
        "③平台名导流": ["淘宝", "天猫", "京东", "拼多多", "B站", "微博"],
        "⑦医疗功效(严)": ["诊断", "处方", "药到病除", "降血糖", "降血压", "抗菌", "消毒", "解毒", "吸脂", "燃脂", "减脂", "祛斑", "丰胸", "美白针", "溶脂针", "修复细胞", "脱敏"],
        "焦虑营销": ["容貌焦虑", "身材焦虑", "年龄焦虑"],
    },
    "wechat": {
        "③站外导流": ["引导加微信", "留联系方式", "脱离视频号场景", "外部交流或交易"],
        "⑤金融严词": ["荐股", "承诺收益", "稳赚翻倍", "实盘指导"],
    },
}

# ---------- 语境敏感词（MEDIUM，人工判断） ----------

MEDIUM_WORDS: dict[str, list[str]] = {
    "⑨天花板/封神/yyds": ["天花板", "封神", "yyds", "绝绝子"],
    "⑨教父/大师/专家": ["教父", "大师"],
    "⑨永久/绝对/无敌(术语?)": ["永久", "绝对", "无敌"],
}

_MOST_COMMERCIAL = re.compile(r"最(低|赚|优|新|实惠|高性价比|划算)")
_MOST_NEUTRAL = re.compile(r"最(直接|值得|优先|常用|简单|大|小|快|慢|常见|后|早|先|合适|适合|接近|相似|近)")

# ---------- INFO 规则（平台行为红线，非词） ----------

INFO_RULES: dict[str, list[str]] = {
    "通用": [
        "AI 生成声明：抖音/快手/小红书/视频号发布时都要标注 AI 生成（AI 占比>50% 需片头/封面/简介标注）",
        "结尾 CTA 中性化：不用「关注我/评论区扣XX/加V」，用中性价值钩子",
        "口播与画面不出现联系方式（QQ/微信/手机号/二维码/平台名跳转）",
        "封面文字会被 OCR：封面标题同样过一遍本检查",
        "标题 ≤ 平台字数限制，不堆砌极限词",
        "平台规则持续更新，以各平台官方规则中心为准",
    ],
    "douyin": ["主题黑名单：同主体累计 3 次中度违规，旗下所有账号同步限流"],
    "kuaishou": ["内容红线零容忍：赌博/色情/暴力，处罚分级：警告→功能限制→短期封禁→永久封禁"],
    "xiaohongshu": [
        "私信发微信严重违规直接封禁，没有申诉机会",
        "三品一械新规：保健品/药品/医疗器械/医疗服务，非资质账号禁止推广科普",
    ],
    "wechat": [
        "允许站内转化（关注视频号/公众号/企业微信），禁止站外导流",
        "财经/医疗/法律内容无资质不能讲；带货必须标注广告",
    ],
}

_FILE_EXTS = {".md", ".txt", ".json", ".py", ".html"}


_KV_LINE = re.compile(r"^[A-Za-z0-9_一-鿿]+[：:]\s*")


def _scan_text(text: str, source: str, platform: str, report: list[dict]) -> None:
    lines = text.splitlines()
    for lineno, line in enumerate(lines, 1):
        # 键值行(如 metadata.txt 的「标题_B站: …」)只扫值部分——键名是字段名不会发布，
        # 否则平台变体键名里的「B站」会被平台名导流规则误判(metadata-optimization 后的交叉盲区)
        kv = _KV_LINE.match(line)
        scan_part = line[kv.end():] if kv else line
        for cat, words in COMMON_HIGH.items():
            for w in words:
                if w in scan_part:
                    report.append({"级别": "HIGH", "平台": "通用", "类别": cat, "词": w, "位置": f"{source}:{lineno}", "行": line.strip()[:60]})
        if "最" in scan_part:
            if _MOST_COMMERCIAL.search(scan_part):
                report.append({"级别": "HIGH", "平台": "通用", "类别": "①极限词-最字", "词": "最+商业词", "位置": f"{source}:{lineno}", "行": line.strip()[:60]})
            elif _MOST_NEUTRAL.search(scan_part):
                report.append({"级别": "MEDIUM", "平台": "通用", "类别": "⑨最+技术词(人工判)", "词": "最+中性词", "位置": f"{source}:{lineno}", "行": line.strip()[:60]})
        for cat, words in MEDIUM_WORDS.items():
            for w in words:
                if w in scan_part:
                    report.append({"级别": "MEDIUM", "平台": "通用", "类别": cat, "词": w, "位置": f"{source}:{lineno}", "行": line.strip()[:60]})
        # 平台层：只扫目标平台（all = 全部平台都扫）
        for pf, pf_words in PLATFORM_HIGH.items():
            if platform not in ("all", pf):
                continue
            for cat, words in pf_words.items():
                for w in words:
                    if w in scan_part:
                        report.append({"级别": "HIGH", "平台": PLATFORM_NAMES[pf], "类别": cat, "词": w, "位置": f"{source}:{lineno}", "行": line.strip()[:60]})


def _print_report(report: list[dict], platform: str, as_json: bool) -> int:
    pf = PLATFORM_NAMES.get(platform, "全部平台")
    if as_json:
        print(json.dumps({"目标平台": pf, "HIGH": report, "INFO": INFO_RULES}, ensure_ascii=False, indent=2))
        return 1 if any(r["级别"] == "HIGH" for r in report) else 0

    high = [r for r in report if r["级别"] == "HIGH"]
    medium = [r for r in report if r["级别"] == "MEDIUM"]
    print(f"\n===== 违禁词检查报告（目标平台：{pf}）=====")
    if not report:
        print("✅ 无命中")
    if high:
        print(f"\n🔴 HIGH（必改，{len(high)} 处）")
        for r in high:
            print(f"  [{r['平台']}][{r['类别']}] 「{r['词']}」 {r['位置']}  {r['行']}")
    if medium:
        print(f"\n🟡 MEDIUM（人工判断，{len(medium)} 处）")
        for r in medium:
            print(f"  [{r['类别']}] 「{r['词']}」 {r['位置']}  {r['行']}")
    print("\n📋 INFO 发布前确认：")
    for rule in INFO_RULES.get("通用", []) + INFO_RULES.get(platform if platform != "all" else "douyin", []):
        print(f"  - {rule}")
    if high:
        print("\n❌ 门禁：存在 HIGH 命中，全部替换后复扫（替换建议见 references/word-list.md）")
    else:
        print("\n✅ 门禁：HIGH 归零，MEDIUM 已人工确认")
    return 1 if high else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="多平台违禁词检查")
    ap.add_argument("--path", action="append", help="目标文件（可多次）")
    ap.add_argument("--dir", help="目标目录（扫 .md/.txt/.json/.py/.html）")
    ap.add_argument("--platform", default="all", choices=["all"] + PLATFORMS, help="目标平台（默认 all）")
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
        _scan_text(text, str(f), args.platform, report)

    return _print_report(report, args.platform, args.json)


if __name__ == "__main__":
    sys.exit(main())
