import json
import os
import pytest
import prepare


FIXTURE_HTML = os.path.join(
    os.path.dirname(__file__), "..", "fixtures", "posts", "ai-dev-test", "index.html"
)
FIXTURE_LINK_MAP = os.path.join(
    os.path.dirname(__file__), "..", "fixtures", "link-map.json"
)
# fixtures/ 被 gitignore(仅原开发机存在);缺失时本文件用例整体跳过。
# 不依赖夹具的用例(apply_wechat_overrides)在 test_wechat_overrides.py,始终可跑。
try:
    LINK_MAP = json.load(open(FIXTURE_LINK_MAP, encoding="utf-8"))
except FileNotFoundError:
    pytest.skip("fixtures/ 缺失(gitignore,仅原开发机存在)", allow_module_level=True)


# ============ load_link_map ============
def test_load_link_map_reads_existing(tmp_path, monkeypatch):
    """link-map.json 存在时正常读取。"""
    map_file = tmp_path / "link-map.json"
    map_file.write_text('{"foo": {"weixin": {"draft_appmsgid": "123"}}}', encoding="utf-8")
    monkeypatch.setattr(prepare.config, "LINK_MAP_PATH", str(map_file))
    result = prepare.load_link_map()
    assert result == {"foo": {"weixin": {"draft_appmsgid": "123"}}}


def test_load_link_map_missing_returns_empty(tmp_path, monkeypatch):
    """文件不存在时返回空 dict,不崩。"""
    monkeypatch.setattr(prepare.config, "LINK_MAP_PATH", str(tmp_path / "nope.json"))
    assert prepare.load_link_map() == {}


# ============ replace_internal_links ============
from bs4 import BeautifulSoup  # noqa: E402


def _content_with_links():
    with open(FIXTURE_HTML, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
    return prepare.clean_and_style(soup)


def test_replace_links_uses_juejin_published_url():
    """掘金:有 published_url → 替换成掘金链接。"""
    content = _content_with_links()
    prepare.replace_internal_links(content, "juejin", LINK_MAP, "ai-dev-test")
    html_str = str(content)
    # other-article 在掘金有 published_url
    assert "https://juejin.cn/post/111222333" in html_str
    # 不应保留相对路径
    assert "href=/posts/other-article/" not in html_str


def test_replace_links_fallback_when_no_map_entry():
    """无映射条目 → 回退博客站绝对 URL。"""
    content = _content_with_links()
    prepare.replace_internal_links(content, "juejin", LINK_MAP, "ai-dev-test")
    html_str = str(content)
    assert "https://example.com/posts/not-in-map-article/" in html_str


def test_replace_links_weixin_draft_only_falls_back():
    """微信:只有草稿 appmsgid,没 published_url → 回退博客(草稿链接不能做正文内链)。"""
    content = _content_with_links()
    prepare.replace_internal_links(content, "weixin", LINK_MAP, "ai-dev-test")
    html_str = str(content)
    # draft-only-article 微信只有 draft_appmsgid,published_url=null
    assert "https://example.com/posts/draft-only-article/" in html_str
    # 不应使用草稿 appmsgid 做链接
    assert "100000888" not in html_str


def test_replace_links_weixin_published_used():
    """微信:有 published_url → 用微信永久链接。"""
    content = _content_with_links()
    prepare.replace_internal_links(content, "weixin", LINK_MAP, "ai-dev-test")
    html_str = str(content)
    assert "mp.weixin.qq.com/s?__biz=fake" in html_str


def test_extract_meta_title():
    meta = prepare.extract_meta(FIXTURE_HTML)
    assert meta["title"] == "测试文章标题"  # 去掉 " - Test Author"
    assert "Test Author" not in meta["title"]


def test_extract_meta_digest():
    meta = prepare.extract_meta(FIXTURE_HTML)
    assert meta["digest"] == "测试摘要:验证四道契约闸"


def test_extract_meta_author_default():
    meta = prepare.extract_meta(FIXTURE_HTML)
    assert meta["author"] == "Test Author"


# ============ clean_and_style ============
from bs4 import BeautifulSoup  # noqa: E402


def _read_content():
    with open(FIXTURE_HTML, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
    return prepare.clean_and_style(soup)


def test_clean_and_style_strips_decorations():
    """应剔除 paginav 导航等装饰元素。"""
    content = _read_content()
    html_str = str(content)
    assert "paginav" not in html_str
    assert "上下篇导航" not in html_str


def test_clean_and_style_excludes_toc():
    """details-content(TOC 目录)不应混入正文。"""
    content = _read_content()
    html_str = str(content)
    assert "目录占位" not in html_str
    assert "toc-content-static" not in html_str


def test_clean_and_style_strips_inline_toc():
    """正文内嵌的 toc 块也应被剔除(C1 回归测试)。"""
    content = _read_content()
    html_str = str(content)
    assert "toc-inline" not in html_str
    assert "内嵌目录" not in html_str


def test_clean_and_style_includes_body_text():
    """正文实际内容应保留。"""
    content = _read_content()
    html_str = str(content)
    assert "这是开头段落" in html_str
    assert "二级标题" in html_str


def test_clean_and_style_injects_inline():
    """每个支持的标签应有 inline style。"""
    content = _read_content()
    p = content.find("p")
    assert p.get("style")
    assert "line-height" in p["style"]


def test_clean_and_style_h2_has_border():
    """h2 应有主色左边框。"""
    content = _read_content()
    h2 = content.find("h2")
    assert "border-left:4px solid #2563eb" in h2["style"]


def test_clean_and_style_keeps_table():
    """表格保留并加样式。"""
    content = _read_content()
    table = content.find("table")
    assert table is not None
    th = table.find("th")
    assert "#2563eb" in th["style"]


# ============ convert_images ============
import os as _os  # noqa: E402

FIXTURE_SVG_DIR = _os.path.join(_os.path.dirname(__file__), "..", "fixtures", "svg")


def test_convert_images_replaces_src_with_placeholder(tmp_path):
    """正文 img 的 /svg/x.svg 应替换成 wx-image://N 占位符。"""
    content = _read_content()
    images = prepare.convert_images(
        content, svg_dir=FIXTURE_SVG_DIR, out_dir=str(tmp_path)
    )
    # 两张图
    assert len(images) == 2
    # 占位符格式
    for key in images:
        assert key.startswith("wx-image://")
    # 输出 png 文件存在
    for png_path in images.values():
        assert _os.path.exists(png_path)


def test_convert_images_first_image_is_cover(tmp_path):
    """第一张图应额外生成 cover.png,且为 9:5 比例。"""
    from PIL import Image
    content = _read_content()
    prepare.convert_images(
        content, svg_dir=FIXTURE_SVG_DIR, out_dir=str(tmp_path)
    )
    cover = _os.path.join(str(tmp_path), "cover.png")
    assert _os.path.exists(cover)
    with Image.open(cover) as im:
        w, h = im.size
        assert abs(w / h - 9 / 5) < 0.01


# ============ prepare (端到端) ============
FIXTURES_DIR = _os.path.join(_os.path.dirname(__file__), "..", "fixtures")


def test_prepare_e2e_produces_content_package(tmp_path, monkeypatch):
    """prepare(slug) 应生成 content.html + meta.json + cover.png。"""
    # 把 build 目录重定向到测试夹具
    monkeypatch.setattr(prepare.config, "PUBLIC_DIR", FIXTURES_DIR)
    monkeypatch.setattr(prepare.config, "SVG_DIR", FIXTURE_SVG_DIR)
    monkeypatch.setattr(prepare.config, "WECHAT_BUILD_DIR", str(tmp_path))

    result = prepare.prepare("ai-dev-test")

    assert _os.path.exists(result["content_html"])
    assert _os.path.exists(result["meta_json"])
    assert _os.path.exists(result["cover"])
    # meta.json 可解析
    import json
    with open(result["meta_json"], encoding="utf-8") as f:
        meta = json.load(f)
    assert meta["title"] == "测试文章标题"
    assert meta["author"] == "Test Author"


def test_prepare_raises_when_html_missing(tmp_path, monkeypatch):
    """渲染产物不存在时应抛 FileNotFoundError。"""
    monkeypatch.setattr(prepare.config, "PUBLIC_DIR", str(tmp_path))
    monkeypatch.setattr(prepare.config, "WECHAT_BUILD_DIR", str(tmp_path))
    import pytest
    with pytest.raises(FileNotFoundError):
        prepare.prepare("not-exist-slug")


# ============ apply_wechat_overrides(公众号变体) ============
# 用例已移至 test_wechat_overrides.py(不依赖 fixtures,任何机器可跑)


# ============ prepare_for_wechatsync(多平台生成)===========
def test_prepare_for_wechatsync_generates_per_platform_html(tmp_path, monkeypatch):
    """应按 SUPPORTED_PLATFORMS 生成各平台专属 HTML,内链按平台替换。"""
    fixture_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures")
    monkeypatch.setattr(prepare.config, "PUBLIC_DIR", fixture_dir)
    monkeypatch.setattr(prepare.config, "SVG_DIR", FIXTURE_SVG_DIR)
    monkeypatch.setattr(prepare.config, "WECHAT_BUILD_DIR", str(tmp_path))
    monkeypatch.setattr(prepare.config, "LINK_MAP_PATH", FIXTURE_LINK_MAP)
    # 屏蔽剪贴板写入(测试环境无 JXA)
    monkeypatch.setattr(prepare, "_copy_html_to_clipboard", lambda html: None)

    result = prepare.prepare_for_wechatsync("ai-dev-test")

    # 各平台 HTML 文件存在
    weixin_html = os.path.join(str(tmp_path), "ai-dev-test", "wechat-ready-weixin.html")
    juejin_html = os.path.join(str(tmp_path), "ai-dev-test", "wechat-ready-juejin.html")
    assert os.path.exists(weixin_html)
    assert os.path.exists(juejin_html)

    # 微信版:other-article 用微信永久链接
    with open(weixin_html, encoding="utf-8") as f:
        wx = f.read()
    assert "mp.weixin.qq.com/s?__biz=fake" in wx
    # 掘金版:other-article 用掘金链接
    with open(juejin_html, encoding="utf-8") as f:
        jj = f.read()
    assert "juejin.cn/post/111222333" in jj

    # 兼容:也保留 wechat-ready.html
    assert os.path.exists(os.path.join(str(tmp_path), "ai-dev-test", "wechat-ready.html"))



