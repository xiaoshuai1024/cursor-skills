"""身份映射：统计 msg_id ↔ slug，回填 link-map 与 identity.json。

映射链（2026-08-29 spike 实证）：
- overrides：data/wechat-analytics/identity-overrides.json 人工指定 {msg_id: slug}，最高优先
  （平台标题是手写变体，源稿 wechat_title 对不上时由人工在此登记，48h 回看时顺手做）。
- 标题精确匹配：公众号侧标题 ↔ 源稿 front matter `wechat_title`（缺省回退 `title`）归一化全等。
- 包含匹配：归一化后最长公共子串 ≥12 字且跨 slug 唯一命中才落映射，其余列「人工确认」。
- 送达数 join：发表记录 appmsg_info[].appmsgid 与统计 msg_id 同域（spike 实证）。
- 回填：link-map[slug].weixin.stats_msgids 增量登记（向后兼容，不动其他字段）。
"""
from __future__ import annotations

import json
import os
import re
from typing import Optional

from .common import ARTICLES_SNAPSHOT, PROJECT_ROOT, append_jsonl, norm_title, now_iso, read_jsonl

LINK_MAP_PATH = os.path.join(PROJECT_ROOT, "content", "link-map.json")
POSTS_DIR = os.path.join(PROJECT_ROOT, "content", "posts")
IDENTITY_PATH = os.path.join(os.path.dirname(ARTICLES_SNAPSHOT), "..", "identity.json")


def load_identity() -> dict:
    if os.path.exists(IDENTITY_PATH):
        with open(IDENTITY_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"mapping": {}, "unresolved": [], "updated_at": None}


def save_identity(ident: dict) -> None:
    ident["updated_at"] = now_iso()
    os.makedirs(os.path.dirname(IDENTITY_PATH), exist_ok=True)
    with open(IDENTITY_PATH, "w", encoding="utf-8") as f:
        json.dump(ident, f, ensure_ascii=False, indent=1)


def front_matter_field(slug: str, field: str) -> Optional[str]:
    """从 content/posts/<slug>.md 的 TOML front matter 取字段（轻量正则，不引库）。"""
    path = os.path.join(POSTS_DIR, f"{slug}.md")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        head = f.read(4000)
    m = re.search(rf'^{field}\s*=\s*["\'](.+?)["\']', head, re.M)
    return m.group(1) if m else None


def latest_list_rows() -> dict[int, dict]:
    """每个 msg_id 取最新一次 list 快照。"""
    out: dict[int, dict] = {}
    for row in read_jsonl(ARTICLES_SNAPSHOT):
        if row.get("kind") != "list" or not row.get("msg_id"):
            continue
        cur = out.get(row["msg_id"])
        if cur is None or str(row.get("fetched_at")) > str(cur.get("fetched_at")):
            out[row["msg_id"]] = row
    return out


def load_overrides() -> dict[str, str]:
    """人工映射 {msg_id 字符串: slug}。"""
    path = os.path.join(os.path.dirname(IDENTITY_PATH), "identity-overrides.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _lcs(a: str, b: str) -> str:
    """最长公共子串（标题都很短，O(nm) 足够）。"""
    if not a or not b:
        return ""
    prev = [""] * (len(b) + 1)
    best = ""
    for i in range(1, len(a) + 1):
        cur = [""] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                cur[j] = prev[j - 1] + a[i - 1]
                if len(cur[j]) > len(best):
                    best = cur[j]
        prev = cur
    return best


def slug_wechat_titles() -> dict[str, str]:
    """slug → 公众号侧标题（wechat_title 优先，回退 title）。"""
    with open(LINK_MAP_PATH, encoding="utf-8") as f:
        link_map = json.load(f)
    out = {}
    for slug, rec in link_map.items():
        if slug.startswith("_") or not isinstance(rec, dict):
            continue
        t = front_matter_field(slug, "wechat_title") or front_matter_field(slug, "title")
        if t:
            out[slug] = t
    return out


def main() -> None:
    ident = load_identity()
    overrides = load_overrides()
    rows = latest_list_rows()
    titles = slug_wechat_titles()
    norm_titles = {slug: norm_title(t) for slug, t in titles.items()}

    mapping = ident.get("mapping", {})
    unresolved = []
    confirmed = 0
    for msg_id, row in rows.items():
        key = str(msg_id)
        if key in mapping:
            continue  # 已映射不重算
        if key in overrides:
            mapping[key] = {"slug": overrides[key], "item_idx": row.get("item_idx"), "title": row.get("title"), "confirmed_at": now_iso(), "how": "override"}
            confirmed += 1
            continue
        nt = norm_title(row.get("title", ""))
        # pass 1：精确
        hits = [slug for slug, t in norm_titles.items() if t == nt]
        how = "exact"
        # pass 2：LCS ≥12 且唯一
        if not hits:
            cands = []
            for slug, t in norm_titles.items():
                lcs = _lcs(nt, t)
                if len(lcs) >= 12:
                    cands.append((len(lcs), slug))
            cands.sort(reverse=True)
            if cands and (len(cands) == 1 or cands[0][0] > cands[1][0]):
                hits = [cands[0][1]]
                how = f"lcs{cands[0][0]}"
        if len(hits) == 1:
            mapping[key] = {"slug": hits[0], "item_idx": row.get("item_idx"), "title": row.get("title"), "confirmed_at": now_iso(), "how": how}
            confirmed += 1
        else:
            unresolved.append({"msg_id": msg_id, "title": row.get("title"), "reason": "ambiguous" if len(hits) > 1 else "no_match"})

    ident["mapping"] = mapping
    ident["unresolved"] = unresolved
    save_identity(ident)

    # 回填 link-map（只增不改：slug.weixin.stats_msgids 登记 msg_id 列表）
    by_slug: dict[str, list] = {}
    for msg_id_s, info in mapping.items():
        by_slug.setdefault(info["slug"], []).append(int(msg_id_s))
    with open(LINK_MAP_PATH, encoding="utf-8") as f:
        link_map = json.load(f)
    changed = 0
    for slug, msg_ids in by_slug.items():
        rec = link_map.get(slug)
        if rec is None:
            continue
        wx = rec.setdefault("weixin", {})
        merged = sorted(set(int(x) for x in wx.get("stats_msgids", [])) | set(msg_ids))
        if wx.get("stats_msgids") != [str(x) for x in merged]:
            wx["stats_msgids"] = [str(x) for x in merged]
            changed += 1
    if changed:
        with open(LINK_MAP_PATH, "w", encoding="utf-8") as f:
            json.dump(link_map, f, ensure_ascii=False, indent=2)
            f.write("\n")

    print(f"✅ 身份映射: 新确认 {confirmed}，累计 {len(mapping)}，未解决 {len(unresolved)}（link-map 回填 {changed} slug）")
    for u in unresolved:
        print(f"  ⚠️ {u['reason']}: {u['msg_id']} [{str(u.get('title'))[:30]}]")


if __name__ == "__main__":
    main()
