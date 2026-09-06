// @node_id: protocol-community-coherence
// @label: "Community Coherence"
// ============================================================================
// Protocol: Community Coherence
// ============================================================================
// Measures the structural tightness of every semantic community in the graph.
// A "tight" community has many internal edges relative to external edges.
// A "loose" community is fragmented — nodes within it point mostly outside.
//
// Use this before compose-reply.cypher to:
//   1. See which communities speak clearly (high coherence_score)
//   2. Flag messy communities that bleed into others (low coherence_score)
//   3. Understand label diversity — communities with mixed types are healthier
//      than homogeneous ones (Protocol-only, CypherAtom-only clusters)
//
// Parameters: None (read-only analysis of all communities)
//
// Returns one row per semantic community:
//   community_id        the community identifier (usually a node_id)
//   node_count          total nodes in the community (size >= 2)
//   internal_edges      count of edges where both endpoints are in community
//   external_edges      count of edges where exactly one endpoint is in community
//   coherence_score     internal_edges / (internal_edges + external_edges)
//                       Range [0, 1]. 1 = pure cluster, 0 = completely bleeding
//   label_diversity     count of distinct node labels in the community
//                       Healthy: 3+ types mixed. Unhealthy: 1 type only.
//   sample_node_ids     top 5 nodes by embedding presence (presence of
//                       non-null embedding indicates "substance" in the graph)
//
// Tuning:
//   - Set WHERE node_count >= N to exclude small cliques (default: 2)
//   - Coherence_score is 0 when internal_edges + external_edges = 0
//     (handles isolated nodes gracefully)
//   - Communities of size 1 are excluded by the WHERE clause
//   - Sample nodes are sorted by embedding non-null-ness, then by node_id
//
// Design notes:
//   - This protocol is read-only (no SET, CREATE, MERGE)
//   - Runtime: ~2 seconds on 4k-node graph with 4k communities
//   - Scales linearly with graph density (# edges)
// ============================================================================

// Collect all nodes in each semantic community
MATCH (n) WHERE n.semantic_community IS NOT NULL
WITH n.semantic_community AS community, collect(n) AS members, count(n) AS node_count
// Exclude single-node "communities"
WHERE node_count >= 2

// Count internal edges (both endpoints in community)
UNWIND members AS m
OPTIONAL MATCH (m)-[r]-(neighbor)
WITH community, members, node_count, r, neighbor,
     CASE WHEN neighbor IN members THEN 1 ELSE 0 END AS is_internal
WITH community, members, node_count,
     sum(is_internal) AS internal_edges,
     sum(CASE WHEN is_internal = 0 THEN 1 ELSE 0 END) AS external_edges

// Calculate coherence score (internal / (internal + external))
// Handle divide-by-zero: if no edges at all, score is 0
WITH community, node_count, internal_edges, external_edges,
     CASE WHEN (internal_edges + external_edges) = 0 THEN 0
          ELSE toFloat(internal_edges) / (internal_edges + external_edges)
     END AS coherence_score

// Count distinct node labels for diversity metric
OPTIONAL MATCH (sub) WHERE sub.semantic_community = community
WITH community, node_count, internal_edges, external_edges, coherence_score,
     count(DISTINCT [l IN labels(sub) WHERE l <> 'GraphNode' | l][0]) AS label_diversity

// Collect sample node IDs (top 5, prioritizing nodes with embeddings)
OPTIONAL MATCH (sample) WHERE sample.semantic_community = community
WITH community, node_count, internal_edges, external_edges, coherence_score, label_diversity,
     sample, sample.embedding IS NOT NULL AS has_embedding
ORDER BY has_embedding DESC, sample.node_id
WITH community, node_count, internal_edges, external_edges, coherence_score, label_diversity,
     collect(sample.node_id)[0..5] AS sample_node_ids

// Return results sorted by coherence (best first), then by node count (largest first)
RETURN community AS community_id,
       node_count,
       internal_edges,
       external_edges,
       round(coherence_score * 1000) / 1000.0 AS coherence_score,
       label_diversity,
       sample_node_ids
ORDER BY coherence_score DESC, node_count DESC;
