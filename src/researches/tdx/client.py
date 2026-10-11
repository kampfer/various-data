# tdx/client.py
import sys
from pathlib import Path

# 通达信插件目录（建议做成可配置）
TDX_PLUGIN_DIR = r"D:/tdx/PYPlugins/user"

if TDX_PLUGIN_DIR not in sys.path:
    sys.path.append(TDX_PLUGIN_DIR)

from tqcenter import tq  # noqa: E402

# 只初始化一次（模块级代码在首次 import 时执行，之后被缓存）
_initialized = False

def _ensure_init():
    global _initialized
    if not _initialized:
        tq.initialize(__file__)
        _initialized = True

_ensure_init()

__all__ = ["tq"]