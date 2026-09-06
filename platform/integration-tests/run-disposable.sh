#!/usr/bin/env bash
set -euo pipefail

# Run real graph boundary checks against a disposable Neo4j container.
# This never targets the configured production graph.
CONTAINER="seedforth-integration-$$"
PORT="${NEO4J_TEST_PORT:-17474}"
IMAGE="${NEO4J_TEST_IMAGE:-neo4j:5-community}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
MODEL="$ROOT/platform/mycelium/graph/knowledge/seedforth-control-model-v1.cypher"
BASE="http://127.0.0.1:${PORT}"
cd "$ROOT"

cleanup() {
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
}
trap cleanup EXIT

if ! command -v docker >/dev/null 2>&1; then
  echo "SKIP: docker is required for the disposable Neo4j gate" >&2
  exit 2
fi

docker run --rm -d --name "$CONTAINER" -p "${PORT}:7474" \
  -e NEO4J_AUTH=none "$IMAGE" >/dev/null
docker cp "$MODEL" "$CONTAINER:/tmp/control-model.cypher"

for attempt in $(seq 1 60); do
  if curl -fsS "$BASE" >/dev/null 2>&1; then
    break
  fi
  if [ "$attempt" = 60 ]; then
    echo "Neo4j did not become ready" >&2
    exit 1
  fi
  sleep 1
done

# The bootstrap must be safe to apply repeatedly.
docker exec "$CONTAINER" cypher-shell --format plain -f /tmp/control-model.cypher >/dev/null
docker exec "$CONTAINER" cypher-shell --format plain -f /tmp/control-model.cypher >/dev/null

python3 - "$BASE" <<'PY'
import json
import sys
import urllib.request
from pathlib import Path

base = sys.argv[1]
sys.path.insert(0, str(Path.cwd() / "platform" / "delta"))
from delta.control_envelope import make_envelope


def query(statement, parameters=None):
    body = {"statements": [{"statement": statement}]}
    if parameters:
        body["statements"][0]["parameters"] = parameters
    request = urllib.request.Request(
        f"{base}/db/neo4j/tx/commit",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        payload = json.loads(response.read())
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    result = payload["results"][0]
    return [dict(zip(result["columns"], row["row"])) for row in result["data"]]


envelope = make_envelope(
    kind="progress",
    project="integration",
    source="delta",
    correlation_id="integration-session-1",
    payload={"status": "in_progress", "summary": "disposable replay"},
    message_id="integration-message-1",
    occurred_at="2026-09-06T12:00:00+00:00",
)

statement = (
    "MERGE (e:Signal {node_id: $message_id}) "
    "SET e.schema = $schema, e.kind = $kind, e.project = $project, "
    "e.payload = $payload, e.source = $source "
    "RETURN e.node_id AS node_id"
)
for _ in range(2):
    query(statement, envelope)

count = query(
    "MATCH (e:Signal {node_id: $message_id}) RETURN count(e) AS count",
    {"message_id": envelope["message_id"]},
)[0]["count"]
assert count == 1, count
print("PASS: control model bootstrap is idempotent")
print("PASS: Delta progress envelope replay produces one durable signal")
PY
