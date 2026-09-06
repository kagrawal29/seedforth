#!/usr/bin/env bash
# ============================================================================
# Runner: witness-init
# ============================================================================
# Bootstraps a Witness identity:
#   1. generates an ed25519 keypair via mycelium-crypto.py keygen
#   2. stores the private key at ~/.mycelium/witness-<alias>.key (chmod 600)
#   3. registers the public key on the Witness node in Neo4j, creating the
#      node if missing
#
# Usage:
#   witness-init.sh <alias>
#
# Example:
#   witness-init.sh Mycelium
#
# Env vars:
#   NEO4J_CONTAINER   default: mycelium-neo4j-local
#   NEO4J_USER        default: neo4j
#   NEO4J_PASS        default: localtest12
#   KEY_DIR           default: ~/.mycelium
# ============================================================================
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: $0 <alias>" >&2
  exit 1
fi

ALIAS="$1"
BOLT="${NEO4J_BOLT:-bolt://localhost:7687}"
USER="${NEO4J_USER:-neo4j}"
PASS="${NEO4J_PASS:-localtest12}"
KEY_DIR="${KEY_DIR:-$HOME/.mycelium}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRYPTO="$SCRIPT_DIR/mycelium-crypto.py"

if [ ! -f "$CRYPTO" ]; then
  echo "[witness-init] ERROR: crypto sidecar missing: $CRYPTO" >&2
  exit 1
fi

echo "[witness-init] generating ed25519 keypair for $ALIAS"
PUB_KEY=$(python3 "$CRYPTO" keygen --alias "$ALIAS" --key-dir "$KEY_DIR")

if [ -z "$PUB_KEY" ]; then
  echo "[witness-init] ERROR: keygen produced no public key" >&2
  exit 1
fi

echo "[witness-init] public_key=$PUB_KEY"
echo "[witness-init] private key stored at $KEY_DIR/witness-$ALIAS.key"

echo "[witness-init] registering Witness node in Neo4j..."
cypher-shell -a "$BOLT" \
  -u "$USER" -p "$PASS" --encryption false --format plain \
  -P "{alias: \"$ALIAS\", public_key: \"$PUB_KEY\"}" <<'CYPHER'
MERGE (w:Witness {alias: $alias})
ON CREATE SET w.node_id = 'witness-' + toLower($alias),
              w.active = true,
              w.role = 'signer',
              w.registered_at = toString(datetime()),
              w.key_algorithm = 'ed25519'
SET w.public_key = $public_key,
    w.key_algorithm = 'ed25519',
    w.public_key_registered_at = toString(datetime())
RETURN w.node_id AS node_id, w.alias AS alias, substring(w.public_key, 0, 16) + '...' AS pubkey_preview;
CYPHER
