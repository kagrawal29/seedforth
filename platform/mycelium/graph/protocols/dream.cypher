// @node_id: protocol-dream
// @label: "Dream"
// ============================================================================
// DREAM PROTOCOL — Nonlinear Deep Traversals
// Runs Tier 4 every 1000 ticks (~17 hours) during sleep
// The graph explores its own topology without a specific goal
// Finds bridges, mandalas, leaps, echoes, convergences
// ============================================================================

// ============================================================================
// SETUP: Seed the Rhythm node (idempotent)
// ============================================================================

MERGE (r:Rhythm {node_id: 'rhythm-dream'})
SET r.name = 'dream',
    r.cadence_type = 'deep',
    r.description = 'Nonlinear deep traversals during sleep. Finds bridges between communities, self-similar mandala patterns, semantic leaps, community echoes, and purpose convergences. The graph dreams about its own topology and surfaces insights it did not know it had.';

MATCH (p:Purpose {node_id: 'purpose-learn-from-use'})
MATCH (r:Rhythm {node_id: 'rhythm-dream'})
MERGE (r)-[:SERVES]->(p);

// ============================================================================
// MODE 1: Random Walk Discovery (Bridge Detection)
// Walk 5-7 hops through typed edges. If endpoints are in different communities,
// record as a bridge.
// ============================================================================

MATCH (start)
WHERE start.embedding IS NOT NULL AND rand() < 0.001
WITH start LIMIT 1
MATCH path = (start)-[*5..7]-(end)
WHERE end.semantic_community IS NOT NULL
  AND start.semantic_community IS NOT NULL
  AND end.semantic_community <> start.semantic_community
WITH start, end, length(path) AS hops,
     [n IN nodes(path) | n.node_id] AS path_nodes,
     [r IN relationships(path) | type(r)] AS edge_types
LIMIT 3
CREATE (d:DreamInsight {
  node_id: 'dream-bridge-' + toString(timestamp()),
  type: 'bridge',
  start_id: start.node_id,
  start_community: start.semantic_community,
  end_id: end.node_id,
  end_community: end.semantic_community,
  path_length: hops,
  path_nodes: path_nodes,
  edge_types_traversed: edge_types,
  dreamed_at: toString(datetime()),
  file_type: 'dream-insight'
});

// ============================================================================
// MODE 2: Pattern Repetition (Mandala Detection)
// Find nodes with identical outgoing edge signatures
// Two nodes are mandala-similar if they have the same set of edge types
// ============================================================================

MATCH (n)
WHERE n.node_id IS NOT NULL
OPTIONAL MATCH (n)-[r]->()
WITH n, apoc.coll.sort(collect(DISTINCT type(r))) AS edge_signature
WITH edge_signature, collect(n.node_id) AS members, count(n) AS cnt
WHERE cnt >= 3 AND size(edge_signature) >= 3
WITH edge_signature, members, cnt LIMIT 5
CREATE (d:DreamInsight {
  node_id: 'dream-mandala-' + toString(timestamp()) + '-' + toString(cnt),
  type: 'mandala',
  edge_signature: edge_signature,
  member_count: cnt,
  sample_members: members[0..5],
  all_members: members,
  dreamed_at: toString(datetime()),
  file_type: 'dream-insight'
});

// ============================================================================
// MODE 3: Semantic Leap (Structural Gap Detection)
// Find two nodes with high cosine similarity (> 0.8) but NO typed path
// within 3 hops. These "should" be connected but aren't.
// ============================================================================

MATCH (a)
WHERE a.embedding IS NOT NULL AND rand() < 0.005
WITH a LIMIT 10
MATCH (b)
WHERE b.embedding IS NOT NULL AND b.node_id <> a.node_id
WITH a, b, vector.similarity.cosine(a.embedding, b.embedding) AS sim
WHERE sim > 0.8
OPTIONAL MATCH (a)-[*1..3]-(b)
WITH a, b, sim, count(*) as path_count
WHERE path_count = 0
WITH a, b, sim LIMIT 3
CREATE (d:DreamInsight {
  node_id: 'dream-leap-' + toString(timestamp()),
  type: 'semantic-leap',
  node_a: a.node_id,
  node_a_label: labels(a)[0],
  node_b: b.node_id,
  node_b_label: labels(b)[0],
  similarity: round(sim * 1000) / 1000.0,
  gap_description: 'High semantic similarity (' + toString(round(sim * 100)) + '%) but no typed path within 3 hops',
  dreamed_at: toString(datetime()),
  file_type: 'dream-insight'
});

// ============================================================================
// MODE 4: Community Echo (Cross-Community Resonance)
// For each pair of communities, count INFERRED_SIMILAR bridges.
// High bridge count = communities "echo" each other
// ============================================================================

MATCH (a)-[r:INFERRED_SIMILAR]-(b)
WHERE a.semantic_community IS NOT NULL AND b.semantic_community IS NOT NULL
  AND a.semantic_community <> b.semantic_community
WITH a.semantic_community AS comm_a, b.semantic_community AS comm_b, count(r) AS bridges
WHERE bridges >= 5
WITH comm_a, comm_b, bridges
ORDER BY bridges DESC LIMIT 3
CREATE (d:DreamInsight {
  node_id: 'dream-echo-' + toString(timestamp()),
  type: 'community-echo',
  community_a: comm_a,
  community_b: comm_b,
  bridge_count: bridges,
  description: 'Communities talk about similar things from different angles',
  dreamed_at: toString(datetime()),
  file_type: 'dream-insight'
});

// ============================================================================
// MODE 5: Purpose Convergence (Multi-Purpose Identity)
// Check if multiple Purposes are being served by the SAME set of protocols.
// Convergence = two purposes sharing >30% of their evidence protocols.
// This reveals which purposes are actually the same thing viewed differently.
// ============================================================================

MATCH (p1:Purpose)<-[:EMBODIED_IN]-(proto:Protocol)
OPTIONAL MATCH (p2:Purpose)<-[:EMBODIED_IN]-(proto)
WHERE p1.node_id < p2.node_id
WITH p1, p2, count(DISTINCT proto) AS shared
WHERE p2 IS NOT NULL
OPTIONAL MATCH (p1)<-[:EMBODIED_IN]-(all1:Protocol)
WITH p1, p2, shared, count(all1) AS total1
OPTIONAL MATCH (p2)<-[:EMBODIED_IN]-(all2:Protocol)
WITH p1, p2, shared, total1, count(all2) AS total2
WITH p1, p2, shared, total1, total2,
     CASE WHEN (total1 + total2) > 0
          THEN toFloat(shared) / ((total1 + total2) / 2.0)
          ELSE 0.0 END AS convergence
WHERE convergence > 0.3
CREATE (d:DreamInsight {
  node_id: 'dream-convergence-' + toString(timestamp()),
  type: 'purpose-convergence',
  purpose_a: p1.node_id,
  purpose_a_label: p1.label,
  purpose_b: p2.node_id,
  purpose_b_label: p2.label,
  shared_protocols: shared,
  total_a: total1,
  total_b: total2,
  convergence_score: round(convergence * 1000) / 1000.0,
  interpretation: 'These purposes may be the same phenomenon viewed from different angles',
  dreamed_at: toString(datetime()),
  file_type: 'dream-insight'
});

// ============================================================================
// DREAM METABOLISM: Wire insights to the graph
// ============================================================================

// Wire each DreamInsight to the Ontology
MATCH (di:DreamInsight)
OPTIONAL MATCH (ont:Ontology)
WHERE NOT EXISTS { (di)-[:DREAMED_IN]->(ont) }
FOREACH (o IN CASE WHEN ont IS NOT NULL THEN [ont] ELSE [] END |
  CREATE (di)-[:DREAMED_IN]->(o)
);

// Wire bridges and leaps to purpose-dense-by-design
MATCH (di:DreamInsight)
WHERE di.type IN ['bridge', 'semantic-leap']
OPTIONAL MATCH (purpose:Purpose {node_id: 'purpose-dense-by-design'})
WHERE NOT EXISTS { (di)-[:DISCOVERED_BY]->(purpose) }
FOREACH (p IN CASE WHEN purpose IS NOT NULL THEN [purpose] ELSE [] END |
  CREATE (di)-[:DISCOVERED_BY]->(p)
);

// Wire mandalas to design-fractal-self-similarity
MATCH (di:DreamInsight {type: 'mandala'})
OPTIONAL MATCH (dp:DesignPrinciple {node_id: 'design-fractal-self-similarity'})
WHERE NOT EXISTS { (di)-[:EVIDENCE_OF]->(dp) }
FOREACH (d IN CASE WHEN dp IS NOT NULL THEN [dp] ELSE [] END |
  CREATE (di)-[:EVIDENCE_OF]->(d)
);

// ============================================================================
// FINAL: Report what was dreamed
// ============================================================================

MATCH (di:DreamInsight)
WITH di.type as type, count(di) as count
RETURN type, count
ORDER BY type DESC;
