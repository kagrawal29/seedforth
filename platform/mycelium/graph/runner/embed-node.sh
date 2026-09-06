#!/usr/bin/env bash
# embed-node.sh -- embed a single node by node_id, write to Neo4j
# Usage: bash graph/runner/embed-node.sh <node_id>
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

NODE_ID="$1"
if [ -z "$NODE_ID" ]; then
  echo "usage: embed-node.sh <node_id>" >&2
  exit 1
fi

BOLT="${NEO4J_BOLT:-bolt://localhost:7687}"
USER="${NEO4J_USER:-neo4j}"
PASS="${NEO4J_PASS:-localtest12}"

# Get node text directly from Neo4j (bypass mycelium CLI to avoid preflight output)
TEXT=$(cypher-shell -a "$BOLT" -u "$USER" -p "$PASS" --encryption false --format plain \
  "MATCH (n {node_id: '$NODE_ID'}) RETURN coalesce(labels(n)[0],'') + ' ' + coalesce(n.label,'') + ' ' + coalesce(n.description,'') + ' ' + n.node_id AS text" 2>/dev/null \
  | tail -n +2 | head -1 | sed -e 's/^"//' -e 's/"$//')

if [ -z "$TEXT" ] || [ "$TEXT" = "null" ]; then
  echo "error: node not found: $NODE_ID" >&2
  exit 1
fi

# Embed via Ollama
VEC=$(bash "$SCRIPT_DIR/embed-text.sh" "$TEXT" 2>/dev/null)
if [ -z "$VEC" ]; then
  echo "error: embedding failed for $NODE_ID" >&2
  exit 1
fi

# Write to Neo4j
cypher-shell -a "$BOLT" -u "$USER" -p "$PASS" --encryption false --format plain \
  "MATCH (n {node_id: '$NODE_ID'}) SET n.embedding = [$VEC], n.embedding_model = 'nomic-embed-text', n.embedding_for_leaf_hash = n.leaf_hash RETURN n.node_id" 2>/dev/null | tail -n +2

echo "embedded: $NODE_ID"
