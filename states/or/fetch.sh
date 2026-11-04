#!/usr/bin/env bash
# Oregon: read every chapter of the Oregon Revised Statutes from oregonlegislature.gov and turn it into parts.
# Usage: bash states/oh/fetch.sh <parts dir>
set -euo pipefail
python3 "$(dirname "$0")/bundle.py" "$1"
