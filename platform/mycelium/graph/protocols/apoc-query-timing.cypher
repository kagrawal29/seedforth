// @node_id: protocol-apoc-query-timing
// @label: "APOC Query Timing Wrapper (v2-02)"
// ============================================================================
// Protocol: Capture duration_ms on every apoc.cypher.* invocation
// Part of wi-v2-02-atom-timing — precursor to atom chain decomposition
// ============================================================================
// APOC procedures (apoc.cypher.run, apoc.cypher.runMany, apoc.cypher.doIt)
// execute Cypher dynamically but don't expose execution timing in their
// result sets. This protocol wraps those calls to capture:
//
//   - duration_ms: wall-clock time from call start to return
//   - fired_at: ISO timestamp when the invocation completed
//   - protocol_id: node_id of the Protocol that fired this
//
// Timing is stored on a QueryTrace node created post-execution, linked to
// the calling Protocol via :FIRES edge.
//
// DESIGN NOTE:
// This wrapper exists in the graph as a reference implementation. Real
// instrumentation happens in three places:
//
//   1. Heartbeat (heartbeat.cypher phases 9, 12, 14) — directly wraps calls
//   2. Immune cycle (immune-cycle.cypher) — same pattern
//   3. Future: atom-run.sh will use this pattern when chains execute
//
// The wrapper itself is not called per-invocation. Instead, each caller
// applies the same pattern: capture system time before + after, persist
// to QueryTrace.
//
// Parameters:
//   protocol_id          string — node_id of the Protocol firing this
//   cypher_to_run        string — the cypher text to execute
//   params               map    — parameters to pass to apoc.cypher.run
//   label_for_trace      string — how to label this in the trace (optional)
// ============================================================================

// NOT EXECUTABLE DIRECTLY — this is a reference + documentation only.
// See heartbeat.cypher phases 9, 12, 14 for actual usage.

// ============================================================================
// EXAMPLE: How heartbeat phase 9 uses this pattern
// ============================================================================
//
// MATCH (b:Being {node_id: 'being-mycelium'})
// WITH b WHERE b.heartbeat_count % 100 = 0
// MATCH (hm:HealthMetric) WHERE hm.check_cypher IS NOT NULL
//
// // CAPTURE START TIME
// WITH hm, timestamp() AS start_ms
//
// // EXECUTE the APOC call (this is where duration happens)
// CALL apoc.cypher.run(hm.check_cypher, {}) YIELD value AS row
// WITH hm, row, start_ms, timestamp() AS end_ms, (timestamp() - start_ms) AS duration_ms
//
// // UPDATE the HealthMetric
// SET hm.current_value = row.value,
//     hm.last_evaluated_at = toString(datetime()),
//     hm.current_status = CASE
//       WHEN row.value >= coalesce(hm.healthy_min, -999999) AND row.value <= coalesce(hm.healthy_max, 999999) THEN 'healthy'
//       WHEN row.value < coalesce(hm.healthy_min, -999999) THEN 'low'
//       ELSE 'high'
//     END,
//     hm.last_duration_ms = duration_ms   // <-- PERSIST TIMING
//
// // CREATE QueryTrace with timing information
// CREATE (qt:QueryTrace {
//   node_id: 'qt-' + toString(timestamp()) + '-' + apoc.text.random(6, 'a-z0-9'),
//   protocol_id: 'protocol-heartbeat-core',
//   phase: 'health-metric-eval',
//   duration_ms: duration_ms,
//   fired_at: toString(datetime()),
//   invoked_epoch_ms: timestamp(),
//   metric_node_id: hm.node_id,
//   cypher_summary: 'HealthMetric.check_cypher evaluation',
//   file_type: 'query-trace'
// })
// MERGE (qt)-[:FIRED_BY]->(p:Protocol {node_id: 'protocol-heartbeat-core'})
//
// ============================================================================
// NEW: IndexDecl for QueryTrace filtering by protocol_id + fired_at
// ============================================================================
// These are declared in indexes.cypher for enforcer to create:

MERGE (d:IndexDecl {node_id: 'idx-querytrace-protocol_id'})
  ON CREATE SET
    d.label       = 'QueryTrace',
    d.property    = 'protocol_id',
    d.kind        = 'RANGE',
    d.created_by  = 'apoc-query-timing.cypher',
    d.reason      = 'Protocol timing queries; trace all fires from a specific protocol',
    d.created_at  = toString(datetime())
  ON MATCH SET
    d.updated_at  = toString(datetime());

MERGE (d:IndexDecl {node_id: 'idx-querytrace-fired_at'})
  ON CREATE SET
    d.label       = 'QueryTrace',
    d.property    = 'fired_at',
    d.kind        = 'RANGE',
    d.created_by  = 'apoc-query-timing.cypher',
    d.reason      = 'Time-window queries on QueryTrace; aggregate duration over periods',
    d.created_at  = toString(datetime())
  ON MATCH SET
    d.updated_at  = toString(datetime());

MERGE (d:IndexDecl {node_id: 'idx-querytrace-duration_ms'})
  ON CREATE SET
    d.label       = 'QueryTrace',
    d.property    = 'duration_ms',
    d.kind        = 'RANGE',
    d.created_by  = 'apoc-query-timing.cypher',
    d.reason      = 'Query performance analysis; find slow queries by duration threshold',
    d.created_at  = toString(datetime())
  ON MATCH SET
    d.updated_at  = toString(datetime());

RETURN 'QueryTrace timing indexes declared' AS status;
