// @kind: seed
// ============================================================================
// Protocol: Reports Seed
// ============================================================================
// Seeds :Report nodes — templatized on-demand dashboards. Each report has
// a cypher query that generates its data. `mycelium report <name>` runs
// the query and prints the output as a markdown table.
//
// The reports are also a way to make the graph thinkable: every report
// is a lens that surfaces one aspect of topology, ontology, chain state,
// federation state, or cognition history. Users see what's missing,
// what's hot, what's drifting. A report is just another :Protocol that
// outputs to stdout — nothing special about it.
//
// Idempotent: MERGE on report node_id.
// ============================================================================


// --- Report 1: missing-links — nodes with low structural degree ------------
MERGE (r:Report {node_id: 'report-missing-links'})
SET r.name = 'missing-links',
    r.title = 'Missing Links — Orphan and leaf nodes by type',
    r.description = 'Nodes with 0-1 structural edges (excluding INFERRED_SIMILAR). High counts mean a node type was bulk-ingested without topology investment. Fix: run promote-refs-to-edges or add structural edges explicitly.',
    r.order = 1,
    r.category = 'topology',
    r.cypher = "MATCH (n) WHERE n.node_id IS NOT NULL AND NOT n:QueryTrace CALL { WITH n MATCH (n)-[r]-(x) WHERE type(r) <> 'INFERRED_SIMILAR' RETURN count(DISTINCT r) AS d UNION WITH n RETURN 0 AS d } WITH labels(n)[0] AS type, sum(d) AS degree WITH type, count(*) AS n, sum(CASE WHEN degree = 0 THEN 1 ELSE 0 END) AS orphans, sum(CASE WHEN degree <= 1 THEN 1 ELSE 0 END) AS lonely WHERE orphans > 0 OR lonely > n * 0.5 RETURN type, n, orphans, lonely ORDER BY orphans DESC LIMIT 20",
    r.columns = ['type', 'total', 'orphans', 'lonely'],
    r.file_type = 'report';


// --- Report 2: chain — the current species chain and its state -------------
MERGE (r:Report {node_id: 'report-chain'})
SET r.name = 'chain',
    r.title = 'Species Chain — Current and recent states',
    r.description = 'The current canonical chain head and the most recent species, with their signatures and parent links.',
    r.order = 2,
    r.category = 'chain',
    r.cypher = "MATCH (s:Species) WHERE s.algorithm = 'phase-b-v1' OPTIONAL MATCH (s)-[:DESCENDED_FROM]->(parent:Species) OPTIONAL MATCH (ws:WitnessSignature)-[:SIGNS]->(s) WITH s, parent.node_id AS parent_id, count(ws) AS sig_count RETURN s.node_id AS species, coalesce(s.canonical, false) AS canonical, coalesce(s.signed, false) AS signed, substring(s.manifest_root, 0, 16) AS root, parent_id AS parent, sig_count AS signatures ORDER BY s.minted_at DESC LIMIT 10",
    r.columns = ['species', 'canonical', 'signed', 'root', 'parent', 'signatures'],
    r.file_type = 'report';


// --- Report 3: health — invariants + tests summary -------------------------
MERGE (r:Report {node_id: 'report-health'})
SET r.name = 'health',
    r.title = 'Health — Invariants and tests aggregate',
    r.description = 'What is currently healthy, what is deferred, what is failing. Sources of truth for whether the graph is safe to mutate.',
    r.order = 3,
    r.category = 'health',
    r.cypher = "MATCH (i:Invariant) WITH count(i) AS total_inv, sum(CASE WHEN coalesce(i.enabled, true) THEN 1 ELSE 0 END) AS active_inv, sum(CASE WHEN coalesce(i.enabled, true) AND i.health = 'healthy' THEN 1 ELSE 0 END) AS healthy_inv MATCH (t:TestCase) WITH total_inv, active_inv, healthy_inv, count(t) AS total_tests, sum(CASE WHEN coalesce(t.enabled, true) THEN 1 ELSE 0 END) AS active_tests, sum(CASE WHEN coalesce(t.enabled, true) AND t.last_result = 'pass' THEN 1 ELSE 0 END) AS passing_tests RETURN toString(healthy_inv) + '/' + toString(active_inv) AS invariants_healthy, toString(total_inv - active_inv) AS invariants_deferred, toString(passing_tests) + '/' + toString(active_tests) AS tests_passing, toString(total_tests - active_tests) AS tests_deferred",
    r.columns = ['invariants_healthy', 'invariants_deferred', 'tests_passing', 'tests_deferred'],
    r.file_type = 'report';


// --- Report 4: deferrals — what is parked and why --------------------------
MERGE (r:Report {node_id: 'report-deferrals'})
SET r.name = 'deferrals',
    r.title = 'Deferrals — Tests and invariants parked with reasons',
    r.description = 'Grouped by deferred_reason so you can see where the graphs technical debt is concentrated.',
    r.order = 4,
    r.category = 'health',
    r.cypher = "MATCH (n) WHERE (n:TestCase OR n:Invariant) AND coalesce(n.enabled, true) = false RETURN coalesce(n.deferred_reason, 'no-reason') AS reason, labels(n)[0] AS type, count(n) AS n ORDER BY n DESC",
    r.columns = ['reason', 'type', 'n'],
    r.file_type = 'report';


// --- Report 5: federation — sources, imports, adoptions --------------------
MERGE (r:Report {node_id: 'report-federation'})
SET r.name = 'federation',
    r.title = 'Federation — Sources and imported nodes',
    r.description = 'External graphs registered as Sources and the nodes they have contributed, grouped by provenance + adoption state.',
    r.order = 5,
    r.category = 'federation',
    r.cypher = "MATCH (s:Source) OPTIONAL MATCH (n {provenance: s.alias}) WITH s, count(n) AS total_nodes, sum(CASE WHEN n:Imported THEN 1 ELSE 0 END) AS imported_nodes, sum(CASE WHEN n:Adopted THEN 1 ELSE 0 END) AS adopted_nodes RETURN s.alias AS source, total_nodes, imported_nodes, adopted_nodes, substring(coalesce(s.public_key, 'none'), 0, 16) + '...' AS pubkey ORDER BY total_nodes DESC",
    r.columns = ['source', 'total_nodes', 'imported_nodes', 'adopted_nodes', 'pubkey'],
    r.file_type = 'report';


// --- Report 6: hottest — top fire_count atoms and queries ------------------
MERGE (r:Report {node_id: 'report-hottest'})
SET r.name = 'hottest',
    r.title = 'Hottest Paths — Most-fired atoms and queries',
    r.description = 'What the graph has been used for most. High fire_count = hot path = candidate for optimization/caching/strengthening.',
    r.order = 6,
    r.category = 'cognition',
    r.cypher = "MATCH (a:CypherAtom) WHERE coalesce(a.fire_count, 0) > 0 RETURN 'atom' AS kind, a.node_id AS id, a.fire_count AS fire_count, substring(coalesce(a.semantic, ''), 0, 60) AS detail ORDER BY a.fire_count DESC LIMIT 10 UNION MATCH (q:Query) WHERE coalesce(q.fire_count, 0) > 0 RETURN 'query' AS kind, q.node_id AS id, q.fire_count AS fire_count, substring(coalesce(q.last_command, ''), 0, 60) AS detail ORDER BY q.fire_count DESC LIMIT 10",
    r.columns = ['kind', 'id', 'fire_count', 'detail'],
    r.file_type = 'report';


// --- Report 7: ontology — label and edge type distribution -----------------
MERGE (r:Report {node_id: 'report-ontology'})
SET r.name = 'ontology',
    r.title = 'Ontology — Labels, edge types, and their weights',
    r.description = 'The shape of the graph — which labels exist, how many nodes per label, and which edge types connect them. Use this to spot schema drift or over-concentration.',
    r.order = 7,
    r.category = 'topology',
    r.cypher = "MATCH (n) WHERE n.node_id IS NOT NULL WITH labels(n)[0] AS label, count(n) AS n RETURN label, n ORDER BY n DESC LIMIT 30",
    r.columns = ['label', 'n'],
    r.file_type = 'report';


RETURN count(*) AS reports_seeded;
