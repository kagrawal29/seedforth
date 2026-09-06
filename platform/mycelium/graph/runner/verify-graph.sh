#!/usr/bin/env bash
# ============================================================================
# Runner: verify-graph
# ============================================================================
# Quick health check to run at session start. Verifies the graph has expected
# data volume and that the backup file exists. Exits non-zero if something
# is wrong so the caller knows to investigate before mutating.
#
# Usage: ./graph/runner/verify-graph.sh
#        Returns: node count, edge count, backup status, and warnings
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

BOLT="${NEO4J_BOLT:-bolt://localhost:7687}"
USER="${NEO4J_USER:-neo4j}"
PASS="${NEO4J_PASS:-localtest12}"

# Expected minimums (update as graph grows)
MIN_NODES=8000
MIN_EDGES=100000

errors=0

# --- Check Neo4j is running ---
if ! timeout 5 cypher-shell -a "$BOLT" -u "$USER" -p "$PASS" --encryption false "RETURN 1" >/dev/null 2>&1; then
  # Fallback: check systemctl status on Linux, or brew services on macOS
  if command -v systemctl &>/dev/null && systemctl is-active neo4j >/dev/null 2>&1; then
    # systemctl reports active, but cypher-shell failed - may be starting
    echo "FAIL: Neo4j service running but unreachable at $BOLT"
  elif command -v brew &>/dev/null && brew services list 2>/dev/null | grep -q "neo4j"; then
    echo "FAIL: Neo4j installed but unreachable at $BOLT"
  else
    echo "FAIL: Neo4j is not running. Start with: systemctl start neo4j or brew services start neo4j"
  fi
  exit 1
fi

# --- Check node count ---
nodes=$(cypher-shell -a "$BOLT" \
  -u "$USER" -p "$PASS" --encryption false --format plain \
  "MATCH (n) RETURN count(n)" 2>/dev/null | tail -n +2 | head -1 | tr -d ' ')

if [ -z "$nodes" ]; then
  echo "FAIL: cannot query Neo4j"
  exit 1
fi

echo "nodes: $nodes"

if [ "$nodes" -lt "$MIN_NODES" ]; then
  echo "WARN: node count ($nodes) below expected minimum ($MIN_NODES) -- graph may be degraded"
  errors=$((errors + 1))
fi

# --- Check edge count ---
edges=$(cypher-shell -a "$BOLT" \
  -u "$USER" -p "$PASS" --encryption false --format plain \
  "MATCH ()-[r]->() RETURN count(r)" 2>/dev/null | tail -n +2 | head -1 | tr -d ' ')

echo "edges: $edges"

if [ "$edges" -lt "$MIN_EDGES" ]; then
  echo "WARN: edge count ($edges) below expected minimum ($MIN_EDGES) -- graph may be degraded"
  errors=$((errors + 1))
fi

# --- Check backup exists ---
if [ -f "$REPO_ROOT/graph-state.cypher" ]; then
  backup_size=$(wc -c < "$REPO_ROOT/graph-state.cypher" | tr -d ' ')
  backup_date=$(stat -f '%Sm' -t '%Y-%m-%d %H:%M' "$REPO_ROOT/graph-state.cypher" 2>/dev/null || stat -c '%y' "$REPO_ROOT/graph-state.cypher" 2>/dev/null | cut -d. -f1)
  echo "backup: graph-state.cypher ($backup_size bytes, $backup_date)"
else
  echo "FAIL: no graph-state.cypher backup file"
  errors=$((errors + 1))
fi

# --- Check timestamped backups ---
backup_dir="$REPO_ROOT/graph/backups"
if [ -d "$backup_dir" ]; then
  backup_count=$(ls -1 "$backup_dir"/graph-state-*.cypher 2>/dev/null | wc -l | tr -d ' ')
  latest=$(ls -1t "$backup_dir"/graph-state-*.cypher 2>/dev/null | head -1)
  echo "timestamped backups: $backup_count (latest: $(basename "${latest:-none}"))"
else
  echo "INFO: no timestamped backups yet (run backup-graph.sh to create)"
fi

# --- Summary ---
if [ "$errors" -gt 0 ]; then
  echo ""
  echo "STATUS: $errors warnings -- investigate before running heavy operations"
  exit 1
else
  echo ""
  echo "STATUS: healthy ($nodes nodes, $edges edges, backup current)"
  exit 0
fi
