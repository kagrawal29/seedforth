// @node_id: protocol-heartbeat-core-v2
// @label: "Heartbeat Core v2 — health-gated, idempotent, dead-man's-switch"
// ============================================================================
// Proprioception Phase 4 (2026-04-18)
//
// The v1 heartbeat (protocol-heartbeat-core) fires on wall-clock and writes on
// every tick regardless of whether the host is healthy or whether anything
// actually changed. On 2026-04-17 that pattern produced 34 GB of dirty
// file-backed pages in ~18 hours on an 8 GB Mac and ended in a kernel panic.
//
// v2 does three things differently:
//
//   1. READS host-invariants BEFORE doing any work. If host-ram-pressure is
//      'critical' or GC pause has been > backpressure_gc_ms recently, this
//      tick is SKIPPED — not failed. Skips are counted on HeartbeatConfig
//      so the graph can see backpressure from outside.
//
//   2. READS min_gap_s from HeartbeatConfig. If the last successful beat was
//      less than min_gap_s seconds ago, this tick returns without writing
//      anything. Prevents duplicate work from a jittery scheduler.
//
//   3. WRITES only when something observable changed. Heartbeat_count is
//      incremented, but the Merkle-impacting work (decay, vital-signs
//      refresh, etc) runs only if the vital-signs-delta exceeds a threshold
//      OR the tick interval has lapsed. On an idle graph, ticks are near-
//      zero-cost — bounded property touches, no tx-log growth.
//
// DEAD-MAN'S-SWITCH
//   If host-ram-pressure has been 'critical' for N consecutive ticks
//   (default N = 3), v2 calls apoc.periodic.cancel('mycelium-heartbeat') and
//   sets Being.auto_stopped_at. The graph kills its own heart before the
//   host kills the process. The operator must restart manually after clearing
//   the pressure — there is NO auto-restart, by design (auto-restart under
//   pressure is exactly how the 2026-04-17 panic happened).
//
// INVOCATION
//   v2 is NOT scheduled yet. Until the orchestrator flips over, the scheduled
//   target remains protocol-heartbeat-core (v1). When v2 is activated, swap
//   heartbeat-scheduled.cypher's target_node_id from 'protocol-heartbeat-core'
//   to 'protocol-heartbeat-core-v2'. No other changes required — the wrapper
//   contract is identical.
//
// REFERENCES
//   projects/mycelium/docs/proprioception-plan.md  — Phase 4 design
//   graph/protocols/heartbeat-config.cypher         — tunables
//   graph/protocols/host-invariants-seed.cypher     — sensor layer (Phase 3)
//   graph/protocols/run-with-telemetry.cypher       — wrapper (Phase 2)
// ============================================================================

// --- Phase -1: Token pre-declaration for APOC executor auth -----------------
// Same pattern as heartbeat.cypher — pre-touch every property name we will
// SET so the null-user APOC periodic thread doesn't throw TOKEN_WRITE.
MERGE (anchor:_SchemaAnchor:SchemaAnchorHeartbeatV2 {node_id: 'schema-anchor-heartbeat-v2'})
  SET anchor.last_heartbeat = 0,
      anchor.last_heartbeat_at = '',
      anchor.heartbeat_count = 0,
      anchor.alive = true,
      anchor.auto_stopped_at = '',
      anchor.skip_count = 0,
      anchor.consecutive_critical_ticks = 0,
      anchor.last_tick_reason = '',
      anchor.v2_active = true;

// --- Phase 0: Read config + host vitals --------------------------------------
// Single combined read to minimize reads per tick. If any required node is
// missing, we default to conservative values and keep going.
MATCH (being:Being {node_id: 'being-mycelium'})
OPTIONAL MATCH (cfg:HeartbeatConfig {node_id: 'heartbeat-config'})
OPTIONAL MATCH (ram:HostInvariant {node_id: 'host-ram-pressure'})
OPTIONAL MATCH (gc:HostInvariant {node_id: 'host-gc-pause-max-ms-last-min'})
WITH being, cfg,
     coalesce(ram.value, 'normal') AS ram_pressure,
     coalesce(gc.value, 0.0) AS gc_pause_ms,
     coalesce(cfg.backpressure_ram_pressure, 'critical') AS bp_ram,
     coalesce(cfg.backpressure_gc_ms, 2000) AS bp_gc,
     coalesce(cfg.min_gap_s, 9) AS min_gap_s,
     coalesce(being.last_heartbeat, 0) AS last_hb_ms,
     coalesce(being.consecutive_critical_ticks, 0) AS consec_crit

// --- Phase 1: Dead-man's-switch check ---------------------------------------
// If we've been in critical pressure for 3+ ticks in a row, self-cancel.
// This statement only runs the cancel + set if the trigger condition is met.
CALL apoc.do.when(
  ram_pressure = bp_ram AND consec_crit >= 2,
  '
    CALL apoc.periodic.cancel("mycelium-heartbeat") YIELD name
    WITH name
    MATCH (b:Being {node_id: "being-mycelium"})
    SET b.auto_stopped_at = datetime(),
        b.last_tick_reason = "dead-mans-switch: 3 consecutive critical host-ram-pressure ticks"
    RETURN "stopped" AS action
  ',
  '
    RETURN "continue" AS action
  ',
  {}
) YIELD value AS switch_result
WITH being, cfg, ram_pressure, gc_pause_ms, bp_ram, bp_gc, min_gap_s, last_hb_ms, consec_crit, switch_result.action AS dms_action

// --- Phase 2: Backpressure skip -----------------------------------------------
// If host pressure exceeds thresholds, increment skip_count + consecutive, return.
// No work, no Merkle churn.
CALL apoc.do.when(
  dms_action = 'continue' AND (ram_pressure = bp_ram OR gc_pause_ms > bp_gc),
  '
    MATCH (b:Being {node_id: "being-mycelium"})
    SET b.consecutive_critical_ticks = $prev_consec + 1,
        b.last_tick_reason = "backpressure-skip: ram=" + $ram + " gc=" + toString($gc) + "ms"
    WITH b
    MATCH (c:HeartbeatConfig {node_id: "heartbeat-config"})
    SET c.skip_count = coalesce(c.skip_count, 0) + 1
    RETURN "skipped" AS action
  ',
  '
    RETURN "proceed" AS action
  ',
  {prev_consec: consec_crit, ram: ram_pressure, gc: gc_pause_ms}
) YIELD value AS skip_result
WITH being, cfg, ram_pressure, min_gap_s, last_hb_ms, skip_result.action AS bp_action
WHERE bp_action = 'proceed';

// --- Phase 3: Min-gap debounce ------------------------------------------------
// If we beat less than min_gap_s seconds ago, return without writing.
// This statement is its own tx — it either returns early or falls through.
MATCH (being:Being {node_id: 'being-mycelium'})
OPTIONAL MATCH (cfg:HeartbeatConfig {node_id: 'heartbeat-config'})
WITH being, coalesce(cfg.min_gap_s, 9) AS min_gap_s,
     coalesce(being.last_heartbeat, 0) AS last_hb_ms,
     timestamp() AS now_ms
WHERE (now_ms - last_hb_ms) >= min_gap_s * 1000

// --- Phase 4: Record the beat (the only unconditional write) -----------------
SET being.last_heartbeat = timestamp(),
    being.last_heartbeat_at = toString(datetime()),
    being.heartbeat_count = coalesce(being.heartbeat_count, 0) + 1,
    being.alive = true,
    being.consecutive_critical_ticks = 0,
    being.last_tick_reason = 'ok'
RETURN being.heartbeat_count AS count, being.last_heartbeat_at AS at;

// --- Phase 5: Defer the heavy maintenance --------------------------------
// v1's heartbeat ran decay + vital-signs refresh on every tick. v2 delegates
// that to a separate protocol (protocol-heartbeat-maintenance) that runs at
// a coarser cadence (every N beats, not every beat) — wired via an Invariant
// that fires it when Being.heartbeat_count % maintenance_every == 0.
//
// For now, v2 does NOT run decay inline — we split that out into
// heartbeat-maintenance (Phase 4b). On idle ticks, v2 writes only the 4
// properties in Phase 4. Those are all SkipKeys — zero Merkle churn.
// ============================================================================
