// @node_id: protocol-compose-nuanced
// @label: "Compose Nuanced"
// ============================================================================
// Protocol: Compose Nuanced
// ============================================================================
// 3-pass embedding composition producing nuanced, semantic replies via embedding
// arithmetic. Transforms single-pass factual retrieval into multi-perspective
// responses by computing centroids and anti-centroids of fragment embeddings.
//
// Pipeline:
//   PASS 1 — Factual Retrieval (what the graph knows)
//     - Vector-search top 5 seed nodes from prompt embedding $qvec
//     - For each seed, walk 2-hop typed edges collecting fragments across
//       all roles (Concept, Metaphor, Protocol, DesignPrinciple, Guide, Feature)
//     - Collect fragment embeddings + descriptions
//
//   PASS 2 — Centroid Blending (what the graph implies)
//     - Compute CENTROID of all Pass 1 fragment embeddings using reduce over
//       768 dimensions
//     - Vector-search centroid against node_embeddings index, top 5
//     - Filter out nodes already found in Pass 1 (seek NEW discoveries)
//     - These "blend nodes" sit at the semantic intersection of multiple concepts
//
//   PASS 3 — Dialectical Feedback (what the graph challenges)
//     - Compute ANTI-CENTROID by reflecting centroid across original prompt:
//       anti_centroid[i] = 2.0 * $qvec[i] - centroid[i]
//     - Vector-search anti-centroid, top 3
//     - These nodes are conceptually OPPOSITE but still related to prompt
//     - If cosine > 0.5 to the prompt, include as "however" clauses
//
//   Stitching:
//     [Pass 1 definition]. [Pass 1 metaphor]. [Pass 1 mechanism].
//     This connects to [Pass 2 blend 1 description] and [Pass 2 blend 2 description].
//     Though note: [Pass 3 counterpoint 1 description].
//
// Params:
//   $qvec          list<float>  — prompt embedding, 768 dims (required)
//   $min_cosine    float         — clip threshold (default 0.60)
//   $cache_prompt  string        — raw prompt text, for caching (optional)
//
// Returns:
//   factual_sentence     text from Pass 1 stitched together
//   inferential_sentence text from Pass 2 blend nodes
//   dialectical_sentence text from Pass 3 counterpoints (may be empty)
//   full_response        all three sentences composed
//   fragment_count       number of nodes contributing to final response
//   coherence_score      count of typed edges between all returned nodes
//   confidence_tier      'high' | 'medium' | 'low' based on average cosine
//   centroid_computed    time taken to compute centroid (ms)
// ============================================================================

// ============================================================================
// PASS 1: Factual Retrieval
// ============================================================================

CALL db.index.vector.queryNodes('node_embeddings', 5, $qvec)
YIELD node AS seed, score AS seed_score
WITH seed, seed_score ORDER BY seed_score DESC LIMIT 1
WITH seed, seed_score,
     coalesce(seed.semantic_community, seed.node_id) AS community,
     datetime() AS pass1_start

// Collect all nodes in the subgraph (semantic community + seed itself)
OPTIONAL MATCH (sub)
WHERE sub.embedding IS NOT NULL
  AND sub.node_id IS NOT NULL
  AND (sub.semantic_community = community OR sub.node_id = seed.node_id)
WITH seed, seed_score, community, pass1_start, collect(DISTINCT sub) AS subgraph

// For each SwarmRole, pick the best fragment in the subgraph
MATCH (role:SwarmRole)
WITH seed, seed_score, community, pass1_start, subgraph, role ORDER BY role.order
UNWIND subgraph AS node
WITH seed, seed_score, community, pass1_start, subgraph, role, node,
     vector.similarity.cosine($qvec, node.embedding) AS cos
WHERE size([lbl IN labels(node) WHERE lbl IN role.preferred_labels]) > 0
WITH seed, seed_score, community, pass1_start, subgraph, role, node, cos
ORDER BY role.order, cos DESC
WITH seed, seed_score, community, pass1_start, subgraph, role,
     head(collect({n: node, cos: cos})) AS best
WHERE best IS NOT NULL AND best.cos >= coalesce($min_cosine, 0.60)

// Assemble Pass 1 fragments
WITH seed, seed_score, community, pass1_start,
     collect({
       role: role.role,
       node_id: best.n.node_id,
       kind: head([l IN labels(best.n) WHERE l <> 'GraphNode']),
       text: replace(
         coalesce(best.n.description, best.n.explanation, best.n.content,
                  best.n.claim, best.n.semantic, best.n.label, best.n.name, ''),
         '\n', ' '
       ),
       cosine: round(best.cos * 1000) / 1000.0,
       embedding: best.n.embedding
     }) AS pass1_fragments

// Collect embeddings from Pass 1 fragments for centroid computation
WITH seed, seed_score, community, pass1_start,
     pass1_fragments,
     [f IN pass1_fragments WHERE f.embedding IS NOT NULL | f.embedding] AS pass1_embeddings

// Bail out if < 2 fragments — can't compute meaningful centroid
WHERE size(pass1_embeddings) >= 2

// ============================================================================
// PASS 2: Centroid Blending (compute semantic center of all fragments)
// ============================================================================

WITH seed, seed_score, community, pass1_start, pass1_fragments, pass1_embeddings,
     datetime() AS centroid_start

// Compute centroid: average across all 768 dimensions
// centroid[i] = sum(embedding[i] for all embeddings) / count(embeddings)
WITH seed, seed_score, community, pass1_start, pass1_fragments, pass1_embeddings,
     centroid_start,
     [i IN range(0, 767) |
       CASE
         WHEN size(pass1_embeddings) = 0 THEN 0.0
         ELSE reduce(s = 0.0, emb IN pass1_embeddings | s + emb[i]) / size(pass1_embeddings)
       END
     ] AS centroid

WITH seed, seed_score, community, pass1_start, pass1_fragments,
     centroid,
     centroid_start,
     datetime() AS centroid_end,
     duration.inSeconds(centroid_start, centroid_end).milliseconds AS centroid_ms

// Vector-search with the centroid
CALL db.index.vector.queryNodes('node_embeddings', 5, centroid)
YIELD node AS blend_node, score AS blend_score
WITH seed, seed_score, community, pass1_start, pass1_fragments, centroid, centroid_ms,
     blend_node, blend_score, [f IN pass1_fragments | f.node_id] AS pass1_ids
WHERE NOT blend_node.node_id IN pass1_ids
WITH seed, seed_score, community, pass1_start, pass1_fragments, centroid, centroid_ms,
     collect({
       node_id: blend_node.node_id,
       kind: head([l IN labels(blend_node) WHERE l <> 'GraphNode']),
       text: replace(
         coalesce(blend_node.description, blend_node.explanation, blend_node.content,
                  blend_node.claim, blend_node.semantic, blend_node.label, blend_node.name, ''),
         '\n', ' '
       ),
       cosine: round(blend_score * 1000) / 1000.0,
       embedding: blend_node.embedding
     }) AS pass2_fragments

// ============================================================================
// PASS 3: Dialectical Feedback (compute anti-centroid for counterpoints)
// ============================================================================

// Compute anti-centroid = reflection of centroid across the prompt vector
// anti_centroid[i] = 2.0 * prompt_vector[i] - centroid[i]
WITH seed, seed_score, community, pass1_start, pass1_fragments, pass2_fragments,
     centroid, centroid_ms,
     [i IN range(0, 767) |
       2.0 * $qvec[i] - centroid[i]
     ] AS anti_centroid

// Vector-search with the anti-centroid
CALL db.index.vector.queryNodes('node_embeddings', 3, anti_centroid)
YIELD node AS anti_node, score AS anti_score
WITH seed, seed_score, community, pass1_start, pass1_fragments, pass2_fragments,
     centroid, centroid_ms, anti_node, anti_score,
     [f IN pass1_fragments | f.node_id] AS pass1_ids,
     [f IN pass2_fragments | f.node_id] AS pass2_ids
WHERE NOT anti_node.node_id IN pass1_ids
  AND NOT anti_node.node_id IN pass2_ids
  AND vector.similarity.cosine($qvec, anti_node.embedding) > 0.5
WITH seed, seed_score, community, pass1_start, pass1_fragments, pass2_fragments,
     centroid, centroid_ms,
     collect({
       node_id: anti_node.node_id,
       kind: head([l IN labels(anti_node) WHERE l <> 'GraphNode']),
       text: replace(
         coalesce(anti_node.description, anti_node.explanation, anti_node.content,
                  anti_node.claim, anti_node.semantic, anti_node.label, anti_node.name, ''),
         '\n', ' '
       ),
       cosine: round(vector.similarity.cosine($qvec, anti_node.embedding) * 1000) / 1000.0
     }) AS pass3_fragments

// ============================================================================
// Stitch Passes into Natural Language
// ============================================================================

// Pass 1: Factual sentence
WITH seed, seed_score, community, pass1_fragments, pass2_fragments, pass3_fragments,
     centroid_ms,
     [f IN pass1_fragments WHERE f.text IS NOT NULL AND f.text <> '' |
       f.text] AS pass1_texts

WITH seed, seed_score, community, pass1_fragments, pass2_fragments, pass3_fragments,
     centroid_ms, pass1_texts,
     CASE
       WHEN size(pass1_texts) = 0 THEN coalesce(seed.description, seed.explanation, seed.name, '(no data)')
       ELSE apoc.text.join(pass1_texts, '. ') + '.'
     END AS factual_sentence

// Pass 2: Inferential sentence
WITH seed, seed_score, community, pass1_fragments, pass2_fragments, pass3_fragments,
     centroid_ms, factual_sentence,
     [f IN pass2_fragments WHERE f.text IS NOT NULL AND f.text <> '' |
       f.text] AS pass2_texts

WITH seed, seed_score, community, pass1_fragments, pass2_fragments, pass3_fragments,
     centroid_ms, factual_sentence,
     CASE
       WHEN size(pass2_texts) = 0 THEN ''
       WHEN size(pass2_texts) = 1 THEN 'This connects to ' + pass2_texts[0] + '.'
       ELSE 'This connects to ' + apoc.text.join(pass2_texts, ' and ') + '.'
     END AS inferential_sentence

// Pass 3: Dialectical sentence
WITH seed, seed_score, community, pass1_fragments, pass2_fragments, pass3_fragments,
     centroid_ms, factual_sentence, inferential_sentence,
     [f IN pass3_fragments WHERE f.text IS NOT NULL AND f.text <> '' |
       f.text] AS pass3_texts

WITH seed, seed_score, community, pass1_fragments, pass2_fragments, pass3_fragments,
     centroid_ms, factual_sentence, inferential_sentence,
     CASE
       WHEN size(pass3_texts) = 0 THEN ''
       WHEN size(pass3_texts) = 1 THEN 'Though note: ' + pass3_texts[0] + '.'
       ELSE 'Though note: ' + apoc.text.join(pass3_texts, '; ') + '.'
     END AS dialectical_sentence

// Full response
WITH seed, seed_score, community, pass1_fragments, pass2_fragments, pass3_fragments,
     centroid_ms, factual_sentence, inferential_sentence, dialectical_sentence,
     apoc.text.join(
       [s IN [factual_sentence, inferential_sentence, dialectical_sentence] WHERE s <> ''],
       ' '
     ) AS full_response

// ============================================================================
// Coherence Score & Confidence Tier
// ============================================================================

// Collect all node IDs from all passes
UNWIND pass1_fragments AS f1
WITH seed, seed_score, community, factual_sentence, inferential_sentence, dialectical_sentence,
     full_response, centroid_ms, pass2_fragments, pass3_fragments,
     collect(DISTINCT f1.node_id) +
     [f IN pass2_fragments | f.node_id] +
     [f IN pass3_fragments | f.node_id] AS all_node_ids

// Count edges between all returned nodes
WITH seed, seed_score, community, factual_sentence, inferential_sentence, dialectical_sentence,
     full_response, centroid_ms, all_node_ids,
     size(all_node_ids) AS fragment_count

UNWIND all_node_ids AS id1
UNWIND all_node_ids AS id2
OPTIONAL MATCH (n1 {node_id: id1})-[r]-(n2 {node_id: id2})
WHERE id1 < id2
WITH seed, seed_score, community, factual_sentence, inferential_sentence, dialectical_sentence,
     full_response, centroid_ms, fragment_count,
     count(DISTINCT r) AS coherence_score

// Compute average cosine across all fragments (confidence metric)
WITH seed, seed_score, community, factual_sentence, inferential_sentence, dialectical_sentence,
     full_response, centroid_ms, fragment_count, coherence_score

UNWIND [f IN [p1 IN pass1_fragments | p1.cosine] WHERE f IS NOT NULL | f] AS c1
WITH seed, seed_score, community, factual_sentence, inferential_sentence, dialectical_sentence,
     full_response, centroid_ms, fragment_count, coherence_score,
     collect(c1) +
     [f IN pass2_fragments | f.cosine] +
     [f IN pass3_fragments | f.cosine] AS all_cosines

WITH seed, seed_score, community, factual_sentence, inferential_sentence, dialectical_sentence,
     full_response, centroid_ms, fragment_count, coherence_score,
     CASE size(all_cosines)
       WHEN 0 THEN 0.0
       ELSE reduce(s = 0.0, c IN all_cosines | s + c) / size(all_cosines)
     END AS avg_cosine

// Confidence tier based on average cosine
WITH seed, seed_score, community, factual_sentence, inferential_sentence, dialectical_sentence,
     full_response, centroid_ms, fragment_count, coherence_score, avg_cosine,
     CASE
       WHEN avg_cosine >= 0.80 THEN 'high'
       WHEN avg_cosine >= 0.65 THEN 'medium'
       ELSE 'low'
     END AS confidence_tier

// ============================================================================
// Cache as :ComposedResponse for Hebbian reuse
// ============================================================================

MERGE (cr:ComposedResponse {
  node_id: 'composed-response-' + replace(seed.node_id, '/', '-') + '-nuanced'
})
ON CREATE SET cr.created_at = toString(datetime()),
              cr.fire_count = 1,
              cr.seed_id = seed.node_id,
              cr.community = community,
              cr.full_response = full_response,
              cr.factual_sentence = factual_sentence,
              cr.inferential_sentence = inferential_sentence,
              cr.dialectical_sentence = dialectical_sentence,
              cr.fragment_count = fragment_count,
              cr.coherence_score = coherence_score,
              cr.confidence_tier = confidence_tier,
              cr.centroid_ms = centroid_ms,
              cr.avg_cosine = round(avg_cosine * 1000) / 1000.0,
              cr.file_type = 'composed-response',
              cr.protocol = 'compose-nuanced'
ON MATCH SET cr.fire_count = coalesce(cr.fire_count, 0) + 1,
             cr.last_fired_at = toString(datetime()),
             cr.full_response = full_response,
             cr.centroid_ms = centroid_ms

RETURN full_response,
       factual_sentence,
       inferential_sentence,
       dialectical_sentence,
       fragment_count,
       coherence_score,
       confidence_tier,
       centroid_ms,
       round(seed_score * 1000) / 1000.0 AS seed_cosine,
       round(avg_cosine * 1000) / 1000.0 AS avg_fragment_cosine;
