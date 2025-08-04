import logging
import os

from dotenv import load_dotenv
from pythonjsonlogger import jsonlogger

load_dotenv()

if not logging.getLogger().handlers:
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    handler = logging.StreamHandler()
    handler.setFormatter(jsonlogger.JsonFormatter())
    logging.basicConfig(level=level, handlers=[handler])
