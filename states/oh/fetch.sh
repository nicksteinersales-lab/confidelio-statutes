#!/usr/bin/env bash
# Ohio: read every chapter of the Ohio Revised Code from codes.ohio.gov and turn it into parts.
# Usage: bash states/oh/fetch.sh <parts dir>
set -euo pipefail
python3 "$(dirname "$0")/bundle.py" "$1"
