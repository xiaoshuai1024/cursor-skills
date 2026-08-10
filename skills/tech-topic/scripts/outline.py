# -*- coding: utf-8 -*-
"""大纲生成（tech-topic skill）。

  py -m outline --rough <item.json> --out <xxx_rough.md>
    按候选所属视角给「假设结构」，用于决定对标哪篇，不碰正文。
    in_vertical=True → 垂直深度模板；否则 → 热度速跟模板。

  --deep（拉正文后真实拆解 → 差异化原创可参考大纲）见任务 4.x，当前未实现。
"""
from __future__ import annotations

import argparse
import json
import os
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


def _rough_hot(item: dict[str, Any]) -> list[str]:
    return [
        f"# 假设大纲（🔥 热度速跟）— {item.get('title', '')}",
        "",
        f"> 对标: [{item.get('author', '')}]({item.get('url', '')})  "
        f"👍{item.get('digg_count', 0)} 🔖{item.get('collect_count', 0)}  "
        f"方向: `{item.get('direction') or '-'}`",
        "",
        "**结构假设（借热点反差）**:",
        "1. 钩子：用热点反差/反常识切入，3 秒抓注意",
        "2. 主线段 1：观点 + 证据（现象 → 数据/案例）",
        "3. 主线段 2：观点 + 证据",
        "4. 主线段 3：观点 + 证据",
        "5. 差异化角度：别人没讲透的点 / 自己的真实实践",
        "6. CTA：引导关注 / 内链相关博文",
        "",
        "_⚠️ 假设结构，仅供决策对标；正文素材须来自真实经历/存量博客，禁止照搬原文。_",
    ]


def _rough_vertical(item: dict[str, Any]) -> list[str]:
    kws = ",".join(item.get("matched_keywords") or [])
    return [
        f"# 假设大纲（🎯 垂直深度）— {item.get('title', '')}",
        "",
        f"> 对标: [{item.get('author', '')}]({item.get('url', '')})  "
        f"关键词: `{kws}`  👍{item.get('digg_count', 0)}",
        "",
        "**结构假设（痛点 → 方案）**:",
        "1. 痛点钩子：读者真实卡点 / 常见误解",
        "2. 问题拆解：为什么会卡（原理/根因）",
        "3. 方案演示：我的做法（步骤 + 代码/截图）",
        "4. 沉淀：可复用的判断/模板/清单",
        "5. 内链：关联存量博文（relref）",
        "",
        "_⚠️ 假设结构，仅供决策对标；正文素材须来自真实经历/存量博客，禁止照搬原文。_",
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="大纲生成（当前仅 --rough）")
    parser.add_argument("--rough", dest="item_json", required=True, help="候选 item.json")
    parser.add_argument("--out", required=True, help="输出 md 路径")
    args = parser.parse_args()
    _utf8_stdio()

    item = json.loads(Path(args.item_json).read_text(encoding="utf-8"))
    lines = _rough_vertical(item) if item.get("in_vertical") else _rough_hot(item)
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"✅ 假设大纲 → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
