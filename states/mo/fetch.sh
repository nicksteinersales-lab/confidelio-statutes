#!/usr/bin/env bash
# Missouri: read every section of the Revised Statutes of Missouri from revisor.mo.gov and turn it into parts.
# Usage: bash states/oh/fetch.sh <parts dir>
set -euo pipefail
python3 "$(dirname "$0")/bundle.py" "$1"
