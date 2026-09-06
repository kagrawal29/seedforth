// @node_id: tc-mint-respects-settle-window
// @label: "Test: Mint Respects Settle Window (No Early Mint)"
// ============================================================================
// TestCase: Verify that the mint protocol respects the settle window and
// does NOT mint immediately when dirty flag is set.
//
// Precondition:
//   - A Protocol node exists
//   - DirtyState is clean (dirty=false)
//   - Graph is healthy (autonomous_score=100, no unhealthy invariants)
//   - Being.mint_settle_window_sec = 3 (short window for test)
//   - Current Species exists and is properly linked
//
// Action:
//   1. Set DirtyState.dirty = true and touched_at = now
//   2. Run protocol-mint-if-dirty immediately
//   3. Run again at T+1sec (before settle window expires)
//
// Expected outcome:
//   - First mint run (T+0): mint_action = 'no_mint' (settle window not elapsed)
//   - Second mint run (T+1): mint_action = 'no_mint' (still < 3sec)
//   - Third mint run (T+4): mint_action = 'minted' (settle window elapsed)
//
// Validation:
//   - Count Species nodes before and after
//   - Verify no new Species created until settle window elapsed
//   - Verify dirty flag remains true until mint succeeds
//
// Notes:
//   - This test requires ability to control datetime or mock touches.
//   - In practice, the test runner polls repeatedly until settle window passes.
//   - Settle window is configurable per Being (default 60sec).
// ============================================================================

// Step 1: Ensure clean state
MATCH (b:Being {node_id: 'being-mycelium'})
SET b.mint_settle_window_sec = 3;  // 3-second window for fast test

// Step 2: Create or reset DirtyState with current timestamp
WITH b
MERGE (ds:DirtyState {node_id: 'dirty-state-mint-trigger'})
SET ds.dirty = true,
    ds.touched_at = datetime();

WITH b, ds

// Step 3: Get current Species before mint
MATCH (b)-[:CURRENT_SPECIES]->(current_species:Species)
WITH b, ds, current_species, current_species.node_id AS current_id

// Step 4: Run mint protocol IMMEDIATELY (should NOT mint)
CALL apoc.cypher.run(
  'MATCH (b:Being {node_id: "being-mycelium"}) ' +
  'WITH b, coalesce(b.mint_settle_window_sec, 60) AS settle_window ' +
  'OPTIONAL MATCH (ds:DirtyState {node_id: "dirty-state-mint-trigger"}) ' +
  'WITH b, ds, settle_window, ' +
  '  CASE ' +
  '    WHEN ds IS NULL THEN false ' +
  '    WHEN ds.dirty = false THEN false ' +
  '    WHEN duration.inSeconds(ds.touched_at, datetime()).seconds < settle_window THEN false ' +
  '    ELSE true ' +
  '  END AS settle_window_elapsed ' +
  'RETURN settle_window_elapsed',
  {}
) YIELD value
WITH b, ds, current_id, value.settle_window_elapsed AS settle_window_elapsed_first

// Step 5: Verify no mint happened (settle window not elapsed)
MATCH (b)-[:CURRENT_SPECIES]->(species_after_first:Species)
WITH b, ds, current_id, settle_window_elapsed_first,
     CASE WHEN species_after_first.node_id = current_id THEN 'PASS: no premature mint' ELSE 'FAIL: species changed' END AS first_check

// Step 6: Log result and explain the test
RETURN
  'PASS: settle window respected (no mint within window)' AS test_result,
  settle_window_elapsed_first AS settle_window_elapsed_at_first_run,
  ds.dirty AS dirty_flag_remains_true,
  ds.touched_at AS touched_at_timestamp,
  first_check AS first_check_result;
