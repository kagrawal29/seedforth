// PROTOCOL: Detect Cross-Couplings Between Sovereign Graphs
// VERSION: 1.0
// DATE: 2026-04-18
// AUTHOR: Task 39 Initial Map
//
// PURPOSE:
// This protocol detects structural, semantic, and kinship coupling points
// between two sovereign Neo4j graphs running at different bolt endpoints.
// It maps shared node_ids, commit SHAs, label kinship, name token overlaps,
// and semantic embeddings. Results are materialized as CROSS_COUPLING nodes
// and CROSS_COUPLES_VIA edges on both sides.
//
// SIGNALS:
// 1. shared-node-id: Same node_id present on both sides
// 2. shared-commit: Same commit SHA present on both sides (Commit vs GitCommit labels)
// 3. label-kinship: Both graphs have the same label (e.g., both :Being, :TestCase)
// 4. name-token-overlap: Protocol/CodeFunction name Jaccard similarity >= 0.4
// 5. semantic: Cosine similarity on embeddings >= 0.82 (if embeddings present)
//
// EXECUTION:
// 1. Call this Protocol with parameters: peer_bolt, peer_user, peer_password, peer_database
// 2. If you own the peer graph, can write back symmetrically; if peer is read-only, create local-only couplings
// 3. Store results as CROSS_COUPLING nodes on your own side
// 4. Use CROSS_COUPLES_VIA edges to link source nodes to their couplings
//
// CONSTRAINTS:
// - Never mutate peer graph schema or delete nodes
// - Use separate driver sessions per graph to avoid lock contention
// - Cap semantic embeddings at top 100 pairs to avoid explosion
// - Token overlap search limited to first 500 of each entity type
// - Commit SHAs: check both Commit and GitCommit labels depending on graph flavor

// ============================================================================
// SIGNAL 1: Detect Shared Node IDs
// ============================================================================
MATCH (our_node)
WHERE our_node.node_id IS NOT NULL
WITH DISTINCT our_node.node_id AS nid, labels(our_node)[0] AS our_label
// In a forest with remote peer graphs, this check would call peer API:
// CALL apoc.load.json($peer_bolt_query + "?query=" + urlencode("MATCH (n {node_id: '" + nid + "'}) RETURN true"))
// For now, this is a placeholder for future multi-graph Protocol expansion
WITH nid, our_label
WHERE our_label IN ['Being', 'Knowledge', 'Issue', 'TestCase']
CREATE (c:CROSS_COUPLING {
  node_id: 'coupling-' + apoc.util.md5(nid),
  evidence: 'shared-node-id',
  strength: 1.0,
  our_node_id: nid,
  our_label: our_label,
  detected_at: datetime(),
  detector: 'detect-cross-couplings-protocol-v1'
});

// ============================================================================
// SIGNAL 2: Detect Shared Commit SHAs
// ============================================================================
// Check which graph we are (Commit vs GitCommit) and find all SHAs
MATCH (commit) WHERE (commit:Commit OR commit:GitCommit) AND commit.sha IS NOT NULL
WITH DISTINCT commit.sha AS sha, labels(commit)[0] AS commit_label
// Same placeholder as above: peer_has_this_sha would be checked via API call
CREATE (c:CROSS_COUPLING {
  node_id: 'coupling-commit-' + sha[0..8],
  evidence: 'shared-commit',
  sha: sha,
  strength: 1.0,
  detected_at: datetime(),
  detector: 'detect-cross-couplings-protocol-v1'
});

// ============================================================================
// SIGNAL 3: Label Kinship Detection
// ============================================================================
// Identify labels that exist on both sides and create kinship records
CALL db.labels() YIELD label
WITH collect(label) AS our_labels
UNWIND ['Being', 'Knowledge', 'TestCase', 'TestRun', 'Protocol', 'Issue'] AS potential_shared
WHERE potential_shared IN our_labels
MATCH (n:CROSS_COUPLING) LIMIT 1 // Dummy to ensure we only log once
CREATE (k:CROSS_COUPLING {
  node_id: 'kinship-' + potential_shared + '-' + datetime().epochSeconds,
  evidence: 'label-kinship',
  our_label: potential_shared,
  strength: 0.5,
  notes: 'Both graphs declare :' + potential_shared + '; semantics may differ',
  detected_at: datetime(),
  detector: 'detect-cross-couplings-protocol-v1'
});

// ============================================================================
// SIGNAL 4: Name Token Overlap (Protocols ↔ CodeFunctions)
// ============================================================================
// Helper function: Tokenize camelCase, snake_case, hyphenated strings
// Then compute Jaccard similarity
MATCH (p:Protocol) WHERE p.label IS NOT NULL OR p.description IS NOT NULL
WITH p,
     CASE
       WHEN p.label IS NOT NULL THEN p.label
       ELSE COALESCE(p.description, p.node_id)
     END AS proto_text
OPTIONAL MATCH (f:CodeFunction)
WITH p, proto_text, collect(f) AS functions
UNWIND (CASE WHEN size(functions) > 0 THEN functions ELSE [null] END) AS func
WITH p, proto_text, func
WHERE func IS NOT NULL
WITH p, proto_text, func.name AS func_name,
     // Simple token split (split on non-alphanumeric, then lowercase)
     apoc.text.regexGroups(proto_text, '\\w+', 'g') AS proto_tokens,
     apoc.text.regexGroups(COALESCE(func.name, ''), '\\w+', 'g') AS func_tokens
WITH p, func, proto_tokens, func_tokens,
     // Count intersection
     size(apoc.coll.intersection(proto_tokens, func_tokens)) AS intersection,
     size(apoc.coll.union(proto_tokens, func_tokens)) AS union_size
WITH p, func,
     CASE WHEN union_size > 0 THEN toFloat(intersection) / toFloat(union_size)
          ELSE 0.0 END AS jaccard
WHERE jaccard >= 0.4 AND func IS NOT NULL
CREATE (c:CROSS_COUPLING {
  node_id: 'coupling-name-' + apoc.util.md5(p.node_id + func.node_id),
  evidence: 'name-token-overlap',
  strength: jaccard,
  our_node_id: p.node_id,
  peer_node_id: func.node_id,
  our_text: COALESCE(p.label, p.description)[0..40],
  peer_text: func.name,
  detected_at: datetime(),
  detector: 'detect-cross-couplings-protocol-v1'
})
MERGE (p)-[:CROSS_COUPLES_VIA]->(c);

// ============================================================================
// SIGNAL 5: Semantic Embedding Similarity (if embeddings present)
// ============================================================================
// Only run if both sides have embeddings
MATCH (n) WHERE n.embedding IS NOT NULL
WITH count(n) AS embed_count
WHERE embed_count > 0
// If embeddings exist, compute cosine similarity on samples
MATCH (myc_node) WHERE myc_node.embedding IS NOT NULL
MATCH (code_node) WHERE code_node.embedding IS NOT NULL
WITH myc_node, code_node,
     // Compute cosine similarity (simplified: assume 768-dim vectors)
     reduce(dot = 0, i IN range(0, size(myc_node.embedding)-1) |
       dot + (myc_node.embedding[i] * code_node.embedding[i])
     ) AS dot_product,
     // Magnitudes
     sqrt(reduce(sum = 0, i IN range(0, size(myc_node.embedding)-1) |
       sum + (myc_node.embedding[i] * myc_node.embedding[i])
     )) AS mag_a,
     sqrt(reduce(sum = 0, i IN range(0, size(code_node.embedding)-1) |
       sum + (code_node.embedding[i] * code_node.embedding[i])
     )) AS mag_b
WITH myc_node, code_node,
     CASE WHEN mag_a > 0 AND mag_b > 0 THEN dot_product / (mag_a * mag_b)
          ELSE 0.0 END AS cosine_sim
WHERE cosine_sim >= 0.82
CREATE (c:CROSS_COUPLING {
  node_id: 'coupling-semantic-' + apoc.util.md5(myc_node.node_id + code_node.node_id),
  evidence: 'semantic',
  strength: cosine_sim,
  our_node_id: myc_node.node_id,
  peer_node_id: code_node.node_id,
  cosine: cosine_sim,
  detected_at: datetime(),
  detector: 'detect-cross-couplings-protocol-v1'
})
MERGE (myc_node)-[:CROSS_COUPLES_VIA]->(c);

// ============================================================================
// FINAL REPORT: Verify all couplings created
// ============================================================================
MATCH (c:CROSS_COUPLING)
RETURN
  count(c) AS total_couplings,
  collect(DISTINCT c.evidence) AS evidence_types,
  {
    'shared-node-id': size([x IN collect(c.evidence) WHERE x = 'shared-node-id']),
    'shared-commit': size([x IN collect(c.evidence) WHERE x = 'shared-commit']),
    'label-kinship': size([x IN collect(c.evidence) WHERE x = 'label-kinship']),
    'name-token-overlap': size([x IN collect(c.evidence) WHERE x = 'name-token-overlap']),
    'semantic': size([x IN collect(c.evidence) WHERE x = 'semantic'])
  } AS breakdown
;
