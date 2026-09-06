#!/usr/bin/env bash
# qdrant-search.sh -- semantic search via Qdrant
# Usage: bash graph/runner/qdrant-search.sh "query text" [limit]
# Output: node_id,score,label,fractal_scale (one per line)
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: qdrant-search.sh <text> [limit]" >&2
  exit 1
fi

TEXT="$1"
LIMIT="${2:-5}"
QDRANT_URL="${QDRANT_URL:-http://143.110.226.214:6333}"
COLLECTION="mycelium-embeddings"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Get embedding from Ollama
VEC=$(bash "$SCRIPT_DIR/embed-text.sh" "$TEXT" 2>/dev/null)
if [ -z "$VEC" ]; then
  echo "error: embedding failed" >&2
  exit 1
fi

# Search Qdrant
python3 -c "
import sys, json, requests

vec = [float(x) for x in sys.argv[1].split(',')]
limit = int(sys.argv[2])
url = sys.argv[3]
collection = sys.argv[4]

resp = requests.post(f'{url}/collections/{collection}/points/search',
                     json={'vector': vec, 'limit': limit, 'with_payload': True}, timeout=10)
resp.raise_for_status()
for r in resp.json().get('result', []):
    p = r.get('payload', {})
    print(f\"{p.get('node_id','?')},{r.get('score',0):.3f},{p.get('label','')},{p.get('fractal_scale','')}\")
" "$VEC" "$LIMIT" "$QDRANT_URL" "$COLLECTION"
