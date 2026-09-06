// @node_id: invariant-query-traces-retained-90d
// @label: "QueryTrace 90-Day Retention"
// ============================================================================
// Invariant: Ensures :QueryTrace nodes older than 90 days are pruned.
//
// Healthy when:
//   - No :QueryTrace nodes exist with ts < datetime() - duration('P90D')
//
// Unhealthy when:
//   - One or more :QueryTrace nodes have ts older than 90 days
//
// This invariant is ENFORCED_BY the :Protocol 'prune-old-query-traces' which
// runs nightly via apoc.periodic.repeat. The invariant check runs during each
// heartbeat cycle; the protocol itself handles the actual pruning.
//
// Purpose:
//   - Analytics retention: keep only recent, actionable trace data
//   - Disk usage: prevent unbounded graph growth from trace accumulation
//   - Privacy: enforce automatic PII decay per data policy
//
// Severity: warning (not critical; graph is still queryable if old traces linger)
// ============================================================================

MERGE (inv:Invariant {node_id: 'invariant-query-traces-retained-90d'})
  SET inv.label              = 'QueryTrace 90-Day Retention',
      inv.description        = 'All :QueryTrace nodes must have ts >= datetime() - duration("P90D"). Nightly prune protocol enforces this.',
      inv.severity           = 'warning',
      inv.category           = 'data-lifecycle',
      inv.heal_protocol_id   = 'protocol-prune-old-query-traces',
      inv.heal_protocol      = 'prune-old-query-traces',

      // --- check_cypher ---------------------------------------------------
      // Returns { healthy: bool, stale_count: int, oldest_age_days: float, reason: string }
      //
      // Logic:
      //   1. Query for :QueryTrace nodes with ts < 90 days ago
      //   2. Count them and find the oldest one
      //   3. If count = 0 → healthy
      //   4. If count > 0 → unhealthy, emit age in days
      // -------------------------------------------------------------------
      // Outer delimiter = double quotes so internal cypher literals can use
      // single quotes without mixed-quote ambiguity. Fixes #44: Neo4j 2026.03.1
      // parser rejected the mixed form at bootstrap with
      // "The query must contain an even number of non-escaped quotes".
      inv.check_cypher       =
        "MATCH (q:QueryTrace) " +
        "WITH q, datetime() - duration('P90D') AS cutoff " +
        "WITH collect(q) AS all_q, cutoff, " +
        "     [q IN collect(q) WHERE q.ts < cutoff] AS old_q " +
        "WITH all_q, cutoff, old_q, " +
        "     CASE WHEN size(old_q) > 0 " +
        "       THEN min([q IN old_q | duration.inDays(q.ts, datetime()).days]) " +
        "       ELSE 0 " +
        "     END AS oldest_age_days " +
        "RETURN " +
        "  size(old_q) = 0 AS healthy, " +
        "  size(old_q) AS stale_count, " +
        "  oldest_age_days AS oldest_age_days, " +
        "  CASE " +
        "    WHEN size(old_q) = 0 THEN 'All traces are within 90-day window' " +
        "    ELSE 'Found ' + toString(size(old_q)) + ' traces older than 90d; oldest: ' + toString(round(oldest_age_days, 1)) + ' days old' " +
        "  END AS reason",

      inv.created_at         = datetime();

// --- Wire to monitoring infrastructure ------------------------------------
// Best-effort: if essential nodes don't exist yet, the relationships are skipped.

OPTIONAL MATCH (heartbeat:Rhythm   {node_id: 'rhythm-heartbeat'})
OPTIONAL MATCH (heal:Purpose       {node_id: 'purpose-self-heal'})
OPTIONAL MATCH (ont:Ontology)
WITH heartbeat, heal, ont
MATCH (inv:Invariant {node_id: 'invariant-query-traces-retained-90d'})
FOREACH (_ IN CASE WHEN heartbeat IS NOT NULL THEN [1] ELSE [] END |
  MERGE (inv)-[:MONITORED_BY]->(heartbeat)
)
FOREACH (_ IN CASE WHEN heal IS NOT NULL THEN [1] ELSE [] END |
  MERGE (inv)-[:EMBODIES]->(heal)
)
FOREACH (_ IN CASE WHEN ont IS NOT NULL THEN [1] ELSE [] END |
  MERGE (inv)-[:INVARIANT_OF]->(ont)
);

// --- Summary report -------------------------------------------------------

MATCH (inv:Invariant {node_id: 'invariant-query-traces-retained-90d'})
RETURN
  inv.node_id       AS invariant_node_id,
  inv.label         AS label,
  inv.severity      AS severity,
  inv.category      AS category,
  inv.heal_protocol AS heal_protocol,
  'querytrace-retention invariant loaded (wi-qt-04)' AS status;
