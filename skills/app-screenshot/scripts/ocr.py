#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图片 OCR（跨平台入口）。

macOS: 系统原生 Vision 框架（VNRecognizeTextRequest），支持中文，零额外模型下载。
Windows: 调用原 scripts/ocr.ps1（WinRT OcrEngine）。

用法:
    python scripts/ocr.py <图片路径>
    python scripts/ocr.py window.png

用途: 模型不支持看图时，截图后用 OCR 核对窗口内容是否截对。
技巧: 小字先放大 2-3x 再识别，准确率更高。

> macOS 分支依赖 pyobjc-framework-Vision（见 requirements-macos.txt），首次使用需实测。
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def _ocr_macos(image_path: str) -> list[str]:
    """macOS Vision 框架识别，返回文字行列表。pyobjc 延迟 import（Windows 侧无需装）。"""
    from Vision import VNRecognizeTextRequest, VNImageRequestHandler
    from Foundation import NSURL

    request = VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLanguages_(["zh-Hans", "zh-Hant", "en-US"])
    # 不设 recognitionLevel：默认(fast)在本机对中文识别可靠；
    # setRecognitionLevel_(1) 实测反致中文乱码（pyobjc 下 VNRequestTextRecognitionLevelAccurate 枚举值异常）。

    url = NSURL.fileURLWithPath_(os.path.abspath(image_path))
    handler = VNImageRequestHandler.alloc().initWithURL_options_(url, None)
    ok, error = handler.performRequests_error_([request], None)
    if not ok:
        print(f"❌ Vision 识别失败: {error}", file=sys.stderr)
        return []

    lines: list[str] = []
    for obs in request.results():
        candidates = obs.topCandidates_(1)
        if candidates:
            lines.append(candidates[0].string())
    return lines


def _ocr_windows(image_path: str) -> list[str]:
    """Windows: 调原 ocr.ps1（WinRT OcrEngine）。"""
    ps1 = Path(__file__).resolve().parent / "ocr.ps1"
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-File", str(ps1), "-ImagePath", image_path],
        capture_output=True, text=True, encoding="utf-8",
    )
    if result.returncode != 0:
        print(f"❌ ocr.ps1 失败: {result.stderr[:300]}", file=sys.stderr)
        return []
    return [ln for ln in result.stdout.splitlines() if ln.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="图片 OCR（跨平台）")
    parser.add_argument("image", help="图片路径")
    args = parser.parse_args()

    if not Path(args.image).exists():
        print(f"❌ 图片不存在: {args.image}", file=sys.stderr)
        return 1

    if sys.platform == "win32":
        lines = _ocr_windows(args.image)
    else:
        lines = _ocr_macos(args.image)

    for ln in lines:
        print(ln)
    return 0 if lines else 1


if __name__ == "__main__":
    raise SystemExit(main())
