import os, sys
# 让 tests/ 能 import scripts/ 下的模块（config/prepare/publish_mp 等）
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))
