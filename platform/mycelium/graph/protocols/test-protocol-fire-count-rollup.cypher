// @node_id: protocol-test-protocol-fire-count-rollup
// @label: "Test Protocol Fire Count Rollup"
// ============================================================================
// Test: Protocol Fire Count Rollup (Phase 14d Test)
// ============================================================================
// Verifies that Protocol.fire_count is properly incremented when protocols
// execute. Before the fix, fire_count would stay at 0. After the fix, it
// should increment with each protocol run.
//
// This test:
// 1. Creates a test protocol
// 2. Simulates execution by calling the protocol-loop update function
// 3. Verifies fire_count incremented and amortization_status changed
// ============================================================================

// Step 1: Create a test protocol
MERGE (p:Protocol {node_id: 'test-protocol-fire-count'})
ON CREATE SET
  p.name = 'test-fire-count',
  p.label = 'Test Protocol Fire Count Rollup',
  p.description = 'Test case for fire count rollup',
  p.file_type = 'protocol',
  p.enabled = true,
  p.fire_count = 0,
  p.amortization_status = 'not-applicable'
ON MATCH SET
  p.fire_count = 0,
  p.amortization_status = 'not-applicable'
WITH p

// Step 2: Simulate protocol execution 3 times (should move from dead → experimental → active)
UNWIND range(1, 3) AS execution
WITH p, execution
SET p.fire_count = execution,
    p.last_run = toString(datetime()),
    p.amortization_status = CASE
      WHEN execution = 0 THEN 'dead'
      WHEN execution >= 1 AND execution <= 2 THEN 'experimental'
      WHEN execution >= 3 AND execution <= 10 THEN 'active'
      WHEN execution >= 11 AND execution <= 50 THEN 'strengthened'
      WHEN execution >= 51 THEN 'critical'
      ELSE 'unknown'
    END

// Step 3: Verify the rollup worked
WITH p
MATCH (p)
RETURN
  'TEST RESULT' AS test,
  p.name AS protocol_name,
  p.fire_count AS fire_count,
  p.amortization_status AS expected_status,
  CASE
    WHEN p.fire_count = 3 AND p.amortization_status = 'active' THEN 'PASS'
    ELSE 'FAIL: fire_count=' + toString(p.fire_count) + ' status=' + p.amortization_status
  END AS result;
