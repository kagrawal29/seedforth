MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(g:Grant {scope:$scope,revoked:false})
WHERE 'source.observe' IN g.permissions AND (g.expires_at IS NULL OR g.expires_at>datetime())
WITH DISTINCT g.scope AS scope
MATCH (s:SourceStream {node_id:$source,scope_id:scope,path:$path,enabled:true,adapter:'local-git-file-hash-v1'})
WHERE $status IN ['collected','collection_failed']
AND datetime($observed_at)<=datetime()+duration('PT30S')
AND ($status='collection_failed' OR ($revision =~ '[a-f0-9]{40}'
AND ($committed_hash IS NULL OR $committed_hash =~ '[a-f0-9]{64}')
AND ($working_hash IS NULL OR $working_hash =~ '[a-f0-9]{64}')))
WITH s,scope,CASE WHEN $status='collection_failed' THEN 'collection_failed'
WHEN $committed_hash IS NULL AND $working_hash IS NULL THEN 'missing'
WHEN $committed_hash IS NULL THEN 'not_in_commit'
WHEN $working_hash IS NULL THEN 'missing_working_file'
WHEN $committed_hash=$working_hash THEN 'matches_commit' ELSE 'diverged_from_commit' END AS classification
MERGE (o:Observation {node_id:$event_id})
ON CREATE SET o.scope_id=scope,o.source_id=s.node_id,o.observed_at=datetime($observed_at),
o.received_at=datetime(),o.status=classification,o.committed_hash=$committed_hash,
o.working_hash=$working_hash,o.repository_revision=$revision,o.source_revision=$adapter_revision,
o.adapter=s.adapter,o.path=s.path,o.payload_hash=$payload_hash,
o.trust='deterministic_file_metadata',o.coverage='one_approved_path_not_repository',o.schema_version=1
WITH s,o WHERE o.scope_id=$scope AND o.source_id=$source AND o.payload_hash=$payload_hash
MERGE (o)-[:OBSERVED_STREAM]->(s)
SET s._lock=coalesce(s._lock,0)+1
FOREACH (_ IN CASE WHEN s.last_attempt_at IS NULL OR o.observed_at>s.last_attempt_at THEN [1] ELSE [] END |
SET s.last_attempt_at=o.observed_at,s.last_attempt_status=o.status,s.latest_attempt=o.node_id)
FOREACH (_ IN CASE WHEN o.status<>'collection_failed' AND (s.last_success_at IS NULL OR o.observed_at>s.last_success_at) THEN [1] ELSE [] END |
SET s.last_success_at=o.observed_at,s.code_status=o.status,s.committed_hash=o.committed_hash,
s.working_hash=o.working_hash,s.repository_revision=o.repository_revision,s.latest_observation=o.node_id,
s.reducer='record-code-observation-v1')
RETURN o.node_id AS id,o.status AS status,s.last_success_at AS last_success_at
