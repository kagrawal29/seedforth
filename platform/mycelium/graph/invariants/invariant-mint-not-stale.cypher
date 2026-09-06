// @node_id: invariant-mint-not-stale
// @label: "Mint Not Stale — Detects Long-Uncleared Dirty Flag"
// ============================================================================
// Invariant: Monitors the mutation dirty flag to ensure it doesn't linger
// for >10 minutes without being cleared by a successful mint (or other clear event).
//
// Healthy when:
//   - DirtyState does not exist (no pending mutations), OR
//   - DirtyState.dirty = false (cleared by mint or other process), OR
//   - DirtyState.dirty = true AND <10 min have elapsed since touched_at
//
// Unhealthy when:
//   - DirtyState.dirty = true AND >=10 minutes since touched_at
//
// This is a soft signal that something is blocking the mint cycle, not a
// hard failure. The immune cycle will propose an ActionProposal for investigation,
// not auto-fail the graph. Human review is needed to understand the blockage.
//
// No heal_protocol assigned — raises ActionProposal only.
// ============================================================================

MERGE (inv:Invariant {node_id: 'invariant-mint-not-stale'})
  SET inv.label              = 'Mint Not Stale',
      inv.description        = 'DirtyState flag should not persist >10 minutes without clearing. If stale, suggests mint cycle is blocked.',
      inv.severity           = 'warning',
      inv.category           = 'lifecycle',
      inv.heal_protocol_id   = null,
      inv.heal_protocol      = null,

      // --- check_cypher ---------------------------------------------------
      // Stored as a string property; executed by the immune cycle via
      // apoc.cypher.run(inv.check_cypher, {}) each heartbeat cycle.
      //
      // Returns exactly one row: { healthy: bool, stale_duration_sec: int, reason: string }
      //
      // Logic:
      //   1. Query DirtyState node
      //   2. If doesn't exist or dirty=false → healthy
      //   3. If dirty=true, calculate seconds elapsed since touched_at
      //   4. If elapsed >= 600 sec (10 min) → unhealthy, emit stale_duration_sec
      //   5. Else → healthy
      // -------------------------------------------------------------------
      inv.check_cypher       =
        'OPTIONAL MATCH (ds:DirtyState {node_id: "dirty-state-mint-trigger", dirty: true}) ' +
        'WITH ds, ' +
        '  CASE ' +
        '    WHEN ds IS NULL THEN -1 ' +
        '    WHEN ds.touched_at IS NULL THEN -1 ' +
        '    ELSE duration.inSeconds(ds.touched_at, datetime()).seconds ' +
        '  END AS elapsed_sec ' +
        'RETURN ' +
        '  (elapsed_sec < 0 OR elapsed_sec < 600) AS healthy, ' +
        '  CASE WHEN elapsed_sec < 0 THEN 0 ELSE elapsed_sec END AS stale_duration_sec, ' +
        '  CASE ' +
        '    WHEN elapsed_sec < 0 THEN "DirtyState not found or dirty=false" ' +
        '    WHEN elapsed_sec < 600 THEN "dirty flag age: " + toString(elapsed_sec) + " sec (< 10 min)" ' +
        '    ELSE "dirty flag stale for " + toString(elapsed_sec) + " sec (>= 10 min)" ' +
        '  END AS reason',

      inv.created_at         = datetime();

// --- Wire to monitoring infrastructure ------------------------------------
// Best-effort: if essential nodes don't exist yet, the relationships are skipped.

OPTIONAL MATCH (heartbeat:Rhythm   {node_id: 'rhythm-heartbeat'})
OPTIONAL MATCH (heal:Purpose       {node_id: 'purpose-self-heal'})
OPTIONAL MATCH (ont:Ontology)
OPTIONAL MATCH (being:Being        {node_id: 'being-mycelium'})
WITH heartbeat, heal, ont, being
MATCH (inv:Invariant {node_id: 'invariant-mint-not-stale'})
FOREACH (_ IN CASE WHEN heartbeat IS NOT NULL THEN [1] ELSE [] END |
  MERGE (inv)-[:MONITORED_BY]->(heartbeat)
)
FOREACH (_ IN CASE WHEN heal IS NOT NULL THEN [1] ELSE [] END |
  MERGE (inv)-[:EMBODIES]->(heal)
)
FOREACH (_ IN CASE WHEN ont IS NOT NULL THEN [1] ELSE [] END |
  MERGE (inv)-[:INVARIANT_OF]->(ont)
)
FOREACH (_ IN CASE WHEN being IS NOT NULL THEN [1] ELSE [] END |
  MERGE (inv)-[:MONITORS]->(being)
);

// --- Summary report -------------------------------------------------------

MATCH (inv:Invariant {node_id: 'invariant-mint-not-stale'})
RETURN
  inv.node_id       AS invariant_node_id,
  inv.label         AS label,
  inv.severity      AS severity,
  inv.category      AS category,
  'seed-invariant-mint-not-stale loaded' AS status;
