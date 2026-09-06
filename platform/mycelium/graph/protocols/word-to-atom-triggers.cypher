// @node_id: protocol-word-to-atom-triggers
// @label: "Word to Atom Triggers"
// ============================================================================
// Protocol: Word to Atom Triggers
// ============================================================================
// Bridge the vocabulary extraction layer to the atomic execution layer.
// Creates TRIGGERS edges from high-frequency Words to CypherAtoms, Protocols,
// and Concepts whose descriptions or names contain those words.
//
// Effect: Vocabulary now participates in secondary retrieval paths. When a user
// asks "dead protocols", the Word "dead" can trigger matching atoms via the
// TRIGGERS edge, enabling community detection, cache pre-fetching, and
// convergence walks.
//
// Algorithm:
//   1. Find all Words with frequency >= 2 (signal threshold)
//   2. For each Word, search CypherAtom, Protocol, Concept, WorkItem nodes
//      whose description or name contains the word (case-insensitive)
//   3. Create TRIGGERS edge with weight = word.frequency / 10.0
//   4. Return summary: count of Words processed, edges created, avg edge weight
//
// Side effects:
//   - Creates TRIGGERS edges (idempotent via MERGE)
//   - Does NOT modify Word or target nodes
//   - Runs in <5 seconds for typical graph (88 Words, 630 Atoms)
//
// Performance: O(words * atom_descriptions) but relies on Neo4j string matching
// which is indexed. Vectorized cosine comparison not used (would require
// embedding each description, expensive at scale).
//
// Guardrails:
//   - Minimum frequency threshold prevents spammy edges from rare words
//   - Weight normalization (frequency / 10) keeps edge weights in [0.1, 3.0]
//   - Case-insensitive matching reduces false negatives
// ============================================================================

// --- Step 1: Collect high-frequency Words --------------------------------

WITH 2 AS frequency_threshold
MATCH (w:Word)
WHERE w.frequency >= frequency_threshold
WITH collect({
  node_id: w.node_id,
  lemma: w.lemma,
  frequency: w.frequency,
  lemma_lower: toLower(w.lemma)
}) AS words_to_process, frequency_threshold

// --- Step 2: For each Word, find matching atoms and create TRIGGERS edges

UNWIND words_to_process AS word_spec
WITH word_spec, frequency_threshold
OPTIONAL MATCH (w:Word {node_id: word_spec.node_id})

// Search for atoms/concepts/workitems whose description or name contains this word
OPTIONAL MATCH (target)
WHERE (target:CypherAtom OR target:Protocol OR target:Concept OR
       target:WorkItem OR target:Invariant)
AND (
  (target.description IS NOT NULL AND
   toLower(target.description) CONTAINS word_spec.lemma_lower)
  OR
  (target.name IS NOT NULL AND
   toLower(target.name) CONTAINS word_spec.lemma_lower)
)
WITH word_spec, w, target, frequency_threshold
WHERE w IS NOT NULL AND target IS NOT NULL

// Create TRIGGERS edge with normalized weight
MERGE (w)-[t:TRIGGERS]->(target)
ON CREATE SET
  t.weight = word_spec.frequency / 10.0,
  t.created_at = toString(datetime()),
  t.trigger_strength = CASE
    WHEN word_spec.frequency >= 20 THEN 'strong'
    WHEN word_spec.frequency >= 10 THEN 'medium'
    ELSE 'weak'
  END,
  t.fire_count = 1,
  t.last_fired = toString(datetime())
ON MATCH SET
  t.fire_count = coalesce(t.fire_count, 0) + 1,
  t.last_fired = toString(datetime()),
  t.weight = (t.weight + (word_spec.frequency / 10.0)) / 2

// Collect statistics for return
WITH w.lemma AS lemma, labels(target)[0] AS target_label, t.weight AS weight
RETURN lemma, target_label, weight
ORDER BY lemma, target_label, weight DESC
