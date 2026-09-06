// @node_id: protocol-semantic-densify
// @label: "Semantic Densify"
// ============================================================================
// Protocol: Semantic Densify
// ============================================================================
// Walks every node that has an embedding, queries the HNSW vector index for
// its top-K semantically-similar neighbors, and MERGEs INFERRED_SIMILAR
// edges with the cosine score as a property.
//
// Intent: combat graph sparsity. A freshly-ingested graph has ~1.3 edges
// per node because bulk-ingesters drop nodes without investing in
// connections. This protocol uses the embedding layer (Phase 1.7) to
// synthesize edges between semantically-close nodes at scale, lifting
// density closer to 5-10 e/n without human labeling.
//
// Parameters (via --param):
//   top_k              integer  — number of neighbors per node. Default 5.
//   min_similarity     float    — cosine threshold; skip pairs below this.
//                                  Default 0.82 (nomic-embed-text runs hot,
//                                  anything above ~0.85 is tight semantic
//                                  kinship, 0.80-0.85 is "same topic").
//   only_orphans       boolean  — if true, only densify nodes whose current
//                                  degree = 0. Useful for incremental runs.
//                                  Default false.
//
// Edge shape:
//   (n)-[:INFERRED_SIMILAR {
//     cosine,
//     algorithm: 'nomic-embed-text',
//     inferred_at,
//     inferred_by: 'semantic-densify.cypher'
//   }]->(m)
//
// Idempotent: MERGE on (n, m, INFERRED_SIMILAR). Re-running updates
// `cosine` + `inferred_at`, doesn't duplicate edges.
//
// Chain-layer note: INFERRED_SIMILAR is DERIVED state, not structural
// content. We do NOT exclude it from the merkle hash — adding an inferred
// edge IS a meaningful state change. But the protocol runs deterministically:
// same embeddings + same threshold → same edges. So running densify twice
// in a row produces no new edges and leaves root_hash stable.
//
// Dependencies: APOC (apoc.util.sha256 not needed here, but apoc is loaded
// for other protocols). Requires the :GraphNode vector index
// `node_embeddings` to exist (created by embed-index-init.cypher).
// ============================================================================

// Parameter defaults (cypher-shell --param can override)
WITH
  coalesce($top_k, 5) AS top_k,
  coalesce($min_similarity, 0.82) AS min_sim,
  coalesce($only_orphans, false) AS only_orphans

// --- Step 1: pick the candidate source nodes --------------------------------
MATCH (n:GraphNode)
WHERE n.embedding IS NOT NULL
  AND (only_orphans = false OR COUNT { (n)--() } = 0)
WITH top_k, min_sim, collect(n) AS sources


// --- Step 2: for each source, query the HNSW index for K+1 neighbors --------
// K+1 because the index returns the source itself as the top hit (similarity
// 1.0) — we skip it.
UNWIND sources AS n
CALL db.index.vector.queryNodes('node_embeddings', top_k + 1, n.embedding)
  YIELD node AS m, score
WHERE m.node_id IS NOT NULL
  AND m.node_id <> n.node_id
  AND score >= min_sim
WITH n, m, score, min_sim


// --- Step 3: MERGE the inferred edge ---------------------------------------
// Direction is arbitrary for a symmetric similarity relation — we use
// alphabetically-lower node_id as source to keep the edge canonical and
// avoid duplicate bidirectional edges.
WITH
  CASE WHEN n.node_id < m.node_id THEN n ELSE m END AS a,
  CASE WHEN n.node_id < m.node_id THEN m ELSE n END AS b,
  score
MERGE (a)-[r:INFERRED_SIMILAR]->(b)
ON CREATE SET
  r.cosine = score,
  r.algorithm = 'nomic-embed-text',
  r.inferred_at = toString(datetime()),
  r.inferred_by = 'semantic-densify.cypher',
  r.edge_type = 'semantic'
ON MATCH SET
  r.cosine = CASE WHEN score > coalesce(r.cosine, 0) THEN score ELSE r.cosine END,
  r.last_seen = toString(datetime())


// --- Step 4: summary --------------------------------------------------------
WITH count(*) AS total_pairs_considered
MATCH ()-[r:INFERRED_SIMILAR]->()
RETURN total_pairs_considered,
       count(DISTINCT r) AS inferred_edges_total;
