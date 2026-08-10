# -*- coding: utf-8 -*-
"""结构分析（Phase 2）—— 读保存的原文，产出 analysis.md。

  只做结构分析（标题树/钩子/段落骨架/量化），**不生成仿写内容**（仿写归写博客 skill）。

用法:
  py -m analyze --dir .tech-topic/articles/<article_id>
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def _utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass


def _sections(html: str) -> list[dict[str, Any]]:
    """按标题切节，每节带首段预览（段落骨架）。"""
    import bs4
    soup = bs4.BeautifulSoup(html, "html.parser")
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for el in soup.find_all(["h1", "h2", "h3", "h4", "p", "pre", "ul", "ol", "blockquote"]):
        if el.name in ("h1", "h2", "h3", "h4"):
            current = {"level": int(el.name[1]), "title": el.get_text(strip=True), "preview": ""}
            sections.append(current)
        elif current is not None and not current["preview"]:
            txt = el.get_text(" ", strip=True)
            if len(txt) > 15:
                current["preview"] = txt[:120]
    return sections


def main() -> int:
    parser = argparse.ArgumentParser(description="结构分析（Phase 2）")
    parser.add_argument("--dir", required=True, help="articles/<article_id> 目录")
    args = parser.parse_args()
    _utf8_stdio()

    d = Path(args.dir)
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    html = (d / "article.html").read_text(encoding="utf-8") if (d / "article.html").exists() else ""
    text = (d / "article.txt").read_text(encoding="utf-8") if (d / "article.txt").exists() else ""

    sections = _sections(html) if html else []
    # 钩子 = 正文前 2-3 句
    sentences = [s.strip() for s in re.split(r"[。！？\n]", text) if len(s.strip()) > 8]
    hook = "。".join(sentences[:3]) + ("。" if sentences else "")

    title = meta.get("title") or "(无标题)"
    lines = [
        f"# 结构分析 — {title}",
        "",
        f"> 原文: {meta.get('url')}  |  作者: {meta.get('author') or '-'}",
        f"> 抓取于 {meta.get('fetched_at')}  |  **仅分析用，禁止逐字搬运；仿写由写博客 skill 完成**",
        "",
        "## 概要",
        f"- 字数：**{meta.get('char_count', 0)}**（约 {meta.get('read_minutes', 1)} 分钟）",
        f"- 标题数：{len(meta.get('headings', []))}（H1-H4） | 代码块：{meta.get('code_blocks', 0)} | 配图：{meta.get('images', 0)}",
        "",
        "## 钩子（首段）",
        hook or "_(未提取到)_",
        "",
        "## 标题树 / 段落骨架",
    ]
    if not sections:
        lines.append("_(未解析到标题结构，见 article.txt 原文)_")
    else:
        for s in sections:
            indent = "  " * (s["level"] - 1)
            lines.append(f"{indent}- {'#' * s['level']} {s['title']}")
            if s["preview"]:
                lines.append(f"{indent}  → {s['preview']}…")
    lines += [
        "",
        "---",
        "## 原文位置",
        f"- HTML: `article.html` | 纯文本: `article.txt` | 首屏: `screenshot.png`",
        f"- 仿写时参考结构，内容用自己的真实经历/存量博客，**禁止照搬原文文案**。",
        "",
    ]
    (d / "analysis.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"✅ 结构分析 → {d / 'analysis.md'}（{len(sections)} 节）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
