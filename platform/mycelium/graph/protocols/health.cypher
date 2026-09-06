// @node_id: protocol-health
// @label: "Health View — multi-section status snapshot"
// ============================================================================
// Returns a single result stream with rows tagged by (section, row_type, content).
// Caller formats per section: headers, OK rows, FAIL rows, plain text.
//
// Sections (in order): identity, invariants-active, invariants-deferred,
//   tests-summary, tests-failing, density, embeddings.
// ============================================================================

// --- Identity -------------------------------------------------------------
MATCH (b:Being {node_id: 'being-mycelium'})
OPTIONAL MATCH (b)-[:CURRENT_SPECIES]->(s:Species)
RETURN 'identity' AS section, 'line' AS rtype,
       '  being:      ' + b.node_id AS content
UNION ALL
MATCH (b:Being {node_id: 'being-mycelium'})
RETURN 'identity' AS section, 'line' AS rtype,
       '  root:       ' + substring(coalesce(b.root_hash, 'null'), 0, 48) + '...' AS content
UNION ALL
MATCH (b:Being {node_id: 'being-mycelium'})
RETURN 'identity' AS section, 'line' AS rtype,
       '  leaves:     ' + toString(coalesce(b.leaf_count, 0)) AS content
UNION ALL
MATCH (b:Being {node_id: 'being-mycelium'})
RETURN 'identity' AS section, 'line' AS rtype,
       '  beats:      ' + toString(coalesce(b.heartbeat_count, 0)) AS content
UNION ALL
MATCH (b:Being {node_id: 'being-mycelium'})
OPTIONAL MATCH (b)-[:CURRENT_SPECIES]->(s:Species)
RETURN 'identity' AS section, 'line' AS rtype,
       '  chain head: ' + coalesce(s.node_id, '(none)') AS content
UNION ALL
// --- Invariants (active) ---------------------------------------------------
MATCH (i:Invariant) WHERE coalesce(i.enabled, true) = true
RETURN 'invariants-active' AS section,
       CASE WHEN coalesce(i.health_status, i.health) = 'healthy' THEN 'ok' ELSE 'bad' END AS rtype,
       coalesce(i.label, i.node_id) + '|' + coalesce(i.node_id, '') + '|' + coalesce(i.health_status, i.health, 'unknown') AS content
UNION ALL
// --- Invariants (deferred) -------------------------------------------------
MATCH (i:Invariant) WHERE coalesce(i.enabled, true) = false
RETURN 'invariants-deferred' AS section, 'line' AS rtype,
       '  ' + i.node_id + '  ' + coalesce(i.deferred_reason, '(no reason)') AS content
UNION ALL
// --- Tests (summary) -------------------------------------------------------
MATCH (t:TestCase)
WITH count(t) AS total,
     sum(CASE WHEN coalesce(t.enabled, true) THEN 1 ELSE 0 END) AS active,
     sum(CASE WHEN coalesce(t.enabled, true) AND t.last_result = 'pass' THEN 1 ELSE 0 END) AS passing,
     sum(CASE WHEN coalesce(t.enabled, true) AND t.last_result = 'fail' THEN 1 ELSE 0 END) AS failing,
     sum(CASE WHEN NOT coalesce(t.enabled, true) THEN 1 ELSE 0 END) AS deferred
RETURN 'tests-summary' AS section, 'line' AS rtype,
       '  ' + toString(passing) + '/' + toString(active) + ' passing  (' +
       toString(failing) + ' failing, ' + toString(deferred) + ' deferred, ' +
       toString(total) + ' total)' AS content
UNION ALL
// --- Tests (failing active) ------------------------------------------------
MATCH (t:TestCase) WHERE coalesce(t.enabled, true) = true AND t.last_result = 'fail'
RETURN 'tests-failing' AS section, 'bad' AS rtype,
       t.node_id + '  ' + coalesce(t.label, '') AS content
UNION ALL
// --- Density ---------------------------------------------------------------
MATCH (n) WHERE n.node_id IS NOT NULL AND NOT n:QueryTrace
WITH count(n) AS nodes
MATCH ()-[r]->()
WITH nodes, count(r) AS edges
RETURN 'density' AS section, 'line' AS rtype,
       '  ' + toString(nodes) + ' nodes, ' + toString(edges) + ' edges, ' +
       toString(round(toFloat(edges)/nodes * 100)/100) + ' e/n' AS content
UNION ALL
// --- Embedding coverage ----------------------------------------------------
MATCH (n) WHERE n.leaf_hash IS NOT NULL
WITH count(n) AS total
MATCH (n) WHERE n.leaf_hash IS NOT NULL AND (n.embedding IS NULL OR n.embedding_for_leaf_hash <> n.leaf_hash)
WITH total, count(n) AS drifted
RETURN 'embeddings' AS section, 'line' AS rtype,
       '  ' + toString(total - drifted) + '/' + toString(total) + ' up-to-date, ' +
       toString(drifted) + ' drifted' AS content
