#!/usr/bin/env bash
# embed-dirty.sh — Shell wrapper for embed-dirty.py
# Ensures Ollama is running, nomic-embed-text is pulled, deps installed,
# vector index exists, then runs the Python embedder.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BOLT="${NEO4J_BOLT:-bolt://localhost:7687}"
USER="${NEO4J_USER:-neo4j}"
PASS="${NEO4J_PASS:-localtest12}"
BOLT="${NEO4J_BOLT:-bolt://localhost:7687}"
USER="${NEO4J_USER:-neo4j}"
PASS="${NEO4J_PASS:-localtest12}"

# --- 1. Ensure Python deps ---
python3 -c "import neo4j, requests" 2>/dev/null || pip install --quiet neo4j requests

# --- 2. Ensure Ollama daemon is running ---
if ! /opt/homebrew/bin/ollama ps &>/dev/null; then
  echo "Starting Ollama daemon..."
  /opt/homebrew/bin/ollama serve &>/tmp/ollama.log &
  sleep 3
fi

# --- 3. Ensure nomic-embed-text is pulled ---
if ! /opt/homebrew/bin/ollama list 2>/dev/null | grep -q "nomic-embed-text"; then
  echo "Pulling nomic-embed-text (first time, may take a few minutes)..."
  /opt/homebrew/bin/ollama pull nomic-embed-text
fi

# --- 4. Create vector index (idempotent) ---
# Neo4j 5.x requires a label. embed-dirty.py writes n:GraphNode on every node.
# DROP + CREATE only if index doesn't exist on GraphNode already.
echo "Ensuring vector index on GraphNode label..."
cypher-shell -a "$BOLT" -u "$USER" -p "$PASS" --encryption false \
  "CALL db.index.vector.createNodeIndex('node_embeddings', 'GraphNode', 'embedding', 768, 'cosine')" 2>/dev/null || true
cypher-shell -a "$BOLT" -u "$USER" -p "$PASS" --encryption false \
  "SHOW INDEXES WHERE name = 'node_embeddings'" | grep -q "GraphNode" && echo "Index OK." \
  || (echo "WARNING: vector index may not be on GraphNode label" >&2)

# --- 5. Run embedder ---
echo "Running embed-dirty.py..."
python3 "$SCRIPT_DIR/embed-dirty.py"

echo "embed-dirty.sh complete."
