#!/usr/bin/env bash
set -euo pipefail
command -v pdftotext >/dev/null || (sudo apt-get update -qq && sudo apt-get install -y -qq poppler-utils >/dev/null)
python3 "$(dirname "$0")/bundle.py" "$1"
