import os
import re
import config


def test_base_url_is_https():
    assert config.BASE_URL.startswith("https://")
    assert config.BASE_URL.endswith("/")


def test_build_dir_is_hidden_in_project():
    """构建目录应是项目内的隐藏目录(.wechat-build)。"""
    assert ".wechat-build" in config.WECHAT_BUILD_DIR
    assert os.path.isabs(config.WECHAT_BUILD_DIR)  # 绝对路径,便于 os.path.join


def test_styles_covers_core_tags():
    """覆盖核心标签,避免 publish 时漏样式。"""
    for tag in ["p", "h2", "h3", "pre", "code", "a", "img", "blockquote", "table"]:
        assert tag in config.INLINE_STYLES, f"缺少标签样式: {tag}"


def test_selectors_non_empty():
    """关键选择器不能为空字符串。"""
    for key in ["title", "save_draft", "img_upload_input"]:
        assert config.SELECTORS[key], f"选择器为空: {key}"


def test_cover_ratio_is_9_5():
    w, h = config.COVER_SIZE
    assert abs(w / h - 9 / 5) < 0.01
