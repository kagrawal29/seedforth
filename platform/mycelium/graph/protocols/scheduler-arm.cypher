// @node_id: protocol-scheduler-arm
// @label: "Scheduler Arm — register all enabled SchedulerJob nodes with apoc.periodic.repeat"
// ============================================================================
// Graph-native autonomous loop registry.
//
// Each (:SchedulerJob {enabled:true}) node declares one periodic job:
//   job_name            string   unique APOC job name
//   target_protocol_id  string   Protocol.node_id whose .cypher will be fired
//   interval_seconds    integer  cadence (1 = near-continuous; 10 = heartbeat; 300 = slow)
//   description         string   human-readable purpose
//
// Arming cancels any existing same-named job, then re-registers it with a
// runMany-wrapped invocation that writes safely (apoc.cypher.run is READ-only
// per known gotcha #1; runMany permits multi-statement writes).
//
// Add a new autonomous loop by MERGEing a SchedulerJob node. No code change.
// ============================================================================

MATCH (j:SchedulerJob {enabled: true})
CALL apoc.periodic.cancel(j.job_name) YIELD name AS _cancelled
WITH j, _cancelled
CALL apoc.periodic.repeat(
  j.job_name,
  'MATCH (p:Protocol {node_id: "' + j.target_protocol_id + '"}) WHERE p.cypher IS NOT NULL CALL apoc.cypher.runMany(p.cypher, {}) YIELD result RETURN count(result) AS stmts',
  j.interval_seconds
) YIELD name
RETURN name AS armed_job, j.target_protocol_id AS target, j.interval_seconds AS every_s
ORDER BY j.interval_seconds;
