// Phase 2 — watcher: sync agent activity (SessionTrace/QueryTrace) into project state.
// Runs on heartbeat. Keeps the graph's belief about a project fresh from real activity.

MERGE (a:CypherAtom {node_id: 'atom-activity-sync'})
SET a.semantic = 'Sync agent activity traces into project state: refresh last_activity and activity score from recent exchanges',
    a.cypher = 'MATCH (st:SessionTrace) WHERE st.created_at > datetime() - duration({hours: 24}) WITH st.project AS proj, count(st) AS exchanges MATCH (p:Project {node_id: "project-" + proj}) SET p.last_activity = coalesce(p.last_activity, datetime()), p.activity_24h = exchanges RETURN proj, exchanges ORDER BY exchanges DESC';

MERGE (pr:Protocol {node_id: 'protocol-activity-sync'})
SET pr.label = 'Activity sync', pr.cadence = 'heartbeat', pr.enabled = true;

MATCH (pr:Protocol {node_id: 'protocol-activity-sync'})
MATCH (a:CypherAtom {node_id: 'atom-activity-sync'})
MERGE (pr)-[:FIRST_ATOM]->(a);
