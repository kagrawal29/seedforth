// @node_id: protocol-run-with-telemetry
// @label: "Run-with-Telemetry — wraps any Protocol execution with liveness tracking"
// ============================================================================
// Proprioception Phase 2 (2026-04-17)
//
// The graph must be able to tell when its own protocols are failing. Before
// this wrapper existed, heartbeat-scheduled called `apoc.cypher.runMany`
// directly on heartbeat-core. When heartbeat-core threw (WITH-clause bug,
// TOKEN_WRITE auth error), the error lived only in Neo4j's java log —
// nowhere the graph could perceive. mycelium status reported autonomous_score
// = 86 while the heart was stopped for hours. See:
//   projects/mycelium/docs/proprioception-plan.md
//
// This wrapper makes every scheduled run leave a trace in the graph itself.
//
// INVOCATION
//   The caller is expected to execute this file's cypher via
//       CALL apoc.cypher.runMany(w.cypher, {target_node_id: '<protocol-id>'})
//   where `w` is the Protocol node whose cypher property holds THIS file.
//   The `target_node_id` param identifies the Protocol to actually run.
//
// TRANSACTION ISOLATION STRATEGY (Neo4j 5 + APOC)
//
//   Pattern: apoc.cypher.runMany with THREE semicolon-separated statements.
//
//   Each statement is executed in its own transaction by apoc.cypher.runMany
//   when invoked at the TOP LEVEL (via cypher-shell, driver, or periodic
//   scheduler in auto-commit mode). This guarantees:
//     - Stmt 1 (checkpoint) commits before Stmt 2 runs
//     - If Stmt 2 throws, Stmt 1's writes are permanent
//     - Next invocation detects stuck status retroactively
//
//   APOC Reference: apoc.cypher.runMany(statement STRING, params MAP)
//   Neo4j Behavior: Semicolon-separated statements each execute in their
//   own implicit transaction when runMany is called at top level.
//   See: projects/mycelium/docs/proprioception-plan.md Phase 2.
//
//   Why no try/catch?: Cypher has no try/catch. The stuck-at-running
//   pattern (detecting last_run_status = 'running' on next invocation)
//   is how we count failures without needing exception handling.
//
// PROPERTIES WRITTEN ONTO THE TARGET PROTOCOL
//   run_count                int      monotonic; incremented in stmt 1
//   error_count              int      monotonic; incremented when stmt 1
//                                     finds the prior run stuck at 'running'
//   last_run_started_at      dt       datetime at stmt 1
//   last_run_started_ms      int      epoch ms at stmt 1
//   last_run_status          string   'running' | 'ok'  (never 'error' here;
//                                     stuck-at-running IS the error signal)
//   last_run_at              dt       set in stmt 3; mirror of started_at
//   last_run_ms              int      elapsed ms, set in stmt 3
//   last_run_error           string   cleared in stmt 3; set by stmt 1 to
//                                     'previous run did not complete' when
//                                     a stuck status is detected
//   last_run_stmts           int      count of sub-statements executed
//
// ALL PROTOCOL TELEMETRY KEYS ARE REGISTERED AS SkipKey IN telemetry-seed.cypher
// so they do not drift the Merkle root.
// ============================================================================

// --- Statement 1: Checkpoint --------------------------------------------------
// Runs in its own transaction. Retroactively flags any stuck prior run.
MATCH (p:Protocol {node_id: $target_node_id})
WITH p,
     coalesce(p.last_run_status, 'never') AS prior_status,
     coalesce(p.error_count, 0) AS prior_errs,
     coalesce(p.run_count, 0) AS prior_runs
SET p.error_count = CASE WHEN prior_status = 'running'
                         THEN prior_errs + 1
                         ELSE prior_errs
                    END,
    p.last_run_error = CASE WHEN prior_status = 'running'
                            THEN 'previous run did not complete (stuck at running) — detected retroactively'
                            ELSE null
                       END,
    p.run_count = prior_runs + 1,
    p.last_run_started_at = datetime(),
    p.last_run_started_ms = timestamp(),
    p.last_run_status = 'running'
RETURN p.node_id AS target, p.run_count AS runs, p.error_count AS errs;

// --- Statement 2: Execute the target's cypher -------------------------------
// If the target's cypher throws, this statement's transaction rolls back.
// Statement 1's commit is already durable. Statement 3 never runs.
// The next invocation's statement 1 will observe `last_run_status = 'running'`
// and count this tick as an error.
MATCH (p:Protocol {node_id: $target_node_id})
WHERE p.cypher IS NOT NULL AND size(p.cypher) > 0
CALL apoc.cypher.runMany(p.cypher, {}) YIELD result
RETURN count(result) AS stmts_run;

// --- Statement 3: Mark success ----------------------------------------------
// Only reached if statement 2 returned without throwing.
MATCH (p:Protocol {node_id: $target_node_id})
WHERE p.last_run_status = 'running'
SET p.last_run_status = 'ok',
    p.last_run_at = p.last_run_started_at,
    p.last_run_ms = timestamp() - p.last_run_started_ms,
    p.last_run_error = null
RETURN p.node_id AS target, p.last_run_status AS status, p.last_run_ms AS ms;
