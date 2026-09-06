#!/bin/bash
# SessionStart hook: warns if last cycle was >8 hours ago
# Reads the last line of cycle-log.md and checks the date

set -euo pipefail

CYCLE_LOG="knowledge/meta/cycle-log.md"

if [ ! -f "$CYCLE_LOG" ]; then
  echo "[CYCLE-STALE] No cycle log found. Run /cycle to initialize."
  exit 0
fi

# Get the last data row (skip header lines)
LAST_LINE=$(tail -1 "$CYCLE_LOG" | grep "^|" || echo "")

if [ -z "$LAST_LINE" ]; then
  exit 0
fi

# Extract the date from the first column
LAST_DATE=$(echo "$LAST_LINE" | awk -F'|' '{print $2}' | tr -d ' ')

if [ -z "$LAST_DATE" ]; then
  exit 0
fi

# Calculate hours since last cycle
LAST_EPOCH=$(date -j -f "%Y-%m-%d" "$LAST_DATE" "+%s" 2>/dev/null || echo "0")
NOW_EPOCH=$(date "+%s")
HOURS_AGO=$(( (NOW_EPOCH - LAST_EPOCH) / 3600 ))

if [ "$HOURS_AGO" -gt 8 ]; then
  echo "[CYCLE-STALE] Last cycle was ${HOURS_AGO}h ago ($LAST_DATE). Consider running /cycle or /auto-cycle."
fi
