#!/bin/bash
# update_portfolio.sh — Reliably append portfolio data to omar-data CSVs and push.
#
# CSV Format (5 columns):
#   timestamp,total_account_value,num_positions,unrealized_pnl,notes
#   - timestamp:           ISO 8601 UTC (auto-generated, e.g. 2026-04-03T13:21:00Z)
#   - total_account_value: Decimal DOLLARS, decimal point REQUIRED (e.g. 263.99, 260.00).
#                          NOT cents. Kalshi API returns balances in cents;
#                          divide by 100 before calling this script. The script
#                          rejects integer-only inputs to make the unit
#                          mistake impossible to commit silently.
#   - num_positions:       Integer (e.g. 20)
#   - unrealized_pnl:      Signed decimal (e.g. +63.99 or -12.50)
#   - notes:               Free-text (quoted in CSV; must not contain raw commas)
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

print_usage() {
    echo "Usage: $0 <baseline|quant> <total_value> <num_positions> <unrealized_pnl> <notes>"
    echo ""
    echo "CSV format: timestamp,total_account_value,num_positions,unrealized_pnl,notes"
    echo "  account         : 'baseline' or 'quant'"
    echo "  total_value     : Decimal number (e.g. 263.99)"
    echo "  num_positions   : Integer (e.g. 20)"
    echo "  unrealized_pnl  : Signed decimal (e.g. +63.99 or -12.50)"
    echo "  notes           : Free-text (no raw commas)"
    echo ""
    echo "Example: $0 baseline 263.99 20 \"+63.99\" \"Cycle 24: Post-NFP. Hold.\""
}

# --- Validation ---

# Check exactly 5 args
if [ $# -ne 5 ]; then
    echo "Error: Expected exactly 5 arguments, got $#"
    print_usage
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
    print_usage
    exit 1
fi

# Validate total_value is a positive decimal-dollar amount.
#
# We REQUIRE a decimal point (e.g. 55.17, 263.99, 260.00) and reject bare
# integers like "5517". Rationale: Kalshi's API returns balances in cents
# (integer) and callers have repeatedly forwarded the raw cents value here,
# producing rows like `5517,0,0` instead of `55.17,0,0.00` on the public
# portfolio-history.csv. Forcing a decimal point at the boundary makes the
# unit mistake impossible to commit silently — if you have $260 exactly,
# pass "260.00", never "260".
if ! [[ "$TOTAL_VALUE" =~ ^[0-9]+\.[0-9]{1,2}$ ]]; then
    echo "Error: total_value must be decimal dollars with a decimal point, got '$TOTAL_VALUE'"
    echo "  Examples: 55.17, 263.99, 260.00 (NOT 5517 or 26000 — those are cents)"
    echo "  Kalshi /portfolio/balance returns cents; divide by 100 before calling."
    print_usage
    exit 1
fi

# Validate num_positions is an integer
if ! [[ "$NUM_POSITIONS" =~ ^[0-9]+$ ]]; then
    echo "Error: num_positions must be a non-negative integer, got '$NUM_POSITIONS'"
    print_usage
    exit 1
fi

# Validate unrealized_pnl is a signed or unsigned number
if ! [[ "$UNREALIZED_PNL" =~ ^[+-]?[0-9]+\.?[0-9]*$ ]]; then
    echo "Error: unrealized_pnl must be a number (e.g. +63.99 or -12.50), got '$UNREALIZED_PNL'"
    print_usage
    exit 1
fi

# Reject fields containing commas (would break CSV)
for field in "$TOTAL_VALUE" "$NUM_POSITIONS" "$UNREALIZED_PNL" "$NOTES"; do
    if [[ "$field" == *","* ]]; then
        echo "Error: Fields must not contain commas. Got comma in: '$field'"
        print_usage
        exit 1
    fi
done

CSV_FILE="kalshi/${ACCOUNT}/portfolio-history.csv"

if [ ! -f "$CSV_FILE" ]; then
    echo "Error: $CSV_FILE not found"
    exit 1
fi

# Generate ISO 8601 UTC timestamp (minute precision)
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:00Z")

# Idempotency: skip if the last row has the same timestamp (same minute)
LAST_TS=$(tail -1 "$CSV_FILE" | cut -d',' -f1)
if [ "$LAST_TS" = "$TIMESTAMP" ]; then
    echo "Skipped: last row already has timestamp $TIMESTAMP (idempotent)"
    exit 0
fi

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
