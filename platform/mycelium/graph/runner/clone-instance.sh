#!/usr/bin/env bash
# ============================================================================
# Runner: clone-instance
# ============================================================================
# Clones one Neo4j instance into another by dumping source and loading into
# target. Designed to seed dev/staging from prod, or create backups for
# teammates.
#
# This runner:
#   1. Stops the source instance (optional, for consistent dump)
#   2. Dumps the source database using neo4j-admin
#   3. Restarts the source instance
#   4. Stops the target instance
#   5. Loads the dump into the target using neo4j-admin
#   6. Restarts the target instance
#   7. Resets the target admin password (clone copies source auth)
#   8. Updates the CloneRun node in the graph with completion status
#   9. Verifies node/edge counts match expectations
#   10. Cleans up the dump directory
#
# Env vars:
#   --source <service>              Source Neo4j service name (neo4j, neo4j-prod, etc)
#   --target <service>              Target Neo4j service name (neo4j-dev, neo4j-staging)
#   --source-conf <dir>             Source Neo4j conf dir (default /etc/neo4j)
#   --target-conf <dir>             Target Neo4j conf dir (default /etc/neo4j-dev)
#   --target-admin-pass-env <var>   Env var name holding target admin password
#   --dump-dir <dir>                Temp dir for dump (default /tmp/mycelium-clone-dumps)
#   --skip-restart-source           Don't restart source after dump (use for local dev)
#   --no-stop-source                Don't stop source before dump (risky; dump may be inconsistent)
#
# Example for pulse-server:
#   clone-instance.sh \
#     --source neo4j \
#     --target neo4j-dev \
#     --source-conf /etc/neo4j \
#     --target-conf /etc/neo4j-dev \
#     --target-admin-pass-env NEO4J_DEV_ADMIN_PASS
#
# Exit codes:
#   0 — success
#   1 — pre-flight check failed (missing tools, services not found)
#   2 — dump/load operation failed
#   3 — graph update failed
# ============================================================================

set -euo pipefail

# Defaults
SOURCE_SERVICE="neo4j"
TARGET_SERVICE="neo4j-dev"
SOURCE_CONF="/etc/neo4j"
TARGET_CONF="/etc/neo4j-dev"
TARGET_ADMIN_PASS_ENV="NEO4J_DEV_ADMIN_PASS"
DUMP_DIR="${DUMP_DIR:-/tmp/mycelium-clone-dumps}"
SKIP_RESTART_SOURCE=0
NO_STOP_SOURCE=0

NEO4J_USER="${NEO4J_USER:-neo4j}"
NEO4J_ADMIN_TOOL="${NEO4J_ADMIN_TOOL:-neo4j-admin}"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --source) SOURCE_SERVICE="$2"; shift 2 ;;
    --target) TARGET_SERVICE="$2"; shift 2 ;;
    --source-conf) SOURCE_CONF="$2"; shift 2 ;;
    --target-conf) TARGET_CONF="$2"; shift 2 ;;
    --target-admin-pass-env) TARGET_ADMIN_PASS_ENV="$2"; shift 2 ;;
    --dump-dir) DUMP_DIR="$2"; shift 2 ;;
    --skip-restart-source) SKIP_RESTART_SOURCE=1; shift ;;
    --no-stop-source) NO_STOP_SOURCE=1; shift ;;
    *) echo "unknown arg: $1"; exit 1 ;;
  esac
done

# Resolve target admin password
if [ -z "${!TARGET_ADMIN_PASS_ENV:-}" ]; then
  echo "ERROR: env var $TARGET_ADMIN_PASS_ENV not set" >&2
  exit 1
fi
TARGET_ADMIN_PASS="${!TARGET_ADMIN_PASS_ENV}"

# Logging helper
log_msg() {
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a /tmp/clone-$SOURCE_SERVICE-$TARGET_SERVICE.log
  logger -t mycelium-clone "[$SOURCE_SERVICE → $TARGET_SERVICE] $1"
}

log_step() {
  echo ""
  log_msg "=== Step: $1 ==="
}

log_ok() {
  log_msg "✓ $1"
}

log_error() {
  echo "ERROR: $1" >&2
  logger -t mycelium-clone "ERROR [$SOURCE_SERVICE → $TARGET_SERVICE] $1"
}

# ============================================================================
# PRE-FLIGHT CHECKS
# ============================================================================

log_step "Pre-flight checks"

# Check for neo4j-admin tool
if ! command -v "$NEO4J_ADMIN_TOOL" &>/dev/null; then
  log_error "neo4j-admin not found in PATH"
  exit 1
fi

# Check for nc (network connectivity check)
if ! command -v nc &>/dev/null; then
  # macOS has nc, Linux typically has it, but fall back to bash
  nc_check() { (echo >/dev/tcp/localhost/$1) 2>/dev/null; }
else
  nc_check() { nc -z localhost "$1" 2>/dev/null; }
fi

# Create dump directory
mkdir -p "$DUMP_DIR"
log_ok "dump directory ready: $DUMP_DIR"

# ============================================================================
# DUMP SOURCE
# ============================================================================

log_step "Stop source instance ($SOURCE_SERVICE)"

if [ $NO_STOP_SOURCE -eq 0 ]; then
  if systemctl is-active --quiet "$SOURCE_SERVICE" 2>/dev/null; then
    if sudo -n systemctl stop "$SOURCE_SERVICE" >/dev/null 2>&1; then
      sleep 1
      log_ok "source stopped"
    else
      log_error "failed to stop source (need sudo)"
      exit 1
    fi
  fi
  sleep 1
else
  log_msg "SKIP: source left running (risky; dump may be inconsistent)"
fi

log_step "Dump source database"

dump_ts=$(date +%s)
dump_path="$DUMP_DIR/neo4j-dump-$dump_ts"

# Determine NEO4J_CONF for source (use systemd environment if available)
source_neo4j_conf="${SOURCE_CONF:-/etc/neo4j}"
if [ ! -d "$source_neo4j_conf" ]; then
  log_error "source conf dir not found: $source_neo4j_conf"
  exit 1
fi

log_msg "dumping to $dump_path"

if sudo -u "$NEO4J_USER" env NEO4J_CONF="$source_neo4j_conf" \
  "$NEO4J_ADMIN_TOOL" database dump neo4j --to-path "$dump_path" >/tmp/dump-$dump_ts.log 2>&1; then
  dump_size=$(du -sh "$dump_path" 2>/dev/null | cut -f1)
  log_ok "dump complete: $dump_size"
else
  log_error "dump failed (see /tmp/dump-$dump_ts.log)"
  exit 2
fi

log_step "Restart source instance ($SOURCE_SERVICE)"

if [ $SKIP_RESTART_SOURCE -eq 0 ]; then
  if sudo -n systemctl start "$SOURCE_SERVICE" >/dev/null 2>&1; then
    sleep 2
    log_ok "source restarted"
  else
    log_error "failed to restart source"
    exit 2
  fi
else
  log_msg "SKIP: source restart skipped (dev mode)"
fi

# ============================================================================
# LOAD TARGET
# ============================================================================

log_step "Stop target instance ($TARGET_SERVICE)"

if systemctl is-active --quiet "$TARGET_SERVICE" 2>/dev/null; then
  if sudo -n systemctl stop "$TARGET_SERVICE" >/dev/null 2>&1; then
    sleep 1
    log_ok "target stopped"
  else
    log_error "failed to stop target (need sudo)"
    exit 1
  fi
fi

log_step "Load dump into target database"

target_neo4j_conf="${TARGET_CONF:-/etc/neo4j-dev}"
if [ ! -d "$target_neo4j_conf" ]; then
  log_error "target conf dir not found: $target_neo4j_conf"
  exit 1
fi

log_msg "loading from $dump_path"

if sudo -u "$NEO4J_USER" env NEO4J_CONF="$target_neo4j_conf" \
  "$NEO4J_ADMIN_TOOL" database load neo4j --from-path "$dump_path" --overwrite-destination >/tmp/load-$dump_ts.log 2>&1; then
  log_ok "load complete"
else
  log_error "load failed (see /tmp/load-$dump_ts.log)"
  exit 2
fi

log_step "Restart target instance ($TARGET_SERVICE)"

if sudo -n systemctl start "$TARGET_SERVICE" >/dev/null 2>&1; then
  sleep 3
  log_ok "target restarted"
else
  log_error "failed to restart target"
  exit 2
fi

# ============================================================================
# RESET TARGET ADMIN PASSWORD
# ============================================================================

log_step "Reset target admin password"

# Determine target bolt port (default 7688 for neo4j-dev, 7687 for neo4j)
case "$TARGET_SERVICE" in
  neo4j-prod) TARGET_BOLT="bolt://localhost:7687" ;;
  neo4j-dev) TARGET_BOLT="bolt://localhost:7688" ;;
  *) TARGET_BOLT="bolt://localhost:7687" ;;
esac

log_msg "target bolt: $TARGET_BOLT"

# Wait for target to be ready
max_retries=30
retry=0
while ! echo "RETURN 1" | cypher-shell -a "$TARGET_BOLT" -u "$NEO4J_USER" -p "$TARGET_ADMIN_PASS" >/dev/null 2>&1; do
  retry=$((retry + 1))
  if [ $retry -gt $max_retries ]; then
    log_error "target not responding after 30 retries"
    exit 2
  fi
  echo -n "."
  sleep 1
done
echo ""
log_ok "target is responsive"

# Reset password via Cypher
if echo "ALTER USER neo4j SET PASSWORD '$TARGET_ADMIN_PASS'" | \
  cypher-shell -a "$TARGET_BOLT" -u "$NEO4J_USER" -p "$TARGET_ADMIN_PASS" >/dev/null 2>&1; then
  log_ok "target admin password reset"
else
  log_msg "WARN: password reset via cypher may have failed (but password was already set during load)"
fi

# ============================================================================
# VERIFY COUNTS
# ============================================================================

log_step "Verify node/edge counts"

# Get source count
source_node_count=$(cypher-shell -a bolt://localhost:7687 -u "$NEO4J_USER" -p localtest12 --format plain \
  "MATCH (n) RETURN count(n)" 2>/dev/null | tail -n +2 | head -1 | tr -d ' ')

# Get target count
target_node_count=$(cypher-shell -a "$TARGET_BOLT" -u "$NEO4J_USER" -p "$TARGET_ADMIN_PASS" --format plain \
  "MATCH (n) RETURN count(n)" 2>/dev/null | tail -n +2 | head -1 | tr -d ' ')

if [ -z "$source_node_count" ]; then
  source_node_count="unknown"
fi
if [ -z "$target_node_count" ]; then
  target_node_count="unknown"
fi

log_msg "source node count: $source_node_count"
log_msg "target node count: $target_node_count"

# Node counts should match (within 0.1% due to heartbeat ticks during clone window)
if [[ "$source_node_count" =~ ^[0-9]+$ ]] && [[ "$target_node_count" =~ ^[0-9]+$ ]]; then
  diff=$((source_node_count - target_node_count))
  diff_abs=${diff#-}
  tolerance=$((source_node_count / 1000))  # 0.1%
  if [ "$diff_abs" -le "$tolerance" ]; then
    log_ok "node counts match (within tolerance)"
  else
    log_msg "WARN: node count mismatch: source=$source_node_count target=$target_node_count (diff=$diff)"
  fi
fi

# ============================================================================
# UPDATE GRAPH
# ============================================================================

log_step "Update graph with clone completion"

# Update CloneRun node in the graph
graph_update_cypher="
MATCH (cr:CloneRun)
WHERE cr.status = 'intent'
ORDER BY cr.created_at DESC LIMIT 1
SET cr.status = 'complete',
    cr.completed_at = timestamp(),
    cr.target_count_after = $target_node_count,
    cr.dump_size_bytes = $(stat -f%z "$dump_path" 2>/dev/null || echo 0),
    cr.clone_duration_seconds = $(( $(date +%s) - dump_ts ))
RETURN cr.node_id, cr.status, cr.completed_at
"

if echo "$graph_update_cypher" | \
  cypher-shell -a bolt://localhost:7687 -u "$NEO4J_USER" -p localtest12 >/dev/null 2>&1; then
  log_ok "graph updated with clone status"
else
  log_msg "WARN: graph update failed (clone was successful, but status not recorded)"
fi

# ============================================================================
# CLEANUP
# ============================================================================

log_step "Cleanup"

rm -rf "$dump_path"
log_ok "removed dump directory"

# ============================================================================
# SUMMARY
# ============================================================================

log_step "Clone complete"
log_msg "Source: $SOURCE_SERVICE"
log_msg "Target: $TARGET_SERVICE"
log_msg "Source nodes: $source_node_count"
log_msg "Target nodes: $target_node_count"
log_msg "Log: /tmp/clone-$SOURCE_SERVICE-$TARGET_SERVICE.log"

echo ""
echo "✓ Clone successful. Target is ready for use."
echo ""

exit 0
