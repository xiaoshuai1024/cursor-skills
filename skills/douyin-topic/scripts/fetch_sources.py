# -*- coding: utf-8 -*-
"""抖音热榜数据拉取（免登录公开 API，单源自足）。

A 源: 抖音搜索热榜 API（免登录免签名）-> word_list(主榜) + trending_list(上升榜)
      主榜供 🔥热度系列，上升榜供 📈涨粉系列（2026-08-24 起随多源剥离承接）。

设计决策（探索阶段实证）:
- 仅用免登录公开 API，不依赖任何需登录/第三方 SaaS 的查询通道
- 结果缓存 5-10 分钟，避免打爆接口
- hot_value/view_count 间歇性为 0，作为可选字段透传（评分侧记中性分）
- 浏览器指纹池随机 UA + 随机退避，避免固定节奏被风控识别
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Optional

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# 浏览器指纹池: 每次请求随机取一个真实 UA，避免固定 UA + 固定节奏被风控识别
UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) "
    "Gecko/20100101 Firefox/127.0",
]

# 兼容旧引用（旧代码直接用 UA 常量）
UA = UA_POOL[0]

A_HOT_API = "https://www.douyin.com/aweme/v1/web/hot/search/list/"
A_BASE_PARAMS = {
    "device_platform": "webapp",
    "aid": "6383",
    "channel": "channel_pc_web",
    "pc_client_type": "1",
    "version_code": "170400",
    "version_name": "17.4.0",
    "cookie_enabled": "true",
    "screen_width": "1536",
    "screen_height": "864",
    "browser_language": "zh-CN",
    "browser_platform": "Win32",
    "browser_name": "Chrome",
    "browser_version": "126.0.0.0",
    "browser_online": "true",
    "engine_name": "Blink",
    "engine_version": "126.0.0.0",
    "os_name": "Windows",
    "os_version": "10",
    "cpu_core_num": "16",
    "device_memory": "8",
    "language": "zh-CN",
    "os_architecture": "x86_64",
    "platform": "PC",
    "history_len": "1",
}

CACHE_TTL = 600  # 10 分钟


def project_root() -> Path:
    """定位项目根（向上找 hugo.toml / .git）。"""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "hugo.toml").exists() or (parent / ".git").exists():
            return parent
    return current.parents[-1]


OUTPUT_ROOT = project_root() / ".douyin-topic"
CACHE_DIR = OUTPUT_ROOT / "cache"


# ---------- 通用 ----------

def _http_get_json(url: str, retries: int = 1) -> dict:
    """GET 一个 JSON 接口（随机 UA + 抖音 Referer）。失败随机退避重试。"""
    last_exc: Optional[Exception] = None
    for attempt in range(retries + 1):
        if attempt:
            # 指数退避 + 随机抖动: 固定间隔(2s/4s/…)本身就是反爬特征
            time.sleep(random.uniform(2, 6) * (2 ** (attempt - 1)))
        req = urllib.request.Request(url, headers={
            "User-Agent": random.choice(UA_POOL),
            "Referer": "https://www.douyin.com/",
            "Accept": "application/json, text/plain, */*",
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            last_exc = exc
    assert last_exc is not None
    raise last_exc


def cache_get(key: str) -> Optional[dict]:
    """读缓存（未过期则返回 dict，否则 None）。"""
    path = CACHE_DIR / f"{key}.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if time.time() - payload.get("ts", 0) > CACHE_TTL:
        return None
    return payload.get("items")


def cache_set(key: str, items: list[dict]) -> None:
    """写缓存（带时间戳）。"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"ts": time.time(), "items": items}
    (CACHE_DIR / f"{key}.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )


# ---------- A 源: 搜索热榜（免登录） ----------

def fetch_a(use_cache: bool = True) -> list[dict]:
    """拉取 A 源（搜索热榜 + 上升榜），统一成条目列表。失败抛异常。"""
    if use_cache:
        cached = cache_get("source_a")
        if cached is not None:
            return cached
    query = urllib.parse.urlencode(A_BASE_PARAMS)
    resp = _http_get_json(f"{A_HOT_API}?{query}")
    data = resp.get("data") or {}
    items: list[dict] = []
    for word_item in data.get("word_list") or []:
        items.append({
            "word": word_item.get("word", ""),
            "group_id": word_item.get("group_id"),
            "word_cover": _cover_url(word_item.get("word_cover")),
            "hot_value": word_item.get("hot_value"),
            "view_count": word_item.get("view_count"),
            "video_count": word_item.get("video_count"),
            "discuss_video_count": word_item.get("discuss_video_count"),
            "label": word_item.get("label"),
            "sub_board": "main",
            "source": "a",
        })
    for trend_item in data.get("trending_list") or []:
        items.append({
            "word": trend_item.get("word", ""),
            "group_id": trend_item.get("group_id"),
            "word_cover": _cover_url(trend_item.get("word_cover")),
            "hot_value": trend_item.get("hot_value"),
            "view_count": None,
            "video_count": trend_item.get("video_count"),
            "discuss_video_count": trend_item.get("discuss_video_count"),
            "event_time": trend_item.get("event_time"),
            "sub_board": "rising",
            "source": "a",
        })
    if use_cache:
        cache_set("source_a", items)
    return items


def _cover_url(cover: Optional[dict]) -> Optional[str]:
    """从 word_cover 取第一张封面图 URL。"""
    if not cover:
        return None
    url_list = cover.get("url_list") or []
    return url_list[0] if url_list else None


# ---------- 汇总 ----------

def fetch_all(use_cache: bool = True) -> dict[str, Any]:
    """拉取热榜数据（免登录单源）。返回汇总 dict。"""
    summary: dict[str, Any] = {
        "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "a_ok": False,
        "a": [],
        "notes": [],
    }
    try:
        summary["a"] = fetch_a(use_cache=use_cache)
        summary["a_ok"] = True
    except Exception as exc:
        summary["notes"].append(f"A 源失败: {str(exc)[:160]}")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="拉取抖音热榜数据(免登录公开 API)")
    parser.add_argument("--out", default=None, help="输出 JSON 文件路径（默认 stdout）")
    parser.add_argument("--no-cache", action="store_true", help="忽略缓存强制刷新")
    args = parser.parse_args()

    result = fetch_all(use_cache=not args.no_cache)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"✅ 数据已写入 {args.out}（a:{len(result['a'])}）")
    else:
        sys.stdout.write(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
