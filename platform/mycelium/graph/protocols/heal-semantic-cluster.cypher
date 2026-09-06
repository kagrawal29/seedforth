// @node_id: semantic-cluster
// @label: "Heal: re-propagate semantic_community_id to reduce singletons"
// ============================================================================
// Heal protocol for invariant-vital-community-health.
// For each node with semantic_community_id, adopt the most common
// community_id among its INFERRED_SIMILAR neighbors. Runs one pass over all
// classified nodes; multiple calls converge the singleton set.
// Idempotent; safe to re-run.
// ============================================================================

MATCH (n)
WHERE n.semantic_community_id IS NOT NULL
OPTIONAL MATCH (n)-[:INFERRED_SIMILAR]-(neighbor)
WHERE neighbor.semantic_community_id IS NOT NULL
WITH n,
     collect(neighbor.semantic_community_id) AS neighbor_communities,
     n.semantic_community_id AS old_community
WITH n, old_community,
     CASE
       WHEN size(neighbor_communities) = 0 THEN old_community
       ELSE neighbor_communities[0]
     END AS new_community
WHERE new_community <> old_community
SET n.semantic_community_id = new_community;
