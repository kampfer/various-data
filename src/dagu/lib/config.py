"""运行期路径配置。

规则与 Web 端 `app/database.py` 保持一致：`mode=pro` 使用生产库，其余使用开发库。
所有路径基于本文件位置推导，不依赖进程工作目录。
"""

import os
from pathlib import Path

# src/dagu/lib/config.py -> lib -> dagu -> src -> 仓库根
REPO_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = REPO_ROOT / "data"
LOG_DIR = REPO_ROOT / "log"
BACKUP_DIR = REPO_ROOT / "backup"
OMO_HTML_DIR = DATA_DIR / "omo" / "html"

MODE = os.getenv("mode", "dev")
DB_FILE_PATH = DATA_DIR / (
    "various_data.db" if MODE == "pro" else "various_data_dev.db"
)


def describe() -> str:
    """返回一行可打印的运行环境摘要，便于在任务日志中确认实际使用的库。"""
    return f"mode={MODE} database={DB_FILE_PATH}"


if __name__ == "__main__":
    print(REPO_ROOT)
    print(DB_FILE_PATH)
