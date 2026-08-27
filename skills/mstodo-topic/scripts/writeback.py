# -*- coding: utf-8 -*-
"""结论写回（mstodo-topic skill，浏览器登录态通道）。

用法:
  py -m writeback show --list-id <id> --task-id <id>
      查看任务当前正文/状态（写回前后核对用）
  py -m writeback resolve --list-id <id> --task-id <id> --note-file <path> [--keep-open]
      追加分析备注 + 标记完成；--keep-open 只备注不完成（生产后再完成的例外流）

语义: 先 GET 原任务拿正文（text/html 按 contentType 分支追加，不覆盖原备注），
改完把任务对象整体发回写接口（应用内部接口多为整对象更新，写法以抓包实测为准）。
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import browser_login as bl
import mstodo_common as mc
from fetch_todo import TASK_BODY_KEYS, normalize_task, pick

mc._utf8_stdio()


def get_task(list_id: str, task_id: str) -> dict[str, Any]:
    """单任务 GET 实测不被 todob2 支持（返回 error）→ 走清单拉取按 Id 过滤（实测可靠）。"""
    from fetch_todo import fetch_tasks

    for t in fetch_tasks(list_id):
        if t["taskId"] == task_id:
            return dict(t["_raw"])
    raise RuntimeError(f"清单里找不到任务 {task_id[-16:]}（可能已被删除/移走）")


def _append_note(content_type: str, original: str, note: str) -> str:
    stamp = f"—— mstodo-topic {datetime.now().strftime('%Y-%m-%d')} ——"
    if content_type == "html":
        lines = "<br>".join(html.escape(line) for line in note.splitlines() if line.strip())
        head = f"{original.rstrip()}<br><br>" if original.strip() else ""
        return f"{head}{html.escape(stamp)}<br>{lines}"
    head = f"{original.rstrip()}\n\n" if original.strip() else ""
    return f"{head}{stamp}\n{note.strip()}"


def _has_null(obj) -> bool:
    if obj is None:
        return True
    if isinstance(obj, dict):
        return any(_has_null(v) for v in obj.values())
    if isinstance(obj, list):
        return any(_has_null(x) for x in obj)
    return False


def _strip_nulls(obj):
    """todob2 整对象 PATCH 拒收 null（Reminder.LastSnoozedAt 等「必填属性得 null」报错），
    深度剔除值为 None 的键；含 null 的顶层嵌套对象（如 Reminder）整键省略——
    PATCH 语义=不动该属性，且该对象无法忠实回写。"""
    if isinstance(obj, dict):
        return {k: _strip_nulls(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [_strip_nulls(x) for x in obj]
    return obj


def _apply_note(task_raw: dict[str, Any], note: str, keep_open: bool) -> dict[str, Any]:
    """在原始任务对象上就地追加备注 + 置完成标记（substrate todob2 PascalCase，实测 2026-08-26）。"""
    body_field = pick(task_raw, *TASK_BODY_KEYS)
    if isinstance(body_field, dict):
        ct_key = "ContentType" if "ContentType" in body_field else "contentType"
        content_key = "Content" if "Content" in body_field else "content"
        content_type = str(body_field.get(ct_key) or "text")
        body_field[content_key] = _append_note(
            content_type if content_type.lower() != "text" else "text",
            str(body_field.get(content_key) or ""),
            note,
        )
    else:
        key = next((k for k in TASK_BODY_KEYS if k in task_raw), None)
        if key:
            task_raw[key] = _append_note("text", str(task_raw[key] or ""), note)
        else:
            task_raw["Body"] = {"Content": _append_note("text", "", note), "ContentType": "Text"}
    if not keep_open:
        for key in ("Status", "status", "state"):
            if key in task_raw:
                task_raw[key] = "Completed" if key == "Status" else "completed"
                break
        else:
            task_raw["Status"] = "Completed"
    return task_raw


def cmd_show(args: argparse.Namespace) -> int:
    task = get_task(args.list_id, args.task_id)
    normalized = normalize_task(task)
    normalized.pop("_raw", None)
    print(json.dumps(normalized, ensure_ascii=False, indent=2))
    return 0


def cmd_resolve(args: argparse.Namespace) -> int:
    note_path = Path(args.note_file)
    if not note_path.exists():
        print(f"❌ 备注文件不存在: {note_path}")
        return 1
    note = note_path.read_text(encoding="utf-8").strip()
    if not note:
        print("❌ 备注文件为空")
        return 1

    task_raw = get_task(args.list_id, args.task_id)
    before = normalize_task(task_raw)
    safe_payload = {k: _strip_nulls(v) for k, v in _apply_note(task_raw, note, args.keep_open).items()
                    if not (isinstance(v, dict) and _has_null(v))}
    payload = safe_payload
    # PATCH 响应即更新后的完整任务（实测），直接作核对，省一次清单拉取
    result = bl.fetch_json(mc.endpoint_url("task_update", listId=args.list_id, taskId=args.task_id), method="PATCH", payload=payload)

    after_norm = normalize_task(result)
    if not after_norm["taskId"]:
        raise RuntimeError("PATCH 响应异常（非任务对象），请用 show 核对后再试")
    print(f"✅ 已写回「{after_norm['title'] or before['title'][:30]}」")
    print(f"   备注: {len(before['body']['content'])} 字 → {len(after_norm['body']['content'])} 字（原备注保留）")
    if args.keep_open:
        print("   状态: 保持未完成（--keep-open）")
    else:
        print(f"   状态: {after_norm.get('status')}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="分析结论写回待办（浏览器登录态）")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_show = sub.add_parser("show", help="查看任务当前正文/状态")
    p_show.add_argument("--list-id", required=True)
    p_show.add_argument("--task-id", required=True)
    p_res = sub.add_parser("resolve", help="追加备注 + 标记完成")
    p_res.add_argument("--list-id", required=True, help="清单 id（快照 list.id）")
    p_res.add_argument("--task-id", required=True, help="任务 id（快照 tasks[].taskId）")
    p_res.add_argument("--note-file", required=True, help="备注内容文件（utf-8，多行可含产物路径）")
    p_res.add_argument("--keep-open", action="store_true", help="只追加备注不完成（生产后再完成）")
    args = parser.parse_args()
    try:
        return {"show": cmd_show, "resolve": cmd_resolve}[args.cmd](args)
    except mc.MissingSetup as err:
        print(f"❌ {err.hint}")
        return 2
    except mc.SessionExpired as err:
        print(f"❌ {err.hint}")
        return 2
    except RuntimeError as err:
        print(f"❌ {err}")
        return 1
    finally:
        bl.close_shared()


if __name__ == "__main__":
    sys.exit(main())
