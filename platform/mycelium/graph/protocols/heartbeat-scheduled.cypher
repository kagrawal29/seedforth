// @node_id: protocol-heartbeat-scheduled
// @label: "Heartbeat Scheduled Wrapper — routes through telemetry"
// ============================================================================
// Stable wrapper invoked by APOC's periodic scheduler every N seconds.
// Routes execution through protocol-run-with-telemetry so the graph can
// perceive its own heartbeat's health: run_count, error_count, last_run_status,
// last_run_at, last_run_ms, and last_run_error land on the target Protocol node.
//
// The real work lives in protocol-heartbeat-core.cypher.
// Telemetry specification and checkpoint pattern:
//   projects/mycelium/docs/proprioception-plan.md
//
// If protocol-run-with-telemetry is not yet bootstrapped, this is a no-op.
// ============================================================================

MATCH (w:Protocol {node_id: 'protocol-run-with-telemetry'})
WHERE w.cypher IS NOT NULL AND size(w.cypher) > 0
CALL apoc.cypher.runMany(w.cypher, {target_node_id: 'protocol-heartbeat-core'}) YIELD result
RETURN count(result) AS heartbeat_statements_run;
