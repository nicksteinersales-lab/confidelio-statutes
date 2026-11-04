#!/usr/bin/env bash
# Arizona: read every section of the Arizona Revised Statutes from azleg.gov and turn it into parts.
# Usage: bash states/oh/fetch.sh <parts dir>
set -euo pipefail
python3 "$(dirname "$0")/bundle.py" "$1"
