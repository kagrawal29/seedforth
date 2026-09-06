// @node_id: protocol-status
// @label: "Status View — compact single-column identity/health summary"
// Returns a flat list of "key: value" lines for simple print.

MATCH (b:Being {node_id: 'being-mycelium'}) WITH b LIMIT 1
RETURN 'root_hash:       ' + substring(coalesce(b.root_hash, 'null'), 0, 48) + '...' AS line
UNION ALL
MATCH (b:Being {node_id: 'being-mycelium'}) WITH b LIMIT 1
RETURN 'leaf_count:      ' + toString(coalesce(b.leaf_count, 0)) AS line
UNION ALL
MATCH (b:Being {node_id: 'being-mycelium'}) WITH b LIMIT 1
RETURN 'heartbeat_count: ' + toString(coalesce(b.heartbeat_count, 0)) AS line
UNION ALL
MATCH (b:Being {node_id: 'being-mycelium'}) WITH b LIMIT 1 OPTIONAL MATCH (b)-[:CURRENT_SPECIES]->(head:Species)
RETURN 'chain head:      ' + coalesce(head.node_id, '(no head)') AS line
UNION ALL
MATCH (b:Being {node_id: 'being-mycelium'}) WITH b LIMIT 1
RETURN 'autonomous_score:' + ' ' + toString(coalesce(b.autonomous_score, 0)) + '%' AS line
UNION ALL
MATCH (c:CandidateSpecies) WITH count(c) AS n
RETURN 'pending cands:   ' + toString(n) AS line
UNION ALL
MATCH (i:Invariant) WHERE coalesce(i.enabled, true) = true
WITH count(i) AS total, sum(CASE WHEN coalesce(i.health_status, i.health) = 'healthy' THEN 1 ELSE 0 END) AS healthy
RETURN 'invariants:      ' + toString(healthy) + '/' + toString(total) + ' healthy' AS line
UNION ALL
MATCH (t:TestCase) WHERE coalesce(t.enabled, true) = true
WITH count(t) AS total, sum(CASE WHEN t.last_result = 'pass' THEN 1 ELSE 0 END) AS passing
RETURN 'tests:           ' + toString(passing) + '/' + toString(total) + ' passing' AS line
UNION ALL
MATCH (ap:ActionProposal) WHERE coalesce(ap.status, 'pending') = 'pending'
WITH count(ap) AS n
RETURN 'open proposals:  ' + toString(n) AS line
UNION ALL
CALL apoc.periodic.list() YIELD name WHERE name = 'mycelium-heartbeat'
WITH count(name) AS n
RETURN 'heartbeat sched: ' + CASE WHEN n > 0 THEN 'running' ELSE 'stopped' END AS line
