// @node_id: protocol-question-raise
// @label: "Question Raise"
// ============================================================================
// Protocol: Question Raise
// ============================================================================
// Reusable protocol that other protocols and invariants call to raise a
// :Question. Deduplicates identical questions (same text) and increments
// raise_count when the same question is raised again.
//
// Used by:
//   - Invariants when they detect a gap needing user input
//   - Other protocols when they detect an authorization requirement
//   - Subagents when they encounter ambiguity requiring human judgment
//
// Parameters (via --param):
//   template_id  string — which :QuestionTemplate to instantiate
//   text         string — the actual question text (can override template)
//   severity     string — 'info' | 'warn' | 'block'
//   raised_by    string — node_id of what raised this (Invariant, Protocol, etc.)
//   concerns     list — node_ids this question is about (for impact assessment)
//
// Behavior:
//   1. MATCH the QuestionTemplate by template_id
//   2. Create a text hash to deduplicate identical questions
//   3. MERGE a :Question node using the text hash as the key
//     a. ON CREATE: set all properties, status='pending', raised_at timestamp
//     b. ON MATCH: increment raise_count (same question raised again = more urgent)
//   4. Wire :INSTANCE_OF to the QuestionTemplate
//   5. Wire :RAISED_BY to the originating node
//   6. For each node_id in $concerns, wire :CONCERNS to it
//   7. Wire :QUESTION_OF to :Ontology (so no orphans)
//   8. Return the question node_id for caller reference
//
// Idempotent: MERGE key is the text hash. Multiple raises of the same
// question increment raise_count without creating duplicates.
// ============================================================================

MATCH (template:QuestionTemplate {template_id: $template_id})
WHERE template IS NOT NULL

MATCH (ontology:Ontology)

// Compute text hash for deduplication
WITH template, ontology, apoc.util.md5($text) AS text_hash

// MERGE the Question keyed by text hash
MERGE (q:Question {text_hash: text_hash})
ON CREATE
  SET q.node_id = 'question-' + text_hash,
      q.text = $text,
      q.severity = $severity,
      q.status = 'pending',
      q.raised_at = toString(datetime()),
      q.raise_count = 1,
      q.file_type = 'question'
ON MATCH
  SET q.raise_count = coalesce(q.raise_count, 0) + 1,
      q.last_raised_at = toString(datetime())

WITH q, template, ontology

// Wire :INSTANCE_OF to the QuestionTemplate
MERGE (q)-[:INSTANCE_OF]->(template)

// Wire :RAISED_BY to the originating node
MATCH (raiser {node_id: $raised_by})
MERGE (q)-[:RAISED_BY]->(raiser)

// Wire :CONCERNS to each affected node
WITH q, ontology, $concerns AS concern_ids
UNWIND concern_ids AS concern_id
MATCH (c {node_id: concern_id})
MERGE (q)-[:CONCERNS]->(c)

WITH q, ontology DISTINCT

// Wire :QUESTION_OF to Ontology (no orphans)
MERGE (q)-[:QUESTION_OF]->(ontology)

RETURN q.node_id AS question_id,
       q.text AS text,
       q.severity AS severity,
       q.status AS status,
       q.raise_count AS raise_count;
