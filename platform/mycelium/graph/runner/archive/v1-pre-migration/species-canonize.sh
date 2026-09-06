#!/usr/bin/env bash
# ============================================================================
# Runner: species-canonize
# ============================================================================
# Promotes a candidate Species to canonical if it has enough valid
# WitnessSignatures to meet its quorum_required. Exits non-zero if
# quorum is not met or the candidate does not exist.
#
# Usage:
#   species-canonize.sh <species_node_id>
#
# Example:
#   species-canonize.sh species-candidate-abc123
#
# Env vars:
#   NEO4J_CONTAINER   default: mycelium-neo4j-local
#   NEO4J_USER        default: neo4j
#   NEO4J_PASS        default: localtest12
# ============================================================================
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: $0 <species_node_id>" >&2
  exit 1
fi

SPECIES_NODE_ID="$1"

CONTAINER="${NEO4J_CONTAINER:-mycelium-neo4j-local}"
USER="${NEO4J_USER:-neo4j}"
PASS="${NEO4J_PASS:-localtest12}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROTOCOL_FILE="$SCRIPT_DIR/../protocols/species-canonize.cypher"

PARAMS='{species_node_id: "'"$SPECIES_NODE_ID"'"}'

echo "[species-canonize] promoting $SPECIES_NODE_ID"
docker exec -i "$CONTAINER" cypher-shell \
  -u "$USER" -p "$PASS" --encryption false --format plain \
  -P "$PARAMS" \
  < "$PROTOCOL_FILE"
