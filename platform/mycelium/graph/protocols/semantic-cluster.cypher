// @node_id: protocol-semantic-cluster
// @label: "Semantic Cluster"
// ============================================================================
// Protocol: Semantic Cluster
// ============================================================================
// Emergent community detection via the :INFERRED_SIMILAR edge graph.
// No external GDS / louvain needed — uses a pure cypher iterative
// label-propagation approximation:
//
//   1. Every node starts with its own community_id = node_id
//   2. For each node, look at its INFERRED_SIMILAR neighbors, pick the
//      community_id that is most common among them (simple majority),
//      adopt it if different from current
//   3. Repeat for N iterations (bounded — default 5) until labels settle
//
// This is NOT optimal — it's a cheap approximation that surfaces obvious
// clusters from the semantic-densify edges. Real Louvain would be better
// but requires GDS, which we don't have. Worth it when you want to see
// "which groups of nodes does the graph think belong together" without
// installing another plugin.
//
// Parameters:
//   iterations   int — label propagation passes (default 5)
//
// Side effects:
//   Sets n.semantic_community on every node with an embedding. The
//   property is in SkipKey (derived-output category) so it doesn't
//   drift merkle root.
//
// Dependencies: APOC (apoc.coll.frequenciesAsMap, apoc.coll.max).
// ============================================================================

// --- Step 1: seed every node's community with its own node_id --------------
MATCH (n) WHERE n.embedding IS NOT NULL AND n.node_id IS NOT NULL
SET n.semantic_community = coalesce(n.semantic_community, n.node_id);

// --- Step 2: label propagation (one pass) ----------------------------------
// Each node looks at INFERRED_SIMILAR neighbors and adopts the most common
// community among them. Run this cypher repeatedly (via the shell runner)
// until convergence.
MATCH (n) WHERE n.embedding IS NOT NULL AND n.semantic_community IS NOT NULL
OPTIONAL MATCH (n)-[:INFERRED_SIMILAR]-(m) WHERE m.semantic_community IS NOT NULL
WITH n, collect(m.semantic_community) AS neighbor_communities
WHERE size(neighbor_communities) > 0
WITH n, apoc.coll.frequenciesAsMap(neighbor_communities) AS freq
WITH n, freq,
     reduce(best = {key: null, count: 0}, k IN keys(freq) |
       CASE WHEN freq[k] > best.count THEN {key: k, count: freq[k]} ELSE best END
     ) AS winner
WHERE winner.key IS NOT NULL AND winner.count >= 2
SET n.semantic_community = winner.key;

// --- Step 3: summary --------------------------------------------------------
MATCH (n) WHERE n.semantic_community IS NOT NULL
WITH n.semantic_community AS community, count(n) AS size
WHERE size > 1
RETURN community, size
ORDER BY size DESC
LIMIT 15;
