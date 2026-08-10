# -*- coding: utf-8 -*-
"""三源真实数据拉取（抖音选题 skill）。

A 源: 抖音搜索热榜 API（免登录免签名）-> word_list(51) + trending_list(5 上升)
B 源: yxer query hot-events（蚁小二官方，账号已绑定）-> 热榜 + 真实播放量
C 源: yxer query challenges --query（方向关键词搜抖音话题）

设计决策（探索阶段实证）:
- A 源异常自动降级 B（双源兜底，抗签名收紧）
- 结果缓存 5-10 分钟，避免打爆接口
- 账号 id 动态解析（yxer accounts list），不硬编码
- A 源 hot_value/view_count 间歇性为 0，作为可选字段透传
- C 源 viewNum 量级小，仅作「方向内存在性」信号
"""
from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
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


def yxer(*args: str) -> dict:
    """执行 yxer CLI（蚁小二），返回 JSON 结果。"""
    result = subprocess.run(
        ["yxer", *args, "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        shell=sys.platform == "win32",  # Windows .cmd 需 shell; POSIX 直接调用(yxer 是可执行)
    )
    if result.returncode != 0:
        return {"ok": False, "error": {"message": (result.stderr or result.stdout)[:300]}}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "error": {"message": f"非 JSON 输出: {result.stdout[:200]}"}}


def resolve_douyin_account_id() -> tuple[Optional[str], str]:
    """动态解析抖音在线账号 id。返回 (account_id, error_msg)。"""
    resp = yxer("accounts", "list")
    if not resp.get("ok"):
        return None, f"yxer accounts list 失败: {resp.get('error', {}).get('message', '')}"
    accounts = resp.get("data") or []
    for acct in accounts:
        platform_name = acct.get("platformName", "") or ""
        if "抖音" in platform_name and acct.get("status") == 1:
            return acct.get("id"), ""
    return None, "抖音账号未找到或未在线（status!=1），请在蚁小二后台检查"


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


# ---------- B 源: yxer hot-events ----------

def fetch_b(account_id: str, use_cache: bool = True) -> tuple[list[dict], str]:
    """拉取 B 源（hot-events 热榜）。返回 (items, error_msg)。"""
    if use_cache:
        cached = cache_get("source_b")
        if cached is not None:
            return cached, ""
    resp = yxer("query", "hot-events", account_id)
    if not resp.get("ok"):
        return [], f"yxer query hot-events 失败: {resp.get('error', {}).get('message', '')}"
    items: list[dict] = []
    for entry in (resp.get("data") or {}).get("list") or []:
        raw = entry.get("raw") or {}
        items.append({
            "word": entry.get("yixiaoerName") or raw.get("word", ""),
            "group_id": raw.get("group_id"),
            "word_cover": entry.get("yixiaoerImageUrl") or raw.get("word_cover"),
            "hot_value": raw.get("hot_value"),
            "view_count": entry.get("viewNum"),
            "event_time": raw.get("event_time"),
            "video_count": raw.get("video_count"),
            "discuss_video_count": raw.get("discuss_video_count"),
            "label": raw.get("label"),
            "sub_board": "main",
            "source": "b",
        })
    if use_cache:
        cache_set("source_b", items)
    return items, ""


# ---------- C 源: yxer challenges（方向词搜索） ----------

def fetch_c(account_id: str, keywords: list[str], use_cache: bool = True) -> list[dict]:
    """逐词搜索方向话题（challenges）。C 源 viewNum 仅作存在性信号。"""
    if use_cache:
        cached = cache_get("source_c")
        if cached is not None:
            return cached
    items: list[dict] = []
    seen: set[str] = set()
    for idx, kw in enumerate(keywords):
        resp = yxer("query", "challenges", account_id, "--query", kw)
        if not resp.get("ok"):
            continue
        for entry in (resp.get("data") or {}).get("list") or []:
            word = entry.get("yixiaoerName") or ""
            if not word or word in seen:
                continue
            seen.add(word)
            items.append({
                "word": word,
                "viewNum": entry.get("viewNum"),
                "image_url": entry.get("yixiaoerImageUrl"),
                "match_keyword": kw,
                "source": "c",
            })
        # 词与词之间随机停顿 2.5-6.5s，模拟真人逐个搜索（固定节奏是反爬特征）
        if idx < len(keywords) - 1:
            time.sleep(random.uniform(2.5, 6.5))
    if use_cache:
        cache_set("source_c", items)
    return items


# ---------- 汇总 ----------

def fetch_all(keywords: list[str], use_cache: bool = True) -> dict[str, Any]:
    """三源并行拉取，A 异常降级 B。返回汇总 dict。"""
    summary: dict[str, Any] = {
        "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "a_ok": False, "b_ok": False, "c_ok": False,
        "a": [], "b": [], "c": [],
        "notes": [],
    }

    # A 源（免登录，最优先）
    try:
        summary["a"] = fetch_a(use_cache=use_cache)
        summary["a_ok"] = True
    except Exception as exc:
        summary["notes"].append(f"A 源失败，降级 B 源: {str(exc)[:120]}")

    # 账号 id
    account_id, acct_err = resolve_douyin_account_id()
    if not account_id:
        summary["notes"].append(f"B/C 源跳过: {acct_err}")
        return summary

    # B 源
    b_items, b_err = fetch_b(account_id, use_cache=use_cache)
    if b_err:
        summary["notes"].append(b_err)
    else:
        summary["b"] = b_items
        summary["b_ok"] = True

    # C 源
    try:
        summary["c"] = fetch_c(account_id, keywords, use_cache=use_cache)
        summary["c_ok"] = True
    except Exception as exc:
        summary["notes"].append(f"C 源失败: {str(exc)[:120]}")

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="三源拉取抖音热榜/话题数据")
    parser.add_argument("--out", default=None, help="输出 JSON 文件路径（默认 stdout）")
    parser.add_argument("--no-cache", action="store_true", help="忽略缓存强制刷新")
    parser.add_argument("--keywords-file", default=None,
                        help="方向关键词 JSON（默认取 topic_keywords.json 的 challenge_search）")
    args = parser.parse_args()

    keywords_file = args.keywords_file or str(
        Path(__file__).resolve().parent.parent / "topic_keywords.json"
    )
    try:
        kw_conf = json.loads(Path(keywords_file).read_text(encoding="utf-8"))
        keywords = kw_conf.get("challenge_search") or []
    except (OSError, json.JSONDecodeError):
        keywords = []

    result = fetch_all(keywords, use_cache=not args.no_cache)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"✅ 数据已写入 {args.out}（a:{len(result['a'])} b:{len(result['b'])} c:{len(result['c'])}）")
    else:
        sys.stdout.write(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
