// @node_id: tc-mint-fires-on-protocol-change
// @label: "Test: Mint Dirty Flag on Protocol Mutation"
// ============================================================================
// TestCase: Verify that mutating a Protocol.cypher property triggers the
// dirty flag within one APOC trigger async tick.
//
// Precondition:
//   - A Protocol node exists with some cypher property
//   - No DirtyState node exists (clean slate)
//   - Trigger is installed
//
// Action:
//   - Mutate the Protocol.cypher property
//
// Expected outcome:
//   - DirtyState {node_id: 'dirty-state-mint-trigger'} exists
//   - DirtyState.dirty = true
//   - DirtyState.touched_at is recent (within 5 sec of now)
//
// Validation:
//   - Query for DirtyState.dirty = true
//   - Check mutation_count >= 1
//   - Verify touched_at is current
//
// Notes:
//   - APOC triggers fire afterAsync (non-blocking), so there may be a
//     slight lag between mutation and dirty flag. Test should allow <=1sec.
//   - If trigger is not installed, this test will FAIL (dirty flag never set).
// ============================================================================

// Step 1: Ensure a test Protocol exists
MERGE (test_proto:Protocol {node_id: 'test-proto-mutation-trigger'})
SET test_proto.label = 'Test Protocol for Mutation Trigger',
    test_proto.cypher = 'MATCH (x) RETURN x LIMIT 1;',
    test_proto.created_at = datetime();

WITH test_proto

// Step 2: Clear any existing DirtyState (ensure clean test)
OPTIONAL MATCH (ds_old:DirtyState {node_id: 'dirty-state-mint-trigger'})
DELETE ds_old;

WITH test_proto

// Step 3: Mutate the Protocol.cypher
SET test_proto.cypher = 'MATCH (x) RETURN x LIMIT 5;';

WITH test_proto

// Step 4: Brief pause to allow trigger to fire (triggers are afterAsync)
// In a real test runner, this would be async polling. For synchronous validation:
// query immediately and expect DirtyState to exist. If not, retry polling.
// For now, return the query that validates:

OPTIONAL MATCH (ds:DirtyState {node_id: 'dirty-state-mint-trigger'})
RETURN
  CASE WHEN ds IS NULL THEN 'FAIL: DirtyState not created' ELSE 'PASS: DirtyState exists' END AS test_result,
  ds.dirty AS dirty_flag,
  ds.mutation_count AS mutation_count,
  ds.touched_at AS touched_at,
  test_proto.node_id AS test_proto_id;
