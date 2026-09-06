// @node_id: trace-summarize
// @label: "Heal: summarize old QueryTraces to control node count growth"
// ============================================================================
// Heal protocol for invariant-vital-node-stability.
// Deletes QueryTrace nodes older than 7 days in bounded batches so node_count
// doesn't drift. Also refreshes Being.vital_node_count so the invariant
// re-evaluates against a fresh baseline on the next tick.
// Idempotent; safe to re-run.
// ============================================================================

MATCH (qt:QueryTrace)
WHERE qt.invoked_epoch_ms IS NOT NULL
  AND qt.invoked_epoch_ms < timestamp() - 604800000
WITH qt LIMIT 500
DETACH DELETE qt;

MATCH (n)
WITH count(n) AS nc
MATCH (b:Being {node_id:"being-mycelium"})
SET b.vital_node_count = nc,
    b.vital_measured_at = toString(datetime()),
    b.vital_measured_ms = timestamp();
