// @node_id: protocol-know-thyself
// @label: "Self-Model View — identity, capabilities, protocols, duties, tests, atoms"

// I AM
MATCH (b:Being {node_id: 'being-mycelium'}) WITH b LIMIT 1
RETURN '# I AM' AS line
UNION ALL
MATCH (b:Being {node_id: 'being-mycelium'})-[:CURRENT_SPECIES]->(s:Species) WITH b, s LIMIT 1
RETURN '  being-mycelium — chain head: ' + s.node_id + ' (signed=' + toString(coalesce(s.signed, false)) + ')' AS line
UNION ALL
MATCH (b:Being {node_id: 'being-mycelium'}) WITH b LIMIT 1
RETURN '  root: ' + substring(coalesce(b.root_hash, 'null'), 0, 48) + '...' AS line
UNION ALL
MATCH (b:Being {node_id: 'being-mycelium'}) WITH b LIMIT 1
RETURN '  leaves: ' + toString(coalesce(b.leaf_count, 0)) + ', heartbeats: ' + toString(coalesce(b.heartbeat_count, 0)) + ', score: ' + toString(coalesce(b.autonomous_score, 0)) + '%' AS line
UNION ALL
RETURN '' AS line
UNION ALL
RETURN '# CAPABILITIES (what I can do)' AS line
UNION ALL
MATCH (c:Command) RETURN '  ' + c.usage + ' — ' + c.description AS line ORDER BY c.category, c.order
UNION ALL
RETURN '' AS line
UNION ALL
RETURN '# PROTOCOLS (what I run)' AS line
UNION ALL
MATCH (p:Protocol) WHERE coalesce(p.enabled, true) = true
RETURN '  ' + p.node_id + '  (' + coalesce(p.protocol_type, 'unknown') + ', ' + coalesce(p.cadence, 'on-demand') + ')' AS line
ORDER BY coalesce(p.protocol_order, 999)
UNION ALL
RETURN '' AS line
UNION ALL
RETURN '# DUTIES (what must remain true — invariants)' AS line
UNION ALL
MATCH (i:Invariant) WHERE coalesce(i.enabled, true) = true
RETURN '  [' + coalesce(i.health_status, i.health, 'unknown') + '] ' + coalesce(i.label, i.node_id) AS line
ORDER BY i.node_id
UNION ALL
RETURN '' AS line
UNION ALL
RETURN '# TESTS (what I verify — aggregate)' AS line
UNION ALL
MATCH (t:TestCase)
WITH count(t) AS total,
     sum(CASE WHEN coalesce(t.enabled, true) THEN 1 ELSE 0 END) AS active,
     sum(CASE WHEN coalesce(t.enabled, true) AND t.last_result = 'pass' THEN 1 ELSE 0 END) AS passing
RETURN '  active: ' + toString(active) + '/' + toString(total) + ', passing: ' + toString(passing) + '/' + toString(active) AS line
UNION ALL
RETURN '' AS line
UNION ALL
RETURN '# ATOMS (the code I am made of)' AS line
UNION ALL
MATCH (a:CypherAtom)
RETURN '  ' + toString(count(a)) + ' atoms across ' + toString(count(DISTINCT a.source_protocol)) + ' protocols' AS line
