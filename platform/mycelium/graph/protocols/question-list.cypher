// @kind: seed
// ============================================================================
// Protocol: Question List
// ============================================================================
// Read-only protocol that returns the pending question queue, ordered by
// severity (block > warn > info) and then by age (oldest first).
//
// Used by:
//   - mycelium questions     — CLI reader that displays the queue
//   - mycelium status        — shows top pending question (if any)
//   - Dream rounds           — detect when questions are blocking unblocked items
//
// Parameters: none
//
// Behavior:
//   1. MATCH all :Question nodes with status='pending'
//   2. For each question:
//      a. Include: node_id, text, severity, raised_by node_id, raise_count
//      b. Count CONCERNS edges (impact: how many nodes are affected)
//      c. Lookup the :QuestionTemplate to include options, default_option
//   3. ORDER BY severity DESC (block > warn > info), raised_at ASC (oldest first)
//   4. RETURN the full queue with metadata
//
// Pure MATCH/RETURN — no mutations.
// ============================================================================

MATCH (q:Question {status: 'pending'})
OPTIONAL MATCH (q)-[:INSTANCE_OF]->(template:QuestionTemplate)
OPTIONAL MATCH (q)-[:RAISED_BY]->(raiser)
OPTIONAL MATCH (q)-[:CONCERNS]->(c)

WITH q, template, raiser,
     count(DISTINCT c) AS concern_count,
     collect(DISTINCT c.node_id) AS concern_ids

// Severity scoring for ORDER BY: block=3, warn=2, info=1
WITH q, template, raiser, concern_count, concern_ids,
     CASE q.severity
       WHEN 'block' THEN 3
       WHEN 'warn'  THEN 2
       WHEN 'info'  THEN 1
       ELSE 0
     END AS severity_score

// Coerce raised_at to datetime for proper comparison
WITH q, template, raiser, concern_count, concern_ids, severity_score,
     CASE
       WHEN q.raised_at IS NOT NULL THEN datetime(q.raised_at)
       ELSE datetime()
     END AS raised_at_dt

ORDER BY severity_score DESC, raised_at_dt ASC

RETURN q.node_id AS question_id,
       q.text AS question_text,
       q.severity AS severity,
       q.raise_count AS raise_count,
       raiser.node_id AS raised_by,
       template.template_id AS template_id,
       template.options AS available_options,
       template.default_option AS default_response,
       concern_count AS affected_node_count,
       concern_ids AS affected_nodes,
       q.raised_at AS first_raised_at,
       q.last_raised_at AS last_raised_at;
