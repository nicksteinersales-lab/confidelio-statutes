#!/usr/bin/env bash
# New York: read every consolidated and unconsolidated law from the NY Senate's
# Open Legislation API and turn it into parts. Needs the NY_OPENLEG_KEY secret.
# Usage: bash states/ny/fetch.sh <parts dir>
set -euo pipefail
python3 "$(dirname "$0")/bundle.py" "$1"
