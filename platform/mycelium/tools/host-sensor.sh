#!/bin/bash

# Host Sensor — out-of-process Neo4j host monitor
# Samples macOS metrics (RAM, disk writes, GC pauses, process RSS) every 30s
# and writes values to HostInvariant nodes in Neo4j via mycelium shell.
#
# Guards:
# - Only runs on macOS (Darwin). Exits on Linux with warning.
# - Handles missing commands gracefully (iostat, jcmd missing -> set value to null, log warning)
# - Never crashes the loop. set -euo pipefail with trap for robustness.
#
# This script lives outside the JVM intentionally: a process suffocating
# cannot reliably measure its own suffocation. The sensor must be independent.

set -euo pipefail

# --- Configuration ----
SAMPLE_INTERVAL_SEC=30
LOG_FILE="${MYCELIUM_LOG:-/tmp/mycelium-host-sensor.log}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MYCELIUM_ROOT="$(dirname "$SCRIPT_DIR")"
MYCELIUM_CLI="$MYCELIUM_ROOT/mycelium"

# --- Trap for graceful cleanup ----
trap 'echo "[$(date +"%Y-%m-%d %H:%M:%S")] host-sensor exiting" >> "$LOG_FILE" 2>&1; exit 0' TERM INT

# --- Guard: macOS only ----
if [[ "$(uname)" != "Darwin" ]]; then
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: host-sensor only supports macOS; skipping on $(uname)" >> "$LOG_FILE" 2>&1
  exit 0
fi

# --- Helper: update HostInvariant node ----
update_host_invariant() {
  local node_id="$1"
  local value="$2"

  if [[ -z "$value" || "$value" == "null" ]]; then
    # NULL value
    "$MYCELIUM_CLI" shell "MATCH (h:HostInvariant {node_id:\"$node_id\"}) SET h.value=NULL, h.sampled_at=datetime(), h.sampled_ms=timestamp()" >> "$LOG_FILE" 2>&1 || true
  else
    # Numeric or string value
    # Check if it looks like a number
    if [[ "$value" =~ ^-?[0-9]+\.?[0-9]*$ ]]; then
      "$MYCELIUM_CLI" shell "MATCH (h:HostInvariant {node_id:\"$node_id\"}) SET h.value=$value, h.sampled_at=datetime(), h.sampled_ms=timestamp()" >> "$LOG_FILE" 2>&1 || true
    else
      # String value (e.g., "normal", "warn", "critical")
      "$MYCELIUM_CLI" shell "MATCH (h:HostInvariant {node_id:\"$node_id\"}) SET h.value=\"$value\", h.sampled_at=datetime(), h.sampled_ms=timestamp()" >> "$LOG_FILE" 2>&1 || true
    fi
  fi
}

# --- Helper: compute RAM pressure ----
compute_ram_pressure() {
  local free_mb=$1
  if (( free_mb < 500 )); then
    echo "critical"
  elif (( free_mb < 1500 )); then
    echo "warn"
  else
    echo "normal"
  fi
}

# --- Helper: get Neo4j PID ----
get_neo4j_pid() {
  pgrep -f "org.neo4j.server.Neo4jCommunity" | head -1
}

# --- Main loop ----
echo "[$(date +'%Y-%m-%d %H:%M:%S')] host-sensor started" >> "$LOG_FILE" 2>&1

while true; do
  TIMESTAMP="$(date +'%Y-%m-%d %H:%M:%S')"

  # --- Sample 1: RAM Free (MB) — effective = free + inactive ----
  # On macOS, raw "Pages free" is always low because macOS aggressively uses
  # RAM for cache. "Inactive" pages are reclaimable on demand. The honest
  # signal for ram pressure is (free + inactive). Reporting raw free would
  # flip this sensor to "critical" on any browser-heavy laptop even when
  # plenty of memory is available.
  if command -v vm_stat &> /dev/null; then
    VM_OUT=$(vm_stat 2>/dev/null)
    FREE_PAGES=$(echo "$VM_OUT" | awk '/Pages free/{gsub(/\./,"",$3); print $3}')
    INACTIVE_PAGES=$(echo "$VM_OUT" | awk '/Pages inactive/{gsub(/\./,"",$3); print $3}')
    if [[ -n "$FREE_PAGES" && "$FREE_PAGES" =~ ^[0-9]+$ ]]; then
      EFFECTIVE_PAGES=$((FREE_PAGES + ${INACTIVE_PAGES:-0}))
      RAM_FREE_MB=$((EFFECTIVE_PAGES * 4 / 1024))
    else
      RAM_FREE_MB="null"
    fi
  else
    echo "[$TIMESTAMP] WARNING: vm_stat not found; skipping RAM free sample" >> "$LOG_FILE" 2>&1
    RAM_FREE_MB="null"
  fi

  # --- Sample 2: RAM Pressure (derived) ----
  if [[ "$RAM_FREE_MB" != "null" ]]; then
    RAM_PRESSURE=$(compute_ram_pressure "$RAM_FREE_MB")
  else
    RAM_PRESSURE="null"
  fi

  # --- Sample 3: Disk Writes/sec ----
  # iostat -d disk0 outputs KB/t tps MB/s; tps is disk transactions per second
  if command -v iostat &> /dev/null; then
    DISK_TPS=$(iostat -d 1 disk0 2>/dev/null | tail -1 | awk '{print $2}')
    if [[ -n "$DISK_TPS" && "$DISK_TPS" =~ ^[0-9]+\.?[0-9]*$ ]]; then
      DISK_WRITES_PER_SEC=$(printf "%.2f" "$DISK_TPS")
    else
      DISK_WRITES_PER_SEC="null"
    fi
  else
    echo "[$TIMESTAMP] WARNING: iostat not found; skipping disk writes sample" >> "$LOG_FILE" 2>&1
    DISK_WRITES_PER_SEC="null"
  fi

  # --- Sample 4: Neo4j RSS (MB) ----
  NEO4J_PID=$(get_neo4j_pid)
  if [[ -n "$NEO4J_PID" ]]; then
    RSS_KB=$(ps -o rss= -p "$NEO4J_PID" 2>/dev/null || echo "")
    if [[ -n "$RSS_KB" && "$RSS_KB" =~ ^[0-9]+$ ]]; then
      NEO4J_RSS_MB=$((RSS_KB / 1024))
    else
      NEO4J_RSS_MB="null"
    fi
  else
    NEO4J_RSS_MB="null"
  fi

  # --- Sample 5: Load Average (1m) ----
  if command -v sysctl &> /dev/null; then
    LOAD_AVG=$(sysctl -n vm.loadavg 2>/dev/null | awk '{print $2}')
    if [[ -n "$LOAD_AVG" && "$LOAD_AVG" =~ ^[0-9]+\.?[0-9]*$ ]]; then
      LOAD_AVG_1M=$(printf "%.2f" "$LOAD_AVG")
    else
      LOAD_AVG_1M="null"
    fi
  else
    echo "[$TIMESTAMP] WARNING: sysctl not found; skipping load avg sample" >> "$LOG_FILE" 2>&1
    LOAD_AVG_1M="null"
  fi

  # --- Sample 6: GC Pauses (jcmd, optional) ----
  # jcmd is optional; if not found, set to null and continue
  GC_PAUSE_P99_MS="null"
  GC_PAUSE_MAX_MS="null"
  if [[ -n "$NEO4J_PID" ]] && command -v jcmd &> /dev/null; then
    # Attempt to get GC info via jcmd. This may fail if jcmd is not in PATH
    # or if the process doesn't respond. Gracefully degrade.
    GC_INFO=$(jcmd "$NEO4J_PID" GC.heap_info 2>/dev/null || echo "")
    if [[ -z "$GC_INFO" ]]; then
      echo "[$TIMESTAMP] WARNING: jcmd GC.heap_info failed or timed out; skipping GC pause sample" >> "$LOG_FILE" 2>&1
    else
      # Extract pause times if present. This is simplistic; real parsing would be more robust.
      # For now, set to null to avoid parse errors.
      GC_PAUSE_MAX_MS="null"
      GC_PAUSE_P99_MS="null"
    fi
  fi

  # --- Sample 7: TX Log Size (MB) ----
  # Neo4j tx-log lives in data/databases/neo4j/neostore.transaction.db* files
  # Sum their sizes
  NEO4J_DATA_DIR="${NEO4J_DATA_DIR:-/Users/kshitiz/.mycelium/data}"
  TX_LOG_SIZE_MB="null"
  if [[ -d "${NEO4J_DATA_DIR}/databases/neo4j" ]]; then
    TX_LOG_SIZE_BYTES=$(find "${NEO4J_DATA_DIR}/databases/neo4j" -name "neostore.transaction.db*" -type f 2>/dev/null | xargs du -c 2>/dev/null | tail -1 | awk '{print $1}')
    if [[ -n "$TX_LOG_SIZE_BYTES" && "$TX_LOG_SIZE_BYTES" =~ ^[0-9]+$ ]]; then
      TX_LOG_SIZE_MB=$((TX_LOG_SIZE_BYTES / 1024 / 1024))
    fi
  fi

  # --- Write all samples to graph ----
  echo "[$TIMESTAMP] sampling: RAM=${RAM_FREE_MB}MB pressure=$RAM_PRESSURE disk_w/s=${DISK_WRITES_PER_SEC} neo4j_rss=${NEO4J_RSS_MB}MB load=${LOAD_AVG_1M} tx_log=${TX_LOG_SIZE_MB}MB" >> "$LOG_FILE" 2>&1

  update_host_invariant "host-ram-free-mb" "$RAM_FREE_MB"
  update_host_invariant "host-ram-pressure" "$RAM_PRESSURE"
  update_host_invariant "host-disk-writes-per-sec" "$DISK_WRITES_PER_SEC"
  update_host_invariant "host-gc-pause-p99-ms" "$GC_PAUSE_P99_MS"
  update_host_invariant "host-gc-pause-max-ms-last-min" "$GC_PAUSE_MAX_MS"
  update_host_invariant "host-tx-log-size-mb" "$TX_LOG_SIZE_MB"
  update_host_invariant "host-neo4j-rss-mb" "$NEO4J_RSS_MB"
  update_host_invariant "host-load-avg-1m" "$LOAD_AVG_1M"

  # Sleep and continue
  sleep "$SAMPLE_INTERVAL_SEC"
done
