#!/usr/bin/env bash
# North Carolina: read every chapter of the General Statutes from ncleg.gov and turn it into parts.
# Usage: bash states/oh/fetch.sh <parts dir>
set -euo pipefail
python3 "$(dirname "$0")/bundle.py" "$1"
