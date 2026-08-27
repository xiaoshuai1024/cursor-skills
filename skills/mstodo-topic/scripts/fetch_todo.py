# -*- coding: utf-8 -*-
"""待办拉取（mstodo-topic skill，浏览器登录态通道）。

用法:
  py -m fetch_todo lists                          列出全部清单（displayName + id）
  py -m fetch_todo tasks --list <清单名> [--top N]  拉指定清单最新未完成待办（默认 10 条）

说明:
  接口来自 endpoints.json（抓包固化）。响应字段映射做了多候选兼容（id/taskId、title/name、
  createdDateTime/createdAt…），接口固化后如字段对不上，改这里的关键词候选即可。
  快照落 .mstodo-topic/snapshots/<时间戳>-<清单>.json（含完整正文，供分析阶段读取）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from typing import Any

import browser_login as bl
import mstodo_common as mc

mc._utf8_stdio()

# 字段映射：substrate todob2 为 PascalCase（实测 2026-08-26：Value/Id/Name/Subject/Status/Body.Content），
# 小写候选留作 Graph 风格兜底；接口再变改这里。
LIST_KEY_CANDIDATES = ("Value", "value", "lists", "folders", "items", "data", "tasks")
LIST_ID_KEYS = ("Id", "id", "listId", "folderId")
LIST_NAME_KEYS = ("Name", "displayName", "name", "title")
TASK_ID_KEYS = ("Id", "id", "taskId")
TASK_TITLE_KEYS = ("Subject", "Title", "title", "name", "subject")
TASK_CREATED_KEYS = ("CreatedDateTime", "createdDateTime", "createdAt")
TASK_BODY_KEYS = ("Body", "body", "notes", "content")
TASK_IMPORTANCE_KEYS = ("Importance", "importance")
TASK_STATUS_KEYS = ("Status", "status", "state")


def pick(source: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in source and source[key] is not None:
            return source[key]
    return None


def extract_array(resp: Any) -> list[dict[str, Any]]:
    """从响应里找清单数组：命中候选键，或响应本身是数组。"""
    if isinstance(resp, list):
        return [x for x in resp if isinstance(x, dict)]
    if isinstance(resp, dict):
        for key in LIST_KEY_CANDIDATES:
            inner = resp.get(key)
            if isinstance(inner, list) and (not inner or isinstance(inner[0], dict)):
                return [x for x in inner if isinstance(x, dict)]
        # 再扫一层嵌套（如 {"data": {"lists": [...]}}）
        for value in resp.values():
            if isinstance(value, dict):
                found = extract_array(value)
                if found:
                    return found
    return []


def _fmt_local(iso: str | None) -> str:
    if not iso:
        return "-"
    try:
        aware = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return aware.astimezone().strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return str(iso)[:16]


def _slug(name: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "-", name).strip("-") or "list"


def normalize_list(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(pick(raw, *LIST_ID_KEYS) or ""),
        "displayName": str(pick(raw, *LIST_NAME_KEYS) or ""),
    }


def normalize_task(raw: dict[str, Any]) -> dict[str, Any]:
    body_field = pick(raw, *TASK_BODY_KEYS)
    if isinstance(body_field, dict):
        content = body_field.get("Content") if "Content" in body_field else body_field.get("content")
        ct = body_field.get("ContentType") if "ContentType" in body_field else body_field.get("contentType")
        body = {"content": str(content or ""), "contentType": str(ct or "text")}
    else:
        body = {"content": str(body_field or ""), "contentType": "text"}
    return {
        "taskId": str(pick(raw, *TASK_ID_KEYS) or ""),
        "title": str(pick(raw, *TASK_TITLE_KEYS) or ""),
        "status": pick(raw, *TASK_STATUS_KEYS),
        "importance": pick(raw, *TASK_IMPORTANCE_KEYS),
        "createdDateTime": pick(raw, *TASK_CREATED_KEYS),
        "body": body,
        "_raw": raw,
    }


def get_lists() -> list[dict[str, Any]]:
    resp = bl.fetch_json(mc.endpoint_url("lists"))
    normalized = [normalize_list(x) for x in extract_array(resp)]
    return [x for x in normalized if x["id"] and x["displayName"]]


def resolve_list(name: str) -> tuple[str, str]:
    """清单名 → (id, displayName)。精确 → 包含；0/多命中都列出候选退出。"""
    lists = get_lists()
    target = name.strip().casefold()
    exact = [li for li in lists if li["displayName"].casefold() == target]
    fuzzy = [li for li in lists if target in li["displayName"].casefold()]
    picked = None
    if len(exact) == 1:
        picked = exact[0]
    elif not exact and len(fuzzy) == 1:
        picked = fuzzy[0]
    if picked is None:
        if not lists:
            print("❌ 账号内没有任何清单")
        elif exact:
            print(f"❌ 清单「{name}」精确命中多个：{'、'.join(li['displayName'] for li in exact)}")
        else:
            print(f"❌ 清单「{name}」未命中，可选清单：{'、'.join(li['displayName'] for li in lists)}")
        raise SystemExit(1)
    return picked["id"], picked["displayName"]


def fetch_tasks(list_id: str) -> list[dict[str, Any]]:
    resp = bl.fetch_json(mc.endpoint_url("tasks", listId=list_id))
    tasks = [normalize_task(x) for x in extract_array(resp)]
    return [t for t in tasks if t["taskId"]]


def cmd_lists(_args: argparse.Namespace) -> int:
    lists = get_lists()
    if not lists:
        print("（账号内没有任何清单，或字段映射需按抓包校正——见 fetch_todo.py 候选键）")
        return 0
    print(f"{'清单名':<20} id")
    for li in lists:
        print(f"{li['displayName']:<20} {li['id']}")
    return 0


def cmd_tasks(args: argparse.Namespace) -> int:
    list_id, list_name = resolve_list(args.list)
    tasks = fetch_tasks(list_id)
    open_tasks = [t for t in tasks if "completed" not in str(t.get("status") or "").lower()]
    open_tasks.sort(key=lambda t: str(t.get("createdDateTime") or ""), reverse=True)
    picked = open_tasks[: max(int(args.top), 1)]

    mc.ensure_dirs()
    fetched_at = datetime.now().astimezone().isoformat(timespec="seconds")
    snap_path = mc.SNAPSHOT_DIR / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{_slug(list_name)}.json"
    snapshot = {
        "fetched_at": fetched_at,
        "list": {"id": list_id, "displayName": list_name},
        "count": len(picked),
        "total_open": len(open_tasks),
        "tasks": [{k: v for k, v in t.items() if k != "_raw"} for t in picked],
    }
    snap_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"清单「{list_name}」未完成待办 {len(open_tasks)} 条，取最新 {len(picked)} 条：")
    print(f"{'#':<3} {'taskId':<40} {'创建':<17} 标题")
    for idx, t in enumerate(picked, 1):
        print(f"{idx:<3} {t['taskId']:<40} {_fmt_local(t.get('createdDateTime')):<17} {t['title']}")
    for idx, t in enumerate(picked, 1):
        content = str((t.get("body") or {}).get("content") or "").strip()
        if content:
            brief = re.sub(r"\s+", " ", content)[:80]
            print(f"  [{idx}] 正文: {brief}")
    print(f"\n快照 → {snap_path}（分析阶段读它，勿重复拉取）")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Microsoft To Do 待办拉取（浏览器登录态）")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("lists", help="列出全部清单")
    p_tasks = sub.add_parser("tasks", help="拉指定清单最新未完成待办")
    p_tasks.add_argument("--list", required=True, help="清单名（精确或唯一包含匹配）")
    p_tasks.add_argument("--top", default="10", help="取最新 N 条（默认 10）")
    args = parser.parse_args()
    try:
        return {"lists": cmd_lists, "tasks": cmd_tasks}[args.cmd](args)
    except mc.MissingSetup as err:
        print(f"❌ {err.hint}")
        return 2
    except mc.SessionExpired as err:
        print(f"❌ {err.hint}")
        bl.close_shared()
        return 2
    except RuntimeError as err:
        print(f"❌ {err}")
        bl.close_shared()
        return 1
    finally:
        bl.close_shared()


if __name__ == "__main__":
    sys.exit(main())
