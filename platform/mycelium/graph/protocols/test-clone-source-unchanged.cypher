// @node_id: protocol-test-clone-source-unchanged
// @label: "Test Clone Source Unchanged — verify clone does not modify source"
// ============================================================================
// TestCase asserting that after a CloneRun completes, the source graph's
// node count is unchanged. Compares source_count_before vs. the current
// source node count to detect if the dump/load cycle corrupted or modified
// the source database.
//
// Passes if: source node count == source_count_before (or within 1 node
// tolerance for heartbeat ticks during the brief window).
//
// Fails if: source node count > source_count_before (something was created)
// or < source_count_before (something was deleted).
// ============================================================================

MERGE (anchor:_SchemaAnchor:SchemaAnchorTestClone {node_id: 'schema-anchor-test-clone'})
  SET anchor.test_wire_complete = true;

// --- Create TestCase node ---

MERGE (tc:TestCase {node_id: 'test-clone-source-unchanged'})
  SET tc.label = 'Clone: Source Unchanged',
      tc.description = 'After a clone completes, the source database node count must equal the recorded pre-clone count.',
      tc.target_label = 'CloneRun',
      tc.created_at = datetime(),

      // --- check_cypher: the test assertion logic ---
      // Returns { passed: bool, source_nodes_before: int, source_nodes_after: int, reason: string }
      //
      // Logic:
      //   1. Find the most recent completed CloneRun.
      //   2. Get the recorded source_count_before.
      //   3. Query the current source graph (via bolt connection).
      //   4. Compare: if within 1-node tolerance → pass; else fail.
      //
      // Note: In a distributed setup, the source and target may be on
      // different Neo4j instances. For this test, we assume the test
      // runner has access to both via CYPHER queries (or this test
      // records expectations that a verification script validates).
      //
      // Simplified version: just check that source_count_before is recorded.
      // Full version (on pulse-server): would query actual source post-clone.
      //
      tc.check_cypher =
        'MATCH (cr:CloneRun {status: "complete"}) ' +
        'ORDER BY cr.completed_at DESC LIMIT 1 ' +
        'WITH cr.source_count_before AS before ' +
        'OPTIONAL MATCH (n) WHERE n.node_id IS NOT NULL ' +
        'WITH before, count(n) AS after ' +
        'RETURN ' +
        '  abs(after - before) <= 1 AS passed, ' +
        '  before AS source_nodes_before, ' +
        '  after AS source_nodes_after, ' +
        '  CASE ' +
        '    WHEN abs(after - before) <= 1 ' +
        '      THEN "source node count unchanged (within tolerance)" ' +
        '    WHEN after > before ' +
        '      THEN "ERROR: source gained " + toString(after - before) + " node(s)" ' +
        '    ELSE "ERROR: source lost " + toString(before - after) + " node(s)" ' +
        '  END AS reason',

      tc.severity = 'critical',
      tc.category = 'data-integrity';

// --- Link TestCase to CloneRun target ---

OPTIONAL MATCH (cr:CloneRun)
MATCH (tc:TestCase {node_id: 'test-clone-source-unchanged'})
FOREACH (_ IN CASE WHEN cr IS NOT NULL THEN [1] ELSE [] END |
  MERGE (tc)-[:VALIDATES]->(cr)
);

// --- Summary report -------------------------------------------------------

MATCH (tc:TestCase {node_id: 'test-clone-source-unchanged'})
RETURN
  tc.node_id AS test_id,
  tc.label AS label,
  tc.severity AS severity,
  tc.category AS category,
  'test-clone-source-unchanged wired' AS status;
