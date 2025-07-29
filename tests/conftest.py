import logging

logging.getLogger("urllib3.connectionpool").disabled = True

import sys
from pathlib import Path

# ensure project root is on the import path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
