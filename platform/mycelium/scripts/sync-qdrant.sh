#!/usr/bin/env bash
# sync-qdrant.sh — mirror a Qdrant collection between two instances.
# Use case: Mycelium embeds live on delta-server Qdrant (public-ish) and need
# to also populate pulse-server's co-located Qdrant so team Mycelium queries
# don't pay a cross-datacenter round trip.
#
# Usage:
#   SRC_URL=http://143.110.226.214:6333 \
#   DST_URL=http://127.0.0.1:6333 \
#   COLLECTION=mycelium-embeddings \
#   ./scripts/sync-qdrant.sh
#
# Requires: curl, jq, python3 (for JSON re-emit when batch size matters)

set -euo pipefail
SRC_URL="${SRC_URL:-http://143.110.226.214:6333}"
DST_URL="${DST_URL:-http://127.0.0.1:6333}"
COLL="${COLLECTION:-mycelium-embeddings}"
BATCH="${BATCH:-256}"

echo "[sync-qdrant] $SRC_URL -> $DST_URL  collection=$COLL  batch=$BATCH"

# 1. Ensure destination collection exists with matching vector config
src_info=$(curl -fs "$SRC_URL/collections/$COLL")
vec_size=$(echo "$src_info" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['result']['config']['params']['vectors']['size'])")
distance=$(echo "$src_info" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['result']['config']['params']['vectors']['distance'])")
echo "[sync-qdrant] source: dim=$vec_size distance=$distance"

if ! curl -fs "$DST_URL/collections/$COLL" > /dev/null 2>&1; then
  echo "[sync-qdrant] creating destination collection..."
  curl -fs -X PUT "$DST_URL/collections/$COLL" \
    -H "Content-Type: application/json" \
    -d "{\"vectors\": {\"size\": $vec_size, \"distance\": \"$distance\"}}" | head -c 200
  echo
fi

# 2. Scroll + upsert in batches (preserves IDs and payloads)
offset="null"
total=0
while : ; do
  body=$(python3 -c "
import json, sys
o = sys.argv[1]
b = {'limit': int(sys.argv[2]), 'with_payload': True, 'with_vector': True}
if o != 'null': b['offset'] = json.loads(o)
print(json.dumps(b))
" "$offset" "$BATCH")
  page=$(curl -fs -X POST "$SRC_URL/collections/$COLL/points/scroll" \
    -H "Content-Type: application/json" -d "$body")

  upsert_body=$(echo "$page" | python3 -c "
import json, sys
d = json.load(sys.stdin)['result']
pts = d['points']
print(json.dumps({'points': pts}))
")
  if [ "$(echo "$page" | python3 -c "import json,sys;print(len(json.load(sys.stdin)['result']['points']))")" = "0" ]; then
    break
  fi
  curl -fs -X PUT "$DST_URL/collections/$COLL/points?wait=false" \
    -H "Content-Type: application/json" -d "$upsert_body" > /dev/null
  batch_n=$(echo "$page" | python3 -c "import json,sys;print(len(json.load(sys.stdin)['result']['points']))")
  total=$((total + batch_n))
  echo "[sync-qdrant] $total points transferred..."
  offset=$(echo "$page" | python3 -c "import json,sys; o=json.load(sys.stdin)['result'].get('next_page_offset'); print('null' if o is None else json.dumps(o))")
  [ "$offset" = "null" ] && break
done

echo "[sync-qdrant] done: $total points"
dst_count=$(curl -fs "$DST_URL/collections/$COLL" | python3 -c "import json,sys;print(json.load(sys.stdin)['result']['points_count'])")
echo "[sync-qdrant] destination now: $dst_count points"
