// @node_id: protocol-vocabulary-boost
// @label: "Vocabulary Boost"
// ============================================================================
// Protocol: Vocabulary Boost
// ============================================================================
// Strengthens semantic clustering by connecting Prompt nodes that share
// high-frequency Words, even if their embeddings are not similar. This
// creates INFERRED_SIMILAR edges based on vocabulary overlap.
//
// The insight: two semantically different prompts that ask about the same
// vocabulary domains should be loosely connected. When one is asked again,
// the vocabulary link can surface the other as a related question.
//
// Algorithm:
// 1. Find all Prompt nodes
// 2. For each pair of Prompts, count shared Word nodes (via CONTAINS edges)
// 3. If they share 3+ Words AND have no existing INFERRED_SIMILAR edge,
//    create one with low initial weight (0.3)
// 4. This is lightweight compared to embedding similarity but more robust
//    for vocabulary-driven clustering
//
// Side effects:
// - MERGE :INFERRED_SIMILAR edges between Prompt pairs
// - Weight = 0.3 (low confidence, vocabulary-based, not embedding-based)
// - inference_source = 'vocabulary-overlap'
// - shared_word_count = number of common Words
// - Returns summary: count of new inference edges created
// ============================================================================

// Step 1: For each Prompt, collect its Word nodes
MATCH (p1:Prompt)-[:CONTAINS]->(w:Word)
WITH p1, collect(DISTINCT w) AS words1, count(DISTINCT w) AS word_count1
WHERE word_count1 >= 2  // Only consider prompts with 2+ words

// Step 2: Find other Prompts and count shared Words
WITH p1, words1
MATCH (p2:Prompt)-[:CONTAINS]->(w:Word)
WHERE p2.node_id > p1.node_id  // Avoid duplicate pairs
  AND w IN words1
WITH p1, p2, words1, collect(DISTINCT w) AS shared_words
WHERE size(shared_words) >= 3  // Only if 3+ words in common

// Step 3: Check if an INFERRED_SIMILAR edge already exists
WITH p1, p2, shared_words
OPTIONAL MATCH (p1)-[existing:INFERRED_SIMILAR]-(p2)
WHERE existing IS NULL  // Only if no edge already exists

// Step 4: Create low-confidence INFERRED_SIMILAR edge
WITH p1, p2, shared_words
WHERE existing IS NULL
MERGE (p1)-[sim:INFERRED_SIMILAR]-(p2)
ON CREATE SET
  sim.weight = 0.3,
  sim.inference_source = 'vocabulary-overlap',
  sim.shared_word_count = size(shared_words),
  sim.created_at = toString(datetime()),
  sim.walk_count = 0,
  sim.last_walked_at = timestamp()
ON MATCH SET
  sim.shared_word_count = size(shared_words),
  sim.last_updated_at = toString(datetime())

// Step 5: Return summary
WITH DISTINCT sim, p1, p2, shared_words
RETURN
  COUNT(DISTINCT sim) AS new_inference_edges,
  COLLECT(size(shared_words)) AS shared_word_counts,
  MIN(size(shared_words)) AS min_shared_words,
  MAX(size(shared_words)) AS max_shared_words,
  ROUND(AVG(size(shared_words))) AS avg_shared_words
LIMIT 1;
