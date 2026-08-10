#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""应用窗口截图（跨平台入口，只截应用本身、不截全屏）。

macOS: 系统原生 Quartz（CGWindowListCopyWindowInfo 按进程名/标题匹配窗口
       → CGWindowListCreateImage 截窗口 → PNG）。
Windows: 调用原 scripts/screenshot-app.ps1（GetWindowRect + SetForegroundWindow）。

用法:
    python scripts/screenshot_app.py --process <进程名> --title <窗口标题> --output <输出.png>
    python scripts/screenshot_app.py --process ChatGPT --title ChatGPT --output static/images/x/01.png

> macOS 分支依赖 pyobjc-framework-Quartz / pyobjc-framework-Cocoa（见 requirements-macos.txt），首次使用需实测。
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _find_window_macos(process_name: str, title: str):
    """返回匹配窗口的 (window_id, bounds)，找不到返回 (None, None)。"""
    from Quartz import (
        CGWindowListCopyWindowInfo,
        kCGWindowListOptionOnScreenOnly,
        kCGNullWindowID,
    )
    infos = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)
    for w in infos:
        owner = w.get("kCGWindowOwnerName") or ""
        wname = w.get("kCGWindowName") or ""
        wid = w.get("kCGWindowNumber")
        bounds = w.get("kCGWindowBounds")
        if wid is None or bounds is None:
            continue
        # 只看有标题/有层的真实窗口
        if process_name.lower() in owner.lower() and (not title or title.lower() in wname.lower()):
            return wid, bounds
    return None, None


def _screenshot_macos(process_name: str, title: str, output: str) -> bool:
    """macOS Quartz 截窗口 → PNG。"""
    from Quartz import (
        CGWindowListCreateImage,
        CGRectNull,
        kCGWindowListOptionIncludingWindow,
        kCGWindowImageDefault,
    )
    from AppKit import NSBitmapImageRep, NSPNGFileType

    wid, _bounds = _find_window_macos(process_name, title)
    if wid is None:
        print(f"❌ 找不到窗口: process={process_name!r} title={title!r}", file=sys.stderr)
        return False

    cgimage = CGWindowListCreateImage(
        CGRectNull, kCGWindowListOptionIncludingWindow, wid, kCGWindowImageDefault
    )
    if cgimage is None:
        print("❌ 截图失败:CGWindowListCreateImage 返回空。最常见原因:终端无「屏幕录制」权限", file=sys.stderr)
        print("   → 系统设置 → 隐私与安全 → 屏幕录制 → 勾选 iTerm/Terminal 后重启终端重试", file=sys.stderr)
        return False

    Path(output).parent.mkdir(parents=True, exist_ok=True)
    rep = NSBitmapImageRep.alloc().initWithCGImage_(cgimage)
    data = rep.representationUsingType_properties_(NSPNGFileType, None)
    data.writeToFile_atomically_(output, True)
    print(f"saved {output}")
    return True


def _screenshot_windows(process_name: str, title: str, output: str) -> bool:
    """Windows: 调原 screenshot-app.ps1。"""
    ps1 = Path(__file__).resolve().parent / "screenshot-app.ps1"
    cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
           "-File", str(ps1), "-ProcessName", process_name, "-Output", output]
    if title:
        cmd += ["-WindowTitle", title]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        print(f"❌ screenshot-app.ps1 失败: {result.stderr[:300]}", file=sys.stderr)
        return False
    print(result.stdout.strip())
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="应用窗口截图（跨平台，只截应用本身）")
    parser.add_argument("--process", required=True, help="进程名（模糊匹配）")
    parser.add_argument("--title", default="", help="窗口标题（模糊匹配，可选）")
    parser.add_argument("--output", required=True, help="输出 PNG 路径")
    args = parser.parse_args()

    if sys.platform == "win32":
        ok = _screenshot_windows(args.process, args.title, args.output)
    else:
        ok = _screenshot_macos(args.process, args.title, args.output)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
