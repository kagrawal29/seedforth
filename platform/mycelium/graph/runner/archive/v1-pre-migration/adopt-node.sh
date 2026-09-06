#!/usr/bin/env bash
# ============================================================================
# Runner: adopt-node
# ============================================================================
# Promotes an :Imported node to a full citizen inside a validate-merge
# transaction. If invariants/tests don't hold for the adopted node, the
# transaction rolls back and the node stays :Imported.
#
# Usage:
#   adopt-node.sh <node_id> <adopter_alias>
#
# Example:
#   adopt-node.sh ember:user-rajesh kshitiz
#
# Env vars:
#   NEO4J_CONTAINER   default: mycelium-neo4j-local
#   NEO4J_USER        default: neo4j
#   NEO4J_PASS        default: localtest12
# ============================================================================
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "usage: $0 <node_id> <adopter_alias>" >&2
  exit 2
fi

NODE_ID="$1"
ADOPTER="$2"

CONTAINER="${NEO4J_CONTAINER:-mycelium-neo4j-local}"
USER="${NEO4J_USER:-neo4j}"
PASS="${NEO4J_PASS:-localtest12}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADOPT_PROTOCOL="$SCRIPT_DIR/../protocols/adopt-node.cypher"
VALIDATE_BODY="$SCRIPT_DIR/../protocols/validate-merge.cypher"

tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT

{
  echo ':begin'
  cat "$ADOPT_PROTOCOL"
  cat "$VALIDATE_BODY"
  echo ':commit'
} > "$tmp"

echo "[adopt-node] adopting $NODE_ID by $ADOPTER"
if ! docker exec -i "$CONTAINER" cypher-shell \
      -u "$USER" -p "$PASS" --encryption false --format plain \
      -P "{node_id: \"$NODE_ID\", adopter_alias: \"$ADOPTER\"}" \
      < "$tmp" > /tmp/adopt.out 2>&1; then
  echo "[adopt-node] VALIDATION FAILED — transaction rolled back" >&2
  tail -15 /tmp/adopt.out >&2
  exit 1
fi

tail -10 /tmp/adopt.out
echo "[adopt-node] adopted $NODE_ID"
