#!/usr/bin/env bash
# ============================================================================
# atom-run-embed.sh -- Embedding-aware protocol runner
# ============================================================================
# Extension of atom-run.sh that detects atoms with requires_embedding=true
# and post-processes their output through the embedding bridge.
#
# This runs the same atom chain as atom-run.sh, but adds:
#  1. Check if any atoms are marked requires_embedding
#  2. Post-process outputs through embed-text.sh
#  3. Write embeddings back to Neo4j (optional)
#
# Usage:
#   atom-run-embed.sh <protocol_node_id> [--persist]
#
# Example:
#   atom-run-embed.sh protocol-discover-gaps
#   atom-run-embed.sh protocol-semantic-search --persist
#
# The --persist flag writes embeddings back to Neo4j.embedding property
# for downstream queries. Without it, embeddings flow through the pipeline
# but don't get persisted (useful for ephemeral semantic analysis).
# ============================================================================
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: $0 <protocol_node_id> [--persist]" >&2
  exit 1
fi

PROTOCOL_ID="$1"
PERSIST="${2:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Run the standard atom executor first
echo "[atom-run-embed] phase 1: execute atoms via atom-run.sh"
bash "$SCRIPT_DIR/atom-run.sh" "$PROTOCOL_ID"
ATOM_OUT="/tmp/atom-run.out"

# Check if any atoms in this protocol require embedding
echo "[atom-run-embed] phase 2: check for embedding requirements"
BOLT="${NEO4J_BOLT:-bolt://localhost:7687}"
USER="${NEO4J_USER:-neo4j}"
PASS="${NEO4J_PASS:-localtest12}"

cypher_exec() {
  cypher-shell -a "$BOLT" \
    -u "$USER" -p "$PASS" --encryption false --format plain "$@"
}

HAS_EMBEDDING=$(cypher_exec <<CYPHER
MATCH (a:CypherAtom {source_protocol: '$PROTOCOL_ID'})
WHERE a.requires_embedding = true
RETURN count(a) AS atom_count
CYPHER
| tail -n +2 | head -1)

if [ -z "$HAS_EMBEDDING" ] || [ "$HAS_EMBEDDING" -eq 0 ]; then
  echo "[atom-run-embed] no atoms require embedding, done"
  exit 0
fi

echo "[atom-run-embed] $HAS_EMBEDDING atom(s) require embedding"

# Get the atoms that require embedding
echo "[atom-run-embed] phase 3: extract embedding atoms"
EMBED_ATOMS=$(cypher_exec <<CYPHER
MATCH (a:CypherAtom {source_protocol: '$PROTOCOL_ID'})
WHERE a.requires_embedding = true
RETURN a.node_id, a.atom_order
ORDER BY a.atom_order
CYPHER
| tail -n +2)

# Process outputs through embedding bridge
echo "[atom-run-embed] phase 4: embed outputs"
EMBED_COUNT=0
while IFS= read -r atom_info; do
  [ -z "$atom_info" ] && continue

  # Parse the result line
  atom_info="${atom_info#\"}"
  atom_info="${atom_info%\"}"
  atom_node_id="${atom_info%%|*}"

  # Run embedding on non-empty lines from the atom's output
  echo "[atom-run-embed]   atom $atom_node_id:"

  if [ -f "$ATOM_OUT" ]; then
    # Find lines related to this atom (heuristic: non-empty lines after execution)
    grep -v "^$" "$ATOM_OUT" 2>/dev/null | while read -r line; do
      # Skip command output noise
      if [[ ! "$line" =~ ^(\[|neo4j@|---|^$) ]]; then
        EMBEDDING=$(bash "$SCRIPT_DIR/embed-text.sh" "$line" 2>/dev/null || echo "")
        if [ -n "$EMBEDDING" ]; then
          echo "[atom-run-embed]     embedded: ${line:0:50}..."

          if [ "$PERSIST" = "--persist" ]; then
            # Store embedding in Neo4j (future: also Qdrant)
            cypher_exec \
              "MATCH (n) WHERE n.output_text = '$line' SET n.embedding = [${EMBEDDING}], n.embedding_model = 'nomic-embed-text', n.embedded_at = datetime()" \
              2>/dev/null || true
          fi

          EMBED_COUNT=$((EMBED_COUNT + 1))
        fi
      fi
    done
  fi
done <<< "$EMBED_ATOMS"

echo "[atom-run-embed] embedded $EMBED_COUNT outputs"
echo "[atom-run-embed] phase 5: complete"
