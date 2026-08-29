# -*- coding: utf-8 -*-
"""公众号/博客专用封面生成（大字风格，非视频封面）。

为什么不用 scripts/video/cover.py 的产物直接当公众号封面：
- 视频封面为 1920×1080 视频信息流设计（EP 角标/贴纸带/要点行/CTA 密度高），
  公众号推送卡片展示约 2.35:1 小图，prepare.py 中心裁 9:5 后上下沿仍会被
  会话列表再裁——角标/话题/CTA 全在牺牲区，小图下贴纸带是不可读噪点。
本脚本按公众号卡片规格重做（2026-08-28 定稿，调研依据见 wechat-retention.md 封面节）：
- 画布恒 1800×1000（9:5，prepare.py COVER_SIZE 原生尺寸，裁切零损失）
- 居中构图：全部文字落在中央 2.35:1 安全区（y 117–883）且在 1:1 中心带
  （朋友圈卡/次条裁 x≈400–1400）内——左对齐排版会在 1:1 场景被切
- 大字双行：第一行白 96px 级；第二行默认黄底深字色块锚点（--style block，
  微倾斜 -2°，抖音封面缩略图最强元素移植，同 v4 封面标准「一图一主角」），
  备选青色辉光字（--style glow）
- 副标题 36px 浅灰；标签 ≤3 个 pill（青/紫/橙固定顺序）；无角标/无 CTA/无贴纸带

用法:
  python make_cover.py --spec specs.json        # 批量:[{slug,line1,line2,subtitle,tags[]}]
  python make_cover.py --slug x --line1 .. --line2 .. [--subtitle ..] [--tags a,b,c]
输出: static/images/<slug>/cover.png（同名覆盖，公众号首图与博客封面共用）
依赖: Python311 playwright（channel=msedge），模板内联无外部文件。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

from playwright.sync_api import sync_playwright

W, H = 1800, 1000
SAFE_TOP = 117          # 2.35:1 安全区：中央 1800×766，列表再裁不伤内容
SAFE_BOTTOM = 883


def _project_root() -> Path:
    """从 cwd 向上找 hugo.toml 定位仓根。

    ⚠️ 不能用 __file__.resolve()：.agents/skills 是指向开源 skills 仓的符号链接，
    resolve() 会穿透到 D:/codes/skills，把封面写进镜像仓（vpt 同款坑）。
    """
    env = os.environ.get("BLOG_PROJECT_ROOT")
    if env:
        return Path(env)
    cur = Path.cwd()
    for p in [cur, *cur.parents]:
        if (p / "hugo.toml").exists():
            return p
    sys.exit("❌ 找不到仓根（无 hugo.toml），用 BLOG_PROJECT_ROOT 指定")


ROOT = _project_root()
OUT_BASE = ROOT / "static" / "images"

FONT = '"Microsoft YaHei", "微软雅黑", "PingFang SC", "Noto Sans SC", sans-serif'


def _hero_size(text: str, base: int) -> int:
    """按行宽估算字号：CJK 每字≈1em，字母数字≈0.55em，上限 base 下限 56。"""
    units = sum(1.0 if ord(c) > 0x2E7F else 0.55 for c in text)
    size = int(min(base, 1560 / max(units, 1)))
    return max(56, size)


def build_html(line1: str, line2: str, subtitle: str, tags: list[str], style: str = "glow") -> str:
    s1 = _hero_size(line1, 96)
    s2 = _hero_size(line2, 88)
    pills = "".join(
        f'<span class="tag t{i % 3}">{t}</span>' for i, t in enumerate(tags[:3])
    )
    sub_html = f'<div class="sub">{subtitle}</div>' if subtitle else ""
    # 第二行两种形态:glow=青色辉光字(默认);block=黄底深字色块锚点(抖音封面
    # 最强元素移植,v4 封面标准「一图一主角·缩略锚点」同款设计)
    if style == "block":
        l2_html = f'<span class="l2 block"><span class="block-text">{line2}</span></span>'
        block_css = (
            ".l2.block{display:inline-block;margin-top:10px;background:#facc15;"
            "color:#0a0e1a;padding:6px 34px 12px;border-radius:10px;"
            "transform:rotate(-2deg);box-shadow:0 10px 34px rgba(250,204,21,.28);}"
            ".l2.block .block-text{font-size:%dpx;}" % min(s2, 104)
        )
    else:
        l2_html = f'<span class="l2">{line2}</span>'
        block_css = ".l2{color:#22d3ee;text-shadow:0 0 26px rgba(34,211,238,.35);}"
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
html,body {{ width:{W}px; height:{H}px; overflow:hidden; }}
body {{
  font-family: {FONT};
  background:
    radial-gradient(900px 420px at 78% 18%, rgba(34,211,238,.10), transparent 62%),
    radial-gradient(700px 360px at 12% 88%, rgba(37,99,235,.10), transparent 60%),
    #0a0e1a;
  color:#fff;
}}
.wrap {{
  position:absolute; left:0; right:0; top:{SAFE_TOP}px; height:{SAFE_BOTTOM - SAFE_TOP}px;
  padding:0 120px; display:flex; flex-direction:column; justify-content:center;
  align-items:center; text-align:center;
  /* 居中构图：朋友圈卡/次条是 1:1 中心裁切(约 x 400-1400)，文字必须落在中带 */
}}
.brand {{
  position:absolute; top:34px; right:56px;
  font-size:22px; letter-spacing:2px; color:#64748b; font-weight:600;
  /* 品牌字在安全区外沿，仅装饰；被裁不伤内容 */
}}
.deco {{ position:absolute; top:{SAFE_TOP + 8}px; left:50%; transform:translateX(-50%);
  width:96px; height:6px; background:#22d3ee; border-radius:3px; opacity:.85; }}
h1 {{ font-weight:900; line-height:1.16; letter-spacing:1px; }}
.l1 {{ font-size:{s1}px; color:#f1f5f9; }}
{block_css}
.sub {{ margin-top:26px; font-size:36px; color:#94a3b8; font-weight:500;
        line-height:1.3; }}
.tags {{ margin-top:34px; display:flex; gap:18px; justify-content:center; }}
.tag {{
  font-size:26px; font-weight:700; padding:8px 26px; border-radius:999px;
  border:2px solid #22d3ee; color:#22d3ee; background:rgba(34,211,238,.08);
}}
.tag.t1 {{ border-color:#a78bfa; color:#a78bfa; background:rgba(167,139,250,.08); }}
.tag.t2 {{ border-color:#fb923c; color:#fb923c; background:rgba(251,146,60,.08); }}
</style></head>
<body>
  <div class="brand">1024 工程笔记</div>
  <div class="deco"></div>
  <div class="wrap">
    <h1><span class="l1">{line1}</span><br>{l2_html}</h1>
    {sub_html}
    <div class="tags">{pills}</div>
  </div>
</body></html>"""


def render_one(spec: dict, pw) -> Path:
    slug = spec["slug"]
    tags = spec.get("tags", [])
    html = build_html(spec["line1"], spec["line2"], spec.get("subtitle", ""), tags,
                      spec.get("style", "block"))
    out_dir = OUT_BASE / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "cover.png"
    browser = pw.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": W, "height": H})
    page.set_content(html, wait_until="networkidle")
    page.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": W, "height": H})
    browser.close()
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", help="批量 JSON: [{slug,line1,line2,subtitle,tags[]}]")
    ap.add_argument("--slug")
    ap.add_argument("--line1")
    ap.add_argument("--line2")
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--tags", default="")
    ap.add_argument("--style", default="block", choices=["block", "glow"],
                    help="第二行形态:block=黄底色块锚点(默认,抖音缩略锚点移植) glow=青色辉光(备选)")
    args = ap.parse_args()

    if args.spec:
        specs = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    elif args.slug and args.line1 and args.line2:
        specs = [{
            "slug": args.slug, "line1": args.line1, "line2": args.line2,
            "subtitle": args.subtitle, "tags": [t for t in args.tags.split(",") if t],
            "style": args.style,
        }]
    else:
        sys.exit("用法: --spec specs.json 或 --slug/--line1/--line2")

    with sync_playwright() as p:
        for s in specs:
            out = render_one(s, p)
            print(f"✅ {s['slug']}: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
