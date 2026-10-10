#!/usr/bin/env bash
# California: download the Legislature's latest bulk file and turn it into parts.
# Usage: bash states/ca/fetch.sh <parts dir>
set -euo pipefail
out="$1"
f=$(curl -sf --retry 3 https://downloads.leginfo.legislature.ca.gov/ | grep -oE 'pubinfo_[0-9]{4}\.zip' | sort -u | tail -1)
[ -n "$f" ] || { echo "No pubinfo file listed on downloads.leginfo.legislature.ca.gov"; exit 1; }
echo "Source: $f"
curl -sf --retry 3 -o "/tmp/$f" "https://downloads.leginfo.legislature.ca.gov/$f"
python3 "$(dirname "$0")/bundle.py" "/tmp/$f" "$out"
rm -f "/tmp/$f"
