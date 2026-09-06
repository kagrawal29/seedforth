#!/usr/bin/env bash
# ============================================================================
# Runner: run-invariants
# ============================================================================
# Executes the run-invariants Cypher protocol against Neo4j, parses the
# summary row, and exits non-zero if any invariant is not healthy.
#
# Source of truth is the Protocol node `protocol-run-invariants` in the graph.
# This script reads that node's `cypher` property and pipes it into
# cypher-shell — the file on disk is just a cache for git review.
#
# Env vars (optional):
#   NEO4J_CONTAINER    default: mycelium-neo4j-local
#   NEO4J_USER         default: neo4j
#   NEO4J_PASS         default: localtest12
#   PROTOCOL_ID        default: protocol-run-invariants
#   FALLBACK_FILE      default: graph/protocols/run-invariants.cypher
# ============================================================================

set -euo pipefail

CONTAINER="${NEO4J_CONTAINER:-mycelium-neo4j-local}"
NUSER="${NEO4J_USER:-neo4j}"
NPASS="${NEO4J_PASS:-localtest12}"
PROTOCOL_ID="${PROTOCOL_ID:-protocol-run-invariants}"
FALLBACK_FILE="${FALLBACK_FILE:-graph/protocols/run-invariants.cypher}"

run_cypher() {
  docker exec -i "$CONTAINER" cypher-shell \
    -u "$NUSER" -p "$NPASS" --encryption false --format plain "$@"
}

# Source: prefer local file (so editing the .cypher file takes effect
# immediately). Fall back to the Protocol node in Neo4j.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_FILE="$SCRIPT_DIR/../protocols/run-invariants.cypher"

if [ -f "$LOCAL_FILE" ]; then
  cypher_text=$(cat "$LOCAL_FILE")
  echo "[run-invariants] loaded from file: graph/protocols/run-invariants.cypher"
else
  cypher_text=$(
    run_cypher "MATCH (p:Protocol {node_id: '$PROTOCOL_ID'}) RETURN p.cypher AS cypher LIMIT 1" 2>/dev/null \
      | tail -n +2 \
      | sed -e 's/^"//' -e 's/"$//' -e 's/\\"/"/g' -e 's/\\n/\n/g' \
      || true
  )
  echo "[run-invariants] loaded from Protocol node"
fi

if [ -z "$cypher_text" ] || [ "$cypher_text" = "NULL" ]; then
  echo "[run-invariants] ERROR: no cypher body found" >&2
  exit 2
fi

echo "[run-invariants] executing protocol $PROTOCOL_ID..."

raw_output=$(echo "$cypher_text" | run_cypher 2>&1)
exit_code=$?

if [ $exit_code -ne 0 ]; then
  echo "[run-invariants] cypher execution failed:" >&2
  echo "$raw_output" >&2
  exit 3
fi

echo "$raw_output"

# Parse the final summary row. cypher-shell --format plain prints:
#   total, healthy, unhealthy, unhealthy_names
#   23, 3, 20, ["invariant-1 (unhealthy)", ...]
summary_line=$(echo "$raw_output" | grep -E '^[0-9]+,' | tail -n 1)

if [ -z "$summary_line" ]; then
  echo "[run-invariants] ERROR: could not parse summary row" >&2
  exit 4
fi

total=$(echo "$summary_line" | awk -F',' '{print $1}' | tr -d ' ')
healthy=$(echo "$summary_line" | awk -F',' '{print $2}' | tr -d ' ')
unhealthy=$(echo "$summary_line" | awk -F',' '{print $3}' | tr -d ' ')

echo
echo "[run-invariants] total=$total healthy=$healthy unhealthy=$unhealthy"

if [ "$unhealthy" -gt 0 ]; then
  echo "[run-invariants] UNHEALTHY INVARIANTS:" >&2
  # Extract the bracketed list
  echo "$summary_line" | sed -E 's/.*\[(.*)\].*/\1/' | tr ',' '\n' | sed 's/^ *//' >&2
  exit 1
fi

echo "[run-invariants] all invariants healthy."
exit 0
