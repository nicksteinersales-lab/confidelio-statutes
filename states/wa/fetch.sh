#!/usr/bin/env bash
# Washington: read the Revised Code of Washington from the Legislature's public law files and turn it into parts.
# Usage: bash states/wa/fetch.sh <parts dir>
set -euo pipefail
python3 "$(dirname "$0")/bundle.py" "$1"
