// @node_id: protocol-telemetry-seed
// @label: "Telemetry Seed — SkipKeys and Invariants for protocol run-health"
// ============================================================================
// Seeds the graph with telemetry infrastructure for monitoring protocol
// execution. Every protocol that runs via run-with-telemetry wrapper gets
// telemetry properties written to it (run_count, error_count, last_run_*).
// These are high-churn properties that must NOT drift the Merkle root_hash.
// Invariants then check protocol health by inspecting these telemetry signals.
//
// Reference: graph/docs/proprioception-plan.md (phase 2 — telemetry layer).
// ============================================================================

// --- Phase 1: Register 9 Telemetry SkipKeys ----
// Each property must be registered so protocol telemetry updates don't
// cascade into the Merkle root_hash. The root stays stable while telemetry
// accumulates on load-bearing protocols.

MERGE (sk:SkipKey {node_id: 'skipkey-run_count'})
  SET sk.key = 'run_count',
      sk.category = 'protocol-telemetry',
      sk.reason = 'Execution count; excluded from Merkle to preserve stable root during protocol runs';

MERGE (sk:SkipKey {node_id: 'skipkey-error_count'})
  SET sk.key = 'error_count',
      sk.category = 'protocol-telemetry',
      sk.reason = 'Error tally; excluded from Merkle to allow error tracking without hash drift';

MERGE (sk:SkipKey {node_id: 'skipkey-last_run_started_at'})
  SET sk.key = 'last_run_started_at',
      sk.category = 'protocol-telemetry',
      sk.reason = 'ISO timestamp of last execution start; excluded from Merkle';

MERGE (sk:SkipKey {node_id: 'skipkey-last_run_started_ms'})
  SET sk.key = 'last_run_started_ms',
      sk.category = 'protocol-telemetry',
      sk.reason = 'Epoch ms of last execution start; excluded from Merkle for liveness checks';

MERGE (sk:SkipKey {node_id: 'skipkey-last_run_status'})
  SET sk.key = 'last_run_status',
      sk.category = 'protocol-telemetry',
      sk.reason = 'Status of last execution (ok, error, timeout); excluded from Merkle';

MERGE (sk:SkipKey {node_id: 'skipkey-last_run_at'})
  SET sk.key = 'last_run_at',
      sk.category = 'protocol-telemetry',
      sk.reason = 'ISO timestamp of last execution completion; excluded from Merkle';

MERGE (sk:SkipKey {node_id: 'skipkey-last_run_ms'})
  SET sk.key = 'last_run_ms',
      sk.category = 'protocol-telemetry',
      sk.reason = 'Duration in ms of last execution; excluded from Merkle for perf tracking';

MERGE (sk:SkipKey {node_id: 'skipkey-last_run_error'})
  SET sk.key = 'last_run_error',
      sk.category = 'protocol-telemetry',
      sk.reason = 'Error message from last failed execution; excluded from Merkle';

MERGE (sk:SkipKey {node_id: 'skipkey-last_run_stmts'})
  SET sk.key = 'last_run_stmts',
      sk.category = 'protocol-telemetry',
      sk.reason = 'Count of Cypher statements executed in last run; excluded from Merkle';

// --- Phase 2: Create 2 Invariants monitoring protocol health ----
// Both use check_cypher to evaluate telemetry and report health status.

// 1. Heartbeat Alive — critical protocol must run successfully and recently
MERGE (inv1:Invariant {node_id: 'invariant-heartbeat-alive'})
  SET inv1.label = 'Heartbeat Alive',
      inv1.description = 'protocol-heartbeat-core must have a successful recent run — last_run_status=ok within the last 60000 ms',
      inv1.check_cypher = 'MATCH (p:Protocol {node_id:"protocol-heartbeat-core"}) RETURN (p.last_run_status = "ok" AND p.last_run_started_ms IS NOT NULL AND (timestamp() - p.last_run_started_ms) < 60000) OR p.last_run_started_ms IS NULL = false AS healthy',
      inv1.severity = 'block',
      inv1.heal_protocol = '',
      inv1.question_template_id = 'why-is-heartbeat-dead';

// 2. No Protocol Chronically Failing — error rate must stay healthy across all protocols
MERGE (inv2:Invariant {node_id: 'invariant-no-protocol-chronically-failing'})
  SET inv2.label = 'No Protocol Chronically Failing',
      inv2.description = 'For any Protocol with run_count >= 10, the ratio error_count/run_count must stay below 0.2',
      inv2.check_cypher = 'MATCH (p:Protocol) WHERE p.run_count >= 10 WITH p, toFloat(coalesce(p.error_count,0))/toFloat(p.run_count) AS err_rate WITH coalesce(max(err_rate), 0.0) AS max_err RETURN max_err < 0.2 AS healthy',
      inv2.severity = 'warn',
      inv2.heal_protocol = '',
      inv2.question_template_id = 'why-do-protocols-fail';

// --- Final Summary Report ---

MATCH (sk:SkipKey) WHERE sk.node_id STARTS WITH 'skipkey-' AND sk.category = 'protocol-telemetry'
WITH collect(sk.node_id) AS skipkeys, count(sk) AS sk_count
MATCH (inv:Invariant) WHERE inv.node_id IN ['invariant-heartbeat-alive', 'invariant-no-protocol-chronically-failing']
WITH skipkeys, sk_count, collect(inv.node_id) AS invariants, count(inv) AS inv_count
RETURN
  sk_count AS skipkeys_created,
  skipkeys AS skipkey_node_ids,
  inv_count AS invariants_created,
  invariants AS invariant_node_ids,
  'telemetry-seed seeded' AS status;
