#!/usr/bin/env bash
# ============================================================================
# Runner: backup-graph
# ============================================================================
# Exports the current graph state and stores backups locally and in git.
# Designed to run after every meaningful session and as part of heartbeat.
#
# Backup layers:
#   1. Local: graph-state.cypher at repo root (overwritten each run)
#   2. Timestamped: graph/backups/graph-state-YYYY-MM-DD-HHMMSS.cypher
#   3. Git: committed and pushed to remote
#
# Retention: keeps last 5 timestamped backups locally, prunes older ones.
#
# Env vars (all optional):
#   NEO4J_CONTAINER   default: mycelium-neo4j-local
#   NEO4J_USER        default: neo4j
#   NEO4J_PASS        default: localtest12
#   BACKUP_DIR        default: <repo-root>/graph/backups
#   MAX_BACKUPS       default: 5
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

USER="${NEO4J_USER:-neo4j}"
PASS="${NEO4J_PASS:-localtest12}"
BOLT="${NEO4J_BOLT:-bolt://localhost:7687}"
CYPHER_SHELL="${CYPHER_SHELL:-$(command -v cypher-shell || echo /opt/homebrew/Cellar/neo4j/2026.03.1/libexec/bin/cypher-shell)}"
BACKUP_DIR="${BACKUP_DIR:-$REPO_ROOT/graph/backups}"
MAX_BACKUPS="${MAX_BACKUPS:-5}"

# --- Pre-flight checks ---
if [ ! -x "$CYPHER_SHELL" ]; then
  echo "SKIP: cypher-shell not found at $CYPHER_SHELL" >&2
  exit 0
fi

if ! nc -z localhost 7687 2>/dev/null; then
  echo "SKIP: native Neo4j not running on bolt://localhost:7687" >&2
  exit 0
fi

# Verify graph has data before backing up
node_count=$("$CYPHER_SHELL" \
  -a "$BOLT" -u "$USER" -p "$PASS" --format plain \
  "MATCH (n) RETURN count(n)" 2>/dev/null | tail -n +2 | head -1 | tr -d ' ')

if [ -z "$node_count" ] || [ "$node_count" -lt 100 ]; then
  echo "ABORT: graph has only $node_count nodes -- refusing to overwrite backup with degraded state" >&2
  exit 1
fi

echo "graph has $node_count nodes -- proceeding with backup"

# --- Step 1: Export current state ---
bash "$SCRIPT_DIR/export-graph-state.sh"

if [ ! -f "$REPO_ROOT/graph-state.cypher" ]; then
  echo "ABORT: export-graph-state.sh did not produce graph-state.cypher" >&2
  exit 1
fi

export_size=$(wc -c < "$REPO_ROOT/graph-state.cypher" | tr -d ' ')
echo "export size: $export_size bytes"

# --- Step 2: Timestamped local backup ---
mkdir -p "$BACKUP_DIR"
timestamp=$(date +%Y-%m-%d-%H%M%S)
backup_file="$BACKUP_DIR/graph-state-${timestamp}.cypher"
cp "$REPO_ROOT/graph-state.cypher" "$backup_file"
echo "local backup: $backup_file"

# --- Step 3: Prune old backups (keep last N) ---
backup_count=$(ls -1 "$BACKUP_DIR"/graph-state-*.cypher 2>/dev/null | wc -l | tr -d ' ')
if [ "$backup_count" -gt "$MAX_BACKUPS" ]; then
  to_remove=$((backup_count - MAX_BACKUPS))
  ls -1t "$BACKUP_DIR"/graph-state-*.cypher | tail -n "$to_remove" | while read -r old; do
    rm -f "$old"
    echo "pruned: $(basename "$old")"
  done
fi

# --- Step 4: Git commit and push ---
cd "$REPO_ROOT"
if git diff --quiet graph-state.cypher 2>/dev/null; then
  echo "graph-state.cypher unchanged -- skip git commit"
else
  git add graph-state.cypher
  git commit -m "backup: graph-state export ($node_count nodes, $(date +%Y-%m-%d))" 2>/dev/null || true
  git push 2>/dev/null || echo "WARN: git push failed -- backup is local only"
  echo "committed and pushed to git"
fi

echo "backup complete: $node_count nodes, $export_size bytes"
