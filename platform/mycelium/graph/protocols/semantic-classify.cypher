// @node_id: protocol-semantic-classify
// @label: "Semantic Classify"
// ============================================================================
// Protocol: Semantic Classify
// ============================================================================
// For every node with an embedding that is NOT already a :Concept, find
// the closest :Concept via the vector index and add a :SEEMS_LIKE edge.
// This is zero-shot classification — tagging every node with its best-
// fitting semantic category using only the embedding layer.
//
// Intent: "what kind of thing is this?" becomes a single graph query.
// MATCH (n {node_id: ...})-[:SEEMS_LIKE]->(c:Concept) tells you what
// the graph thinks this node is, without any human-labelled training data.
//
// Parameters:
//   min_similarity  float — only link if cosine >= this. Default 0.70.
//
// Side effects:
//   Creates :SEEMS_LIKE edges from every classifiable node to its top
//   Concept match. Edge carries cosine score.
//
// Dependencies: Neo4j vector index + APOC.
// ============================================================================

// Brute-force O(N × M) over the Concept set. Since Concepts are rare (~15
// of them) and every node has a 768d embedding already, direct pairwise
// cosine via Neo4j's built-in vector.similarity.cosine() is faster and
// more reliable than querying the vector index with top-K (where rare
// labels like Concept often miss the cut).

MATCH (c:Concept) WHERE c.embedding IS NOT NULL
WITH collect(c) AS concepts
MATCH (n:GraphNode)
WHERE n.embedding IS NOT NULL
  AND n.node_id IS NOT NULL
  AND NOT n:Concept
  AND NOT n:Guide
  AND NOT n:QueryTrace
  AND NOT n:Query
UNWIND concepts AS c
WITH n, c, vector.similarity.cosine(n.embedding, c.embedding) AS score
WHERE score >= 0.55
WITH n, c, score
ORDER BY n.node_id, score DESC
WITH n, collect({c: c, s: score}) AS ranked
WHERE size(ranked) > 0
WITH n, ranked[0].c AS best_concept, ranked[0].s AS best_score
MERGE (n)-[r:SEEMS_LIKE]->(best_concept)
ON CREATE SET r.cosine = best_score,
              r.classified_at = toString(datetime()),
              r.classifier = 'semantic-classify'
ON MATCH SET r.cosine = CASE WHEN best_score > coalesce(r.cosine, 0) THEN best_score ELSE r.cosine END,
             r.last_classified_at = toString(datetime());

MATCH ()-[r:SEEMS_LIKE]->(:Concept)
RETURN count(r) AS total_classifications;
