#!/usr/bin/env bash
# ============================================================================
# Runner: source-register
# ============================================================================
# Registers a new external graph Source with a public key and schema version.
# The public key is what the source will use to sign their import bundles
# (future: Phase 8 adoption signing; Phase 7 import is read-only tagged).
#
# Usage:
#   source-register.sh <alias> <public_key> [schema_version] [description]
#
# Env vars:
#   NEO4J_CONTAINER   default: mycelium-neo4j-local
#   NEO4J_USER        default: neo4j
#   NEO4J_PASS        default: localtest12
# ============================================================================
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "usage: $0 <alias> <public_key> [schema_version] [description]" >&2
  exit 1
fi

ALIAS="$1"
PUB_KEY="$2"
SCHEMA="${3:-v1}"
DESC="${4:-}"

BOLT="${NEO4J_BOLT:-bolt://localhost:7687}"
USER="${NEO4J_USER:-neo4j}"
PASS="${NEO4J_PASS:-localtest12}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROTOCOL="$SCRIPT_DIR/../protocols/source-register.cypher"

PARAMS='{alias: "'"$ALIAS"'", public_key: "'"$PUB_KEY"'", schema_version: "'"$SCHEMA"'", description: "'"$DESC"'"}'

echo "[source-register] alias=$ALIAS"
cypher-shell -a "$BOLT" \
  -u "$USER" -p "$PASS" --encryption false --format plain \
  -P "$PARAMS" \
  < "$PROTOCOL"
