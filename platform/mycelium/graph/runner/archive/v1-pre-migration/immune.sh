#!/usr/bin/env bash
# ============================================================================
# Runner: immune
# ============================================================================
# Executes graph/protocols/immune.cypher to run the auto-heal loop, then
# processes any file_path-based heals that cypher couldn't run inline.
#
# Flow:
#   1. Run immune.cypher. For each enabled Invariant with a heal_protocol:
#      a. Check it via apoc.cypher.run
#      b. If unhealthy + cooldown passed:
#         - If heal_protocol has inline cypher: run it inline
#         - If heal_protocol has file_path: mark heal_requested=true
#   2. After immune.cypher completes, look up every Invariant with
#      heal_requested=true, find the linked Protocol's file_path, pipe
#      the file through cypher-shell.
#   3. Re-run the invariant's check and record the new state.
#
# This is the "immune system" — the graph detects unhealthy conditions and
# autonomously repairs them on its own cadence. Typical cadence: same as
# heartbeat-loop (every 1-2s is overkill; 30s-5min is sensible for most
# invariants). Runs on-demand too.
#
# Env vars:
#   NEO4J_CONTAINER   default: mycelium-neo4j-local
#   NEO4J_USER        default: neo4j
#   NEO4J_PASS        default: localtest12
# ============================================================================
set -euo pipefail

CONTAINER="${NEO4J_CONTAINER:-mycelium-neo4j-local}"
USER="${NEO4J_USER:-neo4j}"
PASS="${NEO4J_PASS:-localtest12}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMMUNE_PROTOCOL="$SCRIPT_DIR/../protocols/immune.cypher"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cypher_exec() {
  docker exec -i "$CONTAINER" cypher-shell \
    -u "$USER" -p "$PASS" --encryption false --format plain "$@"
}

echo "[immune] running immune.cypher..."
docker exec -i "$CONTAINER" cypher-shell \
  -u "$USER" -p "$PASS" --encryption false --format plain \
  < "$IMMUNE_PROTOCOL" | tail -15

# --- Phase 2: file-path based heals -----------------------------------------
# For every Invariant that the cypher pass marked heal_requested=true,
# find the linked Protocol's file_path and execute it here.

pending=$(cypher_exec <<'CYPHER' | tail -n +2
MATCH (i:Invariant {heal_requested: true})
MATCH (p:Protocol {node_id: i.heal_protocol})
WHERE p.file_path IS NOT NULL
RETURN i.node_id + '@@@' + p.file_path + '@@@' + coalesce(i.heal_params, '{}') AS row
CYPHER
)

if [ -z "$pending" ]; then
  echo "[immune] no file-based heals pending"
  exit 0
fi

echo "[immune] processing file-based heals..."
while IFS= read -r raw; do
  [ -z "$raw" ] && continue
  line="${raw#\"}"
  line="${line%\"}"
  # Split into 3 fields via awk: invariant_id @@@ file_path @@@ heal_params
  tabbed=$(printf '%s' "$line" | awk '{
    n = split($0, parts, "@@@");
    for (i = 1; i <= n; i++) printf "%s%s", parts[i], (i < n ? "\t" : "")
  }')
  IFS=$'\t' read -r invariant_id protocol_file heal_params <<< "$tabbed"
  [ -z "$heal_params" ] && heal_params="{}"
  if [ ! -f "$protocol_file" ]; then
    echo "[immune] WARN: heal protocol file missing: $protocol_file (for $invariant_id)"
    cypher_exec "MATCH (i:Invariant {node_id: '$invariant_id'}) SET i.heal_requested = false, i.last_heal_status = 'file-missing' RETURN i.node_id" > /dev/null
    continue
  fi
  echo "[immune]   heal $invariant_id via $protocol_file (params=$heal_params)"
  heal_ok=0
  case "$protocol_file" in
    *.sh)
      # Shell runner — execute directly with env vars
      if bash "$protocol_file" > /tmp/heal.out 2>&1; then heal_ok=1; fi
      ;;
    *.cypher|*)
      # Cypher file — pipe through cypher-shell with params
      if docker exec -i "$CONTAINER" cypher-shell \
            -u "$USER" -p "$PASS" --encryption false --format plain \
            -P "$heal_params" \
            < "$protocol_file" > /tmp/heal.out 2>&1; then heal_ok=1; fi
      ;;
  esac
  if [ "$heal_ok" = "1" ]; then
    cypher_exec "MATCH (i:Invariant {node_id: '$invariant_id'}) SET i.heal_requested = false, i.last_heal_status = 'file-heal-completed' RETURN i.node_id" > /dev/null
    echo "[immune]     done"
  else
    cypher_exec "MATCH (i:Invariant {node_id: '$invariant_id'}) SET i.heal_requested = false, i.last_heal_status = 'file-heal-failed' RETURN i.node_id" > /dev/null
    echo "[immune]     FAILED:"
    tail -10 /tmp/heal.out | sed 's/^/       /'
  fi
done <<< "$pending"

echo "[immune] complete"
