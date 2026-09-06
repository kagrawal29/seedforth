// @node_id: protocol-auto-gap-from-tests
// @label: "Auto-Gap-From-Tests"
// ============================================================================
// Protocol: Auto-Gap-From-Tests
// ============================================================================
// Automatically creates Gap nodes from failing ClaimTest nodes.
// This closes the detect-heal-test loop: when a test fails, the system
// creates a Gap node and wires it into the healing feedback path.
//
// Logic:
//   1. Match all ClaimTest nodes where last_result = 'fail'
//   2. For each failing test, MERGE a Gap node with:
//      - node_id = 'gap-from-' + test.node_id
//      - title from test.label
//      - category = 'failing_test'
//      - severity = test dimension (autonomy/invariant/coverage maps to critical/high/medium)
//      - auto_fixable = true (failing tests are often fixable)
//      - created_at = now
//   3. MERGE a CONCERNS edge from Gap to the test's target node
//      (follow test.VALIDATES edges to find target)
//   4. Ensure idempotency via MERGE (no duplicate gaps)
//   5. Return count of new gaps created
//
// Idempotency: Multiple runs create no duplicates because MERGE on node_id
// skips creation if the gap already exists.
// ============================================================================

// Find all failing tests and their target nodes
MATCH (tc:ClaimTest)
WHERE tc.last_result = 'fail'

// For each test, find its target node via VALIDATES edge (optional)
OPTIONAL MATCH (tc)-[:VALIDATES]->(target)

// Create or match a gap node for this failing test
MERGE (g:Gap {node_id: 'gap-from-' + tc.node_id})
ON CREATE SET
  g.title = coalesce(tc.label, tc.node_id) + ' — test failed',
  g.label = 'Gap from failing test: ' + coalesce(tc.label, tc.node_id),
  g.category = 'failing_test',
  g.severity = CASE tc.dimension
    WHEN 'autonomy' THEN 'critical'
    WHEN 'invariant' THEN 'critical'
    WHEN 'coverage' THEN 'high'
    ELSE 'medium'
  END,
  g.auto_fixable = true,
  g.status = 'open',
  g.created_at = toString(datetime()),
  g.created_by = 'auto-gap-from-tests-protocol',
  g.source_test_id = tc.node_id
ON MATCH SET
  g.last_checked_at = toString(datetime())

WITH g, tc, target

// Create edge from gap to the test that failed (TRIGGERED_BY)
MERGE (g)-[:TRIGGERED_BY]->(tc)

// If test validates a target, create CONCERNS edge from gap to target
WITH g, tc, target
WHERE target IS NOT NULL
MERGE (g)-[:CONCERNS]->(target)

WITH count(DISTINCT g.node_id) AS gap_count

// Return summary
RETURN
  'Gap creation from failing tests completed' AS status,
  gap_count AS gaps_created,
  toString(datetime()) AS completed_at;
