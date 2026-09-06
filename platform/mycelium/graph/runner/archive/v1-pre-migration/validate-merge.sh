#!/usr/bin/env bash
# ============================================================================
# Runner: validate-merge
# ============================================================================
# The write gate for the mutation-gate chain layer. Accepts a proposed
# cypher file, applies it inside an explicit transaction, runs every
# enabled Invariant + TestCase, recomputes Merkle, and commits the
# transaction only if all checks pass. On any failure, the transaction
# is rolled back and the proposed mutation leaves no trace.
#
# Usage:
#   validate-merge.sh <proposed_cypher_file> [--mint]
#
#   --mint  after a successful commit, also run species-mint.sh to create
#           a candidate Species for the new state. Default: no mint
#           (useful for local dry-run: "would my changes pass?").
#
# Examples:
#   # Dry-run
#   validate-merge.sh pull-request/add-new-principle.cypher
#
#   # Apply + mint candidate for witness signing
#   validate-merge.sh pull-request/add-new-principle.cypher --mint
#
# Exit codes:
#   0  — all checks passed, transaction committed
#   1  — validation failed (invariant or test broken)
#   2  — proposed cypher had a syntax error or the file is missing
#   3  — mint step failed after successful validation
#
# Env vars:
#   NEO4J_CONTAINER   default: mycelium-neo4j-local
#   NEO4J_USER        default: neo4j
#   NEO4J_PASS        default: localtest12
# ============================================================================
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: $0 <proposed_cypher_file> [--mint]" >&2
  exit 2
fi

PROPOSED="$1"
MINT=0
shift
while [ $# -gt 0 ]; do
  case "$1" in
    --mint) MINT=1 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
  shift
done

if [ ! -f "$PROPOSED" ]; then
  echo "[validate-merge] ERROR: file not found: $PROPOSED" >&2
  exit 2
fi

CONTAINER="${NEO4J_CONTAINER:-mycelium-neo4j-local}"
USER="${NEO4J_USER:-neo4j}"
PASS="${NEO4J_PASS:-localtest12}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VALIDATE_BODY="$SCRIPT_DIR/../protocols/validate-merge.cypher"

if [ ! -f "$VALIDATE_BODY" ]; then
  echo "[validate-merge] ERROR: missing $VALIDATE_BODY" >&2
  exit 2
fi

echo "[validate-merge] proposed: $PROPOSED"
echo "[validate-merge] beginning transaction..."

# Assemble the full transaction body: begin, proposed cypher, validate body,
# commit. Fed as a single stdin to cypher-shell interactive.
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT

{
  echo ':begin'
  cat "$PROPOSED"
  cat "$VALIDATE_BODY"
  echo ':commit'
} > "$tmp"

output=$(docker exec -i "$CONTAINER" cypher-shell \
  -u "$USER" -p "$PASS" --encryption false --format plain \
  < "$tmp" 2>&1) || {
  echo "[validate-merge] VALIDATION FAILED — transaction rolled back" >&2
  echo "$output" >&2
  exit 1
}

echo "$output" | tail -20
echo "[validate-merge] transaction committed — all checks green"

if [ "$MINT" -eq 1 ]; then
  echo "[validate-merge] minting candidate species..."
  "$SCRIPT_DIR/species-mint.sh" || {
    echo "[validate-merge] ERROR: mint step failed after successful validation" >&2
    exit 3
  }
fi
