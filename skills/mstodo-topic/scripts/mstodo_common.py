# -*- coding: utf-8 -*-
"""公共模块：路径 / endpoints 配置 / 抓包工具（mstodo-topic skill）。

通道: 浏览器登录态（To Do 网页版 to-do.microsoft.com）+ in-browser fetch 调网页应用自身 XHR 接口。
接口地址不硬编码——由登录后真实抓包固化进 .mstodo-topic/endpoints.json（应用内部接口可能随版本变，
失效重抓即可，脚本零改动）。
退出码约定：2 = 未登录 / 接口未固化（需 make todo-login），1 = 运行时错误。
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Any

os.environ.setdefault("PYTHONIOENCODING", "utf-8")


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


OUTPUT_ROOT = project_root() / ".mstodo-topic"
PROFILE_DIR = OUTPUT_ROOT / "msedge-profile"
ENDPOINTS_PATH = OUTPUT_ROOT / "endpoints.json"
CAPTURE_PATH = OUTPUT_ROOT / "capture.jsonl"
SNAPSHOT_DIR = OUTPUT_ROOT / "snapshots"
REPORT_DIR = OUTPUT_ROOT / "reports"

# 消费者(MSA)账户的应用域直达：localStorage/MSAL 状态都在 live.com，直达即可自动恢复会话
# （经 microsoft/office.com 进会在 /tasks/?app 空白页卡死，实测 2026-08-26）
TODO_HOME = "https://to-do.live.com/tasks/"
LOGIN_HOST_HINTS = ("login.live.com", "login.microsoftonline.com", "login.microsoft.com")


class MissingSetup(RuntimeError):
    """未登录 / 接口未固化，附人话提示。"""

    def __init__(self, hint: str):
        super().__init__(hint)
        self.hint = hint


class SessionExpired(RuntimeError):
    """登录态过期或未登录。"""

    def __init__(self, hint: str = ""):
        super().__init__(hint or "会话未登录或已过期 —— 重新执行 make todo-login 登录")
        self.hint = hint or "会话未登录或已过期 —— 重新执行 make todo-login 登录"


def ensure_dirs() -> None:
    for p in (OUTPUT_ROOT, SNAPSHOT_DIR, REPORT_DIR):
        p.mkdir(parents=True, exist_ok=True)


def load_endpoints() -> dict[str, Any]:
    """endpoints.json: {"origin": ..., "paths": {"lists": ..., "tasks": ..., "task_update": ...}, "headers": {...}}"""
    if not ENDPOINTS_PATH.exists():
        raise MissingSetup(
            "endpoints.json 不存在 —— 先 make todo-login capture=1 登录并抓包，"
            "再按抓包摘要把接口地址写进 .mstodo-topic/endpoints.json（格式见 SKILL.md「接口固化」）"
        )
    raw = json.loads(ENDPOINTS_PATH.read_text(encoding="utf-8"))
    return {
        "origin": raw.get("origin") or TODO_HOME,
        "paths": raw.get("paths") or {},
        "headers": raw.get("headers") or {},
    }


def endpoint_url(name: str, **params: str) -> str:
    ep = load_endpoints()
    template = ep["paths"].get(name)
    if not template:
        raise MissingSetup(
            f"endpoints.json 缺 paths.{name} —— make todo-login capture=1 重抓后补上"
        )
    filled = template.format(**params)
    return filled if filled.startswith("http") else f"{ep['origin']}{filled}"


_GUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
_LONG_NUM = re.compile(r"/\d{6,}")


def templated(url: str) -> str:
    """URL → 方法无关的路径模板：GUID/长数字段打码，便于聚合计数。"""
    parts = urllib.parse.urlsplit(url)
    path = _GUID.sub("{id}", parts.path)
    path = _LONG_NUM.sub("/{id}", path)
    query = "&".join(sorted(parts.query.split("&"))) if parts.query else ""
    return f"{parts.netloc}{path}" + (f"?{query}" if query else "")


def save_capture_line(record: dict[str, Any]) -> None:
    ensure_dirs()
    with CAPTURE_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def utc_now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + "Z"
