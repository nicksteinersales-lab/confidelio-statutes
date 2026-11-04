#!/usr/bin/env bash
# Minnesota: read every chapter of the Minnesota Statutes from revisor.mn.gov and turn it into parts.
# Usage: bash states/oh/fetch.sh <parts dir>
set -euo pipefail
python3 "$(dirname "$0")/bundle.py" "$1"
