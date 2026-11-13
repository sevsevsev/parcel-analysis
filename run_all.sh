#!/usr/bin/env bash
# Run the full pipeline for one listing.  Usage: ./run_all.sh <listing-name> [--refresh]
#   <listing-name> is listings/<listing-name>.yaml.  --refresh re-downloads remote layers.
set -euo pipefail
cd "$(dirname "$0")"
[ $# -ge 1 ] || { echo "usage: $0 <listing-name> [--refresh]"; ls listings | sed 's/.yaml$//' | grep -v '^_' | sed 's/^/  /'; exit 1; }
export PROPERTY_CONFIG="listings/$1.yaml"; shift
for s in scripts/0*.py; do
  echo "=== $s ==="
  python3 "$s" "$@"
done
