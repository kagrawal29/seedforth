// @node_id: protocol-test-to-gap
// @label: "Test to Gap"
// ============================================================================
// Protocol: Test to Gap
// ============================================================================
// Finds all ClaimTest nodes where last_result = 'fail'.
// For each, checks if a Gap node already exists with CONCERNS edge.
// If not, creates Gap node with title from test label, category='failing_test', auto_fixable=true.
// Creates CONCERNS edge from Gap to the relevant node.
//
// Returns count of new gaps created and summary of failing tests processed.
// ============================================================================

// --- Phase 1: Find failing tests and create corresponding gaps if missing ---

MATCH (ct:ClaimTest)
WHERE ct.last_result = 'fail'
WITH ct
  OPTIONAL MATCH (g:Gap)-[:CONCERNS]->(ct)
  WHERE g.category = 'failing_test'
WITH ct, g
  WHERE g IS NULL
  // Create a new gap for this failing test
  WITH ct,
       'gap-failing-test-' + ct.node_id AS gap_node_id
  MERGE (new_gap:Gap {node_id: gap_node_id})
  SET new_gap.title = 'Failing test: ' + ct.label,
      new_gap.category = 'failing_test',
      new_gap.auto_fixable = true,
      new_gap.created_by = 'test-to-gap-protocol',
      new_gap.created_at = toString(datetime()),
      new_gap.status = 'open'
  WITH ct, new_gap
    MERGE (new_gap)-[:CONCERNS {created_by: 'test-to-gap-protocol', created_at: toString(datetime())}]->(ct)
  RETURN ct.label, new_gap.node_id, 'created' AS action;

// --- Phase 2: Summary ---

MATCH (ct:ClaimTest)
WHERE ct.last_result = 'fail'
WITH count(ct) AS failing_test_count
MATCH (g:Gap)
WHERE g.category = 'failing_test'
  AND g.created_by = 'test-to-gap-protocol'
RETURN
  'test_to_gap_summary' AS metric,
  failing_test_count,
  count(g) AS gaps_created,
  count(CASE WHEN g.created_at = toString(datetime()) THEN 1 END) AS newly_created
