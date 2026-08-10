# -*- coding: utf-8 -*-
"""掘金文章原文保存（Phase 2）。

  chrome 渲染 juejin.cn/post/<article_id>（detail 接口匿名已证实不可用 → 渲染为主路径）
  → 抽 .article-content innerHTML/innerText + 首屏截图 → bs4 解析结构
  → 落 article.html / article.txt / screenshot.png / meta.json

用法:
  py -m fetch_article --article-id <id> --out-dir .tech-topic/articles/<id>
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

CHANNEL = os.environ.get("TECH_TOPIC_BROWSER", "msedge" if sys.platform == "win32" else "chrome")
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
EXTRACT_JS = """
() => {
  const sels = ['.article-content', '#article-content', '.article-viewer', 'article', 'main'];
  for (const s of sels) {
    const el = document.querySelector(s);
    if (el && el.innerText.trim().length > 200) return {html: el.innerHTML, text: el.innerText};
  }
  return {html: document.body.innerHTML, text: document.body.innerText};
}
"""


def _utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass


def project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "hugo.toml").exists() or (parent / ".git").exists():
            return parent
    return current.parents[-1]


OUTPUT_ROOT = project_root() / ".tech-topic"


def _structure(html: str) -> dict[str, Any]:
    import bs4
    soup = bs4.BeautifulSoup(html, "html.parser")
    headings = [
        {"level": int(h.name[1]), "text": h.get_text(strip=True)}
        for h in soup.find_all(["h1", "h2", "h3", "h4"])
    ]
    return {
        "headings": headings,
        "code_blocks": len(soup.find_all("pre")),
        "images": len([img for img in soup.find_all("img") if img.get("src")]),
    }


def fetch_article(article_id: str, out_dir: Path) -> int:
    from playwright.sync_api import sync_playwright

    out_dir.mkdir(parents=True, exist_ok=True)
    url = f"https://juejin.cn/post/{article_id}"

    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel=CHANNEL, headless=True,
            args=["--disable-blink-features=AutomationControlled", "--lang=zh-CN"],
        )
        page = browser.new_page(viewport={"width": 1440, "height": 900}, user_agent=UA)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=40000)
        except Exception as exc:
            print(f"⚠️ goto 失败: {exc}")
        page.wait_for_timeout(3000)  # 等正文渲染
        for _ in range(2):  # 滚动触发懒加载图片
            try:
                page.mouse.wheel(0, 1200); page.wait_for_timeout(800)
            except Exception:
                pass
            page.evaluate("window.scrollTo(0, 0)")

        title = ""
        try:
            title = page.title().split("-")[0].strip()[:50]
        except Exception:
            pass
        author = ""
        try:
            raw = page.evaluate(
                "() => (document.querySelector('.article-author-box .username, .author-name, .main-author-box .username')?.innerText || '').trim()"
            ) or ""
            # 过滤导航栏误命中（多行/过长 = 抓到的是 nav）
            if raw and "\n" not in raw and len(raw) <= 20:
                author = raw
        except Exception:
            pass
        extracted = {"html": "", "text": ""}
        try:
            extracted = page.evaluate(EXTRACT_JS)
        except Exception as exc:
            print(f"⚠️ 抽正文失败: {exc}")
        try:
            page.screenshot(path=str(out_dir / "screenshot.png"), full_page=False)
        except Exception as exc:
            print(f"⚠️ 截图失败: {exc}")
        browser.close()

    html = extracted.get("html") or ""
    text = extracted.get("text") or ""
    if len(text.strip()) < 200:
        print(f"⚠️ 抽到的正文过短（{len(text)} 字），可能渲染未完成或选择器失效")

    (out_dir / "article.html").write_text(html, encoding="utf-8")
    (out_dir / "article.txt").write_text(text, encoding="utf-8")

    struct = _structure(html) if html else {"headings": [], "code_blocks": 0, "images": 0}
    meta = {
        "article_id": article_id,
        "url": url,
        "title": title,
        "author": author,
        "char_count": len(text),
        "read_minutes": max(1, round(len(text) / 400)),
        "fetched_at": int(time.time()),
        **struct,
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 原文保存: {out_dir}/  ({len(text)} 字, {len(struct['headings'])} 标题, {struct['code_blocks']} 代码块)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="掘金文章原文保存（Phase 2）")
    parser.add_argument("--article-id", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    _utf8_stdio()
    return fetch_article(args.article_id, Path(args.out_dir))


if __name__ == "__main__":
    raise SystemExit(main())
