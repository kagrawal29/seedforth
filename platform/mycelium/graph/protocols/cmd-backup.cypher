// @node_id: protocol-cmd-backup
// @label: Backup Command
// @kind: command
// @description: Records backup intent node with timestamp, creates TODO edge for bash runner

// Atom 1: Create Backup node with timestamp
MATCH (being:Being {node_id: 'being-mycelium'})
WITH timestamp() AS ts
MERGE (b:Backup {node_id: 'backup-' + toString(ts), created_at: ts})
SET b.timestamp = ts, b.intent = 'backup-graph'
RETURN 'backup|created|node_id:' + b.node_id + '|ts:' + toString(ts) AS result;

// Atom 2: Count nodes at backup time
MATCH (n) WHERE n.node_id IS NOT NULL
WITH count(n) AS node_count, timestamp() AS ts
MATCH (b:Backup {node_id: 'backup-' + toString(ts)})
SET b.node_count = node_count
RETURN 'backup|nodecount|' + toString(node_count) AS result;

// Atom 3: Count edges at backup time
MATCH (n)-[r]-(m) WHERE n.node_id IS NOT NULL
WITH count(r) AS edge_count
MATCH (b:Backup) WHERE b.timestamp IS NOT NULL
ORDER BY b.timestamp DESC LIMIT 1
SET b.edge_count = edge_count
RETURN 'backup|edgecount|' + toString(edge_count) AS result;

// Atom 4: Create Backup node and link to Being for progress tracking
MATCH (being:Being {node_id: 'being-mycelium'})
MATCH (b:Backup) WHERE b.timestamp IS NOT NULL
ORDER BY b.timestamp DESC LIMIT 1
MERGE (being)-[:INITIATED_BACKUP]->(b)
SET b.status = 'intent', b.notes = 'backup-graph.sh runner should process'
RETURN 'backup|linked|backup_id:' + b.node_id + '|status:intent' AS result;

// Atom 5: Summary of backup intent
MATCH (b:Backup) WHERE b.timestamp IS NOT NULL
ORDER BY b.timestamp DESC LIMIT 1
RETURN 'backup-summary|node_id:' + b.node_id + '|nodes:' + toString(b.node_count) + '|edges:' + toString(b.edge_count) + '|status:' + b.status AS result;
