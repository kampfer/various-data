import logging
import os

# create logger
logger = logging.getLogger("various-data")
logger.setLevel(logging.DEBUG)

# create console handler and set level to debug
# ch = logging.StreamHandler()
logFilePath = os.path.realpath(
    os.path.join(os.path.dirname(__file__), "../../../../log/various_data.log")
)
ch = logging.FileHandler(logFilePath)
ch.setLevel(logging.DEBUG)

# create formatter
formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)
