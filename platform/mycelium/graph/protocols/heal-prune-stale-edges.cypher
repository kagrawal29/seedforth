// @node_id: prune-stale-edges
// @label: "Heal: prune decayed INFERRED_SIMILAR edges below weight threshold"
// ============================================================================
// Heal protocol for invariant-vital-edge-stability.
// Deletes INFERRED_SIMILAR edges whose decayed weight has fallen below 0.1
// (same threshold as heartbeat Phase 2b, but re-runs on demand instead of
// waiting for the next %100 gated beat). Also refreshes Being.vital_edge_count
// so the invariant re-evaluates against a fresh baseline.
// Bounded to 2000 edges per call so a single heal never stalls the DB.
// Idempotent; safe to re-run.
// ============================================================================

MATCH ()-[r:INFERRED_SIMILAR]->()
WHERE coalesce(r.weight, 1.0) < 0.1
WITH r LIMIT 2000
DELETE r;

MATCH ()-[r]->()
WITH count(r) AS ec
MATCH (b:Being {node_id:"being-mycelium"})
SET b.vital_edge_count = ec,
    b.vital_measured_at = toString(datetime()),
    b.vital_measured_ms = timestamp();
