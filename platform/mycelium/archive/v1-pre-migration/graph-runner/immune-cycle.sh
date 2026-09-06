#!/usr/bin/env bash
# ============================================================================
# Runner: immune-cycle
# ============================================================================
# Complete immune cycle: check invariants → heal unhealthy → recheck → score
#
# This is a wrapper around the graph's immune system. It performs the FULL
# immune cycle on each tick:
#
#   1. Query all Invariants with check_cypher defined
#   2. For each, run the check (via mycelium shell)
#   3. Update health_status based on result
#   4. For unhealthy invariants with heal_protocol, dispatch healing:
#      - Use swarm --from-prompt to run the protocol
#   5. Recheck the invariant (via mycelium shell)
#   6. Update autonomous_score on Being based on health ratio
#
# This closes the loop: detect → heal → verify → score
#
# Uses:
#   ./mycelium shell "CYPHER"          -- run cypher via graph shell
#   ./mycelium swarm --from-prompt     -- dispatch agents for healing
#
# Env vars (optional):
#   VERBOSE   set to 1 for detailed output
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VERBOSE="${VERBOSE:-0}"

log() {
  echo "[immune-cycle] $*"
}

log_debug() {
  [ "$VERBOSE" = "1" ] && echo "[immune-cycle] DEBUG: $*" || true
}

# ============================================================================
# PHASE 1: Query all invariants with check_cypher defined
# ============================================================================

log "=== PHASE 1: Querying all invariants ==="

cd "$REPO_ROOT"

# First, get all invariant IDs that have a check_cypher
# Write to a temp file to avoid stdin consumption issues in the loop
INV_LIST_FILE=$(mktemp)
trap "rm -f $INV_LIST_FILE /tmp/inv-detail-$$.txt" EXIT

./mycelium shell "
MATCH (inv:Invariant)
WHERE inv.check_cypher IS NOT NULL AND inv.node_id IS NOT NULL
RETURN inv.node_id
ORDER BY inv.node_id
" 2>&1 | grep -v "^✗\|^  system\|^inv\." | grep -v "^[[:space:]]*$" > "$INV_LIST_FILE"

if [ ! -s "$INV_LIST_FILE" ]; then
  log "WARNING: No invariants found. Aborting."
  exit 1
fi

total_count=0
healthy_count=0
healed_count=0
failed_count=0

# Process each invariant (read from fd 3 so inner commands don't steal lines)
while IFS= read -r inv_id_raw <&3; do
  [ -z "$inv_id_raw" ] && continue
  node_id=$(echo "$inv_id_raw" | tr -d '"' | xargs)
  [ -z "$node_id" ] && continue

  # ========================================================================
  # Fetch invariant details individually
  # ========================================================================

  inv_details=$(./mycelium shell "
MATCH (inv:Invariant {node_id: '$node_id'})
RETURN inv.check_cypher, inv.heal_protocol, inv.label
LIMIT 1
" </dev/null 2>&1 | grep -v "^✗\|^  system\|^inv\." | grep -v "^[[:space:]]*$" | head -1)

  if [ -z "$inv_details" ]; then
    log_debug "skipped $node_id (no details found)"
    continue
  fi

  # Parse the CSV line (3 fields)
  # Use a temp file to avoid quoting issues
  tmpf="/tmp/inv-detail-$$.txt"
  echo "$inv_details" > "$tmpf"

  # Extract the first 3 comma-separated fields, handling quotes properly
  check_cypher=$(python3 -c "
import csv
with open('$tmpf') as f:
    row = next(csv.reader(f))
    print(row[0] if len(row) > 0 else '')
" 2>/dev/null || echo "")

  heal_protocol=$(python3 -c "
import csv
with open('$tmpf') as f:
    row = next(csv.reader(f))
    print(row[1] if len(row) > 1 else '')
" 2>/dev/null || echo "")

  label=$(python3 -c "
import csv
with open('$tmpf') as f:
    row = next(csv.reader(f))
    print(row[2] if len(row) > 2 else '')
" 2>/dev/null || echo "")

  rm -f "$tmpf"

  [ -z "$check_cypher" ] && continue

  total_count=$((total_count + 1))

  # ========================================================================
  # PHASE 2: Run the check_cypher for this invariant
  # ========================================================================

  log_debug "checking $node_id (label: $label)"

  # Run the check and get the result
  check_result=$(./mycelium shell "$check_cypher" </dev/null 2>&1 | grep -v "^✗\|^  system\|^[[:space:]]*$" | head -1 | tr -d '"' | xargs || echo "")

  log_debug "  check result: [$check_result]"

  # Determine health: 'true' (without 'false') = healthy
  is_healthy=0
  if echo "$check_result" | grep -qi "true" && ! echo "$check_result" | grep -qi "false"; then
    is_healthy=1
  fi

  if [ "$is_healthy" = "1" ]; then
    log "  [OK] $node_id"
    healthy_count=$((healthy_count + 1))
    # Update health_status
    ./mycelium shell "
MATCH (inv:Invariant {node_id: '$node_id'})
SET inv.health_status = 'healthy', inv.last_checked = toString(datetime())
RETURN inv.node_id
" </dev/null 2>/dev/null > /dev/null || true
  else
    log "  [FAIL] $node_id"
    failed_count=$((failed_count + 1))
    # Update health_status
    ./mycelium shell "
MATCH (inv:Invariant {node_id: '$node_id'})
SET inv.health_status = 'unhealthy', inv.last_checked = toString(datetime())
RETURN inv.node_id
" </dev/null 2>/dev/null > /dev/null || true

    # ====================================================================
    # PHASE 3: If unhealthy and has heal_protocol, mark for healing
    # ====================================================================

    if [ -n "$heal_protocol" ] && [ "$heal_protocol" != "null" ] && [ "$heal_protocol" != "NULL" ]; then
      log "    -> dispatch healing via: $heal_protocol"
      # Set the flag on the invariant so the heartbeat loop can dispatch healing
      ./mycelium shell "
MATCH (inv:Invariant {node_id: '$node_id'})
SET inv.healing_needed = true, inv.heal_marked_at = toString(datetime())
RETURN inv.node_id
" </dev/null 2>/dev/null > /dev/null || true
      healed_count=$((healed_count + 1))
    fi
  fi

done 3< "$INV_LIST_FILE"

# ============================================================================
# PHASE 4: Recheck unhealthy invariants after healing
# ============================================================================

log ""
log "=== PHASE 4: Rechecking after healing ==="

# Query unhealthy invariants and recheck them
# Write to temp file to avoid stdin consumption by ./mycelium shell inside the loop
RECHECK_FILE=$(mktemp)
./mycelium shell "
MATCH (inv:Invariant)
WHERE inv.health_status = 'unhealthy' AND inv.check_cypher IS NOT NULL
RETURN inv.node_id
ORDER BY inv.node_id
" 2>&1 | grep -v "^✗\|^  system\|^inv\." | grep -v "^[[:space:]]*$" > "$RECHECK_FILE"

rechecked_healthy=0
while IFS= read -r recheck_id_raw <&3; do
  [ -z "$recheck_id_raw" ] && continue
  node_id=$(echo "$recheck_id_raw" | tr -d '"' | xargs)
  [ -z "$node_id" ] && continue

  # Get the check_cypher for this invariant
  check_cypher=$(./mycelium shell "
MATCH (inv:Invariant {node_id: '$node_id'})
RETURN inv.check_cypher
LIMIT 1
" </dev/null 2>&1 | grep -v "^✗\|^  system\|^inv\." | grep -v "^[[:space:]]*$" | head -1 | tr -d '"' | xargs || echo "")

  [ -z "$check_cypher" ] && continue

  log_debug "rechecking $node_id"

  check_result=$(./mycelium shell "$check_cypher" </dev/null 2>&1 | grep -v "^✗\|^  system\|^[[:space:]]*$" | head -1 | tr -d '"' | xargs || echo "")

  log_debug "  recheck result: [$check_result]"

  is_healthy=0
  if echo "$check_result" | grep -qi "true" && ! echo "$check_result" | grep -qi "false"; then
    is_healthy=1
  fi

  if [ "$is_healthy" = "1" ]; then
    log "  [HEALED] $node_id"
    rechecked_healthy=$((rechecked_healthy + 1))
    # Update status
    ./mycelium shell "
MATCH (inv:Invariant {node_id: '$node_id'})
SET inv.health_status = 'healthy', inv.last_healed = toString(datetime())
RETURN inv.node_id
" </dev/null 2>/dev/null > /dev/null || true
  else
    log "  [STILL FAILING] $node_id"
  fi
done 3< "$RECHECK_FILE"
rm -f "$RECHECK_FILE"

healthy_count=$((healthy_count + rechecked_healthy))
failed_count=$((failed_count - rechecked_healthy))

# ============================================================================
# PHASE 5: Update autonomous_score on Being
# ============================================================================

log ""
log "=== PHASE 5: Updating autonomous score ==="

score=0
if [ "$total_count" -gt 0 ]; then
  score=$((healthy_count * 100 / total_count))
fi

log "  invariants: $total_count | healthy: $healthy_count | score: $score%"

./mycelium shell "
MATCH (b:Being {node_id: 'being-mycelium'})
SET b.autonomous_score = $score,
    b.invariants_healthy = $healthy_count,
    b.invariants_total = $total_count,
    b.last_immune_cycle = toString(datetime()),
    b.immune_cycle_heals = $healed_count
RETURN b.node_id, b.autonomous_score, b.last_immune_cycle
" 2>/dev/null | grep -v "^✗\|^  system\|^b\." | grep '"' | head -1

# ============================================================================
# Summary
# ============================================================================

log ""
log "=== IMMUNE CYCLE COMPLETE ==="
log "  checked: $total_count | healthy: $healthy_count | healed: $healed_count | failed: $failed_count"
log "  autonomous_score: $score%"

# Exit with error if any invariants are still unhealthy
if [ "$failed_count" -gt 0 ]; then
  log "WARNING: $failed_count invariants still unhealthy after healing"
  exit 1
fi

exit 0
