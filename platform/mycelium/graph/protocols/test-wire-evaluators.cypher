// @node_id: protocol-test-wire-evaluators
// @label: "Test Wire Evaluators — attach every TestCase to its Evaluator"
// ============================================================================
// Given the 6 Evaluators from test-evaluators-seed.cypher, wire every
// TestCase to the one whose `target_label_match` matches the TestCase's
// target label.
//
// Runs in parallel shape — one statement per TestCase via apoc.periodic.iterate
// so this scales to thousands of TestCases without a single long transaction.
//
// Idempotent: MERGE on :EVALUATED_BY. Multiple runs are safe.
// Re-runnable: if a TestCase's target changes label, re-run to reassign.
// ============================================================================

// Pre-declare token so APOC executor can set it later
MERGE (anchor:_SchemaAnchor:SchemaAnchorTestWire {node_id: 'schema-anchor-test-wire'})
  SET anchor.evaluator_assigned = true;

// --- Wire specific-label TestCases to their matching Evaluators -----------
// For every (TestCase, target, Evaluator) triple where target's label
// matches evaluator.target_label_match, create :EVALUATED_BY.
//
// Ordering: specific evaluators are tried first; the generic "eval-target-exists"
// is applied last to any TestCase still unwired.
CALL apoc.periodic.iterate(
  '
    MATCH (tc:TestCase)-[:VALIDATES|:TESTS]->(target)
    MATCH (e:Evaluator)
    WHERE e.target_label_match <> "*"
      AND e.target_label_match IN labels(target)
    RETURN tc, e
  ',
  '
    MERGE (tc)-[:EVALUATED_BY]->(e)
  ',
  {batchSize: 200, parallel: true, concurrency: 3}
) YIELD batches, total, errorMessages
RETURN "specific wiring" AS phase, batches, total, errorMessages;

// --- Wire remaining (unmatched) TestCases to the generic evaluator --------
CALL apoc.periodic.iterate(
  '
    MATCH (tc:TestCase)
    WHERE NOT (tc)-[:EVALUATED_BY]->()
    MATCH (e:Evaluator {node_id: "eval-target-exists"})
    RETURN tc, e
  ',
  '
    MERGE (tc)-[:EVALUATED_BY]->(e)
  ',
  {batchSize: 200, parallel: true, concurrency: 3}
) YIELD batches, total, errorMessages
RETURN "fallback wiring" AS phase, batches, total, errorMessages;
