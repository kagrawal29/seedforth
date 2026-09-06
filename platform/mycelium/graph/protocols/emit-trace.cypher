// @node_id: protocol-emit-trace
// @label: "Emit Query Trace (Phase 14 v2 — fire-together-wire-together)"
// ============================================================================
// Protocol: Emit Query Trace (Phase 14 v2 — fire-together-wire-together)
// ============================================================================
// Two-tier memory of queries:
//
//   (:Query)       canonical record of a unique cypher, keyed by sha256
//                  of the cypher text. Accumulates fire_count over its
//                  lifetime — same cypher repeated = same node with a
//                  higher count. Hebbian: paths that fire together are
//                  literally the same node, and their strength is its
//                  fire_count.
//
//   (:QueryTrace)  per-invocation historical record. Links to the Query
//                  via :INSTANCE_OF. Optional — controlled by the caller.
//                  Used when you want the full timeline (who ran this
//                  when, how long, what it touched); skipped when you
//                  only need the aggregate.
//
// Semantic field on Query:
//   Query.semantic holds the natural-language meaning of the cypher.
//   Populated lazily by an LLM-assisted protocol (or by hand). Over
//   time, semantic embeddings on these Query nodes form a natural-
//   language → cypher index: "find me all invariants that check auth"
//   → vector-search the Query.semantic field → return the matching
//   cypher text.
//
// Parameters:
//   cypher           string — the full cypher text (hashed as the key)
//   cypher_summary   string — short form for display (up to 300 chars)
//   invoked_by       string — 'mycelium cli', 'heartbeat-loop', 'ci', etc.
//   command          string — logical command name
//   duration_ms      int    — how long it took (optional)
//   result_count     int    — rows returned (optional)
//   touched_ids      list   — node_ids that surfaced in the result
//   create_trace     bool   — if true, also create a QueryTrace record
//                              (default true for first invocation)
// ============================================================================

WITH
  coalesce($cypher, $cypher_summary, '') AS cypher_text,
  coalesce($cypher_summary, '') AS cypher_summary,
  coalesce($invoked_by, 'unknown') AS invoked_by,
  coalesce($command, '') AS command,
  coalesce($duration_ms, 0) AS duration_ms,
  coalesce($result_count, 0) AS result_count,
  coalesce($touched_ids, []) AS touched_ids,
  coalesce($create_trace, true) AS create_trace
WITH cypher_text, cypher_summary, invoked_by, command, duration_ms, result_count, touched_ids, create_trace,
     apoc.util.sha256([cypher_text]) AS cypher_hash

// --- Step 1: MERGE the canonical Query node ---------------------------------
MERGE (q:Query {cypher_hash: cypher_hash})
ON CREATE SET
  q.node_id = 'query-' + substring(cypher_hash, 0, 16),
  q.cypher = cypher_text,
  q.cypher_summary = cypher_summary,
  q.semantic = '',  // populated later by describe-queries protocol
  q.first_seen = toString(datetime()),
  q.fire_count = 1,
  q.file_type = 'query'
ON MATCH SET
  q.fire_count = coalesce(q.fire_count, 0) + 1

SET q.last_seen = toString(datetime()),
    q.last_duration_ms = duration_ms,
    q.last_result_count = result_count,
    q.last_invoked_by = invoked_by,
    q.last_command = command

// --- Step 2: optionally create a QueryTrace for this invocation ------------
WITH q, cypher_hash, cypher_summary, invoked_by, command, duration_ms, result_count, touched_ids, create_trace
FOREACH (_ IN CASE WHEN create_trace THEN [1] ELSE [] END |
  CREATE (qt:QueryTrace {
    node_id: 'qt-' + toString(timestamp()) + '-' + apoc.text.random(6, 'a-z0-9'),
    cypher_hash: cypher_hash,
    cypher_summary: cypher_summary,
    invoked_by: invoked_by,
    command: command,
    duration_ms: duration_ms,
    result_count: result_count,
    touched_ids: touched_ids,
    invoked_at: toString(datetime()),
    invoked_epoch_ms: timestamp(),
    file_type: 'query-trace'
  })
  MERGE (qt)-[:INSTANCE_OF]->(q)
)

RETURN q.node_id AS query_id,
       q.fire_count AS fire_count,
       cypher_hash AS hash;
