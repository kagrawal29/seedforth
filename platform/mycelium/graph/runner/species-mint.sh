#!/usr/bin/env bash
# ============================================================================
# Runner: species-mint
# ============================================================================
# Creates a candidate Species from the current Being.root_hash. Idempotent —
# returns "noop-no-drift" if the current canonical already commits to the
# current state.
#
# Env vars:
#   NEO4J_CONTAINER   default: mycelium-neo4j-local
#   NEO4J_USER        default: neo4j
#   NEO4J_PASS        default: localtest12
# ============================================================================
set -euo pipefail

BOLT="${NEO4J_BOLT:-bolt://localhost:7687}"
USER="${NEO4J_USER:-neo4j}"
PASS="${NEO4J_PASS:-localtest12}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROTOCOL_FILE="$SCRIPT_DIR/../protocols/species-mint.cypher"

if [ ! -f "$PROTOCOL_FILE" ]; then
  echo "[species-mint] ERROR: protocol file missing: $PROTOCOL_FILE" >&2
  exit 1
fi

echo "[species-mint] reading current Being.root_hash..."
cypher-shell -a "$BOLT" \
  -u "$USER" -p "$PASS" --encryption false --format plain \
  < "$PROTOCOL_FILE"
