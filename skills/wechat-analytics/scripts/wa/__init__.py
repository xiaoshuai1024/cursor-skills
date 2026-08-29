"""wa 包初始化：项目根定位与 wechat-publishing 基建复用路径。

Makefile 以 `cd scripts && python -m wa.collect` 方式调用，包内统一从这里
拿 PROJECT_ROOT，避免各模块重复向上找。
"""
from __future__ import annotations

import os
import sys

PROJ_ROOT = os.environ.get("WECHAT_PROJECT_ROOT") or os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
WP_SCRIPTS = os.path.join(PROJ_ROOT, ".agents", "skills", "wechat-publishing", "scripts")


def ensure_wp_path() -> None:
    """把 wechat-publishing/scripts 加进 sys.path（复用 config.py / get_token）。"""
    if WP_SCRIPTS not in sys.path:
        sys.path.insert(0, WP_SCRIPTS)
