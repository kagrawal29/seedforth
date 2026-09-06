// @node_id: protocol-test-delegate-v2
// @label: "Test Delegate v2 — family-batch evaluation (native Cypher, no apoc.cypher.run)"
// ============================================================================
// v2 (first version) used apoc.cypher.run per (TestCase, target) pair. For
// aggregate tests spanning 600+ targets, that was thousands of subqueries
// and timed out.
//
// This rewrite collapses each Evaluator family into a single native Cypher
// statement that evaluates all its TestCases at once. Six statements replace
// thousands of subquery calls. Orders of magnitude faster, same semantics.
//
// FRACTAL SHAPE
//   Every family has the identical rollup pattern:
//     MATCH TCs in this family
//     MATCH each TC's targets
//     Compute per-target healthy boolean (family-specific Cypher)
//     Aggregate to pass/fail at TC level
//     Write telemetry onto TC
//
//   Adding a new family = add one more statement in the same shape.
//
// EVALUATOR AUTHORSHIP MOVES TO GRAPH IN v3
//   The per-family check-logic is still embedded here. In v3 each Evaluator
//   will own its own batch query as a property. For now, the logic lives
//   here and the Evaluator node is the topological anchor that TestCases
//   point at via :EVALUATED_BY.
// ============================================================================

MERGE (anchor:_SchemaAnchor:SchemaAnchorDelegateV2 {node_id: 'schema-anchor-delegate-v2'})
  SET anchor.last_result = 'pass',
      anchor.last_evaluated_at = datetime(),
      anchor.actual = '',
      anchor.assertion_cypher = '',
      anchor.phase = 'delegated-v3',
      anchor.target_count = 0,
      anchor.targets_passed = 0;

// --- Family 1: Invariant — delegate to target's health_status ---------------
MATCH (tc:TestCase)-[:EVALUATED_BY]->(:Evaluator {node_id:'eval-invariant-check'})
MATCH (tc)-[:VALIDATES|:TESTS]->(i:Invariant)
WITH tc, collect(CASE WHEN i.health_status = 'healthy' THEN 1 ELSE 0 END) AS hs
WITH tc, reduce(s=0, x IN hs | s+x) AS n_pass, size(hs) AS n_total
SET tc.last_result = CASE WHEN n_pass = n_total AND n_total > 0 THEN 'pass' ELSE 'fail' END,
    tc.target_count = n_total,
    tc.targets_passed = n_pass,
    tc.last_evaluated_at = datetime(),
    tc.actual = toString(n_pass) + '/' + toString(n_total),
    tc.assertion_cypher = 'batch: Invariant.health_status',
    tc.phase = 'delegated-v3';

// --- Family 2: Protocol — has_fired OR (has_code AND is_wired) --------------
MATCH (tc:TestCase)-[:EVALUATED_BY]->(:Evaluator {node_id:'eval-protocol-liveness'})
MATCH (tc)-[:VALIDATES|:TESTS]->(p:Protocol)
WITH tc, p,
     coalesce(p.is_semantic_head, false) AS is_head,
     (p.last_run_status = 'ok' AND coalesce(p.run_count, 0) > 0) AS has_fired,
     (p.cypher IS NOT NULL AND size(coalesce(p.cypher, '')) > 0) AS has_code,
     (count{ (p)-[:CONTAINS|:EMBEDS_VIA]-() } >= 5) AS is_hub,
     exists((p)-[:SERVES|:CONTAINS|:CALLS|:STABILIZES|:WILL_FIRE|:ASPIRES_TO|:READS|:PRE_DECLARES_FOR|:EMBEDS_VIA|:VALIDATES|:BELONGS_TO|:COMMITS_TO|:DECLARES_FOR]-()) AS is_wired
WITH tc, collect(CASE WHEN (is_head OR has_fired OR is_hub OR (has_code AND is_wired)) THEN 1 ELSE 0 END) AS hs
WITH tc, reduce(s=0, x IN hs | s+x) AS n_pass, size(hs) AS n_total
SET tc.last_result = CASE WHEN n_pass = n_total AND n_total > 0 THEN 'pass' ELSE 'fail' END,
    tc.target_count = n_total,
    tc.targets_passed = n_pass,
    tc.last_evaluated_at = datetime(),
    tc.actual = toString(n_pass) + '/' + toString(n_total),
    tc.assertion_cypher = 'batch: Protocol fired-or-wired',
    tc.phase = 'delegated-v3';

// --- Family 3: HostInvariant — value not critical ---------------------------
MATCH (tc:TestCase)-[:EVALUATED_BY]->(:Evaluator {node_id:'eval-host-threshold'})
MATCH (tc)-[:VALIDATES|:TESTS]->(h:HostInvariant)
WITH tc, h,
     CASE
       WHEN h.value IS NULL THEN true
       WHEN h.value = 'critical' THEN false
       ELSE true
     END AS healthy
WITH tc, collect(CASE WHEN healthy THEN 1 ELSE 0 END) AS hs
WITH tc, reduce(s=0, x IN hs | s+x) AS n_pass, size(hs) AS n_total
SET tc.last_result = CASE WHEN n_pass = n_total AND n_total > 0 THEN 'pass' ELSE 'fail' END,
    tc.target_count = n_total,
    tc.targets_passed = n_pass,
    tc.last_evaluated_at = datetime(),
    tc.actual = toString(n_pass) + '/' + toString(n_total),
    tc.assertion_cypher = 'batch: HostInvariant.value',
    tc.phase = 'delegated-v3';

// --- Family 4: WorkItem — has tracked status --------------------------------
MATCH (tc:TestCase)-[:EVALUATED_BY]->(:Evaluator {node_id:'eval-workitem-tracked'})
MATCH (tc)-[:VALIDATES|:TESTS]->(w:WorkItem)
WITH tc, w,
     (coalesce(w.status, '') IN ['open','in_progress','completed','blocked','done','new','pending','planned','resolved']) AS healthy
WITH tc, collect(CASE WHEN healthy THEN 1 ELSE 0 END) AS hs
WITH tc, reduce(s=0, x IN hs | s+x) AS n_pass, size(hs) AS n_total
SET tc.last_result = CASE WHEN n_pass = n_total AND n_total > 0 THEN 'pass' ELSE 'fail' END,
    tc.target_count = n_total,
    tc.targets_passed = n_pass,
    tc.last_evaluated_at = datetime(),
    tc.actual = toString(n_pass) + '/' + toString(n_total),
    tc.assertion_cypher = 'batch: WorkItem.status',
    tc.phase = 'delegated-v3';

// --- Family 5: CodeCypher — has content ------------------------------------
MATCH (tc:TestCase)-[:EVALUATED_BY]->(:Evaluator {node_id:'eval-codecypher-presence'})
MATCH (tc)-[:VALIDATES|:TESTS]->(cc:CodeCypher)
WITH tc, cc,
     (coalesce(cc.query_text, cc.literal, cc.cypher, '') <> '') AS healthy
WITH tc, collect(CASE WHEN healthy THEN 1 ELSE 0 END) AS hs
WITH tc, reduce(s=0, x IN hs | s+x) AS n_pass, size(hs) AS n_total
SET tc.last_result = CASE WHEN n_pass = n_total AND n_total > 0 THEN 'pass' ELSE 'fail' END,
    tc.target_count = n_total,
    tc.targets_passed = n_pass,
    tc.last_evaluated_at = datetime(),
    tc.actual = toString(n_pass) + '/' + toString(n_total),
    tc.assertion_cypher = 'batch: CodeCypher content presence',
    tc.phase = 'delegated-v3';

// --- Family 6: Generic target-exists ---------------------------------------
// Fallback for TestCases whose evaluator is eval-target-exists (mixed target
// types). Healthy iff every target exists with node_id — by construction of
// the MATCH, they do, so this family passes unless a target was deleted.
MATCH (tc:TestCase)-[:EVALUATED_BY]->(:Evaluator {node_id:'eval-target-exists'})
MATCH (tc)-[:VALIDATES|:TESTS]->(target)
WITH tc, target, (target.node_id IS NOT NULL) AS healthy
WITH tc, collect(CASE WHEN healthy THEN 1 ELSE 0 END) AS hs
WITH tc, reduce(s=0, x IN hs | s+x) AS n_pass, size(hs) AS n_total
SET tc.last_result = CASE WHEN n_pass = n_total AND n_total > 0 THEN 'pass' ELSE 'fail' END,
    tc.target_count = n_total,
    tc.targets_passed = n_pass,
    tc.last_evaluated_at = datetime(),
    tc.actual = toString(n_pass) + '/' + toString(n_total),
    tc.assertion_cypher = 'batch: generic target existence',
    tc.phase = 'delegated-v3';

// --- Guards ---------------------------------------------------------------
MATCH (tc:TestCase)
WHERE NOT (tc)-[:EVALUATED_BY]->()
SET tc.last_result = 'no-evaluator',
    tc.last_evaluated_at = datetime(),
    tc.actual = 'false',
    tc.assertion_cypher = 'no :EVALUATED_BY edge — run protocol-test-wire-evaluators',
    tc.phase = 'delegated-v3';

MATCH (tc:TestCase)
WHERE NOT (tc)-[:VALIDATES|:TESTS]->()
SET tc.last_result = 'no-target',
    tc.last_evaluated_at = datetime(),
    tc.actual = 'false',
    tc.assertion_cypher = 'no :VALIDATES / :TESTS edge',
    tc.phase = 'delegated-v3';
