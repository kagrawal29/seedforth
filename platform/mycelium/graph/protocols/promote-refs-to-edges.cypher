// @node_id: protocol-promote-refs-to-edges
// @label: "Promote Refs to Edges"
// ============================================================================
// Protocol: Promote Refs to Edges
// ============================================================================
// Walks the graph looking for property values that are really references to
// other nodes (stored as strings because the ingester/writer didn't invest
// in topology), and promotes each to a proper edge.
//
// Why this matters:
//   A property like `n.agent_id = 'person-agent-3'` is dead weight. You
//   can't traverse it, invariants can't walk it, convergence detection
//   can't follow it. Promoting it to an edge like
//   (n)-[:MADE_BY]->(Person {node_id: 'person-agent-3'}) lifts every
//   downstream query that touches that connection.
//
//   Expected impact: ~600+ new edges from the known-foreign-key property
//   set (agent_id, gap_node_id, supersedes, contradicts, rhythm_node_id,
//   parent_dna, cluster_id, context_id, prev_snapshot_id, next_snapshot_id,
//   solution_node_id).
//
// Idempotent:
//   Each edge is MERGEd. Running this protocol twice produces the same
//   graph. We do NOT remove the source property after promotion — keeping
//   it as a redundant reference is cheap, and removing it would drift
//   leaf_hashes for every promoted node (possible later cleanup, but not
//   structurally required).
//
// Edge type mapping (property name → edge type):
//   agent_id         → MADE_BY
//   gap_node_id      → ADDRESSES
//   supersedes       → SUPERSEDES
//   contradicts      → CONTRADICTS
//   rhythm_node_id   → PART_OF_RHYTHM
//   cluster_id       → IN_CLUSTER
//   context_id       → IN_CONTEXT
//   prev_snapshot_id → PRECEDED_BY
//   next_snapshot_id → FOLLOWED_BY
//   solution_node_id → SOLVED_BY
//   root_context_id  → ROOT_CONTEXT
//   parent_dna       → handled by species chain already — skip
//
// Dependencies: APOC (apoc.create.relationship for parameterized edge types).
// ============================================================================


// --- agent_id → MADE_BY ------------------------------------------------------
MATCH (n) WHERE n.agent_id IS NOT NULL AND n.agent_id <> n.node_id
MATCH (target {node_id: n.agent_id})
MERGE (n)-[r:MADE_BY]->(target)
ON CREATE SET r.promoted_from = 'agent_id',
              r.promoted_at = toString(datetime())
RETURN count(r) AS made_by_edges;


// --- gap_node_id → ADDRESSES ------------------------------------------------
MATCH (n) WHERE n.gap_node_id IS NOT NULL AND n.gap_node_id <> n.node_id
MATCH (target {node_id: n.gap_node_id})
MERGE (n)-[r:ADDRESSES]->(target)
ON CREATE SET r.promoted_from = 'gap_node_id',
              r.promoted_at = toString(datetime())
RETURN count(r) AS addresses_edges;


// --- supersedes → SUPERSEDES -------------------------------------------------
MATCH (n) WHERE n.supersedes IS NOT NULL AND n.supersedes <> n.node_id
MATCH (target {node_id: n.supersedes})
MERGE (n)-[r:SUPERSEDES]->(target)
ON CREATE SET r.promoted_from = 'supersedes',
              r.promoted_at = toString(datetime())
RETURN count(r) AS supersedes_edges;


// --- contradicts → CONTRADICTS -----------------------------------------------
MATCH (n) WHERE n.contradicts IS NOT NULL AND n.contradicts <> n.node_id
MATCH (target {node_id: n.contradicts})
MERGE (n)-[r:CONTRADICTS]->(target)
ON CREATE SET r.promoted_from = 'contradicts',
              r.promoted_at = toString(datetime())
RETURN count(r) AS contradicts_edges;


// --- rhythm_node_id → PART_OF_RHYTHM -----------------------------------------
MATCH (n) WHERE n.rhythm_node_id IS NOT NULL AND n.rhythm_node_id <> n.node_id
MATCH (target {node_id: n.rhythm_node_id})
MERGE (n)-[r:PART_OF_RHYTHM]->(target)
ON CREATE SET r.promoted_from = 'rhythm_node_id',
              r.promoted_at = toString(datetime())
RETURN count(r) AS rhythm_edges;


// --- cluster_id → IN_CLUSTER -------------------------------------------------
MATCH (n) WHERE n.cluster_id IS NOT NULL AND n.cluster_id <> n.node_id
MATCH (target {node_id: n.cluster_id})
MERGE (n)-[r:IN_CLUSTER]->(target)
ON CREATE SET r.promoted_from = 'cluster_id',
              r.promoted_at = toString(datetime())
RETURN count(r) AS cluster_edges;


// --- context_id → IN_CONTEXT -------------------------------------------------
MATCH (n) WHERE n.context_id IS NOT NULL AND n.context_id <> n.node_id
MATCH (target {node_id: n.context_id})
MERGE (n)-[r:IN_CONTEXT]->(target)
ON CREATE SET r.promoted_from = 'context_id',
              r.promoted_at = toString(datetime())
RETURN count(r) AS context_edges;


// --- prev_snapshot_id → PRECEDED_BY -----------------------------------------
MATCH (n) WHERE n.prev_snapshot_id IS NOT NULL AND n.prev_snapshot_id <> n.node_id
MATCH (target {node_id: n.prev_snapshot_id})
MERGE (n)-[r:PRECEDED_BY]->(target)
ON CREATE SET r.promoted_from = 'prev_snapshot_id',
              r.promoted_at = toString(datetime())
RETURN count(r) AS preceded_by_edges;


// --- next_snapshot_id → FOLLOWED_BY -----------------------------------------
MATCH (n) WHERE n.next_snapshot_id IS NOT NULL AND n.next_snapshot_id <> n.node_id
MATCH (target {node_id: n.next_snapshot_id})
MERGE (n)-[r:FOLLOWED_BY]->(target)
ON CREATE SET r.promoted_from = 'next_snapshot_id',
              r.promoted_at = toString(datetime())
RETURN count(r) AS followed_by_edges;


// --- solution_node_id → SOLVED_BY -------------------------------------------
MATCH (n) WHERE n.solution_node_id IS NOT NULL AND n.solution_node_id <> n.node_id
MATCH (target {node_id: n.solution_node_id})
MERGE (n)-[r:SOLVED_BY]->(target)
ON CREATE SET r.promoted_from = 'solution_node_id',
              r.promoted_at = toString(datetime())
RETURN count(r) AS solved_by_edges;


// --- root_context_id → ROOT_CONTEXT -----------------------------------------
MATCH (n) WHERE n.root_context_id IS NOT NULL AND n.root_context_id <> n.node_id
MATCH (target {node_id: n.root_context_id})
MERGE (n)-[r:ROOT_CONTEXT]->(target)
ON CREATE SET r.promoted_from = 'root_context_id',
              r.promoted_at = toString(datetime())
RETURN count(r) AS root_context_edges;
