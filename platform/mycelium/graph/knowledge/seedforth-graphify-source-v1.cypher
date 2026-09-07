CREATE CONSTRAINT seedforth_graphify_fact_id IF NOT EXISTS FOR (n:GraphifyFact) REQUIRE n.node_id IS UNIQUE;
UNWIND ['seedforth-platform','flowing-indian','cajon-sensei'] AS scope_id
MATCH (scope:ControlScope {node_id:scope_id})
MERGE (s:SourceStream {node_id:'source-graphify-'+scope_id})
ON CREATE SET s.scope_id=scope_id,s.adapter='graphify-snapshot-v1',s.stream='graphify-snapshot-v1',
s.enabled=true,s.freshness_seconds=3600,s.expected_interval_seconds=900,
s.authority='observed_extraction_only',s.coverage='selected_graphify_documents',
s.owner='seedforth-platform',s.trigger='periodic',s.schema_version=1,s.created_at=datetime()
MERGE (s)-[:OBSERVES_SCOPE]->(scope)
MERGE (p:Principal {node_id:'principal-graphify-sensor'})
ON CREATE SET p.enabled=true,p.kind='service',p.created_at=datetime()
MERGE (g:Grant {node_id:'grant-graphify-sensor-'+scope_id})
ON CREATE SET g.scope=scope_id,g.permissions=['read','source.observe'],g.revoked=false,
g.authority='owner-upgrade-delegation-20260906',g.created_at=datetime()
MERGE (p)-[:HAS_GRANT]->(g);
