#!/usr/bin/env bash
# ============================================================================
# Runner: run-tests
# ============================================================================
# Reads the Protocol node `protocol-run-tests` from Neo4j and executes its
# cypher once. Parses the summary (total / passed / failed) from the final
# RETURN row and prints a digest plus the list of failing TestCases.
#
# Exits 0 if all tests pass, 1 if any test fails (so it slots cleanly into
# CI / git hooks / parent watchdogs).
#
# Env vars (optional):
#   NEO4J_CONTAINER    default: mycelium-neo4j-local
#   NEO4J_USER         default: neo4j
#   NEO4J_PASS         default: localtest12
#   PROTOCOL_ID        default: protocol-run-tests
# ============================================================================

set -euo pipefail

CONTAINER="${NEO4J_CONTAINER:-mycelium-neo4j-local}"
USER="${NEO4J_USER:-neo4j}"
PASS="${NEO4J_PASS:-localtest12}"
PROTOCOL_ID="${PROTOCOL_ID:-protocol-run-tests}"

cypher_exec() {
  docker exec -i "$CONTAINER" cypher-shell \
    -u "$USER" -p "$PASS" --encryption false --format plain "$@"
}

echo "[run-tests] container=$CONTAINER protocol=$PROTOCOL_ID"

# Protocol source: prefer local file so editing the .cypher takes effect
# immediately; fall back to the Protocol node in Neo4j if the file is absent
# (e.g. running from a checkout where files were deleted).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_FILE="$SCRIPT_DIR/../protocols/run-tests.cypher"

if [ -f "$LOCAL_FILE" ]; then
  cypher_text=$(cat "$LOCAL_FILE")
  echo "[run-tests] loaded from file: graph/protocols/run-tests.cypher"
else
  cypher_text=$(
    cypher_exec \
      "MATCH (p:Protocol {node_id: '$PROTOCOL_ID'}) RETURN p.cypher AS cypher LIMIT 1" \
    | tail -n +2 \
    | sed -e 's/^"//' -e 's/"$//' -e 's/\\"/"/g' -e 's/\\n/\n/g'
  )
  echo "[run-tests] loaded from Protocol node"
fi

if [ -z "$cypher_text" ]; then
  echo "[run-tests] ERROR: no cypher body found (file: $LOCAL_FILE, node: $PROTOCOL_ID)" >&2
  exit 2
fi

# Run it. Capture full output so we can both parse and print on failure.
output=$(echo "$cypher_text" | cypher_exec 2>&1) || {
  echo "[run-tests] ERROR: protocol run failed:" >&2
  echo "$output" >&2
  exit 2
}

# Last non-empty line is the RETURN row: total, passed, failed, failed_ids
summary_line=$(echo "$output" | grep -v '^$' | tail -n 1)

total=$(echo "$summary_line" | awk -F',' '{print $1}' | tr -d ' "')
passed=$(echo "$summary_line" | awk -F',' '{print $2}' | tr -d ' "')
failed=$(echo "$summary_line" | awk -F',' '{print $3}' | tr -d ' "')

echo "[run-tests] total=$total passed=$passed failed=$failed"

if [ "${failed:-0}" != "0" ]; then
  echo "[run-tests] failing tests (active only):"
  cypher_exec \
    "MATCH (t:TestCase {last_result: 'fail'}) WHERE coalesce(t.enabled, true) = true RETURN t.node_id + '  ' + coalesce(t.label, '(no label)') AS line ORDER BY t.node_id" \
    | tail -n +2 | sed -e 's/^"//' -e 's/"$//' | sed 's/^/  /'
  exit 1
fi

echo "[run-tests] all green"
exit 0
