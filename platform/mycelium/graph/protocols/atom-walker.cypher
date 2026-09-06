// @node_id: protocol-atom-walker
// @label: "Atom Walker — graph-native replacement for atom_run.py"
// ============================================================================
// Walks (:Protocol {node_id: $target_protocol_id})-[:HAS_ATOM]->(:CypherAtom)
// in order, executing each atom's cypher via apoc.cypher.doIt inside
// apoc.periodic.iterate (batchSize:1, parallel:false → sequential ordered).
//
// Per-atom: records a QueryTrace with duration_ms, status, and atom_id.
// Per-protocol: records a rollup QueryTrace with atom_count, failures,
// total_duration_ms.
//
// Parameters (required):
//   $target_protocol_id   string   node_id of the Protocol to walk
//
// Fallback: if the target has no :HAS_ATOM chain, invokes its .cypher
// property directly via apoc.cypher.runMany (parity with atom_run.py).
//
// Returns summary rows: protocol_id, atom_count, failures, total_ms, status.
// ============================================================================

WITH $target_protocol_id AS pid, timestamp() AS walk_start
MATCH (p:Protocol {node_id: pid})
OPTIONAL MATCH (p)-[:HAS_ATOM]->(a:CypherAtom) WHERE a.cypher IS NOT NULL
WITH p, pid, walk_start, count(a) AS atom_count

// Branch A: has atoms → iterate them in order
CALL apoc.do.when(
  atom_count > 0,
  '
    CALL apoc.periodic.iterate(
      "MATCH (p:Protocol {node_id: $pid})-[:HAS_ATOM]->(a:CypherAtom)
       WHERE a.cypher IS NOT NULL
       RETURN a ORDER BY a.order ASC",
      "CALL apoc.cypher.doIt(a.cypher, {}) YIELD value
       WITH a, value, timestamp() AS fired_at
       CREATE (qt:QueryTrace {
         node_id: \\"qt-\\" + toString(fired_at) + \\"-\\" + apoc.text.random(6, \\"a-z0-9\\"),
         protocol_id: $pid,
         atom_id: a.atom_id,
         fired_at: toString(datetime()),
         invoked_epoch_ms: fired_at,
         cypher_summary: \\"atom-walker: \\" + a.atom_id,
         file_type: \\"query-trace\\",
         phase: \\"atom-execution\\"
       })
       WITH qt, a
       MATCH (p:Protocol {node_id: $pid})
       MERGE (qt)-[:FIRED_BY]->(p)
       RETURN qt.node_id",
      {batchSize: 1, parallel: false, params: {pid: $pid}}
    ) YIELD batches, total, failedOperations, errorMessages
    RETURN batches, total, failedOperations, errorMessages
  ',
  '
    MATCH (p:Protocol {node_id: $pid}) WHERE p.cypher IS NOT NULL
    CALL apoc.cypher.runMany(p.cypher, {}) YIELD result
    RETURN 1 AS batches, count(result) AS total, 0 AS failedOperations, [] AS errorMessages
  ',
  {pid: pid}
) YIELD value AS exec

// Rollup QueryTrace
WITH p, pid, walk_start, atom_count, exec
WITH p, pid, atom_count, exec, timestamp() - walk_start AS total_ms
CREATE (rollup:QueryTrace {
  node_id: 'qt-' + toString(timestamp()) + '-' + apoc.text.random(6, 'a-z0-9'),
  protocol_id: pid,
  fired_at: toString(datetime()),
  invoked_epoch_ms: timestamp(),
  duration_ms: total_ms,
  atom_count: atom_count,
  failures: coalesce(exec.failedOperations, 0),
  cypher_summary: 'atom-walker rollup for ' + pid,
  file_type: 'query-trace',
  phase: 'protocol-execution'
})
MERGE (rollup)-[:FIRED_BY]->(p)
SET p.fire_count = coalesce(p.fire_count, 0) + 1,
    p.last_fired_at = toString(datetime()),
    p.last_duration_ms = total_ms
RETURN
  pid AS protocol_id,
  atom_count,
  coalesce(exec.failedOperations, 0) AS failures,
  total_ms AS total_duration_ms,
  CASE WHEN coalesce(exec.failedOperations, 0) = 0 THEN 'success' ELSE 'partial' END AS status;
