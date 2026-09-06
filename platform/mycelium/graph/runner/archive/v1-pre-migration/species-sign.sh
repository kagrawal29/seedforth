#!/usr/bin/env bash
# ============================================================================
# Runner: species-sign
# ============================================================================
# Records a WitnessSignature on a candidate species.
#
# Usage:
#   species-sign.sh <species_node_id> <witness_alias> [signed_at_iso]
#
# Example:
#   species-sign.sh species-candidate-abc123 Mycelium
#
# Phase 2 uses a sha256-based commitment as the signature (cypher-native,
# deterministic, reproducible from public fields). Phase 2.5 swaps in real
# ed25519 verification via a Python sidecar.
#
# Env vars:
#   NEO4J_CONTAINER   default: mycelium-neo4j-local
#   NEO4J_USER        default: neo4j
#   NEO4J_PASS        default: localtest12
# ============================================================================
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "usage: $0 <species_node_id> <witness_alias> [signed_at_iso]" >&2
  exit 1
fi

SPECIES_NODE_ID="$1"
WITNESS_ALIAS="$2"
SIGNED_AT="${3:-null}"

CONTAINER="${NEO4J_CONTAINER:-mycelium-neo4j-local}"
USER="${NEO4J_USER:-neo4j}"
PASS="${NEO4J_PASS:-localtest12}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROTOCOL_FILE="$SCRIPT_DIR/../protocols/species-sign.cypher"

# Build the --param JSON. signed_at can be the literal `null` or a quoted ISO string.
if [ "$SIGNED_AT" = "null" ]; then
  SIGNED_AT_JSON="null"
else
  SIGNED_AT_JSON="\"$SIGNED_AT\""
fi

PARAMS='{species_node_id: "'"$SPECIES_NODE_ID"'", witness_alias: "'"$WITNESS_ALIAS"'", signed_at: '"$SIGNED_AT_JSON"'}'

echo "[species-sign] species=$SPECIES_NODE_ID witness=$WITNESS_ALIAS"
docker exec -i "$CONTAINER" cypher-shell \
  -u "$USER" -p "$PASS" --encryption false --format plain \
  -P "$PARAMS" \
  < "$PROTOCOL_FILE"
