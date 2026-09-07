// Project systemd unit health into the platform source stream.
MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(g:Grant {scope:$scope,revoked:false})
WHERE 'source.observe' IN g.permissions AND (g.expires_at IS NULL OR g.expires_at>datetime())
WITH DISTINCT g.scope AS scope
MATCH (s:SourceStream {node_id:$source,scope_id:scope,enabled:true,adapter:'systemd-unit-health-v1',unit:$unit})
WHERE $status IN ['success','failed','collection_failed']
  AND datetime($observed_at)<=datetime()+duration('PT30S')
  AND size($unit)>=1 AND size($unit)<=256
  AND size($active_state)<=64 AND size($sub_state)<=64 AND size($result)<=64
  AND $exec_main_status =~ '[0-9]{1,9}'
  AND size($exit_timestamp)<=256
MERGE (o:Observation {node_id:$event_id})
ON CREATE SET o.scope_id=scope,o.source_id=s.node_id,o.observed_at=datetime($observed_at),
o.received_at=datetime(),o.status=$status,o.unit=$unit,o.active_state=$active_state,
o.sub_state=$sub_state,o.result=$result,o.exec_main_status=toInteger($exec_main_status),
o.exit_timestamp=$exit_timestamp,o.source_revision=$adapter_revision,o.adapter=s.adapter,
o.payload_hash=$payload_hash,o.trust='deterministic_systemd_observation',
o.coverage='allowlisted_unit_status',o.schema_version=1
WITH s,o WHERE o.scope_id=$scope AND o.source_id=$source AND o.payload_hash=$payload_hash
MERGE (o)-[:OBSERVED_STREAM]->(s)
SET s._lock=coalesce(s._lock,0)+1
FOREACH (_ IN CASE WHEN s.last_attempt_at IS NULL OR o.observed_at>s.last_attempt_at THEN [1] ELSE [] END |
  SET s.last_attempt_at=o.observed_at,s.last_attempt_status=o.status,s.latest_attempt=o.node_id)
FOREACH (_ IN CASE WHEN o.status='success' AND (s.last_success_at IS NULL OR o.observed_at>s.last_success_at) THEN [1] ELSE [] END |
  SET s.last_success_at=o.observed_at,s.unit_status=o.result,s.unit_exit_status=o.exec_main_status,
      s.latest_observation=o.node_id)
RETURN o.node_id AS id,o.status AS status,s.last_success_at AS last_success_at
