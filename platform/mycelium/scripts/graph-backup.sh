#!/usr/bin/env bash
#
# graph-backup.sh — Daily FalkorDB backup via Redis RDB snapshot
#
# FalkorDB is Redis-based. BGSAVE triggers an RDB snapshot to /data/dump.rdb
# inside the container. This script:
#   1. Triggers BGSAVE on the FalkorDB container
#   2. Waits for the save to complete
#   3. Copies the RDB file to a dated backup
#   4. Prunes backups older than 7 days
#
# Usage:
#   ./scripts/graph-backup.sh                     # local Docker (port 6380)
#   ./scripts/graph-backup.sh --remote             # production server
#   FALKORDB_PORT=6380 ./scripts/graph-backup.sh   # custom port
#
# Environment:
#   FALKORDB_HOST   — default: localhost
#   FALKORDB_PORT   — default: 6380
#   BACKUP_DIR      — default: /var/backups/falkordb (or ./backups/falkordb locally)
#   BACKUP_KEEP_DAYS — default: 7
#   COMPOSE_FILE    — default: docker/docker-compose.production.yml

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Configuration
HOST="${FALKORDB_HOST:-localhost}"
PORT="${FALKORDB_PORT:-6380}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-7}"
COMPOSE_FILE="${COMPOSE_FILE:-${REPO_ROOT}/docker/docker-compose.production.yml}"
CONTAINER_NAME="falkordb"

# Backup directory: use /var/backups on server, local dir otherwise
if [[ -d /var/backups ]]; then
    BACKUP_DIR="${BACKUP_DIR:-/var/backups/falkordb}"
else
    BACKUP_DIR="${BACKUP_DIR:-${REPO_ROOT}/backups/falkordb}"
fi

DATE="$(date -u +%Y-%m-%d_%H%M%S)"
BACKUP_FILE="${BACKUP_DIR}/asgard-${DATE}.rdb"

log() { echo "[graph-backup] $(date -u +%H:%M:%S) $*"; }

# ── 0. Pre-flight ─────────────────────────────────────────────

mkdir -p "$BACKUP_DIR"

# Check FalkorDB is reachable
if ! redis-cli -h "$HOST" -p "$PORT" ping >/dev/null 2>&1; then
    log "ERROR: Cannot reach FalkorDB at ${HOST}:${PORT}"
    exit 1
fi

log "FalkorDB reachable at ${HOST}:${PORT}"

# ── 1. Trigger BGSAVE ─────────────────────────────────────────

# Get last save timestamp before triggering
LAST_SAVE_BEFORE=$(redis-cli -h "$HOST" -p "$PORT" LASTSAVE 2>/dev/null | tr -d '[:space:]')
log "Last save timestamp before BGSAVE: ${LAST_SAVE_BEFORE}"

log "Triggering BGSAVE..."
BGSAVE_RESULT=$(redis-cli -h "$HOST" -p "$PORT" BGSAVE 2>&1)
log "BGSAVE response: ${BGSAVE_RESULT}"

# ── 2. Wait for BGSAVE to complete ────────────────────────────

MAX_WAIT=120  # seconds
WAITED=0

while [ "$WAITED" -lt "$MAX_WAIT" ]; do
    LAST_SAVE_AFTER=$(redis-cli -h "$HOST" -p "$PORT" LASTSAVE 2>/dev/null | tr -d '[:space:]')
    if [ "$LAST_SAVE_AFTER" != "$LAST_SAVE_BEFORE" ]; then
        log "BGSAVE completed (new timestamp: ${LAST_SAVE_AFTER})"
        break
    fi
    sleep 2
    WAITED=$((WAITED + 2))
done

if [ "$WAITED" -ge "$MAX_WAIT" ]; then
    log "WARNING: BGSAVE did not complete within ${MAX_WAIT}s, proceeding with existing RDB"
fi

# ── 3. Copy RDB from Docker volume ────────────────────────────

# Method: docker cp from the running container's /data/dump.rdb
# This works whether the volume is named or bind-mounted.

# Find the actual container name (docker compose may prefix it)
RUNNING_CONTAINER=$(docker ps --filter "ancestor=falkordb/falkordb:latest" --format '{{.Names}}' | head -1)

if [ -z "$RUNNING_CONTAINER" ]; then
    # Try compose service name pattern
    RUNNING_CONTAINER=$(docker ps --format '{{.Names}}' | grep -i falkordb | head -1)
fi

if [ -z "$RUNNING_CONTAINER" ]; then
    log "ERROR: No running FalkorDB container found"
    exit 1
fi

log "Copying RDB from container '${RUNNING_CONTAINER}'..."
docker cp "${RUNNING_CONTAINER}:/data/dump.rdb" "$BACKUP_FILE"

# Verify the backup file
BACKUP_SIZE=$(stat -f%z "$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_FILE" 2>/dev/null || echo "0")
if [ "$BACKUP_SIZE" -lt 100 ]; then
    log "ERROR: Backup file suspiciously small (${BACKUP_SIZE} bytes), aborting"
    rm -f "$BACKUP_FILE"
    exit 1
fi

log "Backup saved: ${BACKUP_FILE} (${BACKUP_SIZE} bytes)"

# Also keep a 'latest' symlink for easy restore
ln -sf "$BACKUP_FILE" "${BACKUP_DIR}/asgard-latest.rdb"

# ── 4. Prune old backups ──────────────────────────────────────

PRUNED=0
# Use find with -mtime for cross-platform compat
while IFS= read -r old_backup; do
    log "Pruning old backup: $(basename "$old_backup")"
    rm -f "$old_backup"
    PRUNED=$((PRUNED + 1))
done < <(find "$BACKUP_DIR" -name "asgard-*.rdb" -not -name "asgard-latest.rdb" -mtime +"$KEEP_DAYS" -type f 2>/dev/null)

# ── 5. Summary ─────────────────────────────────────────────────

TOTAL_BACKUPS=$(find "$BACKUP_DIR" -name "asgard-*.rdb" -not -name "asgard-latest.rdb" -type f 2>/dev/null | wc -l | tr -d ' ')
log "Done. ${TOTAL_BACKUPS} backup(s) on disk, ${PRUNED} pruned. Keeping last ${KEEP_DAYS} days."

# Print graph stats for the log
NODE_COUNT=$(redis-cli -h "$HOST" -p "$PORT" GRAPH.QUERY asgard "MATCH (n) RETURN count(n)" 2>/dev/null | head -3 | tail -1 || echo "?")
EDGE_COUNT=$(redis-cli -h "$HOST" -p "$PORT" GRAPH.QUERY asgard "MATCH ()-[r]->() RETURN count(r)" 2>/dev/null | head -3 | tail -1 || echo "?")
log "Graph state: ~${NODE_COUNT} nodes, ~${EDGE_COUNT} edges"
