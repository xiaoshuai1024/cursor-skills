"""diagnose / map_ids 层单测：归因动作、分桶样本门禁、反哺降级、标题归一化。"""
from wa.common import norm_title
from wa.diagnose import diagnose_article, factor_buckets, feedback
from wa.map_ids import front_matter_field


def _article(**over):
    base = {
        "msg_id": 1,
        "item_idx": 1,
        "slug": "test-slug",
        "title": "测试文章 Claude Code 实测",
        "ref_date": "2026-08-06",
        "sent_total": 1000,
        "read_uv": 500,
        "open_rate_total": 0.5,
        "session_open_rate": 0.05,
        "read_done_rate": 0.55,
        "avg_read_sec": 90,
        "share_rate": 0.02,
        "fav_rate": 0.01,
        "zaikan_rate": 0.01,
        "follow_conv": 5,
        "follow_rate": 0.01,
        "source_mix": {"推荐": 400, "搜一搜": 60},
        "has_detail": True,
        "word_count": 3000,
    }
    base.update(over)
    return base


def test_diagnose_good_article_no_actions():
    d = diagnose_article(_article(), [])
    assert d["read_done_class"].startswith("进中级池")
    # 各层达标 → 打开层不触发动作
    assert not any("打开层" in a for a in d["actions"])


def test_diagnose_low_read_done_action():
    d = diagnose_article(_article(read_done_rate=0.20), [])
    assert any("读完层" in a for a in d["actions"])


def test_diagnose_low_open_action():
    d = diagnose_article(_article(session_open_rate=0.01), [])
    assert any("打开层" in a for a in d["actions"])
    assert any("消息打开率 1.0%" in e for e in d["evidence"])


def test_buckets_sample_gate():
    arts = [_article(slug=f"s{i}") for i in range(3)]
    b = factor_buckets(arts)
    length = b["length_tier"]["2500-4000 压缩变体"]
    assert length["n"] == 3 and length["conclusive"] is True
    one = factor_buckets([_article(word_count=100)])
    tier = [v for v in one["length_tier"].values()][0]
    assert tier["conclusive"] is False


def test_feedback_degrades_when_thin():
    arts = [_article(slug=f"s{i}", read_done_rate=0.2 + i * 0.1) for i in range(3)]
    fb = feedback(arts)
    assert fb["mode"] == "observation"


def test_feedback_suggestion_when_enough():
    arts = [_article(slug=f"claude-test-{i}", title=f"claude {i}", read_done_rate=0.2 + i * 0.12) for i in range(6)]
    fb = feedback(arts)
    assert fb["mode"] == "suggestion"
    assert isinstance(fb.get("diff"), list)


def test_norm_title():
    assert norm_title("Hello  World：A") == norm_title("hello world:a")
    assert norm_title("（测试）") == norm_title("(测试)")


def test_front_matter_field_real_slug():
    # 仓库现存文章：wechat_title 字段存在与否都能安全返回
    v = front_matter_field("claude-code-must-have-plugins", "title")
    assert v is None or isinstance(v, str)
