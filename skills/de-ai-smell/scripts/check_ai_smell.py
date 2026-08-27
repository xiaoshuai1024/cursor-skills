"""去 AI 味检查器:扫 content/ 或指定 md,输出命中点(只定位,不自动改)。

词表与 de-ai-smell skill 的 references/ai-smell-word-list.md 保持一致,
含 2026-08-03 用户定规的 L1 无例外词:兜底 / 铁证 / 说白了 / 先说 / 根子 / 扎眼,
含 2026-08-26 用户定规升 L1:PPT 名词(赋能/闭环/抓手/打通/对齐/拉通/洞察/沉淀/底层逻辑等)、
口头禅(一句话/一件事/踩一遍/踩坑)、值得注意/我的判断是/恰恰(业务术语与引用语境不豁免)、
「A，而不是 B」形态并入不是A而是B句型(一律改直陈)。
含 2026-08-27 用户定规:记账类比(X的账/这笔账/算账/算总账)升 L1——字面义(账单/账号/账户/
分账/结算账期/账务)负向排除不误报。

用法:
  python scripts/check_ai_smell.py                          # 全站 content/
  python scripts/check_ai_smell.py --path content/posts/xxx.md   # 单篇
  python scripts/check_ai_smell.py --limit 200              # 只输出前 200 行

风格附加检查(只提示不阻断):破折号 >2、冒号密度过高、句长离散度(burstiness)、
连续相似句、对称章节结构(三项量化均为 ⊙ 提示,实验性待校准);
中文句法层(2026-08-26):的链≥3 / 虚动词 / 预判冒号,⊙ 句法提示,跳过代码围栏。
返回码:L1 词表命中 1,否则 0(L2 / 风格 / 量化 / 句法均只提示不阻断,便于 Makefile 门禁)。
"""
from __future__ import annotations

import re
import statistics
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

def _find_root():
    """从脚本向上找项目根，适配任意安装深度。

    不能直接 Path.resolve():.agents/skills 在本机是 junction,resolve 跳到物理路径
    (D:\\codes\\skills\\...) 后向上找不到 blog-src,全站扫描静默变成扫空目录、
    门禁永远绿灯(2026-08-26 实测修复)。依次尝试:未解析路径 / 解析后路径 / cwd,
    命中 hugo.toml 或 (.git + content) 的目录才算项目根。
    """
    def _is_root(p: Path) -> bool:
        return (p / "hugo.toml").exists() or (
            (p / ".git").exists() and (p / "content").is_dir()
        )

    for start in (Path(__file__).parent, Path(__file__).resolve().parent, Path.cwd()):
        p = start
        while p != p.parent:
            if _is_root(p):
                return p
            p = p.parent
    return Path.cwd()  # fallback

ROOT = _find_root()

# 命中即提示人工判断。误报三来源(front matter tags、反讽/引用语境、业务术语合理用法)
# 脚本跳过 front matter;反讽/术语靠人工裁,不为去味破坏内容。
PATTERNS: dict[str, re.Pattern] = {
    "补丁段标题": re.compile(r"^##\s*[^\n]*(回到本质|本质是|核心是)[^\n]*"),
    "我的判断是": re.compile(r"我的判断(是|很直接|[，,])"),
    "口语套话(说白了/先说/根子/扎眼)": re.compile(r"说白了|(?<!事)先说|根子|扎眼"),
    "口语开场(先泼盆冷水)": re.compile(r"先泼盆冷水"),
    "值得注意/一提": re.compile(r"值得(注意|一提)"),
    "不难发现/毋庸置疑/众所周知": re.compile(r"不难发现|毋庸置疑|众所周知"),
    "核心在于": re.compile(r"核心在于"),
    "终极": re.compile(r"终极(?!服)"),
    "恰恰": re.compile(r"恰恰"),
    "护城河/分水岭/定时炸弹": re.compile(r"护城河|分水岭|定时炸弹"),
    "空洞强调(至关重要/不可或缺/意义深远)": re.compile(r"至关重要|不可或缺|意义深远"),
    "真正的(需人工判)": re.compile(r"真正的(?!需求|问题|瓶颈|价值|难点|痛点|实力|区别|用武之地|意思|挑战|门槛|文件|python)"),
    "PPT名词(L1无例外,2026-08-26定规)": re.compile(r"赋能|闭环|抓手|打通|对齐|拉通|洞察|沉淀|底层逻辑|全生命周期|降本增效|技术底座"),
    "套话开场": re.compile(r"综上所述|在.{2,15}的今天|随着.{2,15}的发展|在当今.{0,12}时代"),
    "不是A而是B(AI句型)": re.compile(r"不是.{2,18}而是|而不是"),
    "对仗(单个可留)": re.compile(r"不只是.{2,20}更是|既.{2,15}又.{2,15}|一方面.{2,30}另一方面"),
    "AI味收尾": re.compile(r"以上就是|希望对你有帮助|你学会了吗"),
    "AI网络词(兜底/铁证)": re.compile(r"兜底|铁证"),
    # 2026-08-26 定规:口头禅从 L2 升 L1(引用语境也不豁免,新稿引用改转述)
    "口头禅(一句话/一件事/踩一遍)": re.compile(r"一句话|一件事|踩一遍|踩坑"),
    # 2026-08-27 定规:记账类比升 L1(「时间的账要拆开」「这笔账划得来」「算总账」类比喻全禁)。
    # 负向排除字面义:账单/账号/账户/账期/账务(「把自己的账单拆到每一轮」「结算账户」是实事,不是比喻);
    # (?<!对) 排除「对账」(数据/支付对账是术语,「重算+对账」「各自结算各自对账」不算比喻)。
    "记账类比(X的账/这笔账/算账)": re.compile(
        r"的[账帐](?![单号户期务])|[这两三四五六七八九十几]笔[账帐](?![单号户期务])"
        r"|算[^，。；！？、]{0,6}(?<!对)[账帐](?![单号户期务])"
    ),
}

# 多形态正则命中词不固定(「的账」「算一笔总账」…),SUGGEST 按词取不到时按标签给提示
LABEL_TIPS = {
    "记账类比(X的账/这笔账/算账)": (
        "删记账比喻直说:「时间的账要拆开」→「时间分两块看」;"
        "「这笔账划算」→「值得」;字面义(账单/账号/账户/分账/对账)不受限"
    ),
}

# L2 高危慎用词:命中只提示、不阻断门禁(2026-08-04 新增)。
# 这些词确有实质含义(本质/真相/澄清),AI 味在于被用来铺垫升华/戏剧化,
# 由人工判断"说人话 vs 装腔",确有实质才留。
# 2026-08-26 定规:一句话/一件事/踩一遍/踩坑 升 L1(移入上方 PATTERNS),本层不再含。
L2_PATTERNS: dict[str, re.Pattern] = {
    "L2慎用(本质/澄清/真相/撕开)": re.compile(r"本质|澄清|真相|撕开"),
}
L2_SUGGEST = {
    "本质": "名词(问题的本质)可留;副词「本质上…」改「原理」",
    "澄清": "动词(澄清事实)可留;铺垫「需要澄清的是」删",
    "真相": "名词(事件真相)可留;戏剧化「真相是…/揭开真相」删",
    "撕开": "戏剧化煽情(撕开真相/面具),换具体动作",
    "一件事": "「一件事/一件小事」太笼统,换成具体所指(一次变更/一个目标/一个功能)",
    "一句话": "「一句话说清/总结」是 AI 口头禅,直接说,或改「核心分工是」",
    "踩一遍": "「踩一遍/踩坑」AI 味,换「重新走一遍/再犯一次/从头再来」",
}

# 命中词 → 建议替换(与 ai-smell-word-list.md 一致)
SUGGEST = {
    "兜底": "换「回退/降级/防线/把关/拦下来」;「兜底页」→「降级页」",
    "而不是": "改直陈:「用 A 而不是 B」→「用 A」(B 需要对比就另起一句正面说);2026-08-26 定规同「不是A而是B」",
    "一句话": "直接说内容,或改「核心分工是」;引 skill 描述改转述(2026-08-26 升 L1)",
    "一件事": "换具体所指:一次变更/一个目标/一个功能(2026-08-26 升 L1)",
    "踩坑": "换「重新走一遍/再犯一次」(2026-08-26 升 L1)",
    "铁证": "换「实测/日志为证/数据摆在面前」",
    "说白了": "删掉,直接说结论",
    "先泼盆冷水": "删掉,直接进正题",
    "先说": "「先说结论」→ 直接甩结论",
    "根子": "换「原因/根本/源头」",
    "扎眼": "换「显眼/突兀/一眼看出」",
    "赋能": "换具体动作「帮X做成什么」",
    "闭环": "描述具体回路才留,泛指删",
    "抓手": "换「具体手段/方法」",
    "打通": "换「连上/对接」",
    "拉通": "换「协调」或删",
    "洞察": "换「发现/结论」",
    "沉淀": "换「攒下来/积累」(具体宾语才留)",
    "至关重要": "换具体影响",
    "不可或缺": "没有它会怎样",
    "意义深远": "换具体收益",
}

DASH_RE = re.compile(r"——")
COLON_RE = re.compile(r"[：:]")
DASH_LIMIT = 2
COLON_RATIO = 0.015  # 每字符冒号占比超此值提示(约千字 15 个冒号)

# 中文句法层(翻译腔)机械检测(⊙ 提示,不阻断门禁;2026-08-26 新增,
# 源 novel ai-smell-checklist 检测项 10 取舍,openspec wechat-article-retention)。
# 其余句法项(之一/是…的/介词堆砌/代词复指/物理动词)误报不可控,只进词表人工判。
# 扫描跳过代码围栏内的行(技术文代码注释里「进行 x」属合理表达)。
# 校准记录(2026-08-26,全站 98 篇实测):
#   预判冒号 6 处全为真命中;虚动词收 (?![中不]) 后 5 处全为真命中(集中在早期文章);
#   的链按「段内 ≥3 个的」56 处约九成误报,加功能词排除+破折号分段后 0 命中——
#   现站已无真定语链,该检测主要防新稿。均为 ⊙ 提示,人工判断,不阻断门禁。
SYNTAX_PATTERNS: dict[str, re.Pattern] = {
    # (?![中不]):排除「进行中」(进行态)与「进行不下去」(进行作实义动词),非虚动词
    "虚动词(进行/作出/加以+动词)": re.compile(
        r"(进行|作出|加以)(?![中不])(了|过)?[\u4e00-\u9fff]{2,4}(?![\u4e00-\u9fff])"
    ),
    "预判冒号(结论很明确：)": re.compile(
        r"(结论|原因|逻辑|答案|关键)(很)?(明确|简单|清晰|直白)[：:]"
    ),
}
SYNTAX_SUGGEST = {
    "的链≥3": "定语链拆句或冒号列举:「基于规则驱动的可扩展的轻量的框架」→「校验框架:规则驱动、可扩展、轻量」",
    "虚动词(进行/作出/加以+动词)": "删虚动词直接用动词:「进行优化」→「优化」,「作出贡献」→「贡献了」",
    "预判冒号(结论很明确：)": "删预判短语,冒号后内容直接成句(判断是读者的事)",
}
# 的链是「的…的…的」链式定语(的之间隔着词,不是连续的的的),正则难精确,
# 按逗号/句号分段计数 + 功能词排除。校准记录(2026-08-26,全站 98 篇实测):
#   仅按「段内 ≥3 个的」计,56 处命中样例约九成误报(「好的环境让正确的行为成为
#   最自然的选择」是正常 prose——的属于不同小句);链内(首末的之间)出现
#   让/成为/是/了等功能词即排除后,命中降到个位数且均为真定语链。仍 ⊙ 人工判。
SEGMENT_SPLIT = re.compile(r"[，。；：、！？,;:!?（）()\[\]【】\s——-]+")
DE_CHAIN_MIN = 3  # 单段「的」数达到此值提示
DE_CHAIN_SEG_LEN = 8  # 段长度低于此值不提示(「我的他的」这类短段不报)
DE_CHAIN_FUNC = set("让使成为意味着把被和与或而且是了在有过就也都还说到给能要不会对从中当为")


def de_chain_segments(line: str) -> list[str]:
    """返回一行中「的」密度过高的分段(链式定语)。

    排除「的」分属不同小句的正常 prose:首末「的」之间出现功能词
    (让/成为/是/了…)说明中间有谓语,不是纯定语堆叠,跳过。
    """
    result = []
    for seg in SEGMENT_SPLIT.split(line):
        if len(seg) < DE_CHAIN_SEG_LEN or seg.count("的") < DE_CHAIN_MIN:
            continue
        first = seg.find("的")
        last = seg.rfind("的")
        if not (DE_CHAIN_FUNC & set(seg[first:last])):
            result.append(seg)
    return result

# 量化检测(⊙ 提示,不阻断门禁;实验性)
# 校准记录(2026-08-04,全站 79 篇实测):
#   burstiness 中文句长离散度天然高(min0.64/中位1.12/max2.95),英文经验值0.3完全失配;
#   0.7 抓全站最均匀的 ~3 篇 + 未来新稿极端均匀。对已去味文章区分度有限,主要价值在写新稿时实时检测。
#   连续相似句中文天然偏多,≥4句±20% 约 47/79 命中(多处命中才需重点关注);对称结构 7/79 区分度好。
SENT_END = re.compile(r"[。！？]")  # 句末标点切句(逗号是句内停顿不切)
BURSTINESS_FLOOR = 0.7  # 句长离散度(总体标准差/均值)低于此值提示句长过匀;中文适配值(见上校准记录)
SIMILAR_TOL = 0.20  # 相邻句字符数差占较大者比例 ≤ 此值视为相似
SIMILAR_RUN = 4  # 连续相似句达到此数提示(3 句对中文太松,曾近全站命中)
SYMMETRIC_RUN = 3  # 连续二级标题段落数相同达到此数提示


def sentence_lengths(body: str) -> list[int]:
    """按句末标点 [。！？] 切句,返回每句字符数。
    剔除标题/代码围栏/空行等 markdown 结构,只算正文(否则标题污染句长)。"""
    result: list[int] = []
    for p in SENT_END.split(body):
        kept = []
        for ln in p.splitlines():
            s = ln.strip()
            if not s or s.startswith("#") or s.startswith("```"):
                continue
            if s[:2] in ("- ", "* ", "+ "):  # 剥离列表标记
                s = s[2:]
            kept.append(s)
        text = "".join(kept)
        if text:
            result.append(len(text))
    return result


def burstiness(lengths: list[int]) -> float | None:
    """句长离散度 = 总体标准差 / 均值。句数 <3 返回 None(样本不足)。"""
    if len(lengths) < 3:
        return None
    mean = statistics.mean(lengths)
    if mean == 0:
        return None
    return statistics.pstdev(lengths) / mean


def similar_runs(lengths: list[int], tol: float, run: int) -> list[list[int]]:
    """连续相似句区间:相邻句字符数差 / max(较大者,1) ≤ tol,连续 ≥ run 句。"""
    result: list[list[int]] = []
    i = 0
    while i < len(lengths):
        j = i
        while j + 1 < len(lengths):
            a, b = lengths[j], lengths[j + 1]
            if abs(a - b) / max(a, b, 1) <= tol:
                j += 1
            else:
                break
        if j - i + 1 >= run:
            result.append(lengths[i : j + 1])
        i = j + 1 if j > i else i + 1
    return result


def symmetric_sections(lines: list[str], run: int) -> list[list[str]]:
    """连续 run+ 个二级标题(## )下段落数完全相同的区间。返回标题列表。"""
    h2 = [i for i, l in enumerate(lines) if l.startswith("## ") and not l.startswith("### ")]
    if len(h2) < run:
        return []
    paras: list[tuple[str, int]] = []
    for idx, start in enumerate(h2):
        end = h2[idx + 1] if idx + 1 < len(h2) else len(lines)
        n = 0
        prev_blank = True
        for l in lines[start + 1 : end]:
            if not l.strip():
                prev_blank = True
            elif prev_blank:
                n += 1
                prev_blank = False
        paras.append((lines[start].strip(), n))
    result: list[list[str]] = []
    i = 0
    while i < len(paras):
        j = i
        while j + 1 < len(paras) and paras[j + 1][1] == paras[i][1] and paras[i][1] > 0:
            j += 1
        if j - i + 1 >= run:
            result.append([t for t, _ in paras[i : j + 1]])
        i = j + 1 if j > i else i + 1
    return result


def is_frontmatter(line: str) -> bool:
    """front matter 区段标记(TOML:以 +++ 开头的行)。"""
    return line.strip() == "+++"


def scan_file(md_path: Path, limit: int, hits: list[str]) -> int:
    """扫单个 md,命中行写入 hits。返回词表命中数。"""
    text = md_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    in_fm = False
    in_code = False
    count = 0
    for lineno, line in enumerate(lines, 1):
        if is_frontmatter(line):
            in_fm = not in_fm
            continue
        if in_fm:
            continue
        # 句法检测跳过代码围栏(词表检测沿用旧行为不跳,避免改变既有命中语义)
        if line.lstrip().startswith("```"):
            in_code = not in_code
            continue
        if not in_code:
            for seg in de_chain_segments(line):
                hits.append(
                    f"⊙ 句法 {md_path} :{lineno}  [的链≥3] 「{seg[:32]}」  {line.strip()[:48]}  → {SYNTAX_SUGGEST['的链≥3']}"
                )
            for label, pat in SYNTAX_PATTERNS.items():
                m = pat.search(line)
                if m:
                    tip = SYNTAX_SUGGEST.get(label, "")
                    hits.append(
                        f"⊙ 句法 {md_path} :{lineno}  [{label}] 「{m.group(0)}」  {line.strip()[:48]}{('  → ' + tip) if tip else ''}"
                    )
        matched_l1 = False
        for label, pat in PATTERNS.items():
            m = pat.search(line)
            if m:
                word = m.group(0)
                tip = SUGGEST.get(word) or LABEL_TIPS.get(label, "")
                hits.append(
                    f"{md_path} :{lineno}  [{label}] 「{word}」  {line.strip()[:48]}{('  → ' + tip) if tip else ''}"
                )
                count += 1
                matched_l1 = True
                break
        if not matched_l1:  # L1 没命中才扫 L2 慎用词(避免一行报两次)
            for label, pat in L2_PATTERNS.items():
                m = pat.search(line)
                if m:
                    word = m.group(0)
                    tip = L2_SUGGEST.get(word, "")
                    hits.append(
                        f"⊙ {md_path} :{lineno}  [{label}] 「{word}」  {line.strip()[:48]}{('  → ' + tip) if tip else ''}"
                    )
                    break
        if len(hits) >= limit:
            break

    # 风格附加检查(只提示,不影响退出码)
    body = "\n".join(l for l in lines if not is_frontmatter(l))
    dash_n = len(DASH_RE.findall(body))
    if dash_n > DASH_LIMIT:
        hits.append(f"⚠ 风格 {md_path}  破折号 —— 共 {dash_n} 处(> {DASH_LIMIT} 提示;理想 0)")
    colon_n = len(COLON_RE.findall(body))
    colon_ratio = colon_n / max(len(body), 1)
    if colon_ratio > COLON_RATIO:
        hits.append(f"⚠ 风格 {md_path}  冒号密度 {colon_ratio:.1%}({colon_n} 个),疑似连续「X：Y」滥用,重写为自然句")

    # 量化检测(⊙ 提示,不阻断门禁;实验性待校准)
    lengths = sentence_lengths(body)
    b = burstiness(lengths)
    if b is not None and b < BURSTINESS_FLOOR:
        hits.append(f"⊙ 量化 {md_path}  句长离散度 {b:.2f}(< {BURSTINESS_FLOOR},句长过匀,疑似统一抛光;实验性)")
    runs = similar_runs(lengths, SIMILAR_TOL, SIMILAR_RUN)
    if runs:
        hits.append(f"⊙ 量化 {md_path}  连续相似长度句 {len(runs)} 处(相邻句 ±{int(SIMILAR_TOL*100)}% 内 ≥{SIMILAR_RUN} 句);实验性")
    syms = symmetric_sections(lines, SYMMETRIC_RUN)
    if syms:
        hits.append(f"⊙ 量化 {md_path}  章节结构对称 {len(syms)} 处(连续 ## 标题段落数相同,疑似流水线标准件);实验性")
    return count


def has_word_hits(hits: list[str]) -> bool:
    """L1 词表命中(⚠ 风格、⊙ L2慎用 都不算)——决定退出码。L2 只提示不阻断。"""
    return any(not (h.startswith("⚠ ") or h.startswith("⊙ ")) for h in hits)


def main(argv: list[str]) -> int:
    target = ROOT / "content"
    limit = 10**9
    args = iter(argv)
    for arg in args:
        if arg == "--path":
            target = ROOT / next(args)
        elif arg == "--limit":
            limit = int(next(args))
        elif arg in ("-h", "--help"):
            print(__doc__)
            return 0

    if target.is_file():
        files = [target]
    else:
        files = sorted(target.rglob("*.md"))

    hits: list[str] = []
    total = 0
    for f in files:
        total += scan_file(f, limit, hits)

    for h in hits:
        print(h)
    if has_word_hits(hits):
        print(f"\n共 {total} 处 L1 词表命中 + 风格/L2 提示(仅定位,需人工判断后手动改)。词表:de-ai-smell skill。")
        return 1
    if hits:
        print("\n仅风格 / 量化 / L2 提示(无 L1 词表命中),均不阻断门禁。")
        return 0
    print("✅ 无命中。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
