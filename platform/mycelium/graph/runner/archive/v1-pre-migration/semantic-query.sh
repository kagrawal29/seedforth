#!/usr/bin/env bash
# semantic-query.sh — Embed a text query and run vector search against Neo4j.
# Usage: ./semantic-query.sh "auth token" [top_k]
set -euo pipefail

if [ -z "${1:-}" ]; then
  echo "Usage: $0 \"<query text>\" [top_k]"
  exit 1
fi

QUERY_TEXT="$1"
TOP_K="${2:-10}"

# --- Ensure Ollama running ---
if ! /opt/homebrew/bin/ollama ps &>/dev/null; then
  /opt/homebrew/bin/ollama serve &>/tmp/ollama.log &
  sleep 3
fi

# --- Embed query + run vector search ---
echo ""
echo "Top $TOP_K matches for: \"$QUERY_TEXT\""
echo "-------------------------------------------------------"
python3 - "$QUERY_TEXT" "$TOP_K" <<'PYEOF'
import json, sys, requests
from neo4j import GraphDatabase

query_text = sys.argv[1]
top_k = int(sys.argv[2])

resp = requests.post(
    "http://localhost:11434/api/embeddings",
    json={"model": "nomic-embed-text", "prompt": query_text},
    timeout=30
)
resp.raise_for_status()
vec = resp.json()["embedding"]

driver = GraphDatabase.driver("bolt://localhost:7689", auth=("neo4j", "localtest12"))

cypher = """
CALL db.index.vector.queryNodes('node_embeddings', $k, $vec)
YIELD node, score
RETURN node.node_id AS node_id,
       labels(node)[0] AS node_type,
       node.label AS name,
       score
ORDER BY score DESC
"""

with driver.session() as session:
    result = session.run(cypher, k=top_k, vec=vec)
    rows = [dict(r) for r in result]

if not rows:
    print("No results (index may still be populating or no embeddings yet).")
else:
    print(f"{'node_id':<45} {'type':<22} {'score':<8} name")
    print("-" * 110)
    for r in rows:
        print(f"{(r['node_id'] or ''):<45} {(r['node_type'] or ''):<22} {r['score']:.4f}  {r['name'] or ''}")

driver.close()
PYEOF
