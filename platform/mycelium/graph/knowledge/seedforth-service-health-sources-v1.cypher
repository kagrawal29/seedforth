// The service sensor observes outcomes of the control loop, not product state.
UNWIND [
 {id:'seedforth-worker', unit:'seedforth-worker.service'},
 {id:'seedforth-control', unit:'seedforth-control.service'},
 {id:'seedforth-identity', unit:'seedforth-identity.service'},
 {id:'seedforth-delta', unit:'seedforth-delta.service'},
 {id:'seedforth-conversation-processor', unit:'seedforth-conversation-processor.service'},
 {id:'seedforth-delta-event-ingest', unit:'seedforth-delta-event-ingest.service'},
 {id:'seedforth-delta-ack-ingest', unit:'seedforth-delta-ack-ingest.service'},
 {id:'seedforth-graphify-sensor', unit:'seedforth-graphify-sensor.service'},
 {id:'seedforth-code-sensor', unit:'seedforth-code-sensor.service'},
 {id:'seedforth-runtime-sensor', unit:'seedforth-runtime-sensor.service'},
 {id:'seedforth-mycelium-heartbeat', unit:'seedforth-mycelium-heartbeat.service'}
] AS item
MATCH (scope:ControlScope {node_id:'seedforth-platform'})
MERGE (s:SourceStream {node_id:'source-service-'+item.id})
ON CREATE SET s.scope_id='seedforth-platform',s.adapter='systemd-unit-health-v1',s.unit=item.unit,
 s.enabled=true,s.freshness_seconds=300,s.expected_interval_seconds=60,
 s.authority='deterministic_systemd_unit_status',s.coverage='allowlisted_unit_status',
 s.owner='seedforth-platform',s.trigger='periodic',s.schema_version=1,s.created_at=datetime()
SET s.unit=item.unit,s.enabled=true
MERGE (s)-[:OBSERVES_SCOPE]->(scope)
MERGE (p:Principal {node_id:'principal-service-sensor'})
ON CREATE SET p.enabled=true,p.kind='service',p.created_at=datetime()
MERGE (g:Grant {node_id:'grant-service-sensor-platform'})
ON CREATE SET g.scope='seedforth-platform',g.permissions=['read','source.observe'],g.revoked=false,
 g.authority='owner-upgrade-delegation-20260906',g.created_at=datetime()
MERGE (p)-[:HAS_GRANT]->(g)
