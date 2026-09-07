MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(g:Grant {scope:$scope,revoked:false})
WHERE 'source.observe' IN g.permissions AND (g.expires_at IS NULL OR g.expires_at>datetime())
WITH DISTINCT g.scope AS scope
MATCH (s:SourceStream {node_id:$source,scope_id:scope,enabled:true,adapter:'delta-provision-events-v1'})
WHERE $event_id =~ '[a-f0-9]{64}' AND $payload_hash =~ '[a-f0-9]{64}'
AND datetime($observed_at)<=datetime()+duration('PT30S')
MERGE (e:DeltaEvent:ProvisionEvent {node_id:$event_id})
ON CREATE SET e.scope_id=scope,e.source_id=s.node_id,e.project=$project,
e.event_type=$provision_type,e.observed_at=datetime($observed_at),e.received_at=datetime(),
e.payload_hash=$payload_hash,e.payload=$payload,e.role=$role,e.model=$model,
e.trust='delta_emitted_event',e.schema_version=1
MERGE (e)-[:FROM_STREAM]->(s)
RETURN e.node_id AS id,e.event_type AS event_type,e.observed_at AS observed_at
