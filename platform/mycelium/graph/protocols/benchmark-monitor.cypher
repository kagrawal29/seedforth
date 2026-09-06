// @node_id: protocol-benchmark-monitor
// @label: "Benchmark Monitor"
// Benchmark Monitor Protocol
// Checks swarm autonomy ClaimTest nodes and creates Gap nodes for failing tests
// Returns: test_name, current_value, target_value, status, action

WITH [
  {test_id: 'ct-swarm-task-completion', target: 1.0},
  {test_id: 'ct-swarm-dispatch-accuracy', target: 0.5},
  {test_id: 'ct-swarm-depth-utilization', target: 1},
  {test_id: 'ct-swarm-then-strength', target: 2},
  {test_id: 'ct-swarm-heal-effectiveness', target: 1}
] AS tests

UNWIND tests AS test_def

MATCH (ct:ClaimTest {node_id: test_def.test_id})

WITH ct, test_def.target AS target_value

// Create Gap nodes for failing tests only
FOREACH (_ IN CASE WHEN ct.current_value < target_value OR ct.current_status = 'failing' THEN [1] ELSE [] END |
  MERGE (gap:Gap {
    node_id: 'gap-' + ct.node_id,
    label: 'Gap: ' + ct.name + ' below target',
    description: ct.name + ' = ' + toString(ct.current_value),
    auto_fixable: true,
    created_at: toString(datetime()),
    status: 'open'
  })
  MERGE (gap)-[:TRIGGERED_BY]->(ct)
)

RETURN
  ct.name AS test_name,
  ct.current_value AS current_value,
  target_value,
  ct.current_status AS status,
  CASE
    WHEN ct.current_value < target_value OR ct.current_status = 'failing'
    THEN 'gap_created'
    ELSE 'passing'
  END AS action
