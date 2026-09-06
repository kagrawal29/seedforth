#!/bin/bash
# Appends a cycle summary line to the results ledger
# Usage: ./scripts/cycle-summary.sh <cycle-type> <signals> <insights> <distributed> <summary>

set -euo pipefail

LEDGER="knowledge/meta/cycle-log.md"
DATE=$(date +%Y-%m-%d)
CYCLE_TYPE="${1:-manual}"
SIGNALS="${2:-0}"
INSIGHTS="${3:-0}"
DISTRIBUTED="${4:-0}"
SUMMARY="${5:-no summary}"

mkdir -p "$(dirname "$LEDGER")"

# Add header if file is new/empty
if [ ! -s "$LEDGER" ]; then
  cat > "$LEDGER" << 'HEADER'
# Cycle Log

Results ledger tracking every ingest/synthesize/distribute cycle.

| Date | Type | Signals | Insights | Distributed | Summary |
|------|------|---------|----------|-------------|---------|
HEADER
fi

echo "| $DATE | $CYCLE_TYPE | $SIGNALS | $INSIGHTS | $DISTRIBUTED | $SUMMARY |" >> "$LEDGER"
echo "Logged cycle to $LEDGER"
