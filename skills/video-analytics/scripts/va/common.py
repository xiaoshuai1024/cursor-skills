# -*- coding: utf-8 -*-
"""公共基建：路径 / utf-8 / 快照 jsonl / link-map 读写。

设计要点（openspec/changes/video-analytics-skill/design.md）：
- 快照只 append 不覆盖（时间序列历史不可再生）；同 item 同日重复采集跳过。
- 失败降级：单平台异常不阻塞其他平台，错误写 data/analytics/errors.json。
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

CST = timezone(timedelta(hours=8))


def project_root() -> Path:
    env = os.environ.get("VA_PROJECT_ROOT")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[5]


ROOT = project_root()
SKILL_DIR = ROOT / ".agents" / "skills" / "video-analytics"
DATA_DIR = ROOT / "data" / "analytics"
SNAP_DIR = DATA_DIR / "snapshots"
REPORT_DIR = SKILL_DIR / ".video-analytics" / "reports"
LINK_MAP = ROOT / "content" / "link-map.json"

# 复用发布管线的登录态与反检测（不新开登录通道）
PUB_VENDOR = ROOT / "scripts" / "pub" / "vendor"
PUB_COOKIES = ROOT / "scripts" / "pub" / "cookies"


def setup_utf8() -> None:
    for enc in ("utf-8",):
        try:
            sys.stdout.reconfigure(encoding=enc)
            sys.stderr.reconfigure(encoding=enc)
        except Exception:
            pass
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def now_iso() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def today() -> str:
    return datetime.now(CST).strftime("%Y-%m-%d")


def snap_path(platform: str) -> Path:
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    return SNAP_DIR / f"{platform}.jsonl"


def load_snapshots(platform: str) -> list[dict]:
    p = snap_path(platform)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def append_snapshots(platform: str, records: list[dict]) -> tuple[int, int]:
    """append 快照；同 (item_id, 当日) 已存在则跳过。返回 (新增, 跳过)。"""
    existing = {(r.get("item_id"), (r.get("fetched_at") or "")[:10]) for r in load_snapshots(platform)}
    added = skipped = 0
    with snap_path(platform).open("a", encoding="utf-8") as f:
        for r in records:
            key = (r.get("item_id"), (r.get("fetched_at") or "")[:10])
            if key in existing:
                skipped += 1
                continue
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            existing.add(key)
            added += 1
    return added, skipped


def latest_by_item(platform: str) -> dict[str, dict]:
    """item_id → 最新快照（按 fetched_at 取最新）。"""
    out: dict[str, dict] = {}
    for r in load_snapshots(platform):
        iid = str(r.get("item_id") or "")
        if not iid:
            continue
        if iid not in out or (r.get("fetched_at") or "") > (out[iid].get("fetched_at") or ""):
            out[iid] = r
    return out


def load_link_map() -> dict:
    return json.loads(LINK_MAP.read_text(encoding="utf-8"))


def save_link_map(lm: dict) -> None:
    LINK_MAP.write_text(json.dumps(lm, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def record_error(platform: str, message: str) -> None:
    ERRS = DATA_DIR / "errors.json"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    errs = json.loads(ERRS.read_text(encoding="utf-8")) if ERRS.exists() else {}
    errs.setdefault("collect", []).append({"platform": platform, "error": message[:500], "at": now_iso()})
    # 只留最近 50 条
    errs["collect"] = errs["collect"][-50:]
    ERRS.write_text(json.dumps(errs, ensure_ascii=False, indent=1), encoding="utf-8")


def crop_title_inline(title: str, max_len: int) -> str:
    """与 scripts/pub/meta.py 的 crop_title 同口径（内联避免拖入发布管线 import 链）。"""
    if len(title) <= max_len:
        return title
    for sep in ["：", ":", "—", "-", "，", ","]:
        parts = title.split(sep, 1)
        if len(parts) == 2 and len(parts[0]) <= max_len:
            return parts[0].strip()
    return title[: max_len - 1] + "…"
