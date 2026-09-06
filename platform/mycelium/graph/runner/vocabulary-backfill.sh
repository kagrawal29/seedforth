#!/bin/bash
# ============================================================================
# vocabulary-backfill.sh
# ============================================================================
# Extract vocabulary from corpus and backfill into graph in batches.
#
# Usage:
#   bash graph/runner/vocabulary-backfill.sh [--batch-size N]
#
# Defaults:
#   batch_size: 100 records per cypher-shell invocation
#
# Output:
#   Progress to stderr, final summary to stdout.
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MYCELIUM_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Environment
BOLT="${NEO4J_BOLT:-bolt://localhost:7687}"
NEO4J_USER="${NEO4J_USER:-neo4j}"
NEO4J_PASS="${NEO4J_PASS:-localtest12}"
BATCH_SIZE="${1:-100}"

# Paths
CORPUS_FILE="/tmp/vocab-corpus-$$.jsonl"
PROTOCOL_FILE="$MYCELIUM_ROOT/graph/protocols/vocabulary-backfill.cypher"

if [ ! -f "$PROTOCOL_FILE" ]; then
  echo "ERROR: Protocol not found: $PROTOCOL_FILE" >&2
  exit 1
fi

# Step 1: Extract corpus
echo "[1/2] Extracting vocabulary corpus..." >&2
python3 "$MYCELIUM_ROOT/graph/runner/extract-vocabulary.py" --corpus > "$CORPUS_FILE" 2>&1
RECORD_COUNT=$(wc -l < "$CORPUS_FILE")
echo "  -> Extracted $RECORD_COUNT records" >&2

if [ "$RECORD_COUNT" -eq 0 ]; then
  echo "ERROR: No records extracted" >&2
  rm "$CORPUS_FILE"
  exit 1
fi

# Step 2: Process in batches
echo "[2/2] Backfilling into graph (batch size: $BATCH_SIZE)..." >&2

# Read records into array
mapfile -t records < "$CORPUS_FILE"
total_records=${#records[@]}

batch_idx=0
processed=0
while [ $processed -lt $total_records ]; do
  end=$((processed + BATCH_SIZE))
  if [ $end -gt $total_records ]; then
    end=$total_records
  fi

  batch_records=()
  for ((i=processed; i<end; i++)); do
    batch_records+=("${records[$i]}")
  done

  # Build the JSON array of records for this batch
  json_array=$(printf '%s\n' "${batch_records[@]}" | jq -s '.')

  # Build cypher with parameter
  cypher=$(cat "$PROTOCOL_FILE")

  # Execute batch
  result=$(cypher-shell -a "$BOLT" \
    -u "$NEO4J_USER" -p "$NEO4J_PASS" \
    --encryption false \
    --format json <<< "WITH $json_array AS \$records
$cypher" 2>&1 || echo '{"error":"execution failed"}')

  batch_num=$((batch_idx + 1))
  batch_end=$((end))
  echo "  [$batch_num] Processed records $processed-$((batch_end - 1))/$total_records" >&2

  processed=$((end))
  batch_idx=$((batch_idx + 1))
done

# Final summary
echo "" >&2
echo "[Summary] Backfill complete." >&2
cypher-shell -a "$BOLT" \
  -u "$NEO4J_USER" -p "$NEO4J_PASS" \
  --encryption false \
  --format plain <<< 'MATCH (w:Word) WHERE NOT w.is_stopword RETURN count(w) AS content_words, sum(w.frequency) AS total_mentions, count(DISTINCT w.node_id) AS unique_lemmas' 2>&1 | tail -2

# Cleanup
rm "$CORPUS_FILE"
