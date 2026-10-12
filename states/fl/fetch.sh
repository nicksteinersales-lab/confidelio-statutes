#!/usr/bin/env bash
# Florida: read every chapter of the Florida Statutes from Online Sunshine and turn it into parts.
# Usage: bash states/fl/fetch.sh <parts dir>
set -euo pipefail
python3 "$(dirname "$0")/bundle.py" "$1"
