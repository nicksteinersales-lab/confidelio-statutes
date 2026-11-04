#!/usr/bin/env bash
# Virginia: read every chapter of the Code of Virginia from law.lis.virginia.gov and turn it into parts.
# Usage: bash states/oh/fetch.sh <parts dir>
set -euo pipefail
python3 "$(dirname "$0")/bundle.py" "$1"
