"""共享常量与工具：路径、端点、基准线、场景映射、mp 会话、jsonl 追加。

端点口径（2026-08-29 spike 实证，见 openspec wechat-analytics-skill tasks.md）：
- 直连 GET 均无需 fingerprint，用 wechat-profile 登录态 + token 即可。
- detailpage 数据服务端内嵌在 HTML 的 window.wx.cgiData JSON 岛里，无需轮询。
- datacubequery tmpl=28（留存曲线等深度数据）服务端异步计算，delay:true 时当日
  拿不到，诚实落 null，靠日频重试自然收敛。
"""
from __future__ import annotations

import json
import os
import random
import re
import time
from typing import Any, Optional

from . import ensure_wp_path

ensure_wp_path()

import config as wp_config  # noqa: E402  (wechat-publishing 的 config)

# ============ 路径 ============
PROJECT_ROOT = wp_config.PROJECT_ROOT
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "wechat-analytics")
SNAPSHOT_DIR = os.path.join(DATA_DIR, "snapshots")
ARTICLES_SNAPSHOT = os.path.join(SNAPSHOT_DIR, "articles.jsonl")
ACCOUNT_SNAPSHOT = os.path.join(SNAPSHOT_DIR, "account.jsonl")
ERRORS_PATH = os.path.join(DATA_DIR, "errors.json")
METRICS_PATH = os.path.join(DATA_DIR, "metrics.json")
DIAGNOSIS_PATH = os.path.join(DATA_DIR, "diagnosis.json")
REPORT_DIR = os.path.join(PROJECT_ROOT, ".wechat-analytics", "reports")
SPIKE_DIR = os.path.join(DATA_DIR, "spike")

# ============ mp 后台端点（只读）============
MP_BASE = "https://mp.weixin.qq.com"
# 单篇图文列表：msg_id/item_idx/title/ref_date/total_read_uv/read_uv_ratio/tendency_list
URL_ARTICLE_LIST = (
    MP_BASE + "/misc/appmsganalysis?action=get_article_list"
    "&begin_timestamp={d1}&end_timestamp={d2}&article_source=9999&offset={offset}&count={count}"
    "&token={token}&lang=zh_CN&f=json&ajax=1"
)
# 账号级日趋势×场景 + 流量来源（scene 9999 行含 collection_uv/source_uv/mass_pv）
URL_TENDENCY_SOURCE = (
    MP_BASE + "/misc/appmsganalysis?action=get_article_stat_tendency_and_source"
    "&begin_timestamp={d1}&end_timestamp={d2}&fingerprint={fp}&token={token}&lang=zh_CN&f=json&ajax=1"
)
# 发表记录：msgid/群发时间/sent_status.total（送达数，打开率分母）
URL_PUBLISH_LIST = (
    MP_BASE + "/cgi-bin/appmsgpublish?sub=list&begin={begin}&count={count}"
    "&query=&fakeid=&type=101_1&token={token}&lang=zh_CN&f=json&ajax=1"
)
# 单篇详情页（HTML，cgiData 内嵌 article_data_new/articleSummaryData/detailData）
URL_DETAIL_PAGE = (
    MP_BASE + "/misc/appmsganalysis?action=detailpage&msgid={msgid}&publish_date={pub_date}"
    "&type=int&pageVersion=1&token={token}&lang=zh_CN"
)
# 深度数据（留存曲线等）：异步，delay:true 当日不可得
URL_DATACUBE_QUERY = MP_BASE + "/misc/datacubequery"

# ============ 场景映射（scene → 流量来源）============
# UI 图例校准（2026-08-29）：推荐 85.6% 对应 scene 6（数据主导证实）；
# 其余标签按官方图文来源排序对位，采集保留 raw scene，standardize 用此表映射。
SCENE_LABELS = {
    1: "公众号消息",
    2: "聊天会话",
    4: "朋友圈",
    5: "公众号主页",
    6: "推荐",
    7: "搜一搜",
    0: "其它",
    9999: "合计",
}

# ============ 基准线（wechat-traffic-research 2026-08-28 调研口径）============
BASELINE_READ_DONE = {"terminate": 0.30, "pool": 0.50, "push": 0.65}  # 完读率 <30% 终止 / ≥50% 进池 / >65% 加推
BASELINE_OPEN = {"avg": 0.019, "good": 0.04}  # 打开率大盘 1.9%、4% 优秀
BASELINE_SHARE = (0.01, 0.03)  # 分享率正常区间 1%-3%
# 基线积累期门槛：已发表文章快照 < MIN_PUBLISHED_SAMPLES 只给行业基准对照
MIN_PUBLISHED_SAMPLES = 3
# 反哺建议门槛：快照累计 < MIN_FEEDBACK_SAMPLES 降级为观察清单
MIN_FEEDBACK_SAMPLES = 5

# ============ 采集纪律 ============
SLEEP_RANGE = (3.0, 8.0)  # 请求间随机间隔（秒）
LAUNCH_RETRY = 5
LAUNCH_RETRY_WAIT = 6.0
DETAIL_PAGE_WINDOW_DAYS = 30  # detailpage 仅统计发表后 30 天内数据（页面明示）


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S+08:00")


def today_str() -> str:
    return time.strftime("%Y-%m-%d")


def polite_sleep() -> None:
    time.sleep(random.uniform(*SLEEP_RANGE))


def append_jsonl(path: str, record: dict) -> None:
    """快照只 append，历史行永不修改（时间序列不可再生）。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def read_jsonl(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def load_errors() -> list[dict]:
    if os.path.exists(ERRORS_PATH):
        with open(ERRORS_PATH, encoding="utf-8") as f:
            return json.load(f)
    return []


def record_error(source: str, message: str, context: Optional[dict] = None) -> None:
    errors = load_errors()
    errors.append({"ts": now_iso(), "source": source, "error": str(message)[:500], "context": context or {}})
    os.makedirs(os.path.dirname(ERRORS_PATH), exist_ok=True)
    with open(ERRORS_PATH, "w", encoding="utf-8") as f:
        json.dump(errors[-200:], f, ensure_ascii=False, indent=1)


class MpSession:
    """mp 后台只读会话：persistent context 启动重试 + token + GET/POST 封装。

    只读承诺：仅封装 GET 与 datacubequery 的查询 POST，不触碰任何写端点。
    """

    def __init__(self, headless: bool = True):
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        self.ctx = None
        last_exc: Optional[Exception] = None
        for attempt in range(LAUNCH_RETRY):
            try:
                self.ctx = self._pw.chromium.launch_persistent_context(
                    wp_config.WECHAT_PROFILE_DIR,
                    channel=wp_config.BROWSER_CHANNEL,
                    headless=headless,
                    args=["--disable-blink-features=AutomationControlled"],
                    viewport={"width": 1440, "height": 900},
                )
                break
            except Exception as exc:  # Windows 上强杀实例后 profile 短暂不可用，重试即恢复
                last_exc = exc
                time.sleep(LAUNCH_RETRY_WAIT)
        if self.ctx is None:
            self.close()
            raise RuntimeError(f"mp profile 启动失败（重试 {LAUNCH_RETRY} 次）: {last_exc}")

        self.ctx.request.get(wp_config.WECHAT_MP_URL, timeout=30000)
        self.mp: Optional[dict] = None
        deadline = time.time() + wp_config.HEADLESS_LOGIN_WAIT
        while time.time() < deadline:
            from publish_mp import get_token

            self.mp = get_token(self.ctx.request)
            if self.mp:
                break
            time.sleep(2)
        if not self.mp:
            self.close()
            raise RuntimeError("mp 登录态失效（token/ticket 拿不到）——先 `make wechat-auth` 扫码恢复")

    def get(self, url: str, timeout: int = 30000) -> Any:
        return self.ctx.request.get(url, timeout=timeout, headers={"Referer": MP_BASE + "/"})

    def get_json(self, url: str, timeout: int = 30000) -> dict:
        resp = self.get(url, timeout)
        return resp.json()

    def datacube_query(self, tmpl: str, args: dict, fingerprint: str = "") -> dict:
        """datacubequery 查询 POST（tmpl=28 单篇留存等深度数据，delay:true 表示服务端未就绪）。"""
        import urllib.parse

        body = urllib.parse.urlencode(
            {
                "action": "query",
                "busi": "3",
                "tmpl": tmpl,
                "args": json.dumps(args, separators=(",", ":")),
                "fingerprint": fingerprint,
                "token": self.mp["token"],
                "lang": "zh_CN",
                "f": "json",
                "ajax": "1",
            }
        )
        resp = self.ctx.request.post(
            URL_DATACUBE_QUERY,
            timeout=30000,
            headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "Origin": MP_BASE, "Referer": MP_BASE + "/"},
            data=body.encode(),
        )
        return resp.json()

    def close(self) -> None:
        try:
            if self.ctx:
                self.ctx.close()
        finally:
            self._pw.stop()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


# ============ 身份映射辅助 ============
def norm_title(t: str) -> str:
    """标题归一化：去空白/全半角差异/标点，用于公众号↔slug 标题匹配。"""
    t = re.sub(r"\s+", "", t or "")
    t = t.replace("（", "(").replace("）", ")").replace("：", ":").replace("，", ",")
    return t.lower()
