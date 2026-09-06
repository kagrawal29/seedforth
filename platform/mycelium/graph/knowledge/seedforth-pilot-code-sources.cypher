CREATE CONSTRAINT seedforth_source_stream_id IF NOT EXISTS FOR (n:SourceStream) REQUIRE n.node_id IS UNIQUE;
UNWIND [{scope:'cajon-sensei',path:'app/index.html',key:'app-index'},
{scope:'flowing-indian',path:'app/api/order/route.ts',key:'order-route'},
{scope:'flowing-indian',path:'app/api/verify/route.ts',key:'verify-route'}] AS pilot
MATCH (scope:ControlScope {node_id:pilot.scope})
MERGE (s:SourceStream {node_id:'source-code-'+pilot.scope+'-'+pilot.key})
ON CREATE SET s.scope_id=pilot.scope,s.adapter='local-git-file-hash-v1',s.path=pilot.path,
s.enabled=true,s.freshness_seconds=900,s.expected_interval_seconds=300,
s.authority='observed_selected_file_metadata_only',s.coverage='one_approved_path_not_repository',
s.owner='seedforth-platform',s.trigger='periodic',s.schema_version=1,s.created_at=datetime(),
s.consumer='control-board',s.retry='next_cadence_no_repair',s.retention='pending_policy_no_automatic_deletion'
MERGE (s)-[:OBSERVES_SCOPE]->(scope)
MERGE (p:Principal {node_id:'principal-code-sensor'})
ON CREATE SET p.enabled=true,p.kind='service',p.created_at=datetime()
MERGE (g:Grant {node_id:'grant-code-sensor-'+pilot.scope})
ON CREATE SET g.scope=pilot.scope,g.permissions=['read','source.observe'],g.revoked=false,
g.authority='owner-upgrade-delegation-20260906',g.created_at=datetime()
MERGE (p)-[:HAS_GRANT]->(g);
