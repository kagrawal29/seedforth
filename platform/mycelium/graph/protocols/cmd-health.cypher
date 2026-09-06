// @node_id: protocol-cmd-health
// @label: Health Command
// @kind: command
// @description: Comprehensive health check with invariant status, tests, density, embeddings

// Atom 1: System identity header
MATCH (being:Being {node_id: 'being-mycelium'})
RETURN 'identity|' + being.node_id + '|' + 'node_count query follows' AS result;

// Atom 2: Graph node and edge counts
MATCH (n)
WITH count(n) AS node_count
MATCH (r)--()
WITH node_count, count(r) AS edge_count
RETURN 'density|' + toString(node_count) + ' nodes|' + toString(edge_count) + ' edges' AS result;

// Atom 3: Active invariants with health status (ok)
MATCH (inv:Invariant) WHERE coalesce(inv.enabled, true) = true AND inv.health = 'healthy'
RETURN 'invariants-active|ok|' + inv.label + '|' + inv.node_id + '|healthy' AS result;

// Atom 4: Active invariants with health status (bad)
MATCH (inv:Invariant) WHERE coalesce(inv.enabled, true) = true AND inv.health <> 'healthy'
RETURN 'invariants-active|bad|' + inv.label + '|' + inv.node_id + '|' + coalesce(inv.health, 'unknown') AS result;

// Atom 5: Test summary
MATCH (t:TestCase) WHERE coalesce(t.enabled, true) = true
WITH count(t) AS total, count(CASE WHEN t.last_result = 'pass' THEN 1 END) AS passed
RETURN 'tests-summary|' + toString(passed) + '/' + toString(total) + ' passing' AS result;

// Atom 6: Failing tests
MATCH (t:TestCase) WHERE coalesce(t.enabled, true) = true AND t.last_result = 'fail'
RETURN 'tests-failing|bad|' + t.node_id + ' — ' + coalesce(t.label, 'unlabeled') AS result;

// Atom 7: Embedding coverage
MATCH (n) WHERE n.embedding IS NOT NULL
WITH count(n) AS embedded
MATCH (m) WHERE m.node_id IS NOT NULL
WITH embedded, count(m) AS total
RETURN 'embeddings|' + toString(round(embedded * 100.0 / total)) + '% covered (' + toString(embedded) + '/' + toString(total) + ')' AS result;
