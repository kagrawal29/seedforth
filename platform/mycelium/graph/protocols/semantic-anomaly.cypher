// @node_id: protocol-semantic-anomaly
// @label: "Semantic Anomaly"
// ============================================================================
// Protocol: Semantic Anomaly
// ============================================================================
// For every node with an embedding, find the top-K nearest neighbors. If
// the best neighbor cosine is BELOW a threshold, the node is a semantic
// outlier — it doesn't fit anywhere in the existing graph.
//
// Outliers are interesting. They're the nodes that:
//   - were imported from a source with different vocabulary
//   - were hand-authored with unusual content
//   - represent a concept the graph hasn't seen before
//   - might be stale or corrupted
//
// Tag them with :SemanticOutlier so operators can surface them:
//   MATCH (n:SemanticOutlier)
//   RETURN n.node_id, n.best_neighbor_score, n.best_neighbor_id
//
// Parameters:
//   min_fit  float — nodes below this cosine are outliers (default 0.55)
//   top_k    int   — how many neighbors to check per node (default 3)
//
// Side effects:
//   Adds :SemanticOutlier label + best_neighbor_score + best_neighbor_id
//   properties on outlier nodes. Idempotent — previous outlier tagging
//   is cleared first.
// ============================================================================

// --- Clear previous outlier tagging ----------------------------------------
MATCH (n:SemanticOutlier)
REMOVE n:SemanticOutlier, n.best_neighbor_score, n.best_neighbor_id;

WITH 0.55 AS min_fit, 3 AS top_k

// --- Find outliers ---------------------------------------------------------
MATCH (n:GraphNode)
WHERE n.embedding IS NOT NULL
  AND n.node_id IS NOT NULL
  AND NOT n:QueryTrace
  AND NOT n:Query
WITH n, min_fit, top_k
CALL db.index.vector.queryNodes('node_embeddings', top_k + 1, n.embedding)
  YIELD node AS neighbor, score
WHERE neighbor.node_id <> n.node_id
WITH n, min_fit, neighbor, score
ORDER BY n.node_id, score DESC
WITH n, min_fit, head(collect({nid: neighbor.node_id, s: score})) AS best
WHERE best.s < min_fit
SET n:SemanticOutlier,
    n.best_neighbor_score = best.s,
    n.best_neighbor_id = best.nid;

MATCH (n:SemanticOutlier)
RETURN count(n) AS outliers;
