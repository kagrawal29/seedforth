// @node_id: trigger-protocol-mutation-observed
// @label: "Protocol/Atom/Invariant Mutation Detector — Reactive APOC Trigger"
// ============================================================================
// APOC Trigger: Fires when Protocol, CypherAtom, or Invariant nodes are
// created or when their critical properties (cypher, label) are modified.
//
// Behavior:
//   1. On Protocol/CypherAtom/Invariant node CREATE: MERGE DirtyState.dirty=true
//   2. On .cypher or .label property SET: MERGE DirtyState.dirty=true
//   3. MERGE collapses to a single DirtyState node (not per-mutation)
//   4. Link DirtyState to Being via OBSERVES edge
//
// Phase: 'afterAsync' — fires after transaction commits, non-blocking
// Events: ['create', 'set']
//
// Installation:
//   This file is reference documentation. The actual trigger is installed by
//   graph/runner/install-triggers.py or bootstrap logic that invokes
//   apoc.trigger.install() with the cypher below.
//
// Selector parameters (JSON):
//   {
//     "phase": "afterAsync",
//     "events": ["create", "set"],
//     "assignedNodeProperties": ["cypher", "label"],
//     "createdNodes": ["*"]
//   }
// ============================================================================

// --- Trigger cypher (executed on mutations) --------------------------------
// This is the body that APOC fires on Protocol/CypherAtom/Invariant changes.
//
// Input: $createdNodes (array of newly created nodes)
//        $assignedNodeProperties (array of {node, key, oldValue, newValue})
//
// Logic:
//   1. Check if any new node is a Protocol, CypherAtom, or Invariant
//   2. Check if any assigned property is .cypher or .label on those node types
//   3. If either is true, MERGE a single DirtyState node
//   4. Set dirty=true and touched_at=datetime()
//   5. Link DirtyState OBSERVES Being (one-way)

UNWIND (($createdNodes // []) + ($assignedNodeProperties // []))  AS mutation
WITH mutation
WHERE
  // Check created nodes
  (mutation IN $createdNodes AND
   (labels(mutation) CONTAINS 'Protocol' OR
    labels(mutation) CONTAINS 'CypherAtom' OR
    labels(mutation) CONTAINS 'Invariant'))
  OR
  // Check assigned properties
  (mutation.node IS NOT NULL AND mutation.key IN ['cypher', 'label'] AND
   (labels(mutation.node) CONTAINS 'Protocol' OR
    labels(mutation.node) CONTAINS 'CypherAtom' OR
    labels(mutation.node) CONTAINS 'Invariant'))
WITH COUNT(*) AS mutation_count
WHERE mutation_count > 0
MATCH (b:Being {node_id: 'being-mycelium'})
MERGE (ds:DirtyState {node_id: 'dirty-state-mint-trigger'})
SET ds.dirty = true,
    ds.touched_at = datetime(),
    ds.mutation_count = (ds.mutation_count // 0) + 1
MERGE (ds)-[:OBSERVES]->(b)
RETURN ds.node_id AS dirty_state, ds.dirty AS is_dirty, ds.touched_at AS marked_at;
