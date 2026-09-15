CREATE CONSTRAINT seedforth_source_stream_id IF NOT EXISTS FOR (n:SourceStream) REQUIRE n.node_id IS UNIQUE;
UNWIND [
 {scope:'flowing-indian',project:'project-flowing-indian',port:7745},
 {scope:'cajon-sensei',project:'project-cajon-sensei',port:7724},
 {scope:'ethos',project:'project-ethos',port:7744},
 {scope:'linkedin-himanshu-ghiya',project:'project-linkedin-himanshu-ghiya',port:7730},
 {scope:'linkedin-kshitiz-agarwal',project:'project-linkedin-kshitiz-agarwal',port:7731},
 {scope:'seedforthing',project:'project-seedforthing',port:7740},
 {scope:'zuuro',project:'project-zuuro',port:7743}
] AS pilot
MATCH (project:Project {node_id:pilot.project})
MERGE (scope:ControlScope {node_id:pilot.scope})
ON CREATE SET scope.name=pilot.scope,scope.portfolio_state=CASE WHEN pilot.scope IN ['flowing-indian','cajon-sensei'] THEN 'active' ELSE 'archived' END,
scope.work_enabled=false,scope.new_work=CASE WHEN pilot.scope IN ['flowing-indian','cajon-sensei'] THEN 'held' ELSE 'disabled' END,
scope.created_at=datetime(),scope.updated_at=datetime(),scope.state_version=0
MERGE (scope)-[:MAPS_PROJECT]->(project)
MERGE (s:SourceStream {node_id:'source-runtime-'+pilot.scope})
ON CREATE SET s.scope_id=pilot.scope,s.adapter='local-opencode-process-v1',s.port=pilot.port,
s.enabled=true,s.freshness_seconds=180,s.expected_interval_seconds=60,
s.authority='observed_process_only',s.owner='seedforth-platform',s.created_at=datetime()
MERGE (s)-[:OBSERVES_SCOPE]->(scope)
MERGE (sensor:Principal {node_id:'principal-runtime-sensor'})
ON CREATE SET sensor.enabled=true,sensor.kind='service',sensor.created_at=datetime()
MERGE (g:Grant {node_id:'grant-runtime-sensor-'+pilot.scope})
ON CREATE SET g.scope=pilot.scope,g.permissions=['read','source.observe'],g.revoked=false,
g.authority='owner-upgrade-delegation-20260906',g.created_at=datetime()
MERGE (sensor)-[:HAS_GRANT]->(g);
