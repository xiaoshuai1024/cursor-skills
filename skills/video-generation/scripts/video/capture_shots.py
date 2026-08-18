"""抓取真实网页截图 + 热点坐标，供 realshot 渲染器（screencast）打底使用。

「拟物化」方向：不再用 CSS 画假窗口，而是真实浏览器截图 + 箭头标注指向
下载/安装按钮。本脚本用 Playwright 抓目标页面，滚动到目标区域，记录每个
热点（下载按钮/安装按钮）在截图里的百分比坐标，输出 manifest.json。

产物：
  .video-generation/assets/<slug>/<key>.png      截图（1600x900 视口）
  .video-generation/assets/<slug>/manifest.json  热点坐标（百分比，相对截图）

用法：
  cd .agents/skills/video-generation/scripts
  PYTHONIOENCODING=utf-8 python -m video.capture_shots --slug <slug>

热点坐标用百分比：渲染时 <img> 缩放显示，百分比定位始终落在正确位置。
每个热点 {x,y,w,h,label} 都是相对整张截图的比例（0~100）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
from video.config import OUTPUT_ROOT  # noqa: E402

VIEW_W, VIEW_H = 1600, 900
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def _pct(v: float, denom: float) -> float:
    return round(v / denom * 100.0, 2)


class Shot:
    """一张截图的抓取定义。"""

    def __init__(self, key: str, url: str, hotspots: list[dict],
                 scroll_heading: str | None = None, wait_sel: str | None = None,
                 settle_ms: int = 900, wait_commit: bool = False):
        self.key = key
        self.url = url
        self.hotspots = hotspots          # [{sel|text, after_heading?, label}]
        self.scroll_heading = scroll_heading  # 滚动到文章内含该文本的标题
        self.wait_sel = wait_sel
        self.settle_ms = settle_ms
        # 2026-08-17: 部分官网对 domcontentloaded 超时（curl 却 200），
        # 用 wait_until="commit" + 长 settle 兜底（dshdesktop.cn 踩坑）
        self.wait_commit = wait_commit

    @staticmethod
    def _locate(pg, h: dict) -> dict | None:
        """定位热点框。h 可为 {sel} 或 {text, after_heading?}。

        text 模式：在 scope（默认 article.markdown-body）内找含该文本、且在视口内
        的叶子元素；给了 after_heading 则先从该标题的父容器开始找（跳过 README 顶部）。
        """
        if "sel" in h:
            el = pg.query_selector(h["sel"])
            if not el or not el.is_visible():
                return None
            return el.bounding_box()
        return pg.evaluate(
            """({text, after_heading}) => {
              const scope = document.querySelector('article.markdown-body') || document.body;
              let min = null, minTop = Infinity;
              // after_heading 只用于锚定候选顺序：收集其 document 位置前的候选排后。
              const heads = [...document.querySelectorAll(
                'article.markdown-body h2, article.markdown-body h3, article.markdown-body h4')];
              const anchor = after_heading
                ? heads.find(x => x.textContent.includes(after_heading)) : null;
              const all = scope.querySelectorAll('p, li, code, span, td, div');
              for (const n of all) {
                if (!n.textContent.includes(text)) continue;
                const r = n.getBoundingClientRect();
                if (!(r.width > 0 && r.height > 0 && r.height < 200)) continue;
                if (!(r.top >= 0 && r.bottom <= innerHeight)) continue;
                // 若给了锚点标题，排在标题上方的候选跳过（优先取段落内的行）
                if (anchor && r.top < anchor.getBoundingClientRect().top) continue;
                if (r.top < minTop) { minTop = r.top; min = {x: r.x, y: r.y, width: r.width, height: r.height}; }
              }
              return min;
            }""", {"text": h["text"], "after_heading": h.get("after_heading")})


SHOTS: list[Shot] = [
    # 0. DeepSeek Harness repo 首屏：star 计数 + 仓库名/描述（deepseek-harness-first-look 教程版）
    Shot(
        key="dsh-repo",
        url="https://github.com/deepseek-ai/deepseek-harness",
        hotspots=[
            {"sel": "#repo-stars-counter-star", "label": "3 万 Star"},
        ],
        settle_ms=2200,
    ),
    # 1. VSCode 官网下载页：第一视口 = hero + 平台下载表；热点 = Windows 下载行
    Shot(
        key="vscode-download",
        url="https://code.visualstudio.com/download",
        hotspots=[
            {"sel": "a.dlink", "label": "Windows 下载"},
        ],
        settle_ms=1200,
    ),
    # 2. 市场 Claude Code 插件页：热点 = Install 按钮（vscode:extension 直装链接）
    Shot(
        key="market-claude-code",
        url="https://marketplace.visualstudio.com/items?itemName=anthropic.claude-code",
        hotspots=[
            {"sel": "a[href^='vscode:extension/']", "label": "安装插件"},
        ],
        settle_ms=1500,
    ),
    # 3. CcSwitch README 的 Download & Installation 段：热点 = 标题下含 Windows 的行
    Shot(
        key="ccsw-download",
        url="https://github.com/farion1231/cc-switch",
        scroll_heading="Download",
        hotspots=[
            {"text": "Windows", "after_heading": "Download", "label": "Windows 安装包"},
        ],
        settle_ms=1200,
    ),
    # 4. DeepSeek 开放平台：登录墙，热点 = 发送验证码按钮（手机登录第一步）
    Shot(
        key="deepseek-platform",
        url="https://platform.deepseek.com",
        hotspots=[
            {"text": "发送验证码", "label": "登录申请 key"},
        ],
        settle_ms=2500,
    ),
    # 5. DSH Desktop 官网（deepseek-harness-desktop-cli 教程版）：hero 下载按钮
    #    官网对 domcontentloaded 超时 → wait_commit=True（2026-08-17 踩坑）
    Shot(
        key="dshdesktop-home",
        url="https://www.dshdesktop.cn/",
        wait_commit=True,
        settle_ms=12000,
        # 按钮坐标用 bounding_box 实测（百分比，见 deck.json 静态热点）：
        #   「下载 Mac 版」(8.0,58.1,9.7,6.0)  「下载 Windows 版」(18.7,58.1,12.1,6.0)
        hotspots=[],
    ),
    # 6. DSH Desktop GitHub 仓库：star 计数
    Shot(
        key="dsh-desktop-repo",
        url="https://github.com/anywhere-labs/deepseek-harness-desktop",
        hotspots=[
            {"sel": "#repo-stars-counter-star", "label": "8.5k Star"},
        ],
        settle_ms=2200,
    ),
    # 7. dsh-TUI 官网：hero 安装区
    Shot(
        key="dsh-tui-home",
        url="https://dshtui.com/",
        hotspots=[
            {"text": "npm", "label": "安装命令"},
        ],
        settle_ms=2200,
    ),
]


def _dismiss_consent(pg) -> None:
    """关掉常见 cookie 横幅，避免遮挡热点。"""
    for sel in ["#cc-banner .close", "#onetrust-accept-btn-handler",
                "button[data-testid='cookie-accept']", ".cc-banner__btn-accept"]:
        try:
            el = pg.query_selector(sel)
            if el and el.is_visible():
                el.click()
                pg.wait_for_timeout(300)
                return
        except Exception:
            pass


def capture(shots: list[Shot], out_dir: Path) -> dict:
    """抓取所有 shot，返回 manifest 结构。"""
    from playwright.sync_api import sync_playwright

    manifest: dict = {"slug": out_dir.parent.name, "shots": []}
    out_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        # 本机代理（如 Clash 7897）：访问 GitHub 等境外站必须走代理，否则
        # chromium DNS/连接超时（curl/git 走系统代理能通，chromium 默认不走）。
        proxy = os.environ.get("PLAYWRIGHT_PROXY", "").strip()
        b = pw.chromium.launch(
            proxy={"server": proxy} if proxy else None,
        )
        ctx = b.new_context(viewport={"width": VIEW_W, "height": VIEW_H}, user_agent=UA)
        pg = ctx.new_page()

        for shot in shots:
            print(f"\n=== {shot.key}: {shot.url}")
            rec = {"key": shot.key, "url": shot.url, "hotspots": []}
            png = out_dir / f"{shot.key}.png"
            try:
                pg.goto(shot.url,
                       wait_until="commit" if shot.wait_commit else "domcontentloaded",
                       timeout=40000)
                try:
                    pg.wait_for_load_state("networkidle", timeout=20000)
                except Exception:
                    pass
                _dismiss_consent(pg)

                if shot.scroll_heading:
                    # 滚动到文章内指定标题，block=center 让目标居中
                    found = pg.evaluate(
                        """(text) => {
                          const heads = document.querySelectorAll('article.markdown-body h2, article.markdown-body h3');
                          for (const h of heads) {
                            if (h.textContent.includes(text)) {
                              h.scrollIntoView({block: 'center'});
                              return true;
                            }
                          }
                          return false;
                        }""", shot.scroll_heading)
                    print(f"  scroll heading {shot.scroll_heading!r}: {found}")
                    pg.wait_for_timeout(shot.settle_ms)
                else:
                    pg.wait_for_timeout(shot.settle_ms)

                if shot.wait_sel:
                    try:
                        pg.wait_for_selector(shot.wait_sel, timeout=10000)
                    except Exception:
                        pass

                pg.screenshot(path=str(png), clip={"x": 0, "y": 0, "width": VIEW_W, "height": VIEW_H})
                rec["png"] = str(png)
                rec["size"] = f"{VIEW_W}x{VIEW_H}"

                for h in shot.hotspots:
                    box = Shot._locate(pg, h)
                    if not box:
                        print(f"  !! hotspot miss: {h.get('sel') or h.get('text')}")
                        continue
                    rec["hotspots"].append({
                        "x": _pct(box["x"], VIEW_W),
                        "y": _pct(box["y"], VIEW_H),
                        "w": _pct(box["width"], VIEW_W),
                        "h": _pct(box["height"], VIEW_H),
                        "label": h["label"],
                    })
                    print(f"  hot {h['label']}: ({rec['hotspots'][-1]['x']},"
                          f"{rec['hotspots'][-1]['y']}, {rec['hotspots'][-1]['w']},"
                          f"{rec['hotspots'][-1]['h']})")
            except Exception as exc:
                rec["error"] = f"{type(exc).__name__}: {str(exc)[:120]}"
                print(f"  !! {rec['error']}")

            manifest["shots"].append(rec)

        b.close()

    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser(description="抓真实网页截图 + 热点坐标")
    ap.add_argument("--slug", required=True)
    ap.add_argument("--shot", default=None, help="只抓指定 key（逗号分隔）")
    args = ap.parse_args()

    out_dir = OUTPUT_ROOT / "assets" / args.slug
    shots = SHOTS
    if args.shot:
        keys = set(args.shot.split(","))
        shots = [s for s in shots if s.key in keys]

    manifest = capture(shots, out_dir)
    n_ok = sum(1 for s in manifest["shots"] if "png" in s)
    print(f"\n抓取完成：{n_ok}/{len(manifest['shots'])} 张成功 → {out_dir}")
    print(f"manifest → {out_dir / 'manifest.json'}")


if __name__ == "__main__":
    main()
