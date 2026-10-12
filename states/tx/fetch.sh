#!/usr/bin/env bash
# Texas: download every code from the Texas Legislative Council and turn it into parts.
# Usage: bash states/tx/fetch.sh <parts dir>
set -euo pipefail
python3 "$(dirname "$0")/bundle.py" "$1"
