// @node_id: cmd-clone
// @label: "Clone — copy one Neo4j instance into another"
// @kind: command
// @description: Records clone intent, captures source state before clone, schedules shell runner

// Atom 1: Create CloneRun node with timestamp and parameters
MATCH (being:Being {node_id: 'being-mycelium'})
WITH timestamp() AS ts
MERGE (cr:CloneRun {node_id: 'clone-run-' + toString(ts), created_at: ts})
SET cr.timestamp = ts, cr.intent = 'clone-instances', cr.status = 'intent', cr.requested_at = ts
RETURN 'clone|created|node_id:' + cr.node_id + '|ts:' + toString(ts) AS result;

// Atom 2: Count source nodes at clone request time
MATCH (n) WHERE n.node_id IS NOT NULL
WITH count(n) AS node_count, timestamp() AS ts
MATCH (cr:CloneRun {node_id: 'clone-run-' + toString(ts)})
SET cr.source_count_before = node_count
RETURN 'clone|source-nodecount|' + toString(node_count) AS result;

// Atom 3: Count source edges at clone request time
MATCH (n)-[r]-(m) WHERE n.node_id IS NOT NULL
WITH count(r) AS edge_count
MATCH (cr:CloneRun) WHERE cr.timestamp IS NOT NULL
ORDER BY cr.timestamp DESC LIMIT 1
SET cr.source_edge_count_before = edge_count
RETURN 'clone|source-edgecount|' + toString(edge_count) AS result;

// Atom 4: Link CloneRun to Being for progress tracking
MATCH (being:Being {node_id: 'being-mycelium'})
MATCH (cr:CloneRun) WHERE cr.timestamp IS NOT NULL
ORDER BY cr.timestamp DESC LIMIT 1
MERGE (being)-[:INITIATED_CLONE]->(cr)
SET cr.notes = 'clone-instance.sh runner should process: dump source, load target, reset password, verify counts'
RETURN 'clone|linked|clone_id:' + cr.node_id + '|status:intent' AS result;

// Atom 5: Summary of clone intent
MATCH (cr:CloneRun) WHERE cr.timestamp IS NOT NULL
ORDER BY cr.timestamp DESC LIMIT 1
RETURN 'clone-summary|node_id:' + cr.node_id + '|source_nodes:' + toString(cr.source_count_before) + '|source_edges:' + toString(cr.source_edge_count_before) + '|status:' + cr.status AS result;
