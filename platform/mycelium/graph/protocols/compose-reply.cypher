// @node_id: protocol-compose-reply
// @label: "Compose Reply"
// ============================================================================
// Protocol: Compose Reply
// ============================================================================
// Cypher-native reply composition. Takes a prompt embedding as $qvec (list of
// 768 floats) and produces a natural-language sentence built by walking the
// semantic community around the best seed node.
//
// Pipeline:
//   1. Vector-search top seed node
//   2. Resolve the seed's semantic_community as the subgraph scope
//   3. For each :SwarmRole, find the best node in the subgraph matching the
//      role's preferred labels, scored by cosine to the prompt
//   4. Pairwise-clip fragments: drop any fragment whose cosine to the seed
//      is below 0.65 (prevents off-topic sprawl)
//   5. For each surviving fragment, resolve the connective phrase by walking
//      the typed edge back toward the seed
//   6. Stitch the fragments into a single sentence using apoc.text.join
//   7. MERGE a :Query node caching {prompt_embedding, sentence, fragments}
//      so the next similar prompt snaps straight to the cached reply
//
// Params:
//   $qvec          list<float>  — prompt embedding (required)
//   $min_cosine    float         — clip threshold (default 0.65)
//   $cache_prompt  string        — raw prompt text, for caching (optional)
//
// Returns:
//   sentence    the composed sentence
//   fragments   list of {role, node_id, kind, text, cosine}
//   seed_id     the top seed used as anchor
//   community   the semantic community scope
//   coherence   count of typed edges between returned fragments
// ============================================================================

// --- Step 1: top seed via ANN vector index ---------------------------------
CALL db.index.vector.queryNodes('node_embeddings', 5, $qvec)
YIELD node AS seed, score AS seed_score
WITH seed, seed_score ORDER BY seed_score DESC LIMIT 1
WITH seed, seed_score,
     coalesce(seed.semantic_community, seed.node_id) AS community

// --- Step 2: collect candidate nodes in the subgraph -----------------------
// "Subgraph" = every node sharing the seed's semantic_community AND having
// an embedding (so we can cosine-score them). Plus the seed itself.
OPTIONAL MATCH (sub)
WHERE sub.embedding IS NOT NULL
  AND sub.node_id IS NOT NULL
  AND (sub.semantic_community = community OR sub.node_id = seed.node_id)
WITH seed, seed_score, community, collect(DISTINCT sub) AS subgraph

// --- Step 3: for each SwarmRole, pick the best fragment in the subgraph ----
MATCH (role:SwarmRole)
WITH seed, seed_score, community, subgraph, role ORDER BY role.order
UNWIND subgraph AS node
WITH seed, seed_score, community, subgraph, role, node,
     vector.similarity.cosine($qvec, node.embedding) AS cos
// Filter: node must carry at least one of the role's preferred labels
WITH seed, seed_score, community, subgraph, role, node, cos,
     [lbl IN labels(node) WHERE lbl IN role.preferred_labels] AS matched_labels
WHERE size(matched_labels) > 0
WITH seed, seed_score, community, subgraph, role, node, cos
ORDER BY role.order, cos DESC
WITH seed, seed_score, community, subgraph, role,
     head(collect({n: node, cos: cos})) AS best
WHERE best IS NOT NULL AND best.cos >= coalesce($min_cosine, 0.65)

// --- Step 4: assemble the fragment list ------------------------------------
WITH seed, seed_score, community,
     collect({
       role: role.role,
       order: role.order,
       verb: role.verb,
       node_id: best.n.node_id,
       kind: head([l IN labels(best.n) WHERE l <> 'GraphNode']),
       text: replace(
         coalesce(best.n.description, best.n.explanation, best.n.content,
                  best.n.claim, best.n.semantic, best.n.label, best.n.name, ''),
         '\n', ' '
       ),
       cosine: round(best.cos * 1000) / 1000.0
     }) AS fragments

// --- Step 5: coherence score = count of typed edges BETWEEN fragments ------
// A tight reply has many internal edges; a loose one has few.
UNWIND fragments AS f
MATCH (n {node_id: f.node_id})
WITH seed, seed_score, community, fragments,
     collect(n) AS frag_nodes
UNWIND frag_nodes AS a
UNWIND frag_nodes AS b
OPTIONAL MATCH (a)-[r]-(b)
WHERE a.node_id < b.node_id
WITH seed, seed_score, community, fragments,
     count(DISTINCT r) AS coherence

// --- Step 6: stitch the sentence -------------------------------------------
// Compose clauses ordered by role.order. Each clause = verb + " " + text.
// Join with ". " between clauses. First clause gets "Mycelium" as the
// subject when the seed is a top-level concept; otherwise the seed's label.
WITH seed, seed_score, community, fragments, coherence,
     CASE
       WHEN seed:Concept OR seed:Subsystem
         THEN coalesce(seed.name, seed.label, seed.node_id)
       ELSE coalesce(seed.label, seed.name, seed.node_id)
     END AS subject

WITH seed, seed_score, community, fragments, coherence, subject,
     [f IN fragments WHERE f.text IS NOT NULL AND f.text <> '' |
       f.verb + ' ' + substring(f.text, 0, 220)] AS clauses

WITH seed, seed_score, community, fragments, coherence, subject,
     CASE
       WHEN size(clauses) = 0 THEN coalesce(seed.description, seed.explanation, seed.name, '(no data)')
       ELSE subject + ' ' + apoc.text.join(clauses, '. It ') + '.'
     END AS sentence

// --- Step 7: cache as :Query for Hebbian reinforcement ---------------------
// Next similar prompt hits this Query node first via the existing ask
// reranker — fire_count accumulates and the graph "remembers" its answer.
WITH seed, seed_score, community, fragments, coherence, sentence,
     'query-compose-' + replace(seed.node_id, '/', '-') AS query_id

MERGE (q:Query {node_id: query_id})
ON CREATE SET q.composed_at = toString(datetime()),
              q.fire_count = 1,
              q.seed_id = seed.node_id,
              q.community = community,
              q.sentence = sentence,
              q.coherence = coherence,
              q.fragment_count = size(fragments),
              q.file_type = 'composed-query'
ON MATCH SET q.fire_count = coalesce(q.fire_count, 0) + 1,
             q.last_fired_at = toString(datetime()),
             q.sentence = sentence,
             q.coherence = coherence

RETURN sentence,
       seed.node_id AS seed_id,
       community,
       coherence,
       size(fragments) AS fragment_count,
       fragments;
