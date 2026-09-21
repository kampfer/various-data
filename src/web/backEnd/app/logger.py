import logging
import os

# create logger
logger = logging.getLogger("various-data")
logger.setLevel(logging.DEBUG)

# 同时输出到终端和日志文件，便于开发环境实时观察任务执行情况。
consoleHandler = logging.StreamHandler()
consoleHandler.setLevel(logging.DEBUG)

logFilePath = os.path.realpath(
    os.path.join(os.path.dirname(__file__), "../../../../log/various_data.log")
)
# 指定 utf-8 编码，避免在 Windows 上默认使用 gbk 时无法编码全角空格等字符导致 UnicodeEncodeError
fileHandler = logging.FileHandler(logFilePath, encoding="utf-8")
fileHandler.setLevel(logging.DEBUG)

# create formatter
formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")

# add formatter to handlers
consoleHandler.setFormatter(formatter)
fileHandler.setFormatter(formatter)

# add handlers to logger
logger.addHandler(consoleHandler)
logger.addHandler(fileHandler)
