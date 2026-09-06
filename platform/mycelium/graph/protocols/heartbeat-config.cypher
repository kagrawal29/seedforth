// @node_id: protocol-heartbeat-config
// @label: "Heartbeat Config — tunables read by heartbeat-core at the start of every tick"
// ============================================================================
// Proprioception Phase 4 prep (2026-04-18)
//
// A single Protocol node holding heartbeat's knobs as properties. The Phase 4
// rewrite of protocol-heartbeat-core reads these at the start of every tick
// and applies backpressure accordingly.
//
// Why a Protocol and not a Config label: protocols already have a well-trodden
// lifecycle in this graph (MERGE by node_id, bootstrap-loadable from file,
// editable through the same pipeline). Adding a new label for one row is not
// worth the ceremony. The Protocol's `.cypher` body is this file itself —
// harmless if ever executed (just MERGEs its own config node, idempotent).
//
// Reference: projects/mycelium/docs/proprioception-plan.md Phase 4.
// ============================================================================

// --- Register SkipKeys so config tuning does not drift the Merkle root ------
MERGE (sk:SkipKey {node_id: 'skipkey-hb-interval_s'})
  SET sk.key = 'interval_s',
      sk.category = 'heartbeat-config',
      sk.reason = 'Heartbeat interval knob; operator-tunable, excluded from Merkle';

MERGE (sk:SkipKey {node_id: 'skipkey-hb-min_gap_s'})
  SET sk.key = 'min_gap_s',
      sk.category = 'heartbeat-config',
      sk.reason = 'Minimum spacing between heartbeat ticks; excluded from Merkle';

MERGE (sk:SkipKey {node_id: 'skipkey-hb-backpressure_ram'})
  SET sk.key = 'backpressure_ram_pressure',
      sk.category = 'heartbeat-config',
      sk.reason = 'RAM pressure level above which heartbeat skips ticks; excluded from Merkle';

MERGE (sk:SkipKey {node_id: 'skipkey-hb-backpressure_gc_ms'})
  SET sk.key = 'backpressure_gc_ms',
      sk.category = 'heartbeat-config',
      sk.reason = 'GC pause ms ceiling above which heartbeat skips; excluded from Merkle';

MERGE (sk:SkipKey {node_id: 'skipkey-hb-budget_ms'})
  SET sk.key = 'budget_ms',
      sk.category = 'heartbeat-config',
      sk.reason = 'Heartbeat-core self-imposed time budget per tick; excluded from Merkle';

MERGE (sk:SkipKey {node_id: 'skipkey-hb-skip_count'})
  SET sk.key = 'skip_count',
      sk.category = 'heartbeat-config',
      sk.reason = 'Monotonic count of backpressure-induced skipped ticks; excluded from Merkle';

// --- Seed the config node ----------------------------------------------------
// Tuned for an 8 GB Mac dev host (see 2026-04-17 kernel panic post-mortem).
// On a server these should be raised.
MERGE (cfg:HeartbeatConfig:GraphNode {node_id: 'heartbeat-config'})
  ON CREATE SET
    cfg.label = 'Heartbeat Config',
    cfg.interval_s = 10,
    cfg.min_gap_s = 9,
    cfg.backpressure_ram_pressure = 'critical',
    cfg.backpressure_gc_ms = 2000,
    cfg.budget_ms = 2000,
    cfg.skip_count = 0,
    cfg.created_at = datetime(),
    cfg.description = 'Heartbeat tunables. heartbeat-core reads these at the start of every tick.';

// Do NOT reset skip_count or override values on subsequent runs — this file
// seeds defaults but does not stomp operator edits.
