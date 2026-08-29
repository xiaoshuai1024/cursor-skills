"""standardize 层单测：趋势解析 / 来源构成 / 账号日序列 / 诚实缺失。"""
from wa.standardize import account_daily, daily_from_summary, parse_tendency, source_mix_from_summary
from wa.diagnose import funnel, length_tier, rate_open, rate_read_done


def test_parse_tendency_30d():
    seq = ",".join(str(i) for i in range(30))
    out = parse_tendency(f"20260828_{seq}")
    assert len(out) == 30
    assert out["2026-08-28"] == 29
    assert out["2026-07-30"] == 0


def test_parse_tendency_bad():
    assert parse_tendency("") == {}
    assert parse_tendency("garbage") == {}


def test_source_mix():
    summary = [
        {"ref_date": "2026-08-06", "scene": 9999, "read_user": 100, "share_user": 4},
        {"ref_date": "2026-08-06", "scene": 6, "read_user": 85, "share_user": 0},
        {"ref_date": "2026-08-07", "scene": 6, "read_user": 10, "share_user": 0},
        {"ref_date": "2026-08-07", "scene": 7, "read_user": 5, "share_user": 0},
    ]
    mix = source_mix_from_summary(summary)
    assert mix["推荐"] == 95
    assert mix["搜一搜"] == 5
    assert "合计" not in mix


def test_daily_from_summary():
    summary = [
        {"ref_date": "2026-08-06", "scene": 9999, "read_user": 25, "share_user": 4},
        {"ref_date": "2026-08-07", "scene": 9999, "read_user": 21, "share_user": 4},
    ]
    d = daily_from_summary(summary)
    assert d["2026-08-06"]["read"] == 25
    assert d["2026-08-07"]["share"] == 4


def test_account_daily_scene_labels():
    rows = [
        {
            "fetched_at": "2026-08-29T10:00:00+08:00",
            "tendency_list": [
                {"date": 1785830400, "scene": 6, "read_uv": 530, "share_uv": 0},
                {"date": 1785830400, "scene": 1, "read_uv": 7, "share_uv": 0},
                {"date": 1785830400, "scene": 9999, "read_uv": 620, "share_uv": 90, "source_uv": 0, "collection_uv": 40, "mass_pv": 1},
            ],
        }
    ]
    daily = account_daily(rows)
    assert len(daily) == 1
    row = daily[0]
    assert row["scenes"]["推荐"] == 530
    assert row["collection_uv"] == 40
    assert row["read_uv"] == 620


def test_rates_and_tiers():
    assert rate_read_done(0.20).startswith("低于 30% 终止线")
    assert rate_read_done(0.55).startswith("进中级池")
    assert rate_read_done(0.70).startswith("持续加推")
    assert rate_read_done(None) == "缺失"
    assert rate_open(0.01).startswith("低于大盘")
    assert rate_open(0.05).startswith("优秀")
    assert length_tier(2000) == "≤2500 直发"
    assert length_tier(3000) == "2500-4000 压缩变体"
    assert length_tier(5000) == ">4000 拆系列/结构补偿"
    assert length_tier(None) is None


def test_funnel_honest_nulls():
    f = funnel({"read_uv": 100, "sent_total": 1000, "open_rate_total": 0.1, "session_open_rate": None})
    assert f["送达"] == 1000
    assert f["消息打开率"] is None
