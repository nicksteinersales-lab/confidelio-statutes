#!/usr/bin/env bash
# Illinois: read the Illinois Compiled Statutes from ILGA's public file repository and turn them into parts.
# Usage: bash states/il/fetch.sh <parts dir>
set -euo pipefail
python3 "$(dirname "$0")/bundle.py" "$1"
