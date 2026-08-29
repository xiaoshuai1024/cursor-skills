"""录屏/口播素材静音剪 CLI（auto-editor 包装，openspec shot-motion-upgrade）。

auto-editor 自动检测静音段并剪除/变速，ffmpeg 级输出，音画同步由其内部保证。
用法：
  python -m video.silence_cut in.mp4 -o out.mp4 [--margin 0.15] [--silent-speed 999999]
  路径相对时基于项目根（VIDEO_PROJECT_ROOT 或 cwd）解析。
依赖：pip install auto-editor（Python311）。缺失时打印安装指引并以退出码 2 结束。
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def _project_root() -> Path:
    env = os.environ.get("VIDEO_PROJECT_ROOT")
    if env and Path(env).exists():
        return Path(env)
    return Path.cwd()


def _resolve(p: str) -> Path:
    path = Path(p)
    return path if path.is_absolute() else _project_root() / path


def _run_auto_editor(cmd_args: list[str]) -> int:
    """进程内调 auto-editor 23.32.1（末版纯 Python 实现）。

    不走 subprocess：该版本用了 NumPy 2.0 移除的 np.float_（实测 5 处），
    进程内先打 numpy 兼容补丁再进其 main()，避免改 site-packages。
    """
    import numpy as np
    if not hasattr(np, "float_"):
        np.float_ = np.float64
    if not hasattr(np, "bool8"):
        np.bool8 = np.bool_
    if not hasattr(np, "NaN"):
        np.NaN = np.nan
    if not hasattr(np, "Inf"):
        np.Inf = np.inf
    try:
        import auto_editor.__main__ as ae_main
    except ImportError:
        print("[err] 找不到 auto-editor。安装："
              "pip install auto-editor==23.32.1 --no-deps "
              "&& pip install av numpy", file=sys.stderr)
        return 2
    old_argv = sys.argv
    sys.argv = ["auto-editor"] + cmd_args
    try:
        ae_main.main()
    except SystemExit as e:
        return int(e.code or 0)
    finally:
        sys.argv = old_argv
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="静音剪（auto-editor 包装）")
    parser.add_argument("input", help="输入音视频（mp4/mp3/wav…）")
    parser.add_argument("-o", "--output", help="输出路径（缺省 <输入>_cut.mp4）")
    parser.add_argument("--margin", default="0.15sec",
                        help="静音两侧保留量（auto-editor --margin，默认 0.15sec）")
    parser.add_argument("--silent-speed", type=float, default=999999.0,
                        help="静音段倍速：999999=整段剪除（默认），8=8 倍快放")
    args = parser.parse_args(argv)

    inp = _resolve(args.input)
    if not inp.exists():
        print(f"[err] 输入不存在: {inp}", file=sys.stderr)
        return 1
    out = _resolve(args.output) if args.output else inp.with_name(
        f"{inp.stem}_cut{inp.suffix}")
    out.parent.mkdir(parents=True, exist_ok=True)

    cmd = [str(inp), "-o", str(out),
           "--margin", args.margin, "--silent-speed", str(args.silent_speed)]
    print(f"[silence_cut] auto-editor {' '.join(cmd)}")
    ret = _run_auto_editor(cmd)
    if ret == 0 and out.exists():
        print(f"OUTPUT={out}")
    return ret


if __name__ == "__main__":
    raise SystemExit(main())
