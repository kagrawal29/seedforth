// @node_id: protocol-vocabulary-bridge
// @label: "Vocabulary Bridge"
// ============================================================================
// Protocol: Vocabulary Bridge
// ============================================================================
// Bridges high-frequency Word nodes to the semantic network by creating
// VOCABULARY_BRIDGE edges. This lets vocabulary patterns influence future
// vector search results without modifying the main search query.
//
// The gap problem: extract-vocabulary.py creates Word nodes on every ask,
// incrementing their frequency. But mycelium.sh lines 476-479 explicitly
// filters out Word nodes in vector search. So vocabulary accumulates but
// never helps retrieval.
//
// The solution: this protocol runs in the heartbeat. It:
// 1. Finds Word nodes with frequency > 3 (asked about multiple times)
// 2. For each high-frequency Word, searches Concept/Protocol/Guide nodes
//    whose names or descriptions contain that word (case-insensitive)
// 3. Creates VOCABULARY_BRIDGE edges with weight = word.frequency
// 4. This makes future searches hitting the Concept also register
//    the vocabulary signal (via 2-hop expansion)
//
// Side effects:
// - MERGE :VOCABULARY_BRIDGE edges (Word)-[:VOCABULARY_BRIDGE]->(Concept/Protocol/Guide)
// - ON CREATE: set weight = word.frequency, created_at
// - ON MATCH: increment bridge_count, update last_bridged_at
// - Returns summary: count of new bridges created
// ============================================================================

// Step 1 & 2: Find high-frequency Words and search for matches
MATCH (w:Word)
WHERE w.frequency >= 3 AND w.lemma IS NOT NULL
WITH w ORDER BY w.frequency DESC
WITH w
// Search for Concepts/Protocols/Guides containing this word
OPTIONAL MATCH (c:Concept)
WHERE (c.name IS NOT NULL AND toLower(c.name) CONTAINS toLower(w.lemma))
   OR (c.description IS NOT NULL AND toLower(c.description) CONTAINS toLower(w.lemma))
WITH w, collect(DISTINCT c) AS concept_matches

OPTIONAL MATCH (p:Protocol)
WHERE (p.name IS NOT NULL AND toLower(p.name) CONTAINS toLower(w.lemma))
   OR (p.label IS NOT NULL AND toLower(p.label) CONTAINS toLower(w.lemma))
   OR (p.description IS NOT NULL AND toLower(p.description) CONTAINS toLower(w.lemma))
WITH w, concept_matches, collect(DISTINCT p) AS protocol_matches

OPTIONAL MATCH (g:Guide)
WHERE (g.name IS NOT NULL AND toLower(g.name) CONTAINS toLower(w.lemma))
   OR (g.description IS NOT NULL AND toLower(g.description) CONTAINS toLower(w.lemma))
WITH w, concept_matches, protocol_matches, collect(DISTINCT g) AS guide_matches

// Step 3: Create bridges for all matched nodes
WITH w, concept_matches + protocol_matches + guide_matches AS all_matches
UNWIND (CASE WHEN size(all_matches) = 0 THEN [null] ELSE all_matches END) AS match_node
WITH w, match_node
WHERE match_node IS NOT NULL

MERGE (w)-[b:VOCABULARY_BRIDGE]->(match_node)
ON CREATE SET
  b.weight = w.frequency,
  b.created_at = toString(datetime()),
  b.bridge_count = 1,
  b.source = 'vocabulary-bridge-protocol'
ON MATCH SET
  b.bridge_count = coalesce(b.bridge_count, 0) + 1,
  b.last_bridged_at = toString(datetime()),
  b.weight = w.frequency

// Step 4: Return summary
WITH DISTINCT w, match_node, b
RETURN
  COUNT(DISTINCT b) AS total_bridges,
  COUNT(DISTINCT w) AS words_bridged,
  COUNT(DISTINCT match_node) AS targets_reached
LIMIT 1;
