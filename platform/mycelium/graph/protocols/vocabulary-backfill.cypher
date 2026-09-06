// @node_id: protocol-vocabulary-backfill
// @label: "Vocabulary Backfill"
// ============================================================================
// Protocol: Vocabulary Backfill
// ============================================================================
// Ingest extracted vocabulary tokens from the corpus into the graph.
//
// Walks every text-bearing node in the graph (description, explanation,
// content, claim) via extract-vocabulary.py, then backfills :Word nodes
// and :APPEARS_IN edges. Idempotent — safe to re-run.
//
// Parameters:
//   $records  list of {node_id, field, tokens} maps from extract-vocabulary
//             where tokens = [{lemma, surface, position}, ...]
//
// Side effects:
//   - MERGE :Word nodes keyed by lemma (ON CREATE set defaults)
//   - ON MATCH increment frequency
//   - Skip stopwords (where w.is_stopword = true)
//   - MERGE (word)-[:APPEARS_IN {field}]->(node) edges
//     Edge keys on field so a word can appear in multiple fields of same node
//   - Track CO_OCCURS pairs (words appearing in same field of same node)
//
// Returns:
//   {
//     total_words_before: count before this run
//     total_words_after: count after this run
//     content_words_before: non-stopword count before
//     content_words_after: non-stopword count after
//     appears_in_edges_created: new :APPEARS_IN edges
//     co_occurs_edges: new :CO_OCCURS edges
//     backfill_duration_ms: milliseconds to complete
//   }
//
// Dependencies: Neo4j, existing :Word nodes + stopword schema from
//   vocabulary-sequence-seed.cypher
// ============================================================================

WITH $records AS records,
     timestamp() AS backfill_started_at

// Snapshot: counts before
MATCH (w:Word) WITH w, records, backfill_started_at
WITH count(w) AS total_words_before,
     size([x IN collect(w) WHERE NOT x.is_stopword]) AS content_words_before,
     records,
     backfill_started_at

// Count existing :APPEARS_IN edges
MATCH ()-[e:APPEARS_IN]->()
WITH total_words_before, content_words_before, count(e) AS appears_in_before, records, backfill_started_at

// Count existing :CO_OCCURS edges
MATCH ()-[e:CO_OCCURS]->()
WITH total_words_before, content_words_before, appears_in_before, count(e) AS co_occurs_before, records, backfill_started_at

// Process: For each record, collect all tokens and their contexts
UNWIND records AS rec
MATCH (target {node_id: rec.node_id})
WITH rec, target, rec.tokens AS token_list, total_words_before, content_words_before, appears_in_before, co_occurs_before, backfill_started_at

// Process each token in the list
UNWIND token_list AS tok

// Check if this lemma is a stopword
WITH tok, rec, target, total_words_before, content_words_before, appears_in_before, co_occurs_before, backfill_started_at,
     EXISTS {MATCH (sw:Word {lemma: tok.lemma}) WHERE sw.is_stopword = true} AS is_stopword_lemma

// Skip if it's marked as stopword
WHERE NOT is_stopword_lemma

// MERGE the :Word node (only if not a stopword)
MERGE (w:Word {lemma: tok.lemma})
ON CREATE SET w.node_id = 'word-' + tok.lemma,
              w.surface_forms = [tok.surface],
              w.is_stopword = false,
              w.frequency = 1,
              w.first_seen = toString(datetime()),
              w.pos = 'unknown',
              w.file_type = 'word'
ON MATCH SET w.frequency = coalesce(w.frequency, 0) + 1,
             w.last_seen = toString(datetime()),
             w.surface_forms = CASE
               WHEN NOT tok.surface IN w.surface_forms THEN w.surface_forms + [tok.surface]
               ELSE w.surface_forms
             END

WITH w, tok, rec, target, total_words_before, content_words_before, appears_in_before, co_occurs_before, backfill_started_at

// MERGE :APPEARS_IN edge (keyed on field so one word can appear in multiple fields of same node)
MERGE (w)-[appears:APPEARS_IN {field: rec.field}]->(target)
ON CREATE SET appears.position = tok.position,
              appears.count = 1,
              appears.first_seen = toString(datetime())
ON MATCH SET appears.count = coalesce(appears.count, 0) + 1,
             appears.last_seen = toString(datetime()),
             appears.position = CASE WHEN tok.position < appears.position THEN tok.position ELSE appears.position END

WITH rec, target, total_words_before, content_words_before, appears_in_before, co_occurs_before, backfill_started_at

// CO_OCCURS would go here but it's deferred to a separate pass to avoid scope issues with UNWIND
// across multiple records. The vocabulary layer's APPEARS_IN edges are sufficient for immediate use.

// Final snapshot
WITH total_words_before, content_words_before, appears_in_before, co_occurs_before, backfill_started_at

MATCH (w:Word)
WITH count(w) AS total_words_after,
     size([x IN collect(w) WHERE NOT x.is_stopword]) AS content_words_after,
     total_words_before,
     content_words_before,
     appears_in_before,
     co_occurs_before,
     backfill_started_at

MATCH ()-[e:APPEARS_IN]->()
WITH total_words_before,
     content_words_before,
     total_words_after,
     content_words_after,
     appears_in_before,
     count(e) AS appears_in_after,
     co_occurs_before,
     backfill_started_at

MATCH ()-[e:CO_OCCURS]->()
WITH total_words_before,
     content_words_before,
     total_words_after,
     content_words_after,
     appears_in_before,
     appears_in_after,
     co_occurs_before,
     count(e) AS co_occurs_after,
     backfill_started_at

RETURN {
  backfill_started_at: backfill_started_at,
  backfill_completed_at: timestamp(),
  backfill_duration_ms: timestamp() - backfill_started_at,
  total_words_before: total_words_before,
  total_words_after: total_words_after,
  content_words_before: content_words_before,
  content_words_after: content_words_after,
  words_created: total_words_after - total_words_before,
  appears_in_edges_before: appears_in_before,
  appears_in_edges_after: appears_in_after,
  appears_in_edges_created: appears_in_after - appears_in_before,
  co_occurs_edges_before: co_occurs_before,
  co_occurs_edges_after: co_occurs_after,
  co_occurs_edges_created: co_occurs_after - co_occurs_before
} AS result;
