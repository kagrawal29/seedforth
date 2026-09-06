// Charlie founder loop — graph-native (2026-08-20)
// Briefing + focus atoms (LLM-discoverable via semantic), plus a founder Protocol
// that chains the grounding atoms + briefing + focus, run by graph-runner on cadence.

// ---- Briefing atom: dream + current state + workstreams for what Charlie drives
MERGE (a:CypherAtom {node_id: 'atom-charlie-briefing'})
SET a.semantic = 'Charlie articulates the full picture for every project he drives: dream (north_star), current state (direction score), milestones, open action items, blockers',
    a.cypher = 'MATCH (c:Being {node_id: "being-charlie"})-[:DRIVES]->(p:Project) OPTIONAL MATCH (m:EntityMandate {project: p.name}) OPTIONAL MATCH (ds:DirectionScore {project: p.name}) OPTIONAL MATCH (mil:Milestone {project: p.name}) OPTIONAL MATCH (ap:ActionProposal {project: p.name}) WHERE ap.status IS NULL OR ap.status <> "resolved" OPTIONAL MATCH (b:Blocker {project: p.name}) WHERE b.status = "open" OR b.status IS NULL RETURN p.name AS project, m.north_star AS dream, ds.direction_label AS state, ds.direction_score AS score, collect(DISTINCT mil.title) AS milestones, collect(DISTINCT ap.description) AS open_items, collect(DISTINCT b.description) AS blockers ORDER BY p.name';

// ---- Focus atom: the highest-priority work right now
MERGE (a:CypherAtom {node_id: 'atom-charlie-focus'})
SET a.semantic = 'Charlie decides focus: which projects are stalled or have active/pending milestones needing attention',
    a.cypher = 'MATCH (c:Being {node_id: "being-charlie"})-[:DRIVES]->(p:Project) OPTIONAL MATCH (ds:DirectionScore {project: p.name}) OPTIONAL MATCH (mil:Milestone {project: p.name}) WHERE mil.status = "active" OR mil.status = "pending" RETURN p.name AS project, ds.direction_label AS state, ds.direction_score AS score, collect(DISTINCT mil.title) AS active_milestones, collect(DISTINCT mil.due) AS dues ORDER BY coalesce(ds.direction_score, 0)';

// ---- Founder protocol: grounding -> briefing -> focus (heartbeat cadence)
MERGE (pr:Protocol {node_id: 'protocol-charlie-founder'})
SET pr.label = 'Charlie Founder Loop', pr.cadence = 'heartbeat', pr.enabled = true;

MATCH (pr:Protocol {node_id: 'protocol-charlie-founder'})
MATCH (a1:CypherAtom {node_id: 'atom-charlie-identity'})
MATCH (a2:CypherAtom {node_id: 'atom-charlie-alignments'})
MATCH (a3:CypherAtom {node_id: 'atom-charlie-drive'})
MATCH (a4:CypherAtom {node_id: 'atom-charlie-briefing'})
MATCH (a5:CypherAtom {node_id: 'atom-charlie-focus'})
MERGE (pr)-[:FIRST_ATOM]->(a1)
MERGE (a1)-[:FOLLOWS]->(a2)
MERGE (a2)-[:FOLLOWS]->(a3)
MERGE (a3)-[:FOLLOWS]->(a4)
MERGE (a4)-[:FOLLOWS]->(a5);

// ---- Tie it to being-charlie
MATCH (c:Being {node_id: 'being-charlie'})
MATCH (pr:Protocol {node_id: 'protocol-charlie-founder'})
MERGE (c)-[:HAS_PROTOCOL]->(pr);
