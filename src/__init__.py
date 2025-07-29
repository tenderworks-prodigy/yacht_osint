from dotenv import load_dotenv
import logging
import os

load_dotenv()

if not logging.getLogger().handlers:
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level, format="%(asctime)s %(levelname)s:%(name)s:%(message)s"
    )
