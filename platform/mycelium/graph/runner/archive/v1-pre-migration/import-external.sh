#!/usr/bin/env bash
# ============================================================================
# Runner: import-external
# ============================================================================
# Applies an external graph bundle under a Source namespace, tags every
# imported node with :Imported and :ImportedFrom_<Source> labels plus
# provenance metadata, and runs validate-merge to ensure mycelium's
# invariants/tests still hold after the import.
#
# Hybrid read-only mode: imported nodes carry :Imported label and are
# isolated from core invariants by default (Phase 1.5 scope filter).
# Adoption (promoting specific :Imported nodes to full citizens) happens
# in Phase 8 via adopt-node.cypher.
#
# Usage:
#   import-external.sh <source_alias> <bundle_cypher_file>
#
# Preconditions:
#   1. Source node must already be registered via source-register.cypher
#   2. The bundle's MERGE statements must use compound node_ids of the
#      form "<source_alias>:<original-id>" — enforced by pre-check.
#
# Flow:
#   1. Validate bundle uses compound node_ids for the given source
#   2. Wrap the bundle in a transaction with the tagging pass + Merkle +
#      validate-merge body, apply all as one unit
#   3. On success, mint a candidate species capturing the post-import state
#
# Env vars:
#   NEO4J_CONTAINER   default: mycelium-neo4j-local
#   NEO4J_USER        default: neo4j
#   NEO4J_PASS        default: localtest12
# ============================================================================
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "usage: $0 <source_alias> <bundle_cypher_file>" >&2
  exit 2
fi

SOURCE_ALIAS="$1"
BUNDLE="$2"

if [ ! -f "$BUNDLE" ]; then
  echo "[import-external] ERROR: bundle not found: $BUNDLE" >&2
  exit 2
fi

CONTAINER="${NEO4J_CONTAINER:-mycelium-neo4j-local}"
USER="${NEO4J_USER:-neo4j}"
PASS="${NEO4J_PASS:-localtest12}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TAG_PROTOCOL="$SCRIPT_DIR/../protocols/import-external-tag.cypher"
VALIDATE_BODY="$SCRIPT_DIR/../protocols/validate-merge.cypher"

cypher_exec() {
  docker exec -i "$CONTAINER" cypher-shell \
    -u "$USER" -p "$PASS" --encryption false --format plain "$@"
}

echo "[import-external] source=$SOURCE_ALIAS bundle=$BUNDLE"

# --- Step 0: enforce bundle convention --------------------------------------
# Every `node_id: "..."` in the bundle must start with '<source_alias>:'
# or be something the source registered before (edge case). We do a
# simple regex scan for node_id literals.
wrong_ids=$(grep -oE 'node_id:\s*"[^"]+"' "$BUNDLE" | grep -oE '"[^"]+"' | tr -d '"' | grep -v "^${SOURCE_ALIAS}:" || true)
if [ -n "$wrong_ids" ]; then
  echo "[import-external] ERROR: bundle contains non-namespaced node_ids:" >&2
  echo "$wrong_ids" | head -10 | sed 's/^/  /' >&2
  echo "  (every MERGE must use node_id: \"${SOURCE_ALIAS}:<original>\")" >&2
  exit 1
fi

echo "[import-external] bundle convention check: ok"

# --- Step 1: verify source is registered ------------------------------------
SOURCE_EXISTS=$(cypher_exec "MATCH (s:Source {alias: '$SOURCE_ALIAS'}) WHERE s.active = true RETURN count(s)" | tail -1 | tr -d '"')
if [ "$SOURCE_EXISTS" != "1" ]; then
  echo "[import-external] ERROR: no active Source with alias=$SOURCE_ALIAS" >&2
  echo "  register first via: source-register.sh $SOURCE_ALIAS <public_key>" >&2
  exit 1
fi

# --- Step 2: assemble the transaction ---------------------------------------
# :begin → bundle → tagging → validate-merge body → :commit
# Note: tagging requires $source_alias + $imported_in_species params, and
# validate-merge.cypher runs unparameterized. We use --param to supply
# the tag pass parameters; since :commit only fires if everything above
# succeeds, a validation failure inside validate-merge rolls back the
# whole thing including the tagging and the bundle writes.
#
# For imported_in_species we use a placeholder: 'pending-mint' for now,
# because the species mint happens AFTER validation passes. The tagging
# sets imported_in_species = 'pending-mint' initially and a follow-up
# query rewrites it to the actual candidate id after mint.

tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT

{
  echo ':begin'
  cat "$BUNDLE"
  cat "$TAG_PROTOCOL"
  cat "$VALIDATE_BODY"
  echo ':commit'
} > "$tmp"

echo "[import-external] applying bundle + tagging + validate in transaction..."
if ! cypher_exec -P "{source_alias: \"$SOURCE_ALIAS\", imported_in_species: \"pending-mint\"}" < "$tmp" > /tmp/ie.out 2>&1; then
  echo "[import-external] VALIDATION FAILED — transaction rolled back" >&2
  tail -20 /tmp/ie.out >&2
  exit 1
fi

tail -20 /tmp/ie.out
echo "[import-external] transaction committed"

# --- Step 3: mint candidate species capturing the new state -----------------
echo "[import-external] minting candidate species..."
bash "$SCRIPT_DIR/species-mint.sh" | tail -5

# --- Step 4: backfill imported_in_species on the newly-tagged nodes ---------
# Order by minted_at so we pick the most recent candidate (the one we just
# minted, not a leftover from a previous session).
CANDIDATE=$(cypher_exec "MATCH (c:CandidateSpecies) RETURN c.node_id ORDER BY c.minted_at DESC LIMIT 1" | tail -1 | tr -d '"')
if [ -n "$CANDIDATE" ] && [ "$CANDIDATE" != "NULL" ]; then
  cypher_exec "MATCH (n:Imported {imported_in_species: 'pending-mint'}) WHERE n.provenance = '$SOURCE_ALIAS' SET n.imported_in_species = '$CANDIDATE' RETURN count(n) AS backfilled" | tail -3
  echo "[import-external] candidate=$CANDIDATE"
else
  echo "[import-external] (no candidate minted — no drift from the import, which means it was a no-op)"
fi
