CREATE CONSTRAINT seedforth_source_stream_id IF NOT EXISTS FOR (n:SourceStream) REQUIRE n.node_id IS UNIQUE;
UNWIND [{scope:'flowing-indian',port:7745},{scope:'cajon-sensei',port:7724}] AS pilot
MATCH (scope:ControlScope {node_id:pilot.scope})
MERGE (s:SourceStream {node_id:'source-runtime-'+pilot.scope})
ON CREATE SET s.scope_id=pilot.scope,s.adapter='local-opencode-process-v1',s.port=pilot.port,
s.enabled=true,s.freshness_seconds=180,s.expected_interval_seconds=60,
s.authority='observed_process_only',s.owner='seedforth-platform',s.created_at=datetime()
MERGE (s)-[:OBSERVES_SCOPE]->(scope)
MERGE (p:Principal {node_id:'principal-runtime-sensor'})
ON CREATE SET p.enabled=true,p.kind='service',p.created_at=datetime()
MERGE (g:Grant {node_id:'grant-runtime-sensor-'+pilot.scope})
ON CREATE SET g.scope=pilot.scope,g.permissions=['read','source.observe'],g.revoked=false,
g.authority='owner-upgrade-delegation-20260906',g.created_at=datetime()
MERGE (p)-[:HAS_GRANT]->(g);
