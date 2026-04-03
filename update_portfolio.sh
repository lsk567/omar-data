#!/bin/bash
# update_portfolio.sh — Reliably append portfolio data to omar-data CSVs and push.
#
# Usage:
#   ./update_portfolio.sh <account> <total_value> <num_positions> <unrealized_pnl> "<notes>"
#
# Arguments:
#   account         : "baseline" or "quant"
#   total_value     : Total account value (e.g. 263.99)
#   num_positions   : Number of active positions (e.g. 20)
#   unrealized_pnl  : Unrealized PnL string (e.g. "+63.99" or "-12.50")
#   notes           : Free-text note (will be quoted in CSV)
#
# Example:
#   ./update_portfolio.sh baseline 263.99 20 "+63.99" "Cycle 24: Post-NFP. Hold."
#   ./update_portfolio.sh quant 144.89 14 "+16.29" "v8 cycle #19 post-NFP."

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ $# -lt 5 ]; then
    echo "Usage: $0 <baseline|quant> <total_value> <num_positions> <unrealized_pnl> <notes>"
    echo "Example: $0 baseline 263.99 20 \"+63.99\" \"Cycle 24: Post-NFP. Hold.\""
    exit 1
fi

ACCOUNT="$1"
TOTAL_VALUE="$2"
NUM_POSITIONS="$3"
UNREALIZED_PNL="$4"
NOTES="$5"

# Validate account
if [[ "$ACCOUNT" != "baseline" && "$ACCOUNT" != "quant" ]]; then
    echo "Error: account must be 'baseline' or 'quant', got '$ACCOUNT'"
    exit 1
fi

CSV_FILE="kalshi/${ACCOUNT}/portfolio-history.csv"

if [ ! -f "$CSV_FILE" ]; then
    echo "Error: $CSV_FILE not found"
    exit 1
fi

# Generate ISO 8601 UTC timestamp
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Append row using python to handle CSV quoting properly
python3 -c "
import csv, sys
with open('$CSV_FILE', 'a', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['$TIMESTAMP', '$TOTAL_VALUE', '$NUM_POSITIONS', '$UNREALIZED_PNL', '''$NOTES'''])
"

echo "Appended to $CSV_FILE: $TIMESTAMP,$TOTAL_VALUE,$NUM_POSITIONS,$UNREALIZED_PNL"

# Pull latest, add, commit, push
git pull --rebase --quiet 2>/dev/null || true
git add "$CSV_FILE"
git commit -m "Update ${ACCOUNT} portfolio data" --quiet 2>/dev/null || { echo "Nothing to commit"; exit 0; }
git push --quiet 2>/dev/null && echo "Pushed successfully." || echo "Warning: push failed, will retry next cycle."
