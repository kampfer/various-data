"""dca_sim：A 股场景下的定投、股债配置、再平衡、动态提取与清仓模拟器。

免责声明：本包所有结果仅用于逻辑验证，不构成投资建议。
"""

from .config import SimConfig
from .engine import DCASimulator
from .metrics import performance

__all__ = ["SimConfig", "DCASimulator", "performance"]
