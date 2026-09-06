// Exact identities verified against the restored production snapshot.
// This sets owner-directed portfolio state, not inferred process health.
UNWIND [
  {id:'flowing-indian',project:'project-flowing-indian',name:'Flowing Indian'},
  {id:'cajon-sensei',project:'project-cajon-sensei',name:'Cajon Sensei'}
] AS pilot
MATCH (p:Project {node_id:pilot.project})
MERGE (s:ControlScope {node_id:pilot.id})
ON CREATE SET s.name=pilot.name,s.portfolio_state='active',s.work_enabled=false,
s.hold_reason='governed_execution_not_yet_promoted',s.created_at=datetime(),s.updated_at=datetime(),
s.direction_source='owner-session-2026-09-06',s.state_version=0
MERGE (s)-[:MAPS_PROJECT]->(p)
MERGE (d:Decision {node_id:'decision-upgrade-active-products-20260906'})
ON CREATE SET d.project='system',d.created_at=datetime(),d.status='accepted',
d.summary='Flowing Indian and Cajon Sensei are the active product priorities. Platform upgrade remains active. Other projects require archival assessment preserving services and history.',
d.authority='owner',d.source='owner-session-2026-09-06'
MERGE (d)-[:DIRECTS]->(s)
RETURN s.node_id AS scope,p.node_id AS project_id,s.work_enabled AS work_enabled;
