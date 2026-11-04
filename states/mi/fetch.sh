#!/usr/bin/env bash
# Michigan: read every act of the Michigan Compiled Laws from legislature.mi.gov
# (one official PDF per act) and turn it into parts. Needs pdftotext (poppler-utils).
# Usage: bash states/mi/fetch.sh <parts dir>
set -euo pipefail
command -v pdftotext >/dev/null || (sudo apt-get update -qq && sudo apt-get install -y -qq poppler-utils >/dev/null)
python3 "$(dirname "$0")/bundle.py" "$1"
