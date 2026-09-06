// @node_id: protocol-prune-old-query-traces
// @label: "Prune Old QueryTrace Nodes"
// ============================================================================
// Protocol: Nightly APOC-scheduled job that removes :QueryTrace nodes older
// than 90 days, keeping disk usage bounded and enforcing the
// 'query-traces-retained-90d' invariant.
//
// Execution:
//   - Scheduled via apoc.periodic.repeat('prune-old-query-traces', <cypher>, 86400)
//   - Runs daily (86400 seconds = 24 hours)
//   - Idempotent: safe to run multiple times; only touches nodes outside 90-day window
//   - Safety limit: ≤10,000 nodes per run (prevent huge deletes in single txn)
//
// Prune logic:
//   1. Find all :QueryTrace with ts < datetime() - duration('P90D')
//   2. Order by ts (oldest first)
//   3. Delete up to 10k nodes in this run (next run catches remaining)
//   4. Return counts for auditing
//
// Idempotency:
//   - Each invocation checks the cutoff timestamp fresh
//   - If no nodes match (all within 90d), RETURN early with count=0
//   - Re-running the same timestamp window → 0 rows matched → no deletions
//   - Safe to call via health checks, manual admin runs, or scheduled fire
//
// Related:
//   - Invariant: 'invariant-query-traces-retained-90d' (wi-qt-04)
//   - Schema: 'graph/schemas/querytrace.cypher' (wi-qt-01)
//
// Cost:
//   - Storage reclamation: ~100-500MB per month (depends on query volume)
//   - Execution time: ~200-500ms per run (10k delete + index updates)
// ============================================================================

MERGE (proto:Protocol {node_id: 'protocol-prune-old-query-traces'})
  SET proto.label             = 'Prune Old QueryTrace Nodes',
      proto.description       = 'Nightly scheduled deletion of :QueryTrace nodes older than 90 days.',
      proto.severity          = 'normal',
      proto.category          = 'maintenance',
      proto.enabled           = true,
      proto.schedule_type     = 'periodic',
      proto.schedule_cadence  = 'P1D',
      proto.schedule_seconds  = 86400,
      proto.budget_ms         = 5000,
      proto.last_run_status   = 'idle',

      // --- cypher property ---------------------------------------------------
      // Contains the full Cypher query executed by the periodic scheduler.
      // The scheduler wraps this in apoc.cypher.runMany() for safety.
      //
      // For idempotency:
      //   - Query computes cutoff fresh each invocation
      //   - If size(old_q) = 0, RETURN without writing anything
      //   - If size(old_q) > limit, delete only limit nodes per run
      //   - Next run catches the rest (eventually all removed)
      // -------------------------------------------------------------------
      proto.cypher            =
        'WITH datetime() - duration("P90D") AS cutoff, 10000 AS limit ' +
        'MATCH (q:QueryTrace) WHERE q.ts < cutoff ' +
        'WITH q ORDER BY q.ts ASC LIMIT limit ' +
        'WITH collect(q) AS to_delete, cutoff ' +
        'WITH to_delete, cutoff, size(to_delete) AS count_to_delete ' +
        'FOREACH (q IN to_delete | DETACH DELETE q) ' +
        'RETURN ' +
        '  count_to_delete AS deleted_count, ' +
        '  toString(cutoff) AS cutoff_timestamp, ' +
        '  CASE ' +
        '    WHEN count_to_delete = 0 THEN "No traces older than 90d" ' +
        '    WHEN count_to_delete < 10000 THEN "Cleaned " + toString(count_to_delete) + " stale traces" ' +
        '    ELSE "Cleaned 10000 traces; more may remain (next run will continue)" ' +
        '  END AS status_message',

      proto.created_at        = datetime(),
      proto.last_scheduled_at = null;

// --- Register with SchedulerJob for autonomous arming -------------------
// This SchedulerJob node tells the scheduler-arm protocol to register
// this protocol as an apoc.periodic.repeat job.

MERGE (job:SchedulerJob {node_id: 'scheduler-job-prune-old-query-traces'})
  SET job.label               = 'Prune QueryTrace Scheduler Job',
      job.enabled             = true,
      job.target_protocol_id  = 'protocol-prune-old-query-traces',
      job.job_name            = 'prune-old-query-traces',
      job.interval_seconds    = 86400,
      job.description         = 'Nightly prune of :QueryTrace nodes older than 90 days',
      job.created_at          = datetime();

// --- Wire to monitoring infrastructure ----------------------------------
// Best-effort: if essential nodes don't exist yet, the relationships are skipped.

OPTIONAL MATCH (heartbeat:Rhythm    {node_id: 'rhythm-heartbeat'})
OPTIONAL MATCH (ontology:Ontology)
WITH heartbeat, ontology
MATCH (proto:Protocol {node_id: 'protocol-prune-old-query-traces'})
MATCH (inv:Invariant {node_id: 'invariant-query-traces-retained-90d'})
FOREACH (_ IN CASE WHEN heartbeat IS NOT NULL THEN [1] ELSE [] END |
  MERGE (proto)-[:FIRES_FROM]->(heartbeat)
)
FOREACH (_ IN CASE WHEN ontology IS NOT NULL THEN [1] ELSE [] END |
  MERGE (proto)-[:PROTOCOL_OF]->(ontology)
)
// Wire the invariant → protocol relationship
MERGE (inv)-[:ENFORCED_BY]->(proto);

// --- Summary report -------------------------------------------------------

MATCH (proto:Protocol {node_id: 'protocol-prune-old-query-traces'})
MATCH (job:SchedulerJob {node_id: 'scheduler-job-prune-old-query-traces'})
RETURN
  proto.node_id           AS protocol_node_id,
  proto.label             AS label,
  proto.schedule_seconds  AS schedule_seconds,
  job.job_name            AS registered_job_name,
  proto.budget_ms         AS budget_ms,
  'querytrace-prune nightly protocol + scheduler job loaded (wi-qt-04)' AS status;
