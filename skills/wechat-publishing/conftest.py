import os, sys
# 让 tests/ 能 import scripts/ 下的模块（config/prepare/publish_mp 等）
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))
# 测试环境变量（让 config.py 的 env 驱动有值）
os.environ.setdefault("SITE_BASE_URL", "https://example.com")
os.environ.setdefault("WECHAT_AUTHOR", "Test Author")
os.environ.setdefault("SITE_NAME_SUFFIX", " - Test Blog")
