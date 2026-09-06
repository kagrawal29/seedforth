#!/usr/bin/env bash
#
# graph-restore.sh — Restore FalkorDB from an RDB backup
#
# Disaster recovery for the Asgard graph. Stops FalkorDB, replaces the
# RDB file inside the Docker volume, restarts the container.
#
# Usage:
#   ./scripts/graph-restore.sh                              # restore from latest
#   ./scripts/graph-restore.sh /var/backups/falkordb/asgard-2026-04-11_183000.rdb
#   ./scripts/graph-restore.sh --list                       # list available backups
#
# CAUTION: This will stop FalkorDB, replace its data, and restart it.
#          All data written since the backup will be lost.
#
# Environment:
#   BACKUP_DIR      — default: /var/backups/falkordb (or ./backups/falkordb locally)
#   COMPOSE_FILE    — default: docker/docker-compose.production.yml

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

COMPOSE_FILE="${COMPOSE_FILE:-${REPO_ROOT}/docker/docker-compose.production.yml}"

# Backup directory
if [[ -d /var/backups/falkordb ]]; then
    BACKUP_DIR="${BACKUP_DIR:-/var/backups/falkordb}"
else
    BACKUP_DIR="${BACKUP_DIR:-${REPO_ROOT}/backups/falkordb}"
fi

log() { echo "[graph-restore] $(date -u +%H:%M:%S) $*"; }
warn() { echo "[graph-restore] WARNING: $*" >&2; }
die() { echo "[graph-restore] FATAL: $*" >&2; exit 1; }

# ── List mode ──────────────────────────────────────────────────

if [[ "${1:-}" == "--list" ]]; then
    echo "Available backups in ${BACKUP_DIR}:"
    echo ""
    if [[ -d "$BACKUP_DIR" ]]; then
        ls -lht "$BACKUP_DIR"/asgard-*.rdb 2>/dev/null | grep -v latest || echo "  (none found)"
    else
        echo "  Backup directory does not exist: ${BACKUP_DIR}"
    fi
    exit 0
fi

# ── Determine which backup to restore ─────────────────────────

if [[ -n "${1:-}" ]]; then
    RESTORE_FILE="$1"
else
    RESTORE_FILE="${BACKUP_DIR}/asgard-latest.rdb"
fi

if [[ ! -f "$RESTORE_FILE" ]]; then
    die "Backup file not found: ${RESTORE_FILE}"
fi

# Resolve symlinks
RESTORE_FILE="$(readlink -f "$RESTORE_FILE" 2>/dev/null || realpath "$RESTORE_FILE" 2>/dev/null || echo "$RESTORE_FILE")"

RESTORE_SIZE=$(stat -f%z "$RESTORE_FILE" 2>/dev/null || stat -c%s "$RESTORE_FILE" 2>/dev/null || echo "0")
log "Restoring from: ${RESTORE_FILE} (${RESTORE_SIZE} bytes)"

if [[ "$RESTORE_SIZE" -lt 100 ]]; then
    die "Backup file is suspiciously small (${RESTORE_SIZE} bytes). Aborting."
fi

# ── Safety confirmation ────────────────────────────────────────

echo ""
echo "=========================================="
echo "  ASGARD GRAPH RESTORE"
echo "=========================================="
echo ""
echo "  Backup file : $(basename "$RESTORE_FILE")"
echo "  Size        : ${RESTORE_SIZE} bytes"
echo "  Compose file: ${COMPOSE_FILE}"
echo ""
echo "  This will:"
echo "    1. Stop the FalkorDB container"
echo "    2. Replace /data/dump.rdb with the backup"
echo "    3. Restart FalkorDB"
echo ""
echo "  ALL DATA WRITTEN SINCE THIS BACKUP WILL BE LOST."
echo ""

# Allow non-interactive mode with --yes flag
if [[ "${2:-}" != "--yes" ]]; then
    read -rp "  Type 'restore' to proceed: " CONFIRM
    if [[ "$CONFIRM" != "restore" ]]; then
        log "Aborted by user."
        exit 0
    fi
fi

echo ""

# ── Find the running container ─────────────────────────────────

RUNNING_CONTAINER=$(docker ps --filter "ancestor=falkordb/falkordb:latest" --format '{{.Names}}' | head -1)
if [ -z "$RUNNING_CONTAINER" ]; then
    RUNNING_CONTAINER=$(docker ps --format '{{.Names}}' | grep -i falkordb | head -1)
fi

if [ -z "$RUNNING_CONTAINER" ]; then
    die "No running FalkorDB container found. Start it first, or restore manually."
fi

log "Found container: ${RUNNING_CONTAINER}"

# ── 1. Create a pre-restore backup (safety net) ───────────────

PRE_RESTORE="${BACKUP_DIR}/asgard-pre-restore-$(date -u +%Y-%m-%d_%H%M%S).rdb"
log "Creating pre-restore safety backup: $(basename "$PRE_RESTORE")"
docker cp "${RUNNING_CONTAINER}:/data/dump.rdb" "$PRE_RESTORE" 2>/dev/null || warn "Could not create pre-restore backup (container may not have dump.rdb)"

# ── 2. Stop FalkorDB ──────────────────────────────────────────

log "Stopping FalkorDB container..."
docker stop "$RUNNING_CONTAINER"

# ── 3. Replace the RDB file ───────────────────────────────────

# We need to copy into the stopped container's volume.
# docker cp works on stopped containers too.
log "Copying backup RDB into container volume..."
docker cp "$RESTORE_FILE" "${RUNNING_CONTAINER}:/data/dump.rdb"

# ── 4. Restart FalkorDB ───────────────────────────────────────

log "Starting FalkorDB container..."
docker start "$RUNNING_CONTAINER"

# Wait for Redis to come up
log "Waiting for FalkorDB to become ready..."
MAX_WAIT=60
WAITED=0
while [ "$WAITED" -lt "$MAX_WAIT" ]; do
    if docker exec "$RUNNING_CONTAINER" redis-cli ping 2>/dev/null | grep -q PONG; then
        break
    fi
    sleep 2
    WAITED=$((WAITED + 2))
done

if [ "$WAITED" -ge "$MAX_WAIT" ]; then
    die "FalkorDB did not come up within ${MAX_WAIT}s after restore. Check container logs."
fi

log "FalkorDB is up."

# ── 5. Verify the restored graph ──────────────────────────────

NODE_COUNT=$(docker exec "$RUNNING_CONTAINER" redis-cli GRAPH.QUERY asgard "MATCH (n) RETURN count(n)" 2>/dev/null | head -3 | tail -1 || echo "?")
EDGE_COUNT=$(docker exec "$RUNNING_CONTAINER" redis-cli GRAPH.QUERY asgard "MATCH ()-[r]->() RETURN count(r)" 2>/dev/null | head -3 | tail -1 || echo "?")

echo ""
echo "=========================================="
echo "  RESTORE COMPLETE"
echo "=========================================="
echo ""
echo "  Graph stats : ~${NODE_COUNT} nodes, ~${EDGE_COUNT} edges"
echo "  Pre-restore : $(basename "$PRE_RESTORE")"
echo "  Restored    : $(basename "$RESTORE_FILE")"
echo ""
echo "  If the graph looks wrong, restore the pre-restore backup:"
echo "    $0 ${PRE_RESTORE} --yes"
echo ""
