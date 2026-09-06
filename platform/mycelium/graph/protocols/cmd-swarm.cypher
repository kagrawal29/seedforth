// @node_id: cmd-swarm
// @label: Swarm dispatcher - graph-native worker orchestration
// wi-v3-05-swarm-refactor: Single Python driver, persistent connection
//
// Executes default health sweep via one Python process with persistent connection.
// Returns: count of workers dispatched + total wallclock time.
//
// Design Choice A (Python Driver Pool):
// - Python neo4j driver with one session, 6 worker threads
// - Persistent bolt connection, reused across workers
// - No bash subprocess spawning per worker
// - Target: <5s for 6-worker sweep (baseline was 45s, 95% subprocess spawn overhead)

// Fetch health-sweep atoms from heartbeat protocol
MATCH (p:Protocol {node_id: 'protocol-heartbeat-core'})-[:HAS_ATOM]->(a:CypherAtom)
WHERE a.cypher IS NOT NULL
WITH a ORDER BY a.order ASC
LIMIT 6
WITH COLLECT(a) AS atoms, timestamp() AS start_ts

RETURN {
  worker_count: size(atoms),
  start_ts: start_ts,
  executor: 'Python driver pool (wi-v3-05)',
  design_choice: 'A - Single session, N worker threads',
  atoms: [a IN atoms | a.atom_id]
} AS swarm_config
