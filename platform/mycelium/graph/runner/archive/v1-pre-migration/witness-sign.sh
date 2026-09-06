#!/usr/bin/env bash
# ============================================================================
# Runner: witness-sign
# ============================================================================
# Signs a candidate Species using the witness's ed25519 private key.
#
# Steps:
#   1. Look up the species in Neo4j to get manifest_root, parent_dna, node_id
#   2. Construct the signing message: "<manifest_root>|<parent_dna>|<node_id>"
#      (parent_dna is the literal "genesis" for nodes where parent is null)
#   3. Call mycelium-crypto.py sign → hex signature
#   4. Call species-sign.cypher with the signature + algorithm=ed25519
#
# Usage:
#   witness-sign.sh <species_node_id> <witness_alias>
#
# The witness's private key must exist at ~/.mycelium/witness-<alias>.key
# (create via witness-init.sh).
#
# Env vars:
#   NEO4J_CONTAINER   default: mycelium-neo4j-local
#   NEO4J_USER        default: neo4j
#   NEO4J_PASS        default: localtest12
#   KEY_DIR           default: ~/.mycelium
# ============================================================================
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "usage: $0 <species_node_id> <witness_alias>" >&2
  exit 1
fi

SPECIES_NODE_ID="$1"
ALIAS="$2"
CONTAINER="${NEO4J_CONTAINER:-mycelium-neo4j-local}"
USER="${NEO4J_USER:-neo4j}"
PASS="${NEO4J_PASS:-localtest12}"
KEY_DIR="${KEY_DIR:-$HOME/.mycelium}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRYPTO="$SCRIPT_DIR/mycelium-crypto.py"
SIGN_PROTOCOL="$SCRIPT_DIR/../protocols/species-sign.cypher"

cypher_exec() {
  docker exec -i "$CONTAINER" cypher-shell \
    -u "$USER" -p "$PASS" --encryption false --format plain "$@"
}

echo "[witness-sign] fetching species $SPECIES_NODE_ID"
MESSAGE=$(
  cypher_exec "MATCH (c:Species {node_id: '$SPECIES_NODE_ID'}) RETURN c.manifest_root + '|' + coalesce(c.parent_dna, 'genesis') + '|' + c.node_id AS msg" \
    | tail -n +2 | sed -e 's/^"//' -e 's/"$//'
)

if [ -z "$MESSAGE" ]; then
  echo "[witness-sign] ERROR: species $SPECIES_NODE_ID not found" >&2
  exit 1
fi

echo "[witness-sign] signing message (length=${#MESSAGE}) with witness $ALIAS"
SIGNATURE=$(python3 "$CRYPTO" sign --alias "$ALIAS" --message "$MESSAGE" --key-dir "$KEY_DIR")

if [ -z "$SIGNATURE" ]; then
  echo "[witness-sign] ERROR: signing failed" >&2
  exit 1
fi

echo "[witness-sign] signature=${SIGNATURE:0:32}..."
echo "[witness-sign] writing WitnessSignature node"
cypher_exec \
  -P '{witness_alias: "'"$ALIAS"'", species_node_id: "'"$SPECIES_NODE_ID"'", signed_at: null, signature: "'"$SIGNATURE"'", algorithm: "ed25519"}' \
  < "$SIGN_PROTOCOL"
