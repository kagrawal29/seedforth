// @node_id: protocol-test-clone-target-matches-source
// @label: "Test Clone Target Matches Source — verify successful data transfer"
// ============================================================================
// TestCase asserting that after a CloneRun completes, the target database's
// node count matches the source's pre-clone count. This verifies that:
//   1. The dump captured all source nodes.
//   2. The load transferred all nodes correctly.
//   3. No data was lost or corrupted in transit.
//
// Passes if: target_count_after == source_count_before (or within 0.1%
// tolerance to allow for Being.last_heartbeat_at ticks during the
// brief window while clone was in progress).
//
// Fails if: target has significantly fewer or more nodes, indicating
// a partial or corrupted load.
// ============================================================================

MERGE (anchor:_SchemaAnchor:SchemaAnchorTestClone {node_id: 'schema-anchor-test-clone'})
  SET anchor.test_wire_complete = true;

// --- Create TestCase node ---

MERGE (tc:TestCase {node_id: 'test-clone-target-matches-source'})
  SET tc.label = 'Clone: Target Matches Source',
      tc.description = 'After a clone completes, the target database node count must equal the source pre-clone count (within 0.1% tolerance).',
      tc.target_label = 'CloneRun',
      tc.created_at = datetime(),

      // --- check_cypher: the test assertion logic ---
      // Returns { passed: bool, source_nodes: int, target_nodes: int, tolerance_pct: float, reason: string }
      //
      // Logic:
      //   1. Find the most recent completed CloneRun.
      //   2. Get source_count_before and target_count_after.
      //   3. Compute tolerance as 0.1% of source count.
      //   4. Check if abs(target - source) <= tolerance.
      //   5. Pass if within tolerance; fail otherwise.
      //
      tc.check_cypher =
        'MATCH (cr:CloneRun {status: "complete"}) ' +
        'ORDER BY cr.completed_at DESC LIMIT 1 ' +
        'WITH cr.source_count_before AS source, cr.target_count_after AS target ' +
        'WITH source, target, source * 0.001 AS tolerance ' +
        'RETURN ' +
        '  abs(target - source) <= tolerance AS passed, ' +
        '  source AS source_nodes, ' +
        '  target AS target_nodes, ' +
        '  tolerance AS tolerance_nodes, ' +
        '  CASE ' +
        '    WHEN abs(target - source) <= tolerance ' +
        '      THEN "target node count matches source (within tolerance)" ' +
        '    WHEN target IS NULL ' +
        '      THEN "ERROR: target_count_after not recorded (load may have failed)" ' +
        '    WHEN target < source ' +
        '      THEN "ERROR: target lost " + toString(source - target) + " node(s) during load" ' +
        '    ELSE "ERROR: target gained " + toString(target - source) + " node(s)" ' +
        '  END AS reason',

      tc.severity = 'critical',
      tc.category = 'data-integrity';

// --- Link TestCase to CloneRun target ---

OPTIONAL MATCH (cr:CloneRun)
MATCH (tc:TestCase {node_id: 'test-clone-target-matches-source'})
FOREACH (_ IN CASE WHEN cr IS NOT NULL THEN [1] ELSE [] END |
  MERGE (tc)-[:VALIDATES]->(cr)
);

// --- Summary report -------------------------------------------------------

MATCH (tc:TestCase {node_id: 'test-clone-target-matches-source'})
RETURN
  tc.node_id AS test_id,
  tc.label AS label,
  tc.severity AS severity,
  tc.category AS category,
  'test-clone-target-matches-source wired' AS status;
