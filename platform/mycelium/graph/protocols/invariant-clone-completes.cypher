// @node_id: seed-invariant-clone-completes
// @label: "Clone Completes — detect stalled clone operations"
// ============================================================================
// Seeds the graph with one :Invariant that enforces timely completion of
// CloneRun nodes. If a CloneRun has status='intent' for >10 minutes, the
// invariant marks the system unhealthy. This catches hung clone operations
// (e.g., dump failed, load hung, runner crashed).
//
// No heal_protocol is assigned. The immune cycle will surface an
// :ActionProposal for human review.
//
// Performance target: <50ms for 100 CloneRun nodes.
//   - One indexed lookup (status = 'intent')
//   - Timestamp comparison (no full-graph scan)
// ============================================================================

MERGE (inv:Invariant {node_id: 'invariant-clone-completes'})
  SET inv.label              = 'Clone Completes',
      inv.description        = "Any CloneRun with status='intent' for >10 minutes signals a stalled operation and makes the system unhealthy.",
      inv.severity           = 'medium',
      inv.category           = 'operations',
      inv.heal_protocol_id   = null,
      inv.heal_protocol      = null,

      // --- check_cypher ---------------------------------------------------
      // Returns exactly one row: { healthy: bool, stalled_clones: [node_id], reason: string }
      //
      // Logic:
      //   1. Find all CloneRun nodes with status='intent'.
      //   2. Check if any have been in intent state for >10 minutes (600000 ms).
      //   3. If any are stalled → unhealthy; else healthy.
      // -------------------------------------------------------------------
      inv.check_cypher       =
        'MATCH (cr:CloneRun {status: "intent"}) ' +
        'WITH collect(cr) AS intent_clones ' +
        'OPTIONAL MATCH (stalled) IN intent_clones ' +
        'WHERE (timestamp() - coalesce(stalled.requested_at, stalled.created_at, 0)) > 600000 ' +
        'WITH collect(stalled.node_id) AS stalled_ids ' +
        'RETURN ' +
        '  size(stalled_ids) = 0 AS healthy, ' +
        '  stalled_ids AS stalled_clones, ' +
        '  CASE ' +
        '    WHEN size(stalled_ids) = 0 ' +
        '      THEN "all active CloneRuns completed within 10 minutes" ' +
        '    ELSE "CloneRun(s) stalled in intent state: " + toString(size(stalled_ids)) ' +
        '  END AS reason',

      inv.created_at         = datetime();

// --- Wire to monitoring infrastructure ------------------------------------
// Best-effort: if rhythm/purpose/ontology/being nodes don't exist yet,
// the MATCH simply returns no rows and the SET is silently skipped.

OPTIONAL MATCH (heartbeat:Rhythm   {node_id: 'rhythm-heartbeat'})
OPTIONAL MATCH (heal:Purpose       {node_id: 'purpose-self-heal'})
OPTIONAL MATCH (ont:Ontology)
OPTIONAL MATCH (being:Being        {node_id: 'being-mycelium'})
WITH heartbeat, heal, ont, being
MATCH (inv:Invariant {node_id: 'invariant-clone-completes'})
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

MATCH (inv:Invariant {node_id: 'invariant-clone-completes'})
RETURN
  inv.node_id       AS invariant_node_id,
  inv.label         AS label,
  inv.severity      AS severity,
  inv.category      AS category,
  inv.heal_protocol AS heal_protocol,
  'seed-invariant-clone-completes loaded' AS status;
