// @node_id: protocol-prompt-ingest
// @label: "Prompt Ingest"
// ============================================================================
// Protocol: Prompt Ingest
// ============================================================================
// Forward hot path. Called on every NL prompt entering the CLI BEFORE the
// retrieval/dispatch layer runs its own work. Mints or strengthens a
// :Prompt node and wires it to the nodes it touches.
//
// Parameters:
//   $prompt_text   string          raw prompt as typed
//   $embedding     list<float>     the prompt embedding (same one used for
//                                   downstream vector search — we store it
//                                   so the :Prompt joins the shared vector
//                                   index and becomes retrievable itself)
//   $source        string          'cli' | 'script' | 'subagent' | 'swarm'
//   $command       string          'ask' | 'swarm' | 'q' | etc.
//   $tokens        list<map>       [{lemma, surface, position}, ...] from
//                                   extract-vocabulary.py (can be empty if
//                                   tokenizer not available; gracefully
//                                   degrades to no :Word linkage)
//   $resolved_id   string          node_id of the top resolved result
//                                   ('' if nothing matched)
//   $resolved_score float          cosine of top match (0.0 if no resolve)
//
// Side effects:
//   1. MERGE :Prompt node keyed by text_hash. Set embedding + increment
//      fire_count on repeat.
//   2. For each non-stopword token, MERGE :Word + create :CONTAINS edge.
//      Increment word frequency.
//   3. Wire :BIGRAM edges between adjacent non-stopword words.
//   4. If $resolved_id is set, MERGE :RESOLVED_TO edge with {cosine, rank=1}.
//   5. Create a lightweight :Activation node for this prompt firing and
//      wire :THEN edges to any Activation in the last 300 seconds (5 min
//      window) so the temporal sequence layer builds up.
//   6. Hebbian: all edges use MERGE + ON MATCH increment — repeat observations
//      strengthen counts.
//
// Runs fast (<50ms typical) so CLI latency stays under the user's noticing.
// ============================================================================


// --- Step 1: MERGE the :Prompt node ----------------------------------------
// Key by text hash so identical prompts collapse. Store the embedding so
// the node lives in the shared vector index.

WITH $prompt_text AS text, $embedding AS emb, $source AS source,
     $command AS command, $tokens AS tokens,
     $resolved_id AS resolved_id, $resolved_score AS resolved_score,
     toString(apoc.util.md5([$prompt_text])) AS text_hash,
     timestamp() AS now_ms

MERGE (p:Prompt {text_hash: text_hash})
ON CREATE SET p.node_id = 'prompt-' + substring(text_hash, 0, 16),
              p.raw_text = text,
              p.embedding = emb,
              p.embedding_model = 'nomic-embed-text',
              p.source = source,
              p.command = command,
              p.first_seen = toString(datetime()),
              p.last_seen = toString(datetime()),
              p.first_seen_ms = now_ms,
              p.last_seen_ms = now_ms,
              p.fire_count = 1,
              p.token_count = size(tokens),
              p.file_type = 'prompt'
ON MATCH SET p.fire_count = coalesce(p.fire_count, 0) + 1,
             p.last_seen = toString(datetime()),
             p.last_seen_ms = now_ms

WITH p, text, tokens, resolved_id, resolved_score, now_ms, source, command


// --- Step 2: Ontology linkage --------------------------------------------

WITH p, text, tokens, resolved_id, resolved_score, now_ms, source, command
OPTIONAL MATCH (o:Ontology {node_id: 'ontology-mycelium'})
FOREACH (_ IN CASE WHEN o IS NULL THEN [] ELSE [1] END |
  MERGE (p)-[:PROMPT_OF]->(o)
)

WITH p, text, tokens, resolved_id, resolved_score, now_ms, source, command


// --- Step 3: Tokens → :Word nodes + :CONTAINS edges ----------------------

UNWIND (CASE WHEN size(tokens) = 0 THEN [null] ELSE tokens END) AS tok
WITH p, text, tokens, resolved_id, resolved_score, now_ms, source, command, tok
WHERE tok IS NOT NULL

MERGE (w:Word {lemma: tok.lemma})
ON CREATE SET w.node_id = 'word-' + tok.lemma,
              w.surface_forms = [tok.surface],
              w.is_stopword = false,
              w.frequency = 1,
              w.first_seen = toString(datetime()),
              w.last_seen = toString(datetime()),
              w.pos = 'unknown',
              w.file_type = 'word'
ON MATCH SET w.frequency = coalesce(w.frequency, 0) + 1,
             w.last_seen = toString(datetime()),
             w.surface_forms = CASE
               WHEN tok.surface IN coalesce(w.surface_forms, [])
                 THEN w.surface_forms
               ELSE coalesce(w.surface_forms, []) + tok.surface
             END

MERGE (p)-[c:CONTAINS {position: tok.position}]->(w)
ON CREATE SET c.count = 1
ON MATCH SET c.count = c.count + 1

WITH p, text, tokens, resolved_id, resolved_score, now_ms, source, command, collect(w) AS prompt_words


// --- Step 4: :BIGRAM edges between adjacent non-stopwords ----------------
// For each adjacent pair in position order, MERGE a BIGRAM edge with count.

WITH p, text, tokens, resolved_id, resolved_score, now_ms, source, command, prompt_words,
     [i IN range(0, size(tokens) - 2) | {w1: tokens[i].lemma, w2: tokens[i+1].lemma}] AS pairs

UNWIND (CASE WHEN size(pairs) = 0 THEN [null] ELSE pairs END) AS pair
WITH p, text, resolved_id, resolved_score, now_ms, source, command, pair
WHERE pair IS NOT NULL

MATCH (w1:Word {lemma: pair.w1})
MATCH (w2:Word {lemma: pair.w2})
MERGE (w1)-[bg:BIGRAM]->(w2)
ON CREATE SET bg.count = 1, bg.first_at = toString(datetime()), bg.last_at = toString(datetime())
ON MATCH SET bg.count = bg.count + 1, bg.last_at = toString(datetime())

WITH DISTINCT p, text, resolved_id, resolved_score, now_ms, source, command


// --- Step 5: :RESOLVED_TO edge to the top match (optional) --------------
// Only fire when resolved_id is set. Use FOREACH trick to conditionally
// run the MERGE without killing the WITH chain for empty resolves.

WITH p, resolved_id, resolved_score, now_ms, source, command
OPTIONAL MATCH (target {node_id: resolved_id})
WHERE resolved_id IS NOT NULL AND resolved_id <> ''
WITH p, resolved_id, resolved_score, now_ms, source, command, target
FOREACH (_ IN CASE WHEN target IS NULL OR resolved_id = '' THEN [] ELSE [1] END |
  MERGE (p)-[r:RESOLVED_TO]->(target)
  ON CREATE SET r.cosine = resolved_score, r.rank = 1,
                r.first_at = toString(datetime()), r.fire_count = 1
  ON MATCH SET r.cosine = CASE WHEN resolved_score > coalesce(r.cosine, 0)
                               THEN resolved_score ELSE r.cosine END,
               r.fire_count = coalesce(r.fire_count, 0) + 1,
               r.last_at = toString(datetime())
)

// --- Return summary so caller can log --------------------------------------

WITH DISTINCT p
RETURN p.node_id AS prompt_id, p.fire_count AS fire_count,
       size([(p)-[:CONTAINS]->(:Word) | 1]) AS token_count;
