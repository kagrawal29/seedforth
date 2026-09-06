// Phase 4 — FocusCursor: the graph records what Charlie is focused on each cycle.
// Populated from DirectionScore (stalled -> high priority) + active workstreams.

MERGE (a:CypherAtom {node_id: 'atom-focus-cursor'})
SET a.semantic = 'Charlie writes focus: clear stale FocusCursor and set current focus from stalled projects and active workstreams',
    a.cypher = 'MATCH (fc:FocusCursor) WHERE fc.updated_at < datetime() - duration({days: 2}) DETACH DELETE fc; MATCH (c:Being {node_id: "being-charlie"})-[:DRIVES]->(p:Project) OPTIONAL MATCH (ds:DirectionScore {project: p.name}) WITH p, coalesce(ds.direction_label, "unknown") AS state MERGE (fc:FocusCursor {node_id: "focus-" + p.name}) SET fc.project = p.name, fc.state = state, fc.priority = CASE WHEN state IN ["stalled","declining"] THEN "high" WHEN state = "developing" THEN "medium" ELSE "low" END, fc.focus = CASE WHEN state = "stalled" THEN "unstall and move " + p.name + " forward" WHEN state = "developing" THEN "keep momentum on " + p.name ELSE "watch " + p.name END, fc.updated_at = datetime() RETURN fc.project, fc.priority, fc.focus ORDER BY fc.priority';

MERGE (pr:Protocol {node_id: 'protocol-charlie-focus'})
SET pr.label = 'Charlie Focus', pr.cadence = 'heartbeat', pr.enabled = true;

MATCH (pr:Protocol {node_id: 'protocol-charlie-focus'})
MATCH (a:CypherAtom {node_id: 'atom-focus-cursor'})
MERGE (pr)-[:FIRST_ATOM]->(a);

MATCH (c:Being {node_id: 'being-charlie'})
MATCH (pr:Protocol {node_id: 'protocol-charlie-focus'})
MERGE (c)-[:HAS_PROTOCOL]->(pr);
