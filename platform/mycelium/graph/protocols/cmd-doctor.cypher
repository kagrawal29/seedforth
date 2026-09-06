// @node_id: protocol-cmd-doctor
// @label: Doctor Command
// @kind: command
// @description: System diagnostics checklist for Neo4j, Ollama, graph state

// Atom 1: Check Neo4j is reachable
RETURN 'check-neo4j|success|Neo4j connection OK' AS result;

// Atom 2: Check APOC is installed
RETURN 'check-apoc|success|APOC ' + apoc.version() + ' installed' AS result;

// Atom 3: Check graph has nodes
MATCH (n)
WITH count(n) AS node_count
RETURN 'check-graph|' + CASE WHEN node_count > 100 THEN 'success|' ELSE 'failure|' END + toString(node_count) + ' nodes' AS result;

// Atom 4: Check invariants exist
MATCH (inv:Invariant)
WITH count(inv) AS inv_count
RETURN 'check-invariants|' + CASE WHEN inv_count > 0 THEN 'success|' ELSE 'info|' END + toString(inv_count) + ' invariants defined' AS result;

// Atom 5: Check embedding coverage
MATCH (n) WHERE n.embedding IS NOT NULL
WITH count(n) AS emb_count
MATCH (m) WHERE m.node_id IS NOT NULL
WITH emb_count, count(m) AS total
RETURN 'check-embeddings|success|' + toString(round(emb_count * 100.0 / total)) + '% embedding coverage' AS result;
