"""模块1:内容准备 —— 从 Hugo 渲染产物生成「公众号就绪」内容包。

不依赖 Playwright,可独立运行检查转换质量。
"""
from __future__ import annotations
import io
import json
import os
import re
import subprocess
import sys
# Windows 控制台默认 GBK，打印 emoji/特殊字符会 UnicodeEncodeError；统一 UTF-8 输出
# pytest 下不能包装：capture 会替换 sys.stdout，包装其 .buffer 导致 I/O 冲突（测试全挂）
if "pytest" not in sys.modules:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
from bs4 import BeautifulSoup
from PIL import Image

import config


def load_link_map() -> dict:
    """读取内链映射表 content/link-map.json。

    结构: {slug: {platform: {draft_appmsgid/draft_id, published_url}}}
    文件不存在时返回空 dict(不报错,内链回退博客站)。
    """
    if not os.path.exists(config.LINK_MAP_PATH):
        return {}
    with open(config.LINK_MAP_PATH, encoding="utf-8") as f:
        return json.load(f)


def extract_meta(html_path: str) -> dict:
    """从渲染产物 HTML 提取标题、摘要、作者。

    Args:
        html_path: public/posts/<slug>/index.html 路径。

    Returns:
        {"title": str, "digest": str, "author": str}
    """
    with open(html_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    # 标题:去站点名后缀(先精确匹配 env 后缀,再兜底匹配「1024 工程笔记」写法变体)
    raw_title = soup.find("title").get_text() if soup.find("title") else ""
    title = re.sub(re.escape(config.SITE_NAME_SUFFIX) + r"\s*$", "", raw_title).strip()
    title = re.sub(r"\s*[-–—:：]?\s*1024\s*工程笔记\s*$", "", title).strip()

    # 摘要:取 meta description
    desc_tag = soup.find("meta", attrs={"name": "description"})
    digest = desc_tag.get("content", "").strip() if desc_tag else ""
    digest = digest[:120]  # mp 草稿 digest0 上限 120 字（ret 64703）

    return {
        "title": title,
        "digest": digest,
        "author": config.DEFAULT_AUTHOR,
    }


def apply_wechat_overrides(slug: str, meta: dict) -> dict:
    """用 front matter 可选字段 wechat_title / wechat_digest 覆盖公众号标题/摘要。

    留存规范(openspec wechat-article-retention):公众号标题不是博客 SEO 标题,
    ≤25 字、钩子前 13 字;摘要前 40 字承担打开转化。字段缺省回退 title/description,
    Hugo 忽略未知 front matter 字段,不影响构建。
    """
    src_path = os.path.join(config.PROJECT_ROOT, "content", "posts", f"{slug}.md")
    if not os.path.exists(src_path):
        return meta
    with open(src_path, encoding="utf-8") as f:
        text = f.read()
    parts = text.split("+++", 2)
    if len(parts) < 3:
        return meta
    front = parts[1]

    def _field(key: str) -> str:
        # 只认单行引号字符串;多行/无引号写法视为未填,走回退
        m = re.search(rf'^{key}\s*=\s*["\'](.*?)["\']\s*$', front, re.M)
        return m.group(1).strip() if m else ""

    title = _field("wechat_title")
    digest = _field("wechat_digest")[:120]  # mp 草稿 digest0 上限 120 字(ret 64703)
    if title:
        meta["title"] = title
        print(f"📝 公众号标题变体生效: {title}")
    if digest:
        meta["digest"] = digest
        print(f"📝 公众号摘要变体生效({len(digest)}字)")
    return meta


# 需剔除的装饰元素 class 列表(正则匹配 class 属性)
_STRIP_SELECTORS = [
    {"class": re.compile(r"paginav")},
    {"class": re.compile(r"copy-icon-btn")},
    {"class": re.compile(r"post-share")},
    {"class": re.compile(r"post-comment")},
    {"class": re.compile(r"post-meta")},
    {"class": re.compile(r"post-toc")},
]


def clean_and_style(soup: BeautifulSoup):
    """清洗正文(剔除装饰元素)并注入 inline 样式。

    Args:
        soup: 已解析的完整页面 BeautifulSoup 对象。

    Returns:
        一个 BeautifulSoup 对象,仅含正文内容(已加 inline 样式)。
        注意图源占位符替换由 convert_images 完成。
    """
    # 定位正文容器:FixIt 用 <div id="content" class="content">
    # 注意:details-content(id=toc-content-static)是 TOC 目录,不是正文
    content = soup.find("div", id="content") or soup.find("div", class_="content")
    if content is None:
        # 备选:取 article 内全部
        article = soup.find("article")
        content = article if article else soup

    # 克隆,避免污染原 soup
    doc = BeautifulSoup(str(content), "html.parser")

    # 剔除装饰元素(按 class 正则)
    for selector in _STRIP_SELECTORS:
        for el in doc.find_all(attrs=selector):
            el.decompose()

    # 剔除 nav 标签(上下篇导航)和正文中内嵌的 toc 块
    # 注:正文容器是 div#content,侧边 TOC(details-content)在抓取时已排除,
    # 所以这里对正文内的 toc 元素无条件删除即可。
    for nav in doc.find_all("nav"):
        nav.decompose()
    for toc in doc.find_all(class_=re.compile(r"toc")):
        toc.decompose()

    # 注入 inline 样式:覆盖标签 class/style,统一加 config 样式
    for tag in doc.find_all(True):
        if tag.name in config.SKIP_STYLE_TAGS:
            continue
        style = config.INLINE_STYLES.get(tag.name)
        if style:
            tag["style"] = style
        # 清掉 class,避免残留冲突
        if "class" in tag.attrs:
            del tag["class"]

    return doc


def strip_leading_cover(content) -> bool:
    """剥掉正文开头的封面重复图(weixin 版专用)。

    2026-09-05 定规后博客正文已不内嵌封面图,本函数常态空转,保留作历史稿件
    兼容(旧渲染产物/回滚场景里正文仍可能以 <img cover.png> 题图开头,剥掉防
    推送卡片与首屏同图重复)。
    判据:文档里第一张 <img>,且沿其祖先链向上找不到任何前置兄弟
    (元素或可见文字)——即它是文档的第一个可见内容。首图嵌在段落之间的
    总览图前面有正文,不剥。
    必须在 convert_images 之后调用——封面裁切取的是剥前的第一张图。
    """
    img = content.find("img")
    if img is None:
        return False
    node = img
    while node is not content:
        for sib in node.previous_siblings:
            if isinstance(sib, str):
                if sib.strip():
                    return False  # 前面有可见文字 → img 不是开头
                continue
            return False  # 前面有兄弟元素 → img 不是开头
        node = node.parent
        if node is None:
            return False
    parent = img.parent
    img.decompose()
    # 外壳因剥图变空(仅剩空白)时一并清掉,避免正文开头留空段落
    if parent is not None and parent.name == "p" and not parent.get_text(strip=True) \
            and parent.find() is None:
        parent.decompose()
    return True


def replace_internal_links(content, platform: str, link_map: dict, _current_slug: str = "") -> None:
    """就地替换正文里的博客内链为对应平台的链接。

    替换规则(对每个 <a href="/posts/<slug>/> 或绝对博客 URL):
    1. 该 slug 在 link_map 有 published_url → 替换成平台链接
    2. 否则 → 回退到博客站绝对 URL(BASE_URL + posts/<slug>/)

    特殊:微信草稿 appmsgid 不能做正文内链(必须是已发布永久链接),
    所以 weixin 只有 draft_appmsgid 没 published_url 时也回退博客。

    Args:
        content: BeautifulSoup 对象(就地修改)
        platform: 目标平台(weixin/juejin)
        link_map: load_link_map() 的返回值
        _current_slug: 当前文章 slug(预留,当前未用)
    """
    # 匹配 /posts/<slug>/、BASE_URL + posts/<slug>/，以及 Hugo relref 渲染的
    # 相对路径 posts/<slug>/(无前导斜杠，曾漏匹配 → 原样留在微信 HTML 触发 64562)
    blog_post_re = re.compile(r"^(?:https?://[^/]+)?/?posts/([^/]+)/?$")

    for a in content.find_all("a"):
        href = a.get("href", "")
        m = blog_post_re.match(href)
        if m:
            target_slug = m.group(1)
            entry = link_map.get(target_slug, {}).get(platform, {})
            published = entry.get("published_url")
            if published:
                a["href"] = published
            elif platform == "weixin":
                # mp 拒收一切非 mp.weixin 域链接(64562)：无已发布链接就解包保留内容
                a.unwrap()
            else:
                # 无映射或只有草稿 → 回退博客站绝对 URL
                a["href"] = config.BASE_URL + "posts/" + target_slug + "/"
        elif platform == "weixin" and not href.startswith(
            ("https://mp.weixin.qq.com", "http://mp.weixin.qq.com")
        ):
            # 其余非 mp 链接(外链、/svg /images 内部资源链接图片等)一律解包，
            # 保留文字与图(图片包链接是 DSH 系文章的常见形态)
            a.unwrap()


def _svg_to_png(svg_path: str, out_path: str, width: int) -> None:
    """把 SVG 转 PNG。按优先级尝试:rsvg-convert → cairosvg → sharp(Node.js)。"""
    import shutil
    import sys
    if shutil.which("rsvg-convert"):
        subprocess.run(
            ["rsvg-convert", "-w", str(width), svg_path, "-o", out_path],
            check=True, capture_output=True,
        )
        return

    # 尝试 cairosvg(Python,需 libcairo 动态库)
    try:
        import cairosvg
        cairosvg.svg2png(
            url=svg_path, write_to=out_path,
            output_width=width,
        )
        return
    except (ImportError, OSError):
        pass

    # 回退:sharp(Node.js,内置 libvips,Windows 免安装)
    if shutil.which("node"):
        script = (
            "require('sharp')("
            f"{repr(svg_path)}"
            f").resize({width}).png().toFile("
            f"{repr(out_path)}"
            ").then(()=>process.exit(0)).catch(e=>{console.error(e);process.exit(1)})"
        )
        # sharp 在仓库根 node_modules
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        env = os.environ.copy()
        env["NODE_PATH"] = os.path.join(repo_root, "node_modules") + os.pathsep + env.get("NODE_PATH", "")
        try:
            subprocess.run(
                ["node", "-e", script],
                check=True, capture_output=True, env=env,
            )
            return
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass  # sharp 未装/失败 → 落 Playwright 兜底

    # 回退:Playwright（chrome 渲染 SVG 截图；macOS 自包含，无需 rsvg/cairo/sharp）
    try:
        from playwright.sync_api import sync_playwright
        chan = os.environ.get("BROWSER_CHANNEL", "msedge" if sys.platform == "win32" else "chrome")
        with sync_playwright() as _p:
            _b = _p.chromium.launch(channel=chan, headless=True,
                                    args=["--disable-blink-features=AutomationControlled"])
            _pg = _b.new_page(viewport={"width": width, "height": 800}, device_scale_factor=2)
            _pg.goto("file://" + os.path.abspath(svg_path))
            # file:// 加载 .svg 是 XML 文档(无 HTML head)，add_style_tag 会失败；直接设 svg 元素 style
            _pg.evaluate("() => { const s = document.querySelector('svg') || document.documentElement; if (s) { s.style.width='100%'; s.style.height='auto'; s.style.display='block'; } }")
            _pg.wait_for_timeout(300)
            _el = _pg.query_selector("svg") or _pg.query_selector("body")
            _el.screenshot(path=out_path)
            _b.close()
        return
    except Exception:
        pass

    raise RuntimeError(
        "SVG→PNG 转换失败:需要 rsvg-convert / cairosvg / sharp / Playwright 至少一个可用"
    )


def _make_cover(src_png: str, out_path: str, size: tuple) -> None:
    """把 PNG 居中裁剪到目标比例(9:5)。"""
    target_w, target_h = size
    target_ratio = target_w / target_h
    with Image.open(src_png) as im:
        im = im.convert("RGB")
        src_ratio = im.width / im.height
        if src_ratio > target_ratio:
            # 太宽,裁左右
            new_w = int(im.height * target_ratio)
            left = (im.width - new_w) // 2
            im = im.crop((left, 0, left + new_w, im.height))
        else:
            # 太高,裁上下
            new_h = int(im.width / target_ratio)
            top = (im.height - new_h) // 2
            im = im.crop((0, top, im.width, top + new_h))
        im = im.resize(size, Image.LANCZOS)
        im.save(out_path, "PNG")


def convert_images(content, svg_dir: str, out_dir: str, src_mode: str = "placeholder") -> dict:
    """把正文里的 SVG img 转成 PNG,src 替换为占位符或本地路径。

    第一张图额外生成 cover.png。

    Args:
        content: clean_and_style 的返回值(BeautifulSoup 对象)。
        svg_dir: SVG 源目录(取 static/svg/ 或测试夹具目录)。
        out_dir: PNG 输出目录(.wechat-build/<slug>/)。
        src_mode: "placeholder" → src 改为 wx-image://N(给 Playwright);
                  "filepath"   → src 改为 PNG 绝对路径(给 Wechatsync 粘贴)。

    Returns:
        "placeholder" 模式:{占位符: png 绝对路径} 映射;
        "filepath" 模式:空 dict(图片已在 HTML 里,无需后续替换)。
    """
    os.makedirs(out_dir, exist_ok=True)
    images = {}
    failed = []
    idx = 0
    import shutil
    static_dir = os.path.dirname(svg_dir)   # <root>/static
    for img in content.find_all("img"):
        src = img.get("src", "")
        # 解析 /svg/xxx.svg → 文件名
        m = re.match(r"/svg/(.+\.svg)(?:\?.*)?$", src)
        # 正文首图常态是 /images/<slug>/cover.png 这类本地栅格图——
        # 此前只处理 SVG，导致首图不进循环、封面错取第一张 SVG 的裁切
        raster = re.match(r"^/images/[^?#]+\.(?:png|jpe?g|gif)$", src)
        if not m and not raster:
            continue
        idx += 1
        png_path = os.path.join(out_dir, f"img-{idx}.png")
        if raster:
            src_path = os.path.join(static_dir, src.lstrip("/").split("?")[0])
            if not os.path.exists(src_path):
                failed.append(src)
                img.replace_with(f"[图片缺失: {src}]")
                continue
            shutil.copyfile(src_path, png_path)
        else:
            svg_name = m.group(1)
            svg_path = os.path.join(svg_dir, svg_name)

            # SVG 缺失或转换失败:跳过,插占位文字,记日志(不中断整体流程)
            if not os.path.exists(svg_path):
                failed.append(svg_name)
                img.replace_with(f"[图片缺失: {svg_name}]")
                continue
            try:
                _svg_to_png(svg_path, png_path, config.IMAGE_RENDER_WIDTH)
            except subprocess.CalledProcessError as e:
                failed.append(svg_name)
                img.replace_with(f"[图片转换失败: {svg_name}]")
                continue

        if src_mode == "filepath":
            # Wechatsync 粘贴:src 用本地绝对路径,Wechatsync 自动上传
            img["src"] = png_path
        else:
            # Playwright 模式:占位符,发布时替换
            placeholder = config.IMG_PLACEHOLDER_FMT.format(n=idx)
            images[placeholder] = png_path
            img["src"] = placeholder

        # 兜底封面:仅当 out_dir 还没有专用封面时用第一张图裁(2026-09-05 定规后
        # 常态走 prepare() 的 static/images/<slug>/cover.png 直取;此分支服务缺
        # 专用封面的旧文,防架构图意外当封面——有专用封面时永不触发)
        if idx == 1 and not os.path.exists(os.path.join(out_dir, "cover.png")):
            cover_path = os.path.join(out_dir, "cover.png")
            _make_cover(png_path, cover_path, config.COVER_SIZE)

    # 记录转换失败的图(缺失/损坏),供人工补
    if failed:
        log_path = os.path.join(out_dir, "failed-images.log")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("\n".join(failed))

    return images


def prepare(slug: str) -> dict:
    """完整内容准备流程。

    Args:
        slug: 文章 slug(对应 content/posts/<slug>.md 和 public/posts/<slug>/)。

    Returns:
        {"content_html", "meta_json", "cover", "images"} 路径字典。

    Raises:
        FileNotFoundError: 渲染产物不存在。
    """
    import json

    html_path = os.path.join(config.PUBLIC_DIR, "posts", slug, "index.html")
    if not os.path.exists(html_path):
        raise FileNotFoundError(
            f"渲染产物不存在: {html_path}\n请先运行 make build"
        )

    out_dir = os.path.join(config.WECHAT_BUILD_DIR, slug)
    os.makedirs(out_dir, exist_ok=True)

    # 1. 元数据(公众号变体覆盖:front matter 可选字段 wechat_title/wechat_digest)
    meta = apply_wechat_overrides(slug, extract_meta(html_path))

    # 2. 清洗 + 样式
    with open(html_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
    content = clean_and_style(soup)

    # 2.5 专用封面(2026-09-05 定规:博客正文不内嵌封面,封面一律从 make_cover.py
    # 产物 static/images/<slug>/cover.png 直接取,裁 9:5;正文里没有首图可裁了)
    blog_cover = os.path.join(config.PROJECT_ROOT, "static", "images", slug, "cover.png")
    if os.path.exists(blog_cover):
        _make_cover(blog_cover, os.path.join(out_dir, "cover.png"), config.COVER_SIZE)

    # 3. 图片转换
    images = convert_images(content, svg_dir=config.SVG_DIR, out_dir=out_dir)
    meta["images"] = list(images.keys())

    # 4. 写出
    content_html_path = os.path.join(out_dir, "content.html")
    content_html_str = str(content)
    with open(content_html_path, "w", encoding="utf-8") as f:
        f.write(content_html_str)

    # 5. 字数检查(公众号正文约2万字上限,超限警告)
    char_count = len(content.get_text(strip=True))
    meta["char_count"] = char_count
    if char_count > config.WECHAT_MAX_CHARS:
        print(
            f"⚠️ 警告:正文 {char_count} 字,超过公众号上限 "
            f"{config.WECHAT_MAX_CHARS} 字,可能需要拆分"
        )

    meta_json_path = os.path.join(out_dir, "meta.json")
    with open(meta_json_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    cover_path = os.path.join(out_dir, "cover.png")
    if not os.path.exists(cover_path):
        cover_path = None

    return {
        "content_html": content_html_path,
        "meta_json": meta_json_path,
        "cover": cover_path,
        "images": images,
    }


def main() -> None:
    """CLI 入口。

    python3 -m prepare --slug xxx            # Playwright 用(占位符)
    python3 -m prepare --slug xxx --for-mp   # mp 直推用(本地图片路径+复制剪贴板)
    """
    import argparse
    import json

    parser = argparse.ArgumentParser(description="准备公众号内容包")
    parser.add_argument("--slug", required=True, help="文章 slug")
    parser.add_argument("--for-mp", action="store_true",
                        help="生成 mp 后台直推专用 HTML(本地图片路径)并复制到剪贴板")
    args = parser.parse_args()

    if args.for_mp:
        result = prepare_for_mp(args.slug)
        print(f"✅ mp 直推内容已生成并复制到剪贴板")
        print(f"   HTML: {result['wechat_html']}")
        print(f"   封面: {result['cover']}")
        print(f"   标题: {result['title']}")
        print(f"   → HTML/封面交发布管线使用,剪贴板可手动粘贴核对")
    else:
        result = prepare(args.slug)
        print(f"✅ 内容包已生成: {os.path.dirname(result['content_html'])}")
        print(f"   标题: {json.load(open(result['meta_json']))['title']}")
        print(f"   图片数: {len(result['images'])}")


def _copy_html_to_clipboard(html: str) -> None:
    """把 HTML 以富文本格式复制到剪贴板。

    macOS:JXA + AppKit 写 public.html 类型。
    Windows:跳过(mp 直推直接读 HTML 文件路径,无需剪贴板)。
    """
    import sys
    if sys.platform == "win32":
        # Windows 下发布管线直接传 HTML 文件路径,不需要剪贴板
        return
    import subprocess
    import tempfile

    # 写临时文件,osascript 读取后写入剪贴板(避免转义长 HTML)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(html)
        tmp_path = tmp.name

    jxa = f"""
    ObjC.import('AppKit');
    ObjC.import('Foundation');
    const data = $.NSData.dataWithContentsOfFile("{tmp_path}");
    const html = $.NSString.alloc.initWithDataEncoding(data, $.NSUTF8StringEncoding).js;
    const pb = $.NSPasteboard.generalPasteboard;
    pb.clearContents;
    pb.setStringForType(html, 'public.html');
    pb.setStringForType(html, 'public.utf8-plain-text');
    'ok';
    """
    result = subprocess.run(
        ["osascript", "-l", "JavaScript", "-e", jxa],
        capture_output=True, text=True,
    )
    os.unlink(tmp_path)
    if result.returncode != 0:
        print(f"⚠️ 剪贴板写入失败(回退纯文本): {result.stderr.strip()[:100]}")
        # 回退:pbcopy 纯文本(至少 HTML 字符串在剪贴板里)
        subprocess.run(["pbcopy"], input=html, text=True, check=False)


def prepare_for_mp(slug: str) -> dict:
    """生成 mp 后台直推专用 HTML(本地图片路径)并复制到剪贴板。

    与 prepare() 的区别:图片 src 用本地绝对路径(mp 直推读取本地上传),
    并把 HTML 以富文本格式复制到剪贴板供人工核对。
    """
    import json

    html_path = os.path.join(config.PUBLIC_DIR, "posts", slug, "index.html")
    if not os.path.exists(html_path):
        raise FileNotFoundError(
            f"渲染产物不存在: {html_path}\n请先运行 make build"
        )

    out_dir = os.path.join(config.WECHAT_BUILD_DIR, slug)
    os.makedirs(out_dir, exist_ok=True)

    meta = apply_wechat_overrides(slug, extract_meta(html_path))
    with open(html_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
    content = clean_and_style(soup)

    # 图片转 PNG,src 用本地绝对路径
    convert_images(content, svg_dir=config.SVG_DIR, out_dir=out_dir, src_mode="filepath")

    # 内链映射表(读一次,供各平台替换)
    link_map = load_link_map()

    # 按平台生成专属 HTML(内链按平台替换)
    # content 已被图片转换就地修改过,这里深拷贝避免互相污染
    base_html = str(content)
    platform_outputs = {}
    default_html = None
    for platform in config.SUPPORTED_PLATFORMS:
        platform_content = BeautifulSoup(base_html, "html.parser")
        replace_internal_links(platform_content, platform, link_map, slug)
        if platform == "weixin" and strip_leading_cover(platform_content):
            print("🖼️ 公众号版已剥离开头封面重复图(封面由平台首屏展示,正文不再重复)")
        platform_html = str(platform_content)
        path = os.path.join(out_dir, f"wechat-ready-{platform}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(platform_html)
        platform_outputs[platform] = path
        if platform == config.SUPPORTED_PLATFORMS[0]:
            default_html = platform_html

    # 兼容:保留一份 wechat-ready.html(用第一个平台的版本,供回退/剪贴板)
    wechat_html_path = os.path.join(out_dir, "wechat-ready.html")
    with open(wechat_html_path, "w", encoding="utf-8") as f:
        f.write(default_html or base_html)

    # 后处理：代码块修复 + 语法高亮 + 原文链接注入
    # 公众号不支持 <pre> 和 CSS class，故 <pre>→<section>+<p> 逐行渲染，
    # Hugo chroma class 名转为 Monokai 调色板 inline 颜色
    import re as _re

    # Monokai 调色板: chroma class → inline color
    CHROMA_COLORS = {
        # keywords (async, def, import, True, is, not)
        "k": "#f92672", "kc": "#f92672", "kn": "#f92672", "ow": "#f92672",
        # operators (=, ->, ., >=, ==)
        "o": "#f92672",
        # names (self, class names, function names, __init__)
        "bp": "#a6e22e", "nb": "#a6e22e", "nc": "#a6e22e",
        "ne": "#a6e22e", "nf": "#a6e22e", "fm": "#a6e22e",
        # variables, punctuation
        "n": "#f8f8f2", "nn": "#f8f8f2", "p": "#f8f8f2",
        # string literals
        "s2": "#e6db74", "sa": "#e6db74", "si": "#e6db74",
        # string escapes, numbers
        "se": "#ae81ff", "mi": "#ae81ff", "mf": "#ae81ff",
        # comments
        "c1": "#75715e",
        # errors
        "err": "#960050",
    }

    def _process_code_blocks(html: str) -> str:
        """<pre> → <section>+<p> 逐行，chroma class → inline 颜色"""
        if "<pre" not in html:
            return html

        def _code_section(m):
            inner = m.group(1)
            # 去掉 <code>/<code> 标签（保留内部内容）
            inner = _re.sub(r'<code[^>]*>', '', inner)
            inner = _re.sub(r'</code>', '', inner)
            # 按 <span class="line"><span class="cl"> 拆为逐行单元
            # 每行格式: <span class="line"><span class="cl">CODE</span></span>
            raw_lines = _re.split(
                r'<span\s+class=(?:"line"|line)>\s*<span\s+class=(?:"cl"|cl)>',
                inner)
            processed = []
            for raw in raw_lines:
                raw = raw.strip()
                if not raw:
                    continue
                # 剥行尾 wrapper 闭合——每行末尾恰好两个 </span>（cl + line）
                raw = _re.sub(r'</span>\s*$', '', raw)   # line closing
                raw = _re.sub(r'</span>\s*$', '', raw)   # cl closing
                # chroma class → inline 颜色
                for cls_name, color in CHROMA_COLORS.items():
                    raw = _re.sub(
                        rf'<span\s+class=(?:"{cls_name}"|{cls_name})>',
                        rf'<span style="color:{color};">',
                        raw)
                processed.append(raw.strip())
            # 逐行 <p>:公众号会过滤 <div> 的 background 简写 → 整块变白(实测)
            # 修复:① background→background-color(保留率高) ② 容器 div→section
            #       ③ 每行 <p> 也带 background-color 兜底,容器背景被剥时整块仍深色
            paras = ''.join(
                f'<p style="margin:0;padding:2px 12px;background-color:#334155;font-family:Consolas,Monaco,monospace;font-size:14px;color:#e2e8f0;line-height:1.5;">{l or "&nbsp;"}</p>'
                for l in processed)
            return f'<section style="margin:1em 0;background-color:#334155;border-radius:6px;padding:12px 0;overflow:hidden;">{paras}</section>'

        # 匹配 <pre> 及其外层的 <div class="highlight" id="id-N"> 包装（Hugo chroma 结构）
        html = _re.sub(
            r'(?:<div\s+[^>]*>\s*)?<pre[^>]*>(.*?)</pre>(?:\s*</div>)?',
            _code_section, html, flags=_re.DOTALL)
        # 行内 <code> → styled <span>
        html = _re.sub(r'<code[^>]*>', '<span style="background-color:#334155;padding:2px 6px;border-radius:3px;font-family:Consolas,Monaco,monospace;font-size:14px;color:#e2e8f0;">', html)
        html = _re.sub(r'</code>', '</span>', html)
        return html

    # 原文链接（文末注入）
    source_link = f'{config.BASE_URL}posts/{slug}/'
    source_a = (
        f'<a href="{source_link}" style="color:#2563eb;text-decoration:none;'
        f'border-bottom:1px solid #2563eb;">{source_link}</a>'
    )
    source_para = (
        f'<p style="margin:1.5em 0 0;padding:12px 16px;background-color:#334155;'
        f'border-left:4px solid #2563eb;color:#e2e8f0;font-size:14px;">'
        f'📖 完整原文：{source_a}</p>'
    )
    # weixin 版必须是纯文本：mp 拒收正文里一切非 mp.weixin 域 <a>(64562)。
    # 真链接走草稿 source_url 字段(publish_mp 注入)；BASE_URL 为空时这里
    # 还会生成相对路径 href，同样是 64562 触发源
    source_para_plain = (
        f'<p style="margin:1.5em 0 0;padding:12px 16px;background-color:#334155;'
        f'border-left:4px solid #2563eb;color:#e2e8f0;font-size:14px;">'
        f'📖 完整原文：{source_link}</p>'
    )

    # 处理 wechat-ready.html（默认/剪贴板用）
    html_content = _process_code_blocks(default_html or base_html)
    html_content = html_content.rstrip() + '\n' + source_para
    with open(wechat_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # 处理各平台专属 HTML（mp 直推/juejin 变体用的是这些）
    for platform, path in platform_outputs.items():
        with open(path, encoding="utf-8") as f:
            plat_html = f.read()
        plat_html = _process_code_blocks(plat_html)
        tail = source_para_plain if platform == "weixin" else source_para
        plat_html = plat_html.rstrip() + '\n' + tail
        with open(path, "w", encoding="utf-8") as f:
            f.write(plat_html)

    # 写 meta.json(供 Makefile 取标题/封面路径)
    meta_json_path = os.path.join(out_dir, "meta.json")
    with open(meta_json_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    cover_path = os.path.join(out_dir, "cover.png")
    if not os.path.exists(cover_path):
        cover_path = None

    # 复制到剪贴板(富文本,用默认平台版本)
    _copy_html_to_clipboard(default_html or base_html)

    return {
        "wechat_html": wechat_html_path,
        "platform_outputs": platform_outputs,
        "meta_json": meta_json_path,
        "cover": cover_path,
        "title": meta["title"],
    }


if __name__ == "__main__":
    main()
