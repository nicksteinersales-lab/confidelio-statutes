#!/usr/bin/env bash
# New Jersey: download the statutes in plain text from the Legislature's public
# file server (updated every weekday) and turn them into parts.
# Usage: bash states/nj/fetch.sh <parts dir>
set -euo pipefail
python3 "$(dirname "$0")/bundle.py" "$1"
