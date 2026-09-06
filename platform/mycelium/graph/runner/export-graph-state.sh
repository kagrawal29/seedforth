#!/usr/bin/env bash
# ============================================================================
# Runner: export-graph-state
# ============================================================================
# Executes graph/protocols/export-graph-state.cypher against the local Neo4j
# and writes the cleaned output to ./graph-state.cypher at the repo root.
#
# The protocol RETURNs one cypher statement per row. cypher-shell --format plain
# wraps each string result in double quotes with escaped inner quotes and adds
# a header line. This wrapper strips those artifacts.
#
# Env vars (all optional):
#   NEO4J_CONTAINER   default: mycelium-neo4j-local
#   NEO4J_USER        default: neo4j
#   NEO4J_PASS        default: localtest12
#   OUTPUT            default: <repo-root>/graph-state.cypher
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PROTOCOL="$REPO_ROOT/graph/protocols/export-graph-state.cypher"

USER="${NEO4J_USER:-neo4j}"
PASS="${NEO4J_PASS:-localtest12}"
BOLT="${NEO4J_BOLT:-bolt://localhost:7687}"
CYPHER_SHELL="${CYPHER_SHELL:-$(command -v cypher-shell || echo /opt/homebrew/Cellar/neo4j/2026.03.1/libexec/bin/cypher-shell)}"
OUTPUT="${OUTPUT:-$REPO_ROOT/graph-state.cypher}"

if [ ! -f "$PROTOCOL" ]; then
  echo "missing protocol: $PROTOCOL" >&2
  exit 1
fi

if [ ! -x "$CYPHER_SHELL" ]; then
  echo "cypher-shell not found at $CYPHER_SHELL" >&2
  exit 1
fi

if ! nc -z localhost 7687 2>/dev/null; then
  echo "native Neo4j not running on bolt://localhost:7687" >&2
  exit 1
fi

# Run the protocol, strip cypher-shell --format plain artifacts:
#   1. tail -n +1: keep all rows (protocol RETURNs, no implicit header to drop
#      because we want per-statement output)
#   2. grep '^"': keep only quoted-string rows (drops the "line" header columns
#      that cypher-shell prints before each RETURN's results)
#   3. sed: unwrap the surrounding double quotes and unescape inner \"
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

"$CYPHER_SHELL" \
  -a "$BOLT" -u "$USER" -p "$PASS" --format plain \
  < "$PROTOCOL" \
  | grep '^"' \
  | sed -e 's/^"//' -e 's/"$//' -e 's/\\"/"/g' \
  > "$tmp"

node_count=$(grep -c '^MERGE (n:' "$tmp" || true)
edge_count=$(grep -c '^MATCH (a:' "$tmp" || true)

mv "$tmp" "$OUTPUT"
trap - EXIT

printf 'exported %s nodes, %s edges → %s\n' "$node_count" "$edge_count" "$OUTPUT"
printf 'size: %s\n' "$(wc -c < "$OUTPUT" | awk '{print $1}')"
