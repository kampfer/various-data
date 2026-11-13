"""日志：stdout + log/scheduler.log 双输出，强制 UTF-8。"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

LOGGER_NAME = "scheduler"
LOG_FILE_NAME = "scheduler.log"


def setup_logging(log_dir: Path, level: int = logging.INFO) -> logging.Logger:
    """初始化调度器日志，重复调用不会重复添加 handler。"""

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False
    if logger.handlers:
        return logger

    # Windows 控制台默认可能是 GBK，遇到全角空格等字符会抛 UnicodeEncodeError。
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")

    console = logging.StreamHandler(stream=sys.stdout)
    console.setLevel(level)
    console.setFormatter(formatter)

    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_dir / LOG_FILE_NAME, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    logger.addHandler(console)
    logger.addHandler(file_handler)
    return logger
