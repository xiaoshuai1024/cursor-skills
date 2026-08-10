# -*- coding: utf-8 -*-
"""Playwright(msedge) headless 渲染复刻 HTML 并截图。不依赖屏幕会话，屏幕锁定时也能出图。

用法:
    python shoot.py <输出.png> [宽度=1600]
    python shoot.py C:/tmp/out.png 1600

前置:
    - Python 环境需有 playwright（本机: C:\\Users\\Administrator\\AppData\\Local\\Programs\\Python\\Python311\\python.exe）
    - 浏览器: Windows=msedge / macOS=chrome(见脚本内 CHANNEL 常量)
"""
import sys
from playwright.sync_api import sync_playwright

# 浏览器 channel: Windows msedge(本机 Chrome 损坏), macOS chrome(系统自带,真实浏览器)
CHANNEL = "msedge" if sys.platform == "win32" else "chrome"

# 模板路径：本脚本同级的 ../templates/conv.html
import os
html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates", "conv.html")
out_path = sys.argv[1] if len(sys.argv) > 1 else "conv.png"
width = int(sys.argv[2]) if len(sys.argv) > 2 else 1600

url = "file:///" + os.path.abspath(html_path).replace("\\", "/")
with sync_playwright() as p:
    browser = p.chromium.launch(channel=CHANNEL, headless=True)
    page = browser.new_page(viewport={"width": width, "height": 900}, device_scale_factor=1)
    page.goto(url, wait_until="networkidle")
    page.wait_for_timeout(600)
    page.screenshot(path=out_path, full_page=True)
    browser.close()
print("saved", out_path)
