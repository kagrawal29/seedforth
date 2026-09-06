// @node_id: protocol-wire-islands
// @label: "Wire Islands"
// Wire isolated islands: connect structurally disconnected nodes to semantic hubs
// Islands: CodeCypher (630), Query (969), NLQuery (16), HookMetric (25), Gap (11), Note (12), OperationalRule (12), Repository (6)
// Hub nodes: Ontology (ontology-mycelium), Subsystem (subsystem-mycelium-core)
// Strategy: MERGE typed edges idempotent, find natural join points via properties

// ============================================================================
// Query → Command: CACHED_BY relationship
// ============================================================================
// Join point: Query.last_command names a Command
MATCH (q:Query)
WHERE q.last_command IS NOT NULL AND NOT (q)-[:CACHED_BY]->(:Command)
MATCH (cmd:Command)
WHERE cmd.name = q.last_command
CREATE (q)-[r:CACHED_BY]->(cmd)
SET r.wired_at = timestamp(), r.by = 'wire-islands'
RETURN count(r) AS query_cached_by_edges;

// ============================================================================
// NLQuery → Ontology: LEGACY_OF relationship (legacy maverick-meta nodes)
// ============================================================================
MATCH (nlq:NLQuery)
WHERE NOT (nlq)-[:LEGACY_OF]->(:Ontology)
WITH collect(nlq) AS nlqs
MATCH (ont:Ontology {node_id: 'ontology-mycelium'})
WITH nlqs, ont
UNWIND nlqs AS nlq
CREATE (nlq)-[r:LEGACY_OF]->(ont)
SET r.label = nlq.label, r.wired_at = timestamp(), r.by = 'wire-islands'
RETURN count(r) AS nlquery_legacy_of_edges;

// ============================================================================
// HookMetric → Ontology: METRIC_FOR relationship
// ============================================================================
MATCH (hm:HookMetric)
WHERE NOT (hm)-[:METRIC_FOR]->(:Ontology)
WITH collect(hm) AS hms
MATCH (ont:Ontology {node_id: 'ontology-mycelium'})
WITH hms, ont
UNWIND hms AS hm
CREATE (hm)-[r:METRIC_FOR]->(ont)
SET r.hook_name = hm.hook_name, r.wired_at = timestamp(), r.by = 'wire-islands'
RETURN count(r) AS hookmetric_metric_for_edges;

// ============================================================================
// Gap → Ontology: TRACKS relationship
// ============================================================================
MATCH (g:Gap)
WHERE NOT (g)-[:TRACKS]->(:Ontology)
WITH collect(g) AS gaps
MATCH (ont:Ontology {node_id: 'ontology-mycelium'})
WITH gaps, ont
UNWIND gaps AS g
CREATE (g)-[r:TRACKS]->(ont)
SET r.zone = g.zone, r.wired_at = timestamp(), r.by = 'wire-islands'
RETURN count(r) AS gap_tracks_edges;

// ============================================================================
// Note → Ontology: DOCUMENTED_IN relationship
// ============================================================================
MATCH (n:Note)
WHERE NOT (n)-[:DOCUMENTED_IN]->(:Ontology)
WITH collect(n) AS notes
MATCH (ont:Ontology {node_id: 'ontology-mycelium'})
WITH notes, ont
UNWIND notes AS n
CREATE (n)-[r:DOCUMENTED_IN]->(ont)
SET r.source = n.source, r.wired_at = timestamp(), r.by = 'wire-islands'
RETURN count(r) AS note_documented_in_edges;

// ============================================================================
// OperationalRule → Ontology: ENFORCED_BY relationship
// ============================================================================
MATCH (or:OperationalRule)
WHERE NOT (or)-[:ENFORCED_BY]->(:Ontology)
WITH collect(or) AS ors
MATCH (ont:Ontology {node_id: 'ontology-mycelium'})
WITH ors, ont
UNWIND ors AS or
CREATE (or)-[r:ENFORCED_BY]->(ont)
SET r.rule_name = or.name, r.wired_at = timestamp(), r.by = 'wire-islands'
RETURN count(r) AS operationalrule_enforced_by_edges;

// ============================================================================
// Repository → Subsystem: HOUSED_IN relationship
// ============================================================================
// Join point: Repository.domain → Subsystem; exact domain match
MATCH (repo:Repository)
WHERE repo.domain IS NOT NULL AND NOT (repo)-[:HOUSED_IN]->(:Subsystem)
MATCH (sub:Subsystem)
WHERE sub.domain = repo.domain OR sub.name CONTAINS repo.domain
CREATE (repo)-[r:HOUSED_IN]->(sub)
SET r.wired_at = timestamp(), r.by = 'wire-islands'
RETURN count(r) AS repository_housed_in_edges;

// ============================================================================
// Repository → Subsystem: fallback to primary if domain not found
// ============================================================================
MATCH (repo:Repository)
WHERE repo.domain IS NULL OR NOT (repo)-[:HOUSED_IN]->(:Subsystem)
MATCH (sub:Subsystem {node_id: 'subsystem-mycelium-core'})
WHERE NOT (repo)-[:HOUSED_IN]->(sub)
CREATE (repo)-[r:HOUSED_IN]->(sub)
SET r.wired_at = timestamp(), r.by = 'wire-islands'
RETURN count(r) AS repository_housed_in_fallback_edges;

// ============================================================================
// Summary: report islands wired, verify remaining disconnected nodes
// ============================================================================
MATCH (n:Query)
WHERE NOT (n)-[:CACHED_BY]->(:Command)
WITH 'Query' AS label, 969 AS expected, count(n) AS still_disconnected
RETURN label, expected, still_disconnected
UNION
MATCH (n:NLQuery)
WHERE NOT (n)-[:LEGACY_OF]->(:Ontology)
WITH 'NLQuery' AS label, 16 AS expected, count(n) AS still_disconnected
RETURN label, expected, still_disconnected
UNION
MATCH (n:HookMetric)
WHERE NOT (n)-[:METRIC_FOR]->(:Ontology)
WITH 'HookMetric' AS label, 25 AS expected, count(n) AS still_disconnected
RETURN label, expected, still_disconnected
UNION
MATCH (n:Gap)
WHERE NOT (n)-[:TRACKS]->(:Ontology)
WITH 'Gap' AS label, 11 AS expected, count(n) AS still_disconnected
RETURN label, expected, still_disconnected
UNION
MATCH (n:Note)
WHERE NOT (n)-[:DOCUMENTED_IN]->(:Ontology)
WITH 'Note' AS label, 12 AS expected, count(n) AS still_disconnected
RETURN label, expected, still_disconnected
UNION
MATCH (n:OperationalRule)
WHERE NOT (n)-[:ENFORCED_BY]->(:Ontology)
WITH 'OperationalRule' AS label, 12 AS expected, count(n) AS still_disconnected
RETURN label, expected, still_disconnected
UNION
MATCH (n:Repository)
WHERE NOT (n)-[:HOUSED_IN]->(:Subsystem)
WITH 'Repository' AS label, 6 AS expected, count(n) AS still_disconnected
RETURN label, expected, still_disconnected;
