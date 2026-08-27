"""apply_wechat_overrides 单测(openspec wechat-article-retention)。

不依赖 fixtures/——任何机器可跑(用 tmp_path 造源稿)。
"""
import prepare


def _write_source_md(tmp_path, front_extra=""):
    posts_dir = tmp_path / "content" / "posts"
    posts_dir.mkdir(parents=True)
    (posts_dir / "ai-dev-test.md").write_text(
        f'+++\ntitle = "源稿标题"\n{front_extra}\n+++\n\n正文\n', encoding="utf-8"
    )


def test_overrides_apply_title_and_digest(tmp_path, monkeypatch):
    """front matter 含 wechat_title/wechat_digest → 覆盖生效。"""
    _write_source_md(
        tmp_path,
        'wechat_title = "公众号专属标题"\nwechat_digest = "前40字有痛点的摘要"',
    )
    monkeypatch.setattr(prepare.config, "PROJECT_ROOT", str(tmp_path))
    meta = {"title": "SEO长标题", "digest": "原摘要", "author": "a"}
    out = prepare.apply_wechat_overrides("ai-dev-test", meta)
    assert out["title"] == "公众号专属标题"
    assert out["digest"] == "前40字有痛点的摘要"


def test_overrides_fallback_when_fields_absent(tmp_path, monkeypatch):
    """无覆盖字段 → 原值不变(回退 title/description);源文件缺失同样回退。"""
    _write_source_md(tmp_path)
    monkeypatch.setattr(prepare.config, "PROJECT_ROOT", str(tmp_path))
    meta = {"title": "SEO长标题", "digest": "原摘要", "author": "a"}
    out = prepare.apply_wechat_overrides("ai-dev-test", meta)
    assert out["title"] == "SEO长标题"
    assert out["digest"] == "原摘要"
    # 源文件不存在(如 slug 拼错)也不崩,静默回退
    out2 = prepare.apply_wechat_overrides("not-exist-slug", meta)
    assert out2["title"] == "SEO长标题"


def test_overrides_digest_truncated_to_120(tmp_path, monkeypatch):
    """digest 超过 120 字截断(mp 草稿 digest0 上限 ret 64703)。"""
    _write_source_md(tmp_path, 'wechat_digest = "%s"' % ("长" * 150))
    monkeypatch.setattr(prepare.config, "PROJECT_ROOT", str(tmp_path))
    meta = {"title": "t", "digest": "d"}
    out = prepare.apply_wechat_overrides("ai-dev-test", meta)
    assert len(out["digest"]) == 120
