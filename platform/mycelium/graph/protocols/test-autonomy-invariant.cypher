// @node_id: test-autonomy-invariant-check
// @label: "Test: Autonomy Invariant Check"

MATCH (inv:Invariant {node_id: 'invariant-vital-autonomy-score'})
WITH inv
CALL apoc.cypher.run(inv.check_cypher, {}) YIELD value
WITH inv, value, keys(value)[0] AS result_key
WITH inv, value[result_key] AS result
SET inv.health_status = CASE WHEN result = true THEN 'healthy' ELSE 'unhealthy' END,
    inv.last_checked = toString(datetime())
RETURN inv.node_id AS node_id, inv.health_status AS status, result AS check_result
