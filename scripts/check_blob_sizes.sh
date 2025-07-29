#!/usr/bin/env bash
set -euo pipefail
MAX=250000
while IFS= read -r -d '' f; do
  size=$(wc -c < "$f")
  if [ "$size" -gt "$MAX" ]; then
    echo "$f is too big ($size > $MAX)" >&2
    exit 1
  fi
done < <(git ls-files -z)
