CREATE CONSTRAINT seedforth_delta_event_id IF NOT EXISTS FOR (n:DeltaEvent) REQUIRE n.node_id IS UNIQUE;
UNWIND [
 {scope:'seedforth-platform',node_id:'source-delta-provision-events',adapter:'delta-provision-events-v1',stream:'delta-provision-events-v1',path:'/opt/seedforth/shared/provision-events.jsonl'},
 {scope:'flowing-indian',node_id:'source-delta-project-events-flowing-indian',adapter:'delta-project-events-v1',stream:'delta-project-events-v1',path:'delta-config/logs/graph-events.jsonl'},
 {scope:'cajon-sensei',node_id:'source-delta-project-events-cajon-sensei',adapter:'delta-project-events-v1',stream:'delta-project-events-v1',path:'delta-config/logs/graph-events.jsonl'}
] AS item
MATCH (scope:ControlScope {node_id:item.scope})
MERGE (s:SourceStream {node_id:item.node_id})
ON CREATE SET s.scope_id=item.scope,s.adapter=item.adapter,s.stream=item.stream,s.path=item.path,
s.enabled=true,s.freshness_seconds=300,s.expected_interval_seconds=60,
s.authority='observed_delta_event_only',s.coverage='emitted_events_not_external_truth',
s.owner='seedforth-platform',s.trigger='periodic',s.schema_version=1,s.created_at=datetime()
MERGE (s)-[:OBSERVES_SCOPE]->(scope)
MERGE (p:Principal {node_id:'principal-delta-ingestor'})
ON CREATE SET p.enabled=true,p.kind='service',p.created_at=datetime()
MERGE (g:Grant {node_id:'grant-delta-ingestor-'+item.scope})
ON CREATE SET g.scope=item.scope,g.permissions=['read','source.observe'],g.revoked=false,
g.authority='owner-upgrade-delegation-20260906',g.created_at=datetime()
MERGE (p)-[:HAS_GRANT]->(g);
