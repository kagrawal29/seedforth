// @kind: seed
// ============================================================================
// Protocol: Create HNSW Vector Index for Node Embeddings
// ============================================================================
// Creates a native Neo4j vector index (HNSW) over the `embedding` property.
// 768 dimensions to match nomic-embed-text output. Cosine similarity.
//
// Neo4j 5.x requires a label on vector indexes. embed-dirty.py adds the
// `GraphNode` secondary label to every node when writing embeddings. This
// label is purely structural — it does NOT change labels(n)[0], so Merkle
// root_hash remains stable.
//
// Idempotent: IF NOT EXISTS — safe to re-run.
//
// After running, verify with: SHOW INDEXES WHERE name = 'node_embeddings'
// ============================================================================

CREATE VECTOR INDEX node_embeddings IF NOT EXISTS
FOR (n:GraphNode)
ON n.embedding
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 768,
    `vector.similarity_function`: 'cosine'
  }
};
