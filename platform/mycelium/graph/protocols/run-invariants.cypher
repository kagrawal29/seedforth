// @node_id: protocol-run-invariants
// @label: "Run Invariants"
// ============================================================================
// Protocol: Run Invariants
// ============================================================================
// Phase 1 of the mutation-gate system. Reads every Invariant node, executes
// its `check_cypher` property dynamically via apoc.cypher.run, and writes
// health state back onto the node.
//
// Properties touched on each Invariant:
//   health              'healthy' | 'unhealthy' | 'no_check' | 'error'
//   last_check          ISO 8601 timestamp string (always set by every run)
//   last_check_result   JSON string of the first row returned by check_cypher
//
// Interpretation heuristic for the first returned row:
//   - boolean value         -> use directly (true = healthy)
//   - integer/float value   -> > 0 = healthy, 0 = unhealthy
//   - string value          -> 'healthy'/'ok'/'pass' = healthy, else unhealthy
//   - null / no row         -> unhealthy
//   - exception in cypher   -> 'error' health, error captured in result
//
// Idempotent: pure property update. No node creation. Re-run safe.
//
// Resilience: each invariant runs inside its own transaction with
// `ON ERROR CONTINUE`, so a single broken check_cypher (syntax error,
// unknown function, etc.) does not abort the whole protocol — those nodes
// are caught in the post-pass and marked 'error'.
//
// Merkle stability: writes `health`, `last_check`, `last_check_result` on
// Invariant nodes. Those keys are NOT in SkipKey, BUT root_hash on Being is
// only recomputed when merkle-properties.cypher runs — so writing here does
// not by itself change the stored root_hash. If the merkle protocol is run
// AFTER this one, leaf_hashes for Invariants will drift; in that case those
// three keys must be added to SkipKey nodes (Phase 2 concern).
// ============================================================================

// ---- Step 0: stamp this run's start time on Being so the post-pass can
// identify which invariants got touched. We read it back on every step.
MERGE (b:Being {node_id: 'being-mycelium'})
SET b._invariant_run_started_at = toString(datetime())
RETURN b._invariant_run_started_at AS run_started;

// ---- Step 1: per-invariant execution with isolated error handling ---------
MATCH (b:Being {node_id: 'being-mycelium'})
WITH b._invariant_run_started_at AS run_marker
MATCH (i:Invariant)
WHERE coalesce(i.enabled, true) = true
CALL {
  WITH i, run_marker
  WITH i, run_marker,
       CASE WHEN i.check_cypher IS NULL OR trim(i.check_cypher) = ''
            THEN null ELSE i.check_cypher END AS qtext
  CALL apoc.cypher.run(
    coalesce(qtext, 'RETURN null AS __novalue'),
    {}
  ) YIELD value
  WITH i, run_marker, qtext, collect(value) AS rows
  WITH i, run_marker, qtext,
       CASE WHEN size(rows) = 0 THEN null ELSE rows[0] END AS row0
  WITH i, run_marker, qtext, row0,
       CASE WHEN row0 IS NULL THEN null
            ELSE [k IN keys(row0) | row0[k]][0] END AS v
  WITH i, run_marker, qtext, row0, v,
       CASE
         WHEN qtext IS NULL THEN 'no_check'
         WHEN v IS NULL THEN 'unhealthy'
         WHEN v = true THEN 'healthy'
         WHEN v = false THEN 'unhealthy'
         WHEN apoc.meta.cypher.type(v) IN ['INTEGER','FLOAT']
              THEN CASE WHEN v > 0 THEN 'healthy' ELSE 'unhealthy' END
         WHEN apoc.meta.cypher.type(v) = 'STRING'
              THEN CASE WHEN toLower(toString(v)) IN ['healthy','ok','pass','true']
                        THEN 'healthy' ELSE 'unhealthy' END
         ELSE 'unhealthy'
       END AS health,
       CASE WHEN row0 IS NULL THEN 'null'
            ELSE apoc.convert.toJson(row0) END AS result_json
  SET i.health = health,
      i.last_check = toString(datetime()),
      i.last_check_result = result_json,
      i._invariant_run_marker = run_marker
} IN TRANSACTIONS OF 1 ROW ON ERROR CONTINUE
RETURN count(i) AS attempted;

// ---- Step 2: anyone whose run-marker doesn't match this run's start
// is one whose check_cypher raised — mark it 'error'.
MATCH (b:Being {node_id: 'being-mycelium'})
WITH b._invariant_run_started_at AS run_marker
MATCH (i:Invariant)
WHERE coalesce(i.enabled, true) = true
  AND (i._invariant_run_marker IS NULL OR i._invariant_run_marker <> run_marker)
SET i.health = 'error',
    i.last_check = run_marker,
    i.last_check_result = '{"error":"check_cypher raised exception during run-invariants protocol"}',
    i._invariant_run_marker = run_marker
RETURN count(i) AS errored;

// ---- Step 3: summary (active invariants only) -----------------------------
MATCH (i:Invariant)
WITH collect({
  node_id: i.node_id,
  label: i.label,
  health: i.health,
  enabled: coalesce(i.enabled, true)
}) AS results
WITH results,
     [r IN results WHERE r.enabled] AS active,
     size([r IN results WHERE NOT r.enabled]) AS deferred_count
WITH active, deferred_count,
     size(active) AS total,
     size([r IN active WHERE r.health = 'healthy']) AS healthy,
     size([r IN active WHERE r.health <> 'healthy']) AS unhealthy,
     [r IN active WHERE r.health <> 'healthy' | r.node_id + ' (' + coalesce(r.health, 'null') + ')'] AS unhealthy_names
RETURN total, healthy, unhealthy, unhealthy_names, deferred_count;
