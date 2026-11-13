#!/usr/bin/env bash
# Run the full pipeline. Usage: ./run_all.sh            (uses config.yaml)
#                             PROPERTY_CONFIG=config.sample.yaml ./run_all.sh
set -euo pipefail
cd "$(dirname "$0")"
for s in scripts/0*.py; do
  echo "=== $s ==="
  python3 "$s"
done
