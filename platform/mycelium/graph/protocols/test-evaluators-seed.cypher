// @node_id: protocol-test-evaluators-seed
// @label: "Test Evaluators — fractal evaluation, one Evaluator per family"
// ============================================================================
// Lifts the hardcoded 6-pass test-delegate into graph-native composition.
//
// Before: test-delegate had 6 MATCH branches (one per target label) with the
// check logic baked into Cypher text in the file. Adding a new test family
// meant editing the file. That's imperative, not fractal.
//
// After: 6 :Evaluator nodes, each with a `.check_template` holding the exact
// Cypher to run against a target. Every TestCase points at ONE Evaluator via
// :EVALUATED_BY. The delegate becomes a single MATCH+call: "find TestCase's
// Evaluator, run Evaluator.check_template against TestCase's target."
//
// Adding a new test family = MERGE a new Evaluator node. Zero file edits to
// the delegate. Zero compile/deploy cycles. The graph grows its own test
// capabilities.
//
// BENCHMARKS (future):
//   Each Evaluator will gain a :Benchmark node attached via :BENCHMARKED_BY
//   carrying the expected threshold. Right now thresholds are inline in the
//   check_template; promoting them to Benchmark nodes makes them tunable
//   without touching the template.
// ============================================================================

MERGE (anchor:_SchemaAnchor:SchemaAnchorEvaluators {node_id: 'schema-anchor-evaluators'})
  SET anchor.check_template = '',
      anchor.target_label_match = '',
      anchor.description = '';

// --- Evaluator 1: Invariant-family test ------------------------------------
// Runs target.check_cypher, healthy iff it returns healthy=true.
MERGE (e1:Evaluator:GraphNode {node_id: 'eval-invariant-check'})
  SET e1.label = 'Invariant Check',
      e1.target_label_match = 'Invariant',
      e1.description = 'Run target.check_cypher; pass iff it returns healthy=true',
      e1.check_template = '
        MATCH (t:Invariant {node_id: $target_node_id})
        WHERE t.check_cypher IS NOT NULL AND size(t.check_cypher) > 0
        CALL apoc.cypher.run(t.check_cypher, {}) YIELD value
        RETURN coalesce(value.healthy, false) AS healthy
      ';

// --- Evaluator 2: Protocol-family test -------------------------------------
// Pass iff target has fired at least once successfully (Phase 2 telemetry).
MERGE (e2:Evaluator:GraphNode {node_id: 'eval-protocol-liveness'})
  SET e2.label = 'Protocol Liveness',
      e2.target_label_match = 'Protocol',
      e2.description = 'Pass iff target.last_run_status="ok" AND run_count > 0',
      e2.check_template = '
        MATCH (t:Protocol {node_id: $target_node_id})
        RETURN (t.last_run_status = "ok" AND coalesce(t.run_count, 0) > 0) AS healthy
      ';

// --- Evaluator 3: HostInvariant-family test --------------------------------
// Pass iff value is not critical / below critical threshold.
MERGE (e3:Evaluator:GraphNode {node_id: 'eval-host-threshold'})
  SET e3.label = 'Host Threshold',
      e3.target_label_match = 'HostInvariant',
      e3.description = 'Pass iff HostInvariant value is not critical',
      e3.check_template = '
        MATCH (t:HostInvariant {node_id: $target_node_id})
        WITH t,
             CASE
               WHEN t.value IS NULL THEN true
               WHEN t.value = "critical" THEN false
               WHEN t.value IN ["normal","warn"] THEN true
               WHEN t.threshold_critical IS NOT NULL
                    AND toString(t.value) =~ "^-?[0-9]+(\\\\.[0-9]+)?$"
                    AND toFloat(toString(t.value)) >= toFloat(toString(t.threshold_critical))
                 THEN false
               ELSE true
             END AS healthy
        RETURN healthy
      ';

// --- Evaluator 4: WorkItem-family test -------------------------------------
// Pass iff WorkItem has a tracked status.
MERGE (e4:Evaluator:GraphNode {node_id: 'eval-workitem-tracked'})
  SET e4.label = 'WorkItem Tracked',
      e4.target_label_match = 'WorkItem',
      e4.description = 'Pass iff WorkItem.status is in tracked set',
      e4.check_template = '
        MATCH (t:WorkItem {node_id: $target_node_id})
        RETURN coalesce(t.status, "") IN ["open","in_progress","completed","blocked","done"] AS healthy
      ';

// --- Evaluator 5: CodeCypher-family test -----------------------------------
// Pass iff target has non-empty code content (query_text | literal | cypher).
MERGE (e5:Evaluator:GraphNode {node_id: 'eval-codecypher-presence'})
  SET e5.label = 'CodeCypher Presence',
      e5.target_label_match = 'CodeCypher',
      e5.description = 'Pass iff target has non-empty code content',
      e5.check_template = '
        MATCH (t:CodeCypher {node_id: $target_node_id})
        RETURN coalesce(t.query_text, t.literal, t.cypher, "") <> "" AS healthy
      ';

// --- Evaluator 6: Generic presence (fallback for any other target label) ---
MERGE (e6:Evaluator:GraphNode {node_id: 'eval-target-exists'})
  SET e6.label = 'Target Existence',
      e6.target_label_match = '*',
      e6.description = 'Fallback: pass iff target node exists with node_id',
      e6.check_template = '
        MATCH (t {node_id: $target_node_id})
        RETURN (t IS NOT NULL) AS healthy
      ';

// --- Wire every Evaluator to Being so they are not orphan ------------------
MATCH (b:Being {node_id: 'being-mycelium'})
MATCH (e:Evaluator)
MERGE (e)-[:SERVES]->(b)
RETURN count(e) AS evaluators_seeded;
