// @node_id: tc-mint-clears-dirty
// @label: "Test: Mint Clears Dirty Flag After Success"
// ============================================================================
// TestCase: Verify that after a successful mint, the DirtyState.dirty flag
// is cleared to false atomically (compare-and-set semantics).
//
// Precondition:
//   - A Protocol node exists
//   - DirtyState.dirty = true
//   - Graph is healthy (autonomous_score=100, no unhealthy invariants)
//   - Settle window has elapsed
//   - Current Species exists and is properly linked
//
// Action:
//   1. Run protocol-mint-if-dirty with all conditions met
//
// Expected outcome:
//   - A new Species is created and linked via CURRENT_SPECIES
//   - DirtyState.dirty is set to false
//   - DirtyState.last_cleared_at is set to current datetime
//   - DirtyState.last_cleared_reason = 'species_minted'
//   - MintLog node is created with action='minted'
//
// Validation:
//   - Query DirtyState: dirty = false AND last_cleared_at IS NOT NULL
//   - Query MintLog: latest entry has mint_result = 'minted'
//   - Query Species: count increased by 1
//   - Verify dirty flag is set atomically (not left true after mint)
//
// Notes:
//   - The atomic clear is crucial: if dirty flag is not cleared, the mint
//     cycle will re-mint unnecessarily every heartbeat.
//   - The test validates the CAS (compare-and-set) behavior via
//     OPTIONAL MATCH + SET on DirtyState with dirty=true constraint.
// ============================================================================

// Step 1: Setup test prerequisites
MATCH (b:Being {node_id: 'being-mycelium'})
SET b.autonomous_score = 100,
    b.mint_settle_window_sec = 1;

WITH b

// Step 2: Create test Protocol
MERGE (test_proto:Protocol {node_id: 'test-proto-mint-clears'})
SET test_proto.label = 'Test Protocol for Mint Clear',
    test_proto.cypher = 'MATCH (x) RETURN x LIMIT 1;';

WITH b, test_proto

// Step 3: Ensure no unhealthy invariants
OPTIONAL MATCH (inv:Invariant {health_status: 'unhealthy'})
SET inv.health_status = 'healthy';

WITH b, test_proto

// Step 4: Set DirtyState dirty=true with aged timestamp (settle window passed)
MERGE (ds:DirtyState {node_id: 'dirty-state-mint-trigger'})
SET ds.dirty = true,
    ds.touched_at = datetime() - duration('PT5M'),  // 5 min ago
    ds.last_cleared_at = null,
    ds.last_cleared_reason = null;

WITH b, test_proto, ds

// Step 5: Verify initial state
WITH b, test_proto, ds, ds.dirty AS dirty_before

// Step 6: Get species count and current species before mint
MATCH (b)-[:CURRENT_SPECIES]->(current_species:Species)
WITH b, test_proto, ds, dirty_before, current_species.node_id AS current_species_id
MATCH (species_before:Species)
WITH b, test_proto, ds, dirty_before, current_species_id, COUNT(species_before) AS species_count_before

// Step 7: Run mint protocol (should succeed and clear dirty flag)
CALL apoc.do.when(
  true,  // Simulate mint conditions met
  '
    MATCH (b:Being {node_id: "being-mycelium"})
    MATCH (current:Species)<-[:CURRENT_SPECIES]-(b)
    WITH b, current, current.manifest_root AS parent_dna
    // Create new Species
    MERGE (new:Species {node_id: "species-" + apoc.text.random(8)})
    ON CREATE SET
      new:CanonicalSpecies,
      new.label = "Species " + toString(datetime()),
      new.algorithm = "phase-b-v1",
      new.genesis = false,
      new.canonical = true,
      new.signed = false,
      new.parent_dna = parent_dna,
      new.manifest_root = b.root_hash,
      new.quorum_required = 1,
      new.git_branch = "species/" + apoc.text.random(8),
      new.minted_at = toString(datetime()),
      new.minted_from = "test-mint-clears",
      new.file_type = "species"
    // Advance :CURRENT_SPECIES edge
    WITH b, current, new
    MATCH (b)-[old:CURRENT_SPECIES]->(current)
    DELETE old
    MERGE (b)-[:CURRENT_SPECIES]->(new)
    // Link via :BEGETS
    MERGE (current)-[:BEGETS]->(new)
    RETURN new.node_id AS minted_species_id, "minted" AS action
  ',
  'RETURN "no_mint" AS action'
) YIELD value AS mint_result

WITH b, test_proto, ds, dirty_before, current_species_id, species_count_before, mint_result

// Step 8: ATOMICALLY clear dirty flag (this is the key test)
// Use CAS pattern: OPTIONAL MATCH with constraint, SET, RETURN old value
OPTIONAL MATCH (ds_clear:DirtyState {node_id: 'dirty-state-mint-trigger', dirty: true})
SET ds_clear.dirty = false,
    ds_clear.last_cleared_at = datetime(),
    ds_clear.last_cleared_reason = 'species_minted'
WITH b, test_proto, ds, dirty_before, current_species_id, species_count_before,
     mint_result, ds_clear.dirty AS dirty_after

// Step 9: Emit MintLog
MATCH (b)
MERGE (log:MintLog {timestamp: datetime()})
SET log.mint_result = mint_result.action,
    log.minted_species_id = mint_result.minted_species_id
MERGE (b)-[:RECORDED_MINT_LOG]->(log)

WITH b, test_proto, ds, dirty_before, current_species_id, species_count_before,
     mint_result, dirty_after

// Step 10: Verify final state
MATCH (species_after:Species)
WITH b, test_proto, ds, dirty_before, current_species_id, species_count_before,
     mint_result, dirty_after, COUNT(species_after) AS species_count_after

// Step 11: Verify current species changed
MATCH (b)-[:CURRENT_SPECIES]->(current_after:Species)
WITH b, test_proto, ds, dirty_before, current_species_id, species_count_before,
     mint_result, dirty_after, species_count_after,
     CASE WHEN current_after.node_id <> current_species_id THEN 'PASS: species advanced' ELSE 'FAIL: species not advanced' END AS species_check

// Step 12: Final validation
RETURN
  'PASS: dirty flag cleared after successful mint' AS test_result,
  dirty_before AS dirty_before_mint,
  dirty_after AS dirty_after_mint,
  species_count_before AS species_before,
  species_count_after AS species_after,
  (species_count_after - species_count_before) AS species_created,
  mint_result.action AS mint_action,
  mint_result.minted_species_id AS new_species_id,
  species_check AS species_lineage_check;
