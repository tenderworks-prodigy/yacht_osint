#!/usr/bin/env bash
set -euo pipefail
ruff check --fix .
black .
pytest -q
python -m src.export.csv
ls -lh exports/yachts.csv
