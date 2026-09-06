#!/usr/bin/env bash
# ============================================================================
# Runner: heartbeat-loop
# ============================================================================
# Reads the Protocol node `protocol-heartbeat` from Neo4j and executes its
# cypher on a fixed cadence. The graph is the source of truth for what gets
# run — this script is just the scheduler.
#
# Stops on Ctrl-C. Intended for development. For prod/staging, wrap in a
# systemd unit (deploy/mycelium-neo4j/mycelium-heartbeat@.service in
# tetrahedron).
#
# Env vars (optional):
#   NEO4J_CONTAINER    default: mycelium-neo4j-local
#   NEO4J_USER         default: neo4j
#   NEO4J_PASS         default: localtest12
#   CADENCE_SECONDS    default: 1
#   PROTOCOL_ID        default: protocol-heartbeat
# ============================================================================

set -euo pipefail

CONTAINER="${NEO4J_CONTAINER:-mycelium-neo4j-local}"
USER="${NEO4J_USER:-neo4j}"
PASS="${NEO4J_PASS:-localtest12}"
CADENCE="${CADENCE_SECONDS:-1}"
PROTOCOL_ID="${PROTOCOL_ID:-protocol-heartbeat}"

echo "[heartbeat] container=$CONTAINER protocol=$PROTOCOL_ID cadence=${CADENCE}s"

# Read the cypher from the SOURCE FILE, not the Protocol node's cypher property.
# The Protocol.cypher property is 254 chars (liveness only). The file has the
# full extended heartbeat with decay phases (137 lines). The file IS the source
# of truth — the Protocol node is a registry entry, not the content.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HEARTBEAT_FILE="$SCRIPT_DIR/../protocols/heartbeat.cypher"

if [ ! -f "$HEARTBEAT_FILE" ]; then
  echo "[heartbeat] ERROR: $HEARTBEAT_FILE not found" >&2
  exit 1
fi

cypher_text=$(cat "$HEARTBEAT_FILE")

trap 'echo; echo "[heartbeat] stopped"; exit 0' INT TERM

MYCELIUM_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

while true; do
  # --- BREATHE: run the heartbeat (sense + measure + decay + dream) ---------
  echo "$cypher_text" | docker exec -i "$CONTAINER" cypher-shell \
    -u "$USER" -p "$PASS" --encryption false --format plain \
    > /dev/null 2>&1 \
    || echo "[heartbeat] tick failed at $(date -u +%FT%TZ)" >&2

  # --- ACT: dispatch any protocols flagged by frustration-driven auto-heal --
  # The heartbeat's Phase 9b flags proven-safe protocols with heal_requested_at.
  # Here we actually FIRE them. This closes the loop: sense → feel → act.
  # Only dispatches protocols that are amortizing/amortized (proven safe).
  heal_targets=$(docker exec -i "$CONTAINER" cypher-shell \
    -u "$USER" -p "$PASS" --encryption false --format plain \
    "MATCH (p:Protocol) WHERE p.heal_requested_at IS NOT NULL AND p.heal_requested_at > timestamp() - 120000 AND p.amortization_status IN ['amortizing', 'amortized'] RETURN p.node_id" \
    2>/dev/null | tail -n +2)

  if [ -n "$heal_targets" ]; then
    while IFS= read -r target; do
      [ -z "$target" ] && continue
      target="${target#\"}"
      target="${target%\"}"
      # Check if atoms exist for this protocol
      atom_count=$(docker exec -i "$CONTAINER" cypher-shell \
        -u "$USER" -p "$PASS" --encryption false --format plain \
        "MATCH (a:CypherAtom {source_protocol: '$target'}) RETURN count(a)" \
        2>/dev/null | tail -1 | tr -d ' ')
      if [ "$atom_count" -gt 0 ] 2>/dev/null; then
        echo "[heartbeat] auto-heal: atom-run $target ($atom_count atoms)"
        bash "$SCRIPT_DIR/atom-run.sh" "$target" > /dev/null 2>&1 || true
      fi
      # Clear the flag so it doesn't re-fire next tick
      docker exec -i "$CONTAINER" cypher-shell \
        -u "$USER" -p "$PASS" --encryption false --format plain \
        "MATCH (p:Protocol {node_id: '$target'}) REMOVE p.heal_requested_at, p.heal_requested_by, p.heal_frustration_gap" \
        > /dev/null 2>&1 || true
    done <<< "$heal_targets"
  fi

  # --- EXPLORE: proactive gap discovery from dream insights -------------------
  # Every 1000 ticks (~17h), the heartbeat's dream phase produces DreamInsights.
  # Here we ACT on them: wire discovered bridges/leaps as real edges.
  # This is neuroplasticity — the graph rewires from its own dreams.
  # Then test if the rewiring improved anything (re-check the density claim).
  dream_bridges=$(docker exec -i "$CONTAINER" cypher-shell \
    -u "$USER" -p "$PASS" --encryption false --format plain \
    "MATCH (d:DreamInsight) WHERE d.type IN ['bridge', 'semantic-leap'] AND d.wired IS NULL AND d.dreamed_at > toString(datetime() - duration('PT24H')) RETURN d.node_id + '|' + coalesce(d.start_id, d.node_a) + '|' + coalesce(d.end_id, d.node_b) AS row LIMIT 5" \
    2>/dev/null | tail -n +2)

  if [ -n "$dream_bridges" ]; then
    while IFS= read -r row; do
      [ -z "$row" ] && continue
      row="${row#\"}"
      row="${row%\"}"
      IFS='|' read -r dream_id node_a node_b <<< "$row"
      [ -z "$node_a" ] || [ -z "$node_b" ] && continue
      # Wire the dream as a real edge (neuroplasticity)
      docker exec -i "$CONTAINER" cypher-shell \
        -u "$USER" -p "$PASS" --encryption false --format plain \
        "MATCH (a {node_id: '$node_a'}), (b {node_id: '$node_b'}) MERGE (a)-[r:DREAM_BRIDGE]->(b) ON CREATE SET r.dreamed_at = toString(datetime()), r.source_dream = '$dream_id', r.walk_count = 0 WITH r MATCH (d:DreamInsight {node_id: '$dream_id'}) SET d.wired = true, d.wired_at = toString(datetime())" \
        > /dev/null 2>&1 || true
      echo "[heartbeat] neuroplasticity: wired DREAM_BRIDGE $node_a → $node_b"
    done <<< "$dream_bridges"
  fi

  # --- Read heartbeat count for tier gating ------------------------------------
  hb_count=$(docker exec -i "$CONTAINER" cypher-shell \
    -u "$USER" -p "$PASS" --encryption false --format plain \
    "MATCH (b:Being) RETURN b.heartbeat_count" \
    2>/dev/null | tail -1 | tr -d ' "' || echo "0")

  # --- AUTO-ANSWER: close Questions whose heal protocol already fired ----------
  docker exec -i "$CONTAINER" cypher-shell \
    -u "$USER" -p "$PASS" --encryption false --format plain \
    "MATCH (q:Question {status: 'pending'})-[:HEALED_BY]->(p:Protocol) WHERE p.fire_count > 0 SET q.status = 'auto-answered', q.answered_at = toString(datetime()), q.answer = 'Auto-resolved: ' + p.node_id + ' fire_count=' + toString(p.fire_count)" \
    > /dev/null 2>&1 || true

  # --- EMBED-DIRTY: refresh stale embeddings every 1000 ticks -----------------
  if [ -n "$hb_count" ] 2>/dev/null && [ "$((hb_count % 1000))" = "0" ] 2>/dev/null; then
    if command -v python3 &>/dev/null && [ -f "$MYCELIUM_ROOT/graph/runner/embed-dirty.py" ]; then
      echo "[heartbeat] auto-embed: refreshing stale embeddings..."
      python3 "$MYCELIUM_ROOT/graph/runner/embed-dirty.py" > /dev/null 2>&1 || true
    fi
  fi

  # --- FIRST-FIRE: bootstrap dead protocols once every 1000 ticks -------------
  # Run each "dead" protocol once via atom-run so it becomes "un-amortized"
  # and eligible for future auto-dispatch. This seeds the amortization layer.
  if [ -n "$hb_count" ] 2>/dev/null && [ "$((hb_count % 1000))" = "0" ] 2>/dev/null; then
    dead_protos=$(docker exec -i "$CONTAINER" cypher-shell \
      -u "$USER" -p "$PASS" --encryption false --format plain \
      "MATCH (p:Protocol {amortization_status: 'dead'}) WHERE EXISTS { MATCH (a:CypherAtom {source_protocol: p.node_id}) } RETURN p.node_id LIMIT 3" \
      2>/dev/null | tail -n +2)
    if [ -n "$dead_protos" ]; then
      while IFS= read -r proto; do
        [ -z "$proto" ] && continue
        proto="${proto#\"}"
        proto="${proto%\"}"
        echo "[heartbeat] first-fire: atom-run $proto"
        bash "$SCRIPT_DIR/atom-run.sh" "$proto" > /dev/null 2>&1 || true
      done <<< "$dead_protos"
    fi
  fi

  # --- LEARN: check if recent heals + dream wiring actually improved things ---
  # Every 100 ticks, compare current SystemState to previous. If density or
  # health improved, the learning is working. If degraded, raise awareness.
  # This is the graph LEARNING from its own actions — not just acting.
  if [ -n "$hb_count" ] && [ "$((hb_count % 100))" = "0" ] 2>/dev/null; then
    # Record what we just did as an :Activation so THEN edges track the sequence
    docker exec -i "$CONTAINER" cypher-shell \
      -u "$USER" -p "$PASS" --encryption false --format plain \
      "CREATE (a:Activation {node_id: 'activation-heartbeat-' + toString(timestamp()), activated_at_ms: timestamp(), activated_at: toString(datetime()), actor: 'heartbeat-loop', command: 'autonomous-tick', kind: 'heartbeat-reflection', file_type: 'activation'})" \
      > /dev/null 2>&1 || true
  fi

  # --- Immune cycle: check invariants, heal, recheck, update score ----------
  # Every 10 ticks, run the full immune cycle. This is the circulatory system:
  # detect → heal → verify → score. The heartbeat pushes health through the
  # entire fractal hierarchy on every cycle.
  if [ -n "$hb_count" ] && [ "$((hb_count % 10))" = "0" ] 2>/dev/null; then
    if [ -x "$MYCELIUM_ROOT/graph/runner/immune-cycle.sh" ]; then
      echo "[heartbeat] running immune cycle (tick $hb_count)..."
      bash "$MYCELIUM_ROOT/graph/runner/immune-cycle.sh" 2>&1 | tail -5 || true
    fi
  fi

  sleep "$CADENCE"
done
