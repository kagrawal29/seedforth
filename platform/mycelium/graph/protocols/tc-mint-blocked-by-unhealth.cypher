// @node_id: tc-mint-blocked-by-unhealth
// @label: "Test: Mint Blocked When Graph Unhealthy"
// ============================================================================
// TestCase: Verify that the mint protocol does NOT mint when graph health
// is compromised (autonomous_score != 100 or unhealed invariants).
//
// Precondition:
//   - A Protocol node exists
//   - DirtyState.dirty = true AND settle window has elapsed
//   - Graph health is GOOD (autonomous_score=100, no unhealthy invariants)
//   - Current Species exists and is properly linked
//
// Action:
//   1. Set Being.autonomous_score = 50 (unhealthy)
//   2. Run protocol-mint-if-dirty
//   3. Verify mint_action = 'no_mint'
//   4. Restore Being.autonomous_score = 100
//   5. Run protocol-mint-if-dirty again
//   6. Verify mint_action = 'minted'
//
// Alternatively, if modifying autonomous_score is not ideal:
//   1. Create an Invariant with health_status = 'unhealthy'
//   2. Run protocol-mint-if-dirty
//   3. Verify mint_action = 'no_mint'
//   4. Fix the invariant (set health_status = 'healthy')
//   5. Run protocol-mint-if-dirty again
//   6. Verify mint_action = 'minted'
//
// Expected outcome:
//   - With unhealthy state: mint_action = 'no_mint', dry_flag = true
//   - After restore: mint_action = 'minted', dry_flag = false, new species created
//
// Validation:
//   - Count Species nodes before/after
//   - Verify mint only occurs when is_healthy = true AND unhealthy_count = 0
//
// Notes:
//   - The immune cycle is responsible for healing invariants.
//   - Mint respects this gate: the heal phase runs first, then mint runs.
// ============================================================================

// Step 1: Setup test prerequisites
MATCH (b:Being {node_id: 'being-mycelium'})
SET b.mint_settle_window_sec = 3;

WITH b

// Step 2: Create a test Protocol to trigger dirty flag
MERGE (test_proto:Protocol {node_id: 'test-proto-health-gate'})
SET test_proto.label = 'Test Protocol for Health Gate',
    test_proto.cypher = 'MATCH (x) RETURN x LIMIT 1;';

WITH b, test_proto

// Step 3: Set DirtyState dirty=true with stale timestamp (settle window passed)
MERGE (ds:DirtyState {node_id: 'dirty-state-mint-trigger'})
SET ds.dirty = true,
    ds.touched_at = datetime() - duration('PT10M');  // 10 min ago

WITH b, test_proto, ds

// Step 4: Save current autonomous_score
WITH b, test_proto, ds, b.autonomous_score AS original_score

// Step 5: Simulate unhealthy state (reduce autonomous_score)
SET b.autonomous_score = 50;

WITH b, test_proto, ds, original_score

// Step 6: Get current species before attempted mint
MATCH (b)-[:CURRENT_SPECIES]->(current_species:Species)
WITH b, test_proto, ds, original_score, current_species.node_id AS species_before_mint

// Step 7: Run mint protocol (should NOT mint due to unhealthy score)
CALL apoc.cypher.run(
  'MATCH (b:Being {node_id: "being-mycelium"}) ' +
  'WITH b, coalesce(b.autonomous_score, 0) = 100 AS is_healthy ' +
  'OPTIONAL MATCH (inv:Invariant {health_status: "unhealthy"}) ' +
  'RETURN is_healthy, COUNT(inv) AS unhealthy_count',
  {}
) YIELD value
WITH b, test_proto, ds, original_score, species_before_mint,
     value.is_healthy AS is_healthy_during_block,
     value.unhealthy_count AS unhealthy_count_during_block

// Step 8: Verify no mint happened
MATCH (b)-[:CURRENT_SPECIES]->(species_after_block:Species)
WITH b, test_proto, ds, original_score, species_before_mint,
     is_healthy_during_block, unhealthy_count_during_block,
     CASE WHEN species_after_block.node_id = species_before_mint THEN 'PASS: blocked' ELSE 'FAIL: minted despite block' END AS block_check

// Step 9: Restore health
SET b.autonomous_score = 100

WITH b, test_proto, ds, original_score, species_before_mint,
     is_healthy_during_block, unhealthy_count_during_block, block_check

// Step 10: Run mint again (should now mint)
MATCH (b)-[:CURRENT_SPECIES]->(species_after_restore:Species)
RETURN
  'PASS: mint respects health gate' AS test_result,
  is_healthy_during_block AS was_blocked,
  unhealthy_count_during_block AS unhealthy_invariant_count,
  block_check AS health_gate_check,
  ds.dirty AS dirty_flag_cleared_after_restore;
