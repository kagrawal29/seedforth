// @node_id: protocol-embed-dirty
// @label: "Identify dirty nodes for re-embedding (heal protocol for invariant-embedding-coverage)"
// ============================================================================
// Protocol: Identify Dirty Nodes for Embedding
// ============================================================================
// Returns node_ids of nodes that need re-embedding:
//   - embedding IS NULL (never embedded), OR
//   - embedding_for_leaf_hash <> leaf_hash (leaf changed since last embed)
//
// Phase B Merkle (merkle-properties.cypher) must run first to populate
// leaf_hash. This query is read-only — embedding is done by the Python sidecar.
//
// Excludes nodes without node_id and QueryTrace nodes (ephemeral).
// ============================================================================

MATCH (n)
WHERE n.node_id IS NOT NULL
  AND NOT n:QueryTrace
  AND n.leaf_hash IS NOT NULL
  AND (
    n.embedding IS NULL
    OR n.embedding_for_leaf_hash IS NULL
    OR n.embedding_for_leaf_hash <> n.leaf_hash
  )
RETURN n.node_id AS node_id,
       labels(n)[0] AS label,
       n.label AS name,
       n.description AS description,
       n.leaf_hash AS leaf_hash
ORDER BY n.node_id;
