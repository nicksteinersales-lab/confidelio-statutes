#!/usr/bin/env bash
# Massachusetts: read every section of the General Laws from malegislature.gov and turn it into parts.
# Usage: bash states/oh/fetch.sh <parts dir>
set -euo pipefail
python3 "$(dirname "$0")/bundle.py" "$1"
