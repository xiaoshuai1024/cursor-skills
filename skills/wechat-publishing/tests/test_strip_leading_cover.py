"""strip_leading_cover 单元测试(不依赖 fixtures,任何机器可跑)。

背景:博客端 25 篇源稿以 <img cover.png> 题图开头,公众号封面正是从这同一张
图裁出;平台首屏已展示封面,正文开头再放同一张就是同图重复,还挤走 150 字钩子。
"""
import prepare
from bs4 import BeautifulSoup


def _doc(*children: str):
    return BeautifulSoup("".join(children), "html.parser")


def test_strips_leading_cover_img():
    """首元素是 img(封面横幅) → 剥掉,后续正文保留。"""
    doc = _doc('<img src="/images/x/cover.png" alt="封面图">', "<p>钩子段落</p>")
    assert prepare.strip_leading_cover(doc) is True
    assert doc.find("img") is None
    assert "钩子段落" in doc.get_text()


def test_strips_cover_img_inside_lone_p():
    """img 被仅含图无文字的 <p> 包裹 → 连 <p> 一起剥。"""
    doc = _doc("<p><img src=\"/images/x/cover.png\"></p>", "<p>正文</p>")
    assert prepare.strip_leading_cover(doc) is True
    assert doc.find("img") is None
    assert "正文" in doc.get_text()


def test_keeps_leading_text_paragraph():
    """首元素是文字段落 → 不剥(开头无图的文章,如 ai-bill-cache-30x)。"""
    doc = _doc("<p>钩子在前</p>", '<img src="/images/x/cover.png">')
    assert prepare.strip_leading_cover(doc) is False
    assert doc.find("img") is not None


def test_keeps_text_before_diagram():
    """图嵌在正文段落之间 → 不剥(总览图不是封面横幅)。"""
    doc = _doc("<p>钩子</p>", "<p>铺垫</p>", '<img src="/svg/overview.svg">')
    assert prepare.strip_leading_cover(doc) is False
    assert doc.find("img") is not None


def test_skips_whitespace_only_strings():
    """img 前只有空白文本节点(换行) → 仍视为开头图,剥掉。"""
    doc = _doc("\n\n", '<img src="/images/x/cover.png">', "<p>正文</p>")
    assert prepare.strip_leading_cover(doc) is True
    assert doc.find("img") is None


def test_empty_content_is_noop():
    """空内容不崩、返回 False。"""
    doc = _doc("")
    assert prepare.strip_leading_cover(doc) is False


def test_strips_inside_content_div_wrapper():
    """真实管线形状:正文整体包在 <div id=content> 里(soup 唯一子元素),也要能剥。"""
    doc = BeautifulSoup(
        '<div id="content"><img alt="封面图" src="/images/x/cover.png">'
        "<p>钩子段落</p></div>",
        "html.parser",
    )
    assert prepare.strip_leading_cover(doc) is True
    assert doc.find("img") is None
    assert "钩子段落" in doc.get_text()


def test_keeps_diagram_inside_content_div_wrapper():
    """div 包裹下,首图前有正文段落 → 不剥。"""
    doc = BeautifulSoup(
        '<div id="content"><p>钩子段落</p>'
        '<img alt="总览图" src="/svg/overview.svg"></div>',
        "html.parser",
    )
    assert prepare.strip_leading_cover(doc) is False
    assert doc.find("img") is not None
