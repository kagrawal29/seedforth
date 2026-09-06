MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(g:Grant {scope:$scope,revoked:false})
WHERE 'source.observe' IN g.permissions AND (g.expires_at IS NULL OR g.expires_at>datetime())
WITH DISTINCT g.scope AS scope
MATCH (s:SourceStream {node_id:$source,scope_id:scope,enabled:true,adapter:'local-opencode-process-v1'})
WHERE $status IN ['running','stopped','conflicting','collection_failed']
AND datetime($observed_at)<=datetime()+duration('PT30S')
AND $process_count>=0 AND $process_count<=1000
MERGE (o:Observation {node_id:$event_id})
ON CREATE SET o.scope_id=scope,o.source_id=s.node_id,o.observed_at=datetime($observed_at),
o.received_at=datetime(),o.status=$status,o.process_count=$process_count,
o.source_revision=$revision,o.adapter=s.adapter,o.payload_hash=$payload_hash,
o.trust='deterministic_process_observation',o.coverage='exact_port_process_scan'
WITH s,o WHERE o.scope_id=$scope AND o.source_id=$source AND o.payload_hash=$payload_hash
MERGE (o)-[:OBSERVED_STREAM]->(s)
SET s._lock=coalesce(s._lock,0)+1
FOREACH (_ IN CASE WHEN s.last_attempt_at IS NULL OR o.observed_at>s.last_attempt_at THEN [1] ELSE [] END |
SET s.last_attempt_at=o.observed_at,s.last_attempt_status=o.status)
FOREACH (_ IN CASE WHEN o.status<>'collection_failed' AND (s.last_success_at IS NULL OR o.observed_at>s.last_success_at) THEN [1] ELSE [] END |
SET s.last_success_at=o.observed_at,s.process_status=o.status,s.process_count=o.process_count,s.latest_observation=o.node_id)
RETURN o.node_id AS id,o.status AS status,s.last_success_at AS last_success_at
