# -*- coding: utf-8 -*-
"""文章机检门禁（article-quality-check skill）

九项 ERROR + 三项 WARN，口径见 openspec/changes/article-quality-gate/design.md。
输出格式对齐 check-ai-smell（路径:行号 [标签]）；有 ERROR 时退出码 1。
用法：py -3.11 check_article.py --slug <slug>   （在 blog-src 仓根执行）
"""
import argparse
import os
import re
import sys

ERRORS = []
WARNS = []


def err(line, tag, msg):
    ERRORS.append(f"  [{tag}] {msg}" if line is None else f"  :{line}  [{tag}] {msg}")


def warn(line, tag, msg):
    WARNS.append(f"  [{tag}] {msg}" if line is None else f"  :{line}  [{tag}] {msg}")


def cn_len(s):
    """段落数按中文字符+英文单词近似，用于行数折算。"""
    cn = len(re.findall(r"[\u4e00-\u9fff]", s))
    en = len(re.findall(r"[A-Za-z0-9]+", s))
    return cn + en // 2  # 英文两个词约一个汉字宽


def iter_paragraphs(body_lines):
    """产出 (起始行号, 文本)：排除代码/表格/列表/图片/标题/引用的正文段落块。"""
    para, start = [], None
    in_fence = False
    for i, raw in enumerate(body_lines, 1):
        line = raw.rstrip("\n")
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            if para:
                yield start, "\n".join(para)
                para, start = [], None
            continue
        if in_fence:
            continue
        if stripped.startswith(("|", "-", "*", ">", "#", "<img", "1.", "2.", "3.", "4.", "5.")):
            if para:
                yield start, "\n".join(para)
                para, start = [], None
            continue
        if not stripped:
            if para:
                yield start, "\n".join(para)
                para, start = [], None
            continue
        if start is None:
            start = i
        para.append(stripped)
    if para:
        yield start, "\n".join(para)


def run_wechat_checks(text, fm, body, cn, args):
    """H 组：公众号适配机检（规则权威 = wechat-retention.md，此处只做可自动化子集）。"""
    label = os.path.join("content", "posts", f"{args.slug}.md")
    print(f"\n📲 公众号适配检查（--wechat，权威 wechat-retention.md）｜正文 {cn} 字")

    def werr(tag, msg):
        err(None, tag, msg)

    def wwarn(tag, msg):
        warn(None, tag, msg)

    def fm_field(name):
        m = re.search(rf"^{name}\s*=\s*['\"](.*?)['\"]", fm, re.M)
        return m.group(1) if m else None

    title = fm_field("title") or ""
    wtitle = fm_field("wechat_title")
    wdigest = fm_field("wechat_digest")
    digest = wdigest or fm_field("description") or ""

    # 1. 转化段泄漏（draft-only 定规）
    conv_pat = re.compile(r"点个在看|在看让我知道|点个关注|关注我|后台回复|分享到朋友圈|转发抽奖|加V")
    in_fence = False
    for i, line in enumerate(body.split("\n"), 1):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = conv_pat.search(line)
        if m:
            werr("转化段泄漏", f"源稿出现「{m.group(0)}」——转化段只许 draft-only 后台补（wechat-retention §6）")

    # 2. /posts/ 死路径（判废级；relref 短码除外）
    body_no_relref = re.sub(r'\{\{<\s*relref[^>]*>\}\}', "", body)
    if "/posts/" in body_no_relref:
        werr("posts死路径", "正文出现 /posts/ 字面路径（2026-08-31 判废级：公众号版只许 mp 内链，relref 短码由发布链路处理）")

    # 3. wechat_title
    if wtitle:
        if cn_len(wtitle) > 25:
            werr("wechat_title超长", f"{cn_len(wtitle)} 字（折叠线 25）：{wtitle}")
        head13 = wtitle[:13]
        hook_words = ["坑", "别", "为什么", "错", "翻车", "贵", "省", "怕", "差", "炸", "白", "免费", "瞒", "亏", "不知道", "还在", "自动"]
        if not (any(c.isdigit() for c in head13) or any(w in head13 for w in hook_words)):
            wwarn("title钩子后置", f"前 13 字无钩子信号（数字/痛点/反差）：{head13}…")
    else:
        if cn_len(title) > 25:
            werr("wechat_title缺失", f"主标题 {cn_len(title)} 字超折叠线，回退必被截——补 wechat_title ≤25 字")
        else:
            wwarn("wechat_title缺失", "回退主标题（≤25 字可用，建议出变体）")

    # 4. cover.png
    cover = os.path.join(args.root, "static", "images", args.slug, "cover.png")
    if not os.path.exists(cover):
        werr("封面缺失", f"static/images/{args.slug}/cover.png 不存在（打开层转化件，禁直搬/兜底）")
    # 2026-09-05 用户定规：正文不展示封面——封面只从 static/images/<slug>/cover.png
    # 取（prepare.py 直取裁 9:5），出现在正文里即 WARN
    if re.search(rf'<img src="/images/{re.escape(args.slug)}/cover\.png"', body):
        wwarn("封面进了正文", "正文内嵌 cover.png（2026-09-05 定规：所有文章正文不展示封面，删正文封面行）")

    # 5. digest 前 40 字钩子
    if not wdigest:
        wwarn("wechat_digest缺失", "回退 description——核对 description 前 40 字是否承担打开转化")
    head40 = digest[:40]
    digest_hook_words = ["坑", "别", "问题", "错", "翻车", "贵", "省", "怕", "白", "免费", "不知道", "还在", "怎么办", "怎么"]
    if head40 and not (any(c.isdigit() for c in head40) or any(w in head40 for w in digest_hook_words)):
        wwarn("digest钩子弱", f"digest 前 40 字无痛点词/硬数字：{head40}…")

    # 6. 首屏图（第一个 img 在 800 字内）
    plain = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
    plain = re.sub(r"<[^>]+>", "", plain)
    m_pos = body.find("<img")
    prefix_cn = len(re.findall(r"[\u4e00-\u9fff]", body[:m_pos])) if m_pos >= 0 else len(re.findall(r"[\u4e00-\u9fff]", plain))
    if m_pos < 0 or prefix_cn > 800:
        wwarn("首屏无图", f"第一张图前有 {prefix_cn} 字（前 800 字应有总览图锚视线）")

    # 7. 二级标题间隔 ≤1200 字
    heads = [(m.start(), m.group(0)) for m in re.finditer(r"^## .+", body, re.M)]
    bounds = [h[0] for h in heads] + [len(body)]
    for idx in range(len(heads)):
        seg = body[bounds[idx]:bounds[idx + 1]]
        seg_cn = len(re.findall(r"[\u4e00-\u9fff]", seg))
        if seg_cn > 1200:
            wwarn("标题间隔", f"「{heads[idx][1].strip()[:20]}」到下个标题 {seg_cn} 字（>1200，拆节给滚动锚点）")

    # 8. 收藏资产（表格或 markdown 清单块）
    has_table = re.search(r"^\|.*\|$", body, re.M)
    has_list_block = re.search(r"```markdown", body)
    if not has_table and not has_list_block:
        wwarn("无收藏资产", "全文无表格/清单型代码块——收藏是完读外最强质量信号（速查/对比表/决策树至少一处）")

    # 9. 往期关联（钩子问句式 2-3 条）
    rel_refs = re.findall(r'\{\{<\s*relref "posts/([^"]+)"', body)
    m_assoc = re.search(r"^#{2,3}\s*往期关联\s*$", body, re.M)
    if not m_assoc:
        wwarn("无往期关联", "文末缺「往期关联」节（2-3 条钩子问句 + relref，样板 codex-auto-video-editing）")
    else:
        tail = body[m_assoc.start():]
        n_items = len(re.findall(r'^-', tail, re.M))
        if not (2 <= n_items <= 3):
            wwarn("往期关联条数", f"{n_items} 条（定规 2-3 条）")

    # 10. 长度档位（信息级）
    if cn <= 2500:
        tier = "直发（≤2500）"
    elif cn <= 4000:
        tier = "压缩变体（2500-4000）"
    else:
        tier = "默认压缩变体（>4000，直发是例外需 link-map 记豁免理由）"
    print(f"   长度档位建议：{tier}")

    del label  # 预留


def main():
    ap = argparse.ArgumentParser(description="文章机检门禁")
    ap.add_argument("--slug", required=True, help="posts slug")
    ap.add_argument("--root", default=".", help="blog-src 仓根（缺省当前目录）")
    ap.add_argument("--wechat", action="store_true", help="加跑公众号适配检查（H 组）")
    args = ap.parse_args()

    path = os.path.join(args.root, "content", "posts", f"{args.slug}.md")
    if not os.path.exists(path):
        print(f"❌ 文件不存在: {path}")
        return 1

    text = open(path, encoding="utf-8").read()
    parts = text.split("+++\n", 2)
    fm = parts[1] if len(parts) > 2 else ""
    body = parts[2] if len(parts) > 2 else text
    body_lines = body.split("\n")
    label = os.path.join("content", "posts", f"{args.slug}.md")

    # ---- 1. relref 目标存在 ----
    for m in re.finditer(r'relref "posts/([^"]+)"', text):
        tgt = os.path.join(args.root, "content", "posts", m.group(1))
        if not os.path.exists(tgt):
            err(None, "relref断链", f"relref 目标不存在 posts/{m.group(1)}")

    # ---- 2. 段落长度（≈40字/行：>280字 ERROR，>180字 WARN）----
    for ln, para in iter_paragraphs(body_lines):
        width = cn_len(para)
        if width > 280:
            err(ln, "段落超长", f"段落约 {width} 字宽（≈{width // 40} 行，限 4 行）——拆段：{para[:40]}…")
        elif width > 180:
            warn(ln, "段落偏长", f"段落约 {width} 字宽（≈{width // 40} 行），接近上限，建议拆分")

    # ---- 3. 标题数字在正文出现（按独立数字 token 完整匹配，防 '30' 误兑现 '3'）----
    title_m = re.search(r"^title\s*=\s*['\"](.+?)['\"]", fm, re.M)
    if title_m:
        title = title_m.group(1)
        body_num_tokens = set(re.findall(r"\d+", body))
        for num in set(re.findall(r"\d+", title)):
            if num not in body_num_tokens:
                err(None, "数字不兑现", f"标题数字「{num}」未在正文独立出现")

    # ---- 4. 代码块 ≤15 行 ----
    fence_start = None
    for i, line in enumerate(body_lines, 1):
        if line.strip().startswith("```"):
            if fence_start is None:
                fence_start = i
            else:
                if i - fence_start - 1 > 15:
                    err(fence_start, "代码块超行", f"代码块 {i - fence_start - 1} 行（限 15）")
                fence_start = None

    # ---- 5. 结尾段不是列表/表格（「往期关联」节豁免——定规允许的文末形态）----
    assoc_m = re.search(r"^#{2,3}\s*往期关联\s*$", body, re.M)
    assoc_start = assoc_m.start() if assoc_m else -1
    last_block = None
    last_pos, last_line = 0, 0
    for i, line in enumerate(body_lines, 1):
        if line.strip():
            last_block, last_line = line.strip(), i
            last_pos = sum(len(l) + 1 for l in body_lines[: i - 1])
    if last_block and last_block.startswith(("-", "|", "*", "1.", ">")) and last_pos < assoc_start:
        err(last_line, "清单式收尾", f"最后一段是列表/表格（须结论式散文；往期关联节除外）：{last_block[:40]}…")

    # ---- 6. SVG 存在 + W2 配额 ----
    svg_refs = re.findall(r'src="/svg/([^"]+)"', text)
    for r in svg_refs:
        if not os.path.exists(os.path.join(args.root, "static", "svg", r)):
            err(None, "SVG缺失", f"/svg/{r} 文件不存在")
    clean_body = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
    clean_body = re.sub(r"<img[^>]*>", "", clean_body)
    cn = len(re.findall(r"[\u4e00-\u9fff]", clean_body))
    quota = max(2, round(cn / 1800))
    if len(svg_refs) < quota:
        warn(None, "配图配额", f"{len(svg_refs)} 图（需 ≥{quota}，{cn} 字）")

    # ---- 7. 时间简写 ----
    time_pat = re.compile(r"\d{1,2}\s*月\s*\d{1,2}\s*日|昨天|前天|大前天|\d+\s*(?:天|小时|分钟)前")
    in_fence = False
    for i, line in enumerate(body_lines, 1):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = time_pat.finditer(line)
        for mm in m:
            err(i, "时间简写", f"「{mm.group(0)}」——正文时间用完整年月日时分秒")

    # ---- 8. 同段冒号密度（≥3 降 WARN：对照修辞合法，滥用人工判）----
    for ln, para in iter_paragraphs(body_lines):
        if para.count("：") >= 3:
            warn(ln, "冒号密集", f"一段内冒号 {para.count('：')} 处——判修辞排比（可留）还是顿挫（减一处）：{para[:40]}…")

    # ---- 9. 重复整句（≥10 字完全相同句子出现 ≥2 次）----
    sent_seen = {}
    for ln, para in iter_paragraphs(body_lines):
        for sent in re.split(r"[。！？!?]", para.replace("\n", "")):
            sent = sent.strip()
            if len(sent) >= 10:
                sent_seen.setdefault(sent, []).append(ln)
    for sent, lns in sent_seen.items():
        if len(lns) >= 2:
            err(lns[1], "重复句", f"整句出现 {len(lns)} 次（首现 :{lns[0]}）：{sent[:40]}…")

    # ---- W1 破折号 / W3 零 relref ----
    dash = text.count("——")
    if dash > 2:
        warn(None, "破折号", f"共 {dash} 处（理想 ≤2，风格提示）")
    if "relref" not in text:
        warn(None, "零内链", "全文无 relref 互链（首篇/孤立文章合法，否则补）")

    # ---- H 组：公众号适配（--wechat）----
    if args.wechat:
        run_wechat_checks(text, fm, body, cn, args)

    # ---- 汇总 ----
    print(f"📋 {label} · {cn} 字 / {len(svg_refs)} 图（配额 {quota}）")
    if ERRORS:
        print(f"❌ ERROR（{len(ERRORS)} 处，阻断）：")
        for e in ERRORS:
            print(f"{label}{e}")
    if WARNS:
        print(f"⚠️ WARN（{len(WARNS)} 处，人工判断）：")
        for w in WARNS:
            print(f"{label}{w}")
    if not ERRORS and not WARNS:
        print("✅ 机检全绿（编辑终检 A-F 组仍需过）")
    elif not ERRORS:
        print("✅ 机检无阻断项（处置 WARN 后进编辑终检）")
    return 1 if ERRORS else 0


if __name__ == "__main__":
    sys.exit(main())
